#!/usr/bin/env python3
"""DX2 .ibd texture / MatLib reader, DDS/PNG extractor and offline contact sheet.

Standard library only. Read-only and compatible with personal Maps.zip / .ibd.
Formats: DXT1/DXT3/DXT5 and A8R8G8B8. Texture mip data is never rewritten.

Commands:
  python dx2textures.py stats Maps.zip
  python dx2textures.py export Maps.zip --name greaselgaka03 -o extracted
  python dx2textures.py gallery Maps.zip -o output/DX2_Texture_Gallery.html
  python dx2textures.py materials Maps.zip -o output/materials.json
"""
from __future__ import annotations
import argparse
import base64
from collections import Counter
from dataclasses import dataclass
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
import struct
import zlib
from typing import Optional, List
from dx2bundles import load_bundles, Parts

PIXEL_FORMATS={21:'BGRA8',22:'BGRX8'}
USAGE={0:'diffuse',1:'normal',2:'specular',3:'mask',4:'detail',5:'emissive',6:'environment'}

@dataclass
class Texture:
    name:str
    fmt:str
    width:int
    height:int
    usage:int
    mipmaps:list[tuple[int,int,bytes]]
    source:str
    detail:int=0
    faces:Optional[List[List[bytes]]]=None   # 6 faces per mip for a cubemap


def parse_texture(bundle,res):
    if res.typ!=8:raise ValueError('Not a texture')
    p=Parts(bundle.parts(res))
    version=p.take(1)[0]
    if version!=1:raise ValueError(f'{res.name}: unsupported texture version {version}')
    code=p.take(4)
    fmt=code.decode('ascii') if code in (b'DXT1',b'DXT3',b'DXT5') else PIXEL_FORMATS.get(struct.unpack('<I',code)[0])
    if fmt is None:raise ValueError(f'{res.name}: unknown pixel format {code.hex()}')
    nm=p.u32();usage=p.u32();detail=p.u32();w=p.u32();h=p.u32();w2=p.u32();h2=p.u32();total=p.u32()
    cubemap=usage==6 and w2==0 and h2==0
    p.take(1);p.take(1)
    if not (1<=nm<=16 and 1<=w<=8192 and 1<=h<=8192):raise ValueError('Invalid dimensions or mip count')
    mips=[];faces=[]
    for i in range(nm):
        level,mw,mh,size=p.u32(),p.u32(),p.u32(),p.u32()
        # Nine-byte pad appears in both Ion Storm games. Content is alignment metadata.
        pad=p.take(len(p.parts[p.pos]))
        if len(pad)>128:raise ValueError('Oversized mip prefix')
        raw=p.take(size)
        if level!=i or (mw,mh)!=(max(1,w>>i),max(1,h>>i)):
            raise ValueError(f'{res.name}: invalid mip chain')
        expected=mip_size(fmt,mw,mh)
        if size!=expected:raise ValueError(f'{res.name}: mip {i} is {size}, expected {expected}')
        mips.append((mw,mh,raw))
        if cubemap:
            side_data=[raw]
            for side in range(5):
                repeated_size=p.u32()
                face_pad=p.take(len(p.parts[p.pos]))
                if repeated_size!=size or len(face_pad)>128:raise ValueError('Invalid cubemap face metadata')
                side_data.append(p.take(size))
            faces.append(side_data)
    p.end()
    if total!=sum(len(data) for _,_,data in mips):raise ValueError(f'{res.name}: total byte count mismatch')
    return Texture(res.name,fmt,w,h,usage,mips,bundle.name,detail,faces if cubemap else None)


def parse_material(bundle,res):
    """Reads observed DX2 40-part MatLib layout, retaining stage references."""
    if res.typ!=10:raise ValueError('Not a material')
    p=Parts(bundle.parts(res))
    version=p.take(1)[0];flags=p.u32();mask=p.u32()
    colors=[list(struct.unpack('<4f',p.take(16))) for _ in range(3)]
    floats=[struct.unpack('<f',p.take(4))[0] for _ in range(3)]
    p.take(1);p.u32();p.u32();p.take(1);p.take(1);p.take(1);p.u32();p.take(4)
    source=p.string();category=p.u32();p.take(1);p.u32()
    stages=[p.string() for _ in range(9)]
    p.end()
    if not all(math.isfinite(x) for color in colors for x in color):raise ValueError('Bad material colors')
    return {'name':res.name,'source_bundle':bundle.name,'version':version,'flags':flags,
            'stage_mask':mask,'category_id':category,'source':source,
            'colors':colors,'params':floats,'stages':stages,
            'diffuse':stages[0] or None}


def mip_size(fmt,w,h):
    if fmt=='DXT1':return ((w+3)//4)*((h+3)//4)*8
    if fmt in ('DXT3','DXT5'):return ((w+3)//4)*((h+3)//4)*16
    if fmt in ('BGRA8','BGRX8'):return w*h*4
    raise ValueError(fmt)


def _rgb565(v):
    return (((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31)


def _palette(colorblock,transparent):
    c0,c1,mask=struct.unpack_from('<HHI',colorblock)
    p0=_rgb565(c0);p1=_rgb565(c1)
    if c0>c1 or not transparent:
        p2=tuple((2*a+b)//3 for a,b in zip(p0,p1));p3=tuple((a+2*b)//3 for a,b in zip(p0,p1))
        colors=[(*p0,255),(*p1,255),(*p2,255),(*p3,255)]
    else:
        colors=[(*p0,255),(*p1,255),(*(tuple((a+b)//2 for a,b in zip(p0,p1))),255),(0,0,0,0)]
    return [colors[(mask>>(2*i))&3] for i in range(16)]


def rgba_pixels(tex,face=0):
    """Decode the first mip into RGBA8, without optional third-party packages.

    Bulk strided copies handle uncompressed BGRA; compressed DXT blocks are
    assembled one scanline at a time. Neither path changes source textures.
    """
    w,h,raw=tex.mipmaps[0]
    if tex.faces is not None:
        if not 0<=face<6:raise ValueError('Invalid cubemap face index')
        raw=tex.faces[0][face]
    if w*h>8192*8192:raise ValueError('Image too large')
    if tex.fmt in ('BGRA8','BGRX8'):
        if len(raw)!=w*h*4:raise ValueError('Incorrect BGRA mip length')
        out=bytearray(w*h*4)
        # Strided slice assignment runs the channel shuffle in C, avoiding
        # w*h allocations/slice writes from the legacy per-pixel loop.
        out[0::4]=raw[2::4]
        out[1::4]=raw[1::4]
        out[2::4]=raw[0::4]
        out[3::4]=(raw[3::4] if tex.fmt=='BGRA8'
                    else bytes((255,))*(w*h))
        return w,h,bytes(out)
    if tex.fmt not in ('DXT1','DXT3','DXT5'):
        raise ValueError('Unsupported compressed texture format')
    block_bytes=8 if tex.fmt=='DXT1' else 16
    blocks_across=(w+3)//4
    if len(raw)!=blocks_across*((h+3)//4)*block_bytes:
        raise ValueError('Incorrect DXT mip length')
    out=bytearray(w*h*4)
    for by in range((h+3)//4):
        for bx in range(blocks_across):
            at=(by*blocks_across+bx)*block_bytes
            block=raw[at:at+block_bytes]
            colors=_palette(block[-8:],tex.fmt=='DXT1')
            if tex.fmt=='DXT3':
                alpha_bits=struct.unpack_from('<Q',block)[0]
                alphas=[((alpha_bits>>(4*i))&15)*17 for i in range(16)]
            elif tex.fmt=='DXT5':
                a0,a1=block[:2];bits=int.from_bytes(block[2:8],'little')
                if a0>a1: table=[a0,a1]+[((7-j)*a0+j*a1)//7 for j in range(1,7)]
                else:table=[a0,a1]+[((5-j)*a0+j*a1)//5 for j in range(1,5)]+[0,255]
                alphas=[table[(bits>>(3*i))&7] for i in range(16)]
            else:alphas=None
            width=min(4,w-4*bx)
            height=min(4,h-4*by)
            for yy in range(height):
                row=yy*4
                # Concatenate up to four pixels in C, then make ONE output
                # slice assignment per block-row (instead of one per pixel).
                if alphas is None:
                    pixels=b''.join(bytes(colors[row+xx]) for xx in range(width))
                else:
                    pixels=b''.join(bytes((*colors[row+xx][:3],alphas[row+xx]))
                                    for xx in range(width))
                offset=((by*4+yy)*w+bx*4)*4
                out[offset:offset+width*4]=pixels
    return w,h,bytes(out)

def png_bytes(w,h,rgba):
    if len(rgba)!=w*h*4:raise ValueError('Incorrect RGBA buffer')
    raw=b''.join(b'\0'+rgba[y*w*4:(y+1)*w*4] for y in range(h))
    def chunk(tag,payload):return struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload)&0xffffffff)
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+
            chunk(b'IDAT',zlib.compress(raw,7))+chunk(b'IEND',b''))


def to_png(tex):
    if tex.faces is None:
        w,h,raw=rgba_pixels(tex)
        return png_bytes(w,h,raw)
    # 3 by 2 contact sheet for six cubemap faces; no orientation assumed.
    w,h=tex.width,tex.height
    atlas=bytearray(3*w*2*h*4)
    for i in range(6):
        _,_,rgba=rgba_pixels(tex,i)
        ox=i%3*w;oy=i//3*h
        for y in range(h):
            target=((oy+y)*3*w+ox)*4
            atlas[target:target+w*4]=rgba[y*w*4:(y+1)*w*4]
    return png_bytes(3*w,2*h,bytes(atlas))


def to_dds(tex):
    w,h=tex.width,tex.height;mip_count=len(tex.mipmaps)
    caps=0x1000|(0x8|0x400000 if mip_count>1 else 0)
    flags=0x1007|0x20000 if mip_count>1 else 0x1007
    if tex.fmt.startswith('DXT'):
        flags|=0x80000
        pf=struct.pack('<II4sIIIII',32,4,tex.fmt.encode(),0,0,0,0,0)
        pitch=len(tex.mipmaps[0][2])
    else:
        flags|=0x8; pitch=w*4
        alpha=tex.fmt=='BGRA8'
        pf=struct.pack('<II4sIIIII',32,0x40|(1 if alpha else 0),b'\0'*4,32,0xff0000,0x00ff00,0x0000ff,0xff000000 if alpha else 0)
    if tex.faces is not None:caps|=0x8
    head=struct.pack('<4sIIIIIII44x',b'DDS ',124,flags,h,w,pitch,0,mip_count)+pf+struct.pack('<IIIII',caps,0xFE00 if tex.faces is not None else 0,0,0,0)
    assert len(head)==128
    if tex.faces is not None:
        return head+b''.join(tex.faces[mip][face] for face in range(6) for mip in range(mip_count))
    return head+b''.join(data for _,_,data in tex.mipmaps)


def inventory(bundles):
    textures={};materials={};dups={'textures':0,'materials':0};skipped=[]
    for b in bundles:
        for r in b.resources:
            if r.typ==8:
                key=r.name.casefold()
                if key in textures:dups['textures']+=1
                else:
                    try:textures[key]=parse_texture(b,r)
                    except (ValueError,IndexError) as ex:skipped.append({'name':r.name,'source':b.name,'reason':str(ex)})
            elif r.typ==10:
                key=r.name.casefold()
                if key in materials:dups['materials']+=1
                else:materials[key]=parse_material(b,r)
    return textures,materials,dups,skipped


def thumbnail(tex,max_side=90):
    """Full DX2 pixels decoded, then nearest-neighbour downsampled without PIL."""
    w,h,rgba=rgba_pixels(tex)
    factor=max(1,math.ceil(max(w,h)/max_side))
    tw=max(1,w//factor);th=max(1,h//factor)
    if factor==1:return png_bytes(w,h,rgba)
    downsized=bytearray(tw*th*4)
    for y in range(th):
        for x in range(tw):
            old=4*((y*factor)*w+x*factor);new=4*(y*tw+x)
            downsized[new:new+4]=rgba[old:old+4]
    return png_bytes(tw,th,downsized)


def gallery(textures,materials,out):
    used=Counter(s.casefold() for m in materials.values() for s in m['stages'] if s)
    records=[]
    for t in sorted(textures.values(),key=lambda t:t.name.casefold()):
        png=base64.b64encode(thumbnail(t)).decode('ascii')
        records.append({'name':t.name,'format':t.fmt,'usage':USAGE.get(t.usage,str(t.usage)),
                        'size':f'{t.width} × {t.height}','bundle':t.source,'materials':used[t.name.casefold()],
                        'src':'data:image/png;base64,'+png})
    jsondata=json.dumps(records,separators=(',',':')).replace('</','<\\/')
    page=(Path(__file__).resolve().parent/'templates'/'texture_gallery.html').read_text(encoding='utf-8')
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(page.replace('/*DATA*/',jsondata),encoding='utf-8')
    return out


def safe_file(name):
    return re.sub(r'[^a-zA-Z0-9._-]','_',name)[:120]


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command',choices=('stats','export','gallery','materials'))
    ap.add_argument('bundle',type=Path)
    ap.add_argument('--name',help='Case-insensitive substring to export')
    ap.add_argument('--source-bundle',help='Export only resources from this exact .ibd filename; avoids name collision ambiguity')
    ap.add_argument('-o','--output',type=Path,default=Path('output'))
    args=ap.parse_args()
    bundles=load_bundles(args.bundle)
    tex,mats,dups,skipped=inventory(bundles)
    if args.command=='stats':
        print(json.dumps({'bundle_count':len(bundles),'texture_records':sum(1 for b in bundles for r in b.resources if r.typ==8),
             'unique_textures':len(tex),'material_records':sum(1 for b in bundles for r in b.resources if r.typ==10),
             'unique_materials':len(mats),'duplicate_names':dups,'skipped_textures':skipped,
             'formats':dict(Counter(t.fmt for t in tex.values())),'cubemaps':sum(t.faces is not None for t in tex.values()),
             'usages':dict(Counter(USAGE.get(t.usage,str(t.usage)) for t in tex.values())),
             'resolved_diffuse_material_refs':sum(bool(m['diffuse'] and m['diffuse'].casefold() in tex) for m in mats.values())},indent=2))
    elif args.command=='export':
        args.output.mkdir(exist_ok=True,parents=True)
        found=0
        selected=(parse_texture(b,r) for b in bundles for r in b.resources
                  if r.typ==8 and (not args.source_bundle or Path(b.name).name.casefold()==args.source_bundle.casefold())) if args.source_bundle else tex.values()
        for t in selected:
            if args.name and args.name.casefold() not in t.name.casefold():continue
            dest=args.output/safe_file(t.name)
            dest.with_suffix('.png').write_bytes(to_png(t))
            dest.with_suffix('.dds').write_bytes(to_dds(t))
            found+=1
        if args.source_bundle and found==0:print('No matching resource. Check bundle filename or texture filter.')
        print(f'Exported {found} texture PNG + DDS pairs to {args.output}')
    elif args.command=='gallery':print('Wrote',gallery(tex,mats,args.output))
    else:
        args.output.parent.mkdir(exist_ok=True,parents=True)
        args.output.write_text(json.dumps({'materials':list(mats.values()),'unique':len(mats)},indent=2),encoding='utf-8')
        print('Wrote',len(mats),'material records to',args.output)

if __name__=='__main__':main()