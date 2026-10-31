#!/usr/bin/env python3
"""Strict, read-only Ion Storm DX2 *.ibd resource bundle inspector.

Research observation from the user's retail DX2 bundles: C0000001/0x800 aligned
containers resembling T3 .ibt, but with 0x130-byte table records (not 0x134).
No game executables needed. Python 3.9+ standard library only.

Commands:
  python dx2bundles.py stats Maps.zip
  python dx2bundles.py list Maps.zip --type staticmesh
  python dx2bundles.py stats path/to/Kernel_GFXALL.ibd
  python dx2bundles.py mesh-info Maps.zip GO_basketball
  python dx2bundles.py mesh-glb Maps.zip GO_basketball -o basketball.glb
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

MAGIC=0xc0000001
ENTRY_SIZE=0x130
HEADER_SIZE=0x34
TYPES={4:'staticmesh',5:'physicshull',6:'ragdolls',8:'texture',10:'matlib',16:'skeletalmesh',17:'skeletalanim',21:'triggerscriptdef',29:'fleshshader'}
TYPE_IDS={v:k for k,v in TYPES.items()}
MAX_RESOURCES=200_000

@dataclass(frozen=True)
class Resource:
    index:int
    offset:int
    size:int
    padding:int
    first_part:int
    part_count:int
    typ:int
    name:str
    digest:bytes
    @property
    def kind(self):return TYPES.get(self.typ,f'type_{self.typ:02x}')

class Bundle:
    def __init__(self,name,data):
        self.name=name;self.data=data
        if len(data)<HEADER_SIZE:raise ValueError('Truncated bundle header')
        magic,align,data_start,data_size,maxres,maxpart,nres,nparts=struct.unpack_from('<8I',data)
        if magic!=MAGIC:raise ValueError(f'Bad bundle magic: {magic:#x}')
        if align!=2048 or nres>MAX_RESOURCES or nparts>2_000_000:raise ValueError('Unsupported bundle geometry')
        if data_start%align or data_start+data_size!=len(data):raise ValueError('Invalid data extent')
        table_end=HEADER_SIZE+nres*ENTRY_SIZE+nparts*4
        if table_end>data_start:raise ValueError('Bundle table overruns data start')
        self.data_start=data_start;self.part_count=nparts;self.alignment=align
        self.expected_digest=data[32:52]
        self.part_sizes=struct.unpack_from('<'+str(nparts)+'I',data,HEADER_SIZE+nres*ENTRY_SIZE) if nparts else ()
        self.resources=[]
        seen_names=set()
        extents=[]
        for i in range(nres):
            p=HEADER_SIZE+i*ENTRY_SIZE
            offset,size,padding,first,count=struct.unpack_from('<5I',data,p)
            typ=data[p+0x28]
            rawname=data[p+0x29:p+ENTRY_SIZE].split(b'\0',1)[0]
            name=rawname.decode('latin-1')
            if not name or len(name)>260:raise ValueError(f'Resource #{i}: bad name')
            if (offset%align or offset < data_start or size==0 or offset+size+padding>len(data) or
                (size+padding)%align or first+count>nparts or
                sum(self.part_sizes[first:first+count])!=size):
                raise ValueError(f'Resource #{i} ({name}): invalid size/part layout')
            res=Resource(i,offset,size,padding,first,count,typ,name,data[p+0x14:p+0x28])
            self.resources.append(res)
            extents.append((offset,offset+size+padding))
        extents.sort()
        if any(a1>b0 for (_,a1),(b0,_) in zip(extents,extents[1:])):
            raise ValueError('Overlapping resource areas')
        self.by_name={}
        for r in self.resources:self.by_name.setdefault(r.name.casefold(),[]).append(r)
    def find(self,name,typ=None):
        for r in self.by_name.get(name.casefold(),[]):
            if typ is None or r.typ==typ:return r
        return None
    def parts(self,res):
        sizes=self.part_sizes[res.first_part:res.first_part+res.part_count]
        offset=res.offset
        for size in sizes:
            yield self.data[offset:offset+size]
            offset+=size
    def raw(self,res):return self.data[res.offset:res.offset+res.size]

class Parts:
    def __init__(self, parts):self.parts=list(parts);self.pos=0
    def take(self,size):
        if self.pos>=len(self.parts):raise ValueError('Missing resource part')
        b=self.parts[self.pos];self.pos+=1
        if len(b)!=size:raise ValueError(f'Part #{self.pos-1}: expected {size} bytes, found {len(b)}')
        return b
    def u32(self):return struct.unpack('<I',self.take(4))[0]
    def string(self):
        n=self.u32()
        if n>4096:raise ValueError('Unreasonably long string')
        b=self.take(n) if n else b''
        return b.split(b'\0')[0].decode('latin1')
    def end(self):
        if self.pos!=len(self.parts):raise ValueError(f'{len(self.parts)-self.pos} unread parts')

@dataclass
class Mesh:
    name:str
    skins:list
    flags:int
    hardpoints:list
    positions:list
    normals:list
    uv:list
    indices:list
    sections:list
    bounds:list


def parse_mesh(bundle,res):
    if res.typ!=4:raise ValueError('Not a static mesh resource')
    p=Parts(bundle.parts(res))
    n=p.u32()
    if n>100:raise ValueError('Too many skins')
    skins=[]
    for _ in range(n):
        name=p.string();nm=p.u32()
        if nm>1000:raise ValueError('Too many materials')
        skins.append({'name':name,'materials':[p.string() for _ in range(nm)]})
    nflags=p.u32()
    if nflags>1000:raise ValueError('Too many skin flags')
    skin_flags=[p.u32() for _ in range(nflags)]
    flags=p.u32()
    hcount=p.u32()
    if hcount>1000:raise ValueError('Too many hardpoints')
    hardpoints=[]
    for _ in range(hcount):
        matrix=struct.unpack('<12f',p.take(48))
        hardpoints.append({'name':p.string(),'matrix':matrix})
    size=p.u32()
    if size>res.size:raise ValueError('Oversized mesh payload')
    b=p.take(size)
    p.end()
    if len(b)<80:raise ValueError('Truncated render header')
    bounds=list(struct.unpack_from('<6f',b))
    nv,ni,nt,ns,nsi,nst,nsv,u1,stride,u2=struct.unpack_from('<10I',b,0x28)
    if not (0<nv<=200000 and 0<ni<=1000000 and 0<ns<=10000 and
            stride in (64,0xffffffe0) and ni%3==0):raise ValueError('Unsupported render layout')
    if not all(math.isfinite(x) for x in bounds):raise ValueError('Nonfinite bounds')
    at=0x50;positions=[];normals=[];uv=[]
    for i in range(nv):
        if stride==64:
            v=struct.unpack_from('<3f3f2f3f2f2fI',b,at)
            xyz=v[:3];normal=v[3:6];tex=v[6:8]
        else:
            x,y,z,nrm,u,v,tan,col=struct.unpack_from('<3f4s2f4sI',b,at)
            xyz=(x,y,z);normal=((nrm[2]-128)/127,(nrm[1]-128)/127,(nrm[0]-128)/127);tex=(u,v)
        if not all(math.isfinite(x) and abs(x)<1e6 for x in (*xyz,*normal,*tex)):
            raise ValueError('Nonfinite/out-of-range vertex')
        positions.append(xyz);normals.append(normal);uv.append(tex)
        at+=stride if stride==64 else 32
    at+=nsv*16+nsi*2
    if at+ni*2>len(b):raise ValueError('Indices out of render bounds')
    indices=list(struct.unpack_from('<'+str(ni)+'H',b,at));at+=ni*2
    sections=[]
    for i in range(ns):
        if at>=len(b):raise ValueError('Truncated section')
        n=b[at];at+=1
        if n<1 or n>96 or at+n+24>len(b):raise ValueError('Bad section name')
        sn=b[at:at+n].split(b'\0')[0].decode('latin1');at+=n
        tris,first_v,num_v,first_i,num_i,extra=struct.unpack_from('<6I',b,at);at+=24
        if first_v+num_v>nv or first_i+num_i>ni or num_i%3:
            raise ValueError('Invalid section range')
        if any(not first_v<=idx<first_v+num_v for idx in indices[first_i:first_i+num_i]):
            raise ValueError('Bad section index')
        sections.append({'name':sn,'triangles':num_i//3,'first_vertex':first_v,'vertex_count':num_v,
                         'first_index':first_i,'index_count':num_i})
    if at!=len(b):raise ValueError(f'Unconsumed render bytes: {len(b)-at}')
    return Mesh(res.name,skins,flags,hardpoints,positions,normals,uv,indices,sections,bounds)


def load_bundles(path):
    """Input either .ibd file or a user-created ZIP of .ibd files. No extraction."""
    path=Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            out=[]
            for info in z.infolist():
                if info.filename.lower().endswith('.ibd'):
                    if info.file_size>300_000_000:raise ValueError('Oversized .ibd member')
                    out.append(Bundle(info.filename,z.read(info)))
        if not out:raise ValueError('ZIP contains no .ibd resources')
        return out
    return [Bundle(path.name,path.read_bytes())]


def glb_mesh(mesh,out,scale=0.01905):
    """Single-mesh untextured GLB, preserving section material names, UVs, normals."""
    import json
    buff=bytearray();views=[];access=[];materials=[];primitives=[]
    def view(raw,target):
        buff.extend(b'\0'*(-len(buff)%4));at=len(buff);buff.extend(raw)
        views.append({'buffer':0,'byteOffset':at,'byteLength':len(raw),'target':target});return len(views)-1
    def ac(v,component,count,typ,lo=None,hi=None):
        a={'bufferView':v,'componentType':component,'count':count,'type':typ}
        if lo is not None:a.update(min=lo,max=hi)
        access.append(a);return len(access)-1
    def farray(points,dim):return struct.pack('<'+str(len(points)*dim)+'f',*(v for q in points for v in q))
    def coords(x):return (x[0]*scale,x[2]*scale,x[1]*scale)
    xyz=[coords(v) for v in mesh.positions]
    norms=[(v[0],v[2],v[1]) for v in mesh.normals]
    pos=ac(view(farray(xyz,3),34962),5126,len(xyz),'VEC3',
           [min(p[i] for p in xyz) for i in range(3)],[max(p[i] for p in xyz) for i in range(3)])
    nor=ac(view(farray(norms,3),34962),5126,len(norms),'VEC3')
    uv=ac(view(farray(mesh.uv,2),34962),5126,len(mesh.uv),'VEC2')
    for sec in mesh.sections:
        if not sec['index_count']:continue
        sequence=mesh.indices[sec['first_index']:sec['first_index']+sec['index_count']]
        # Unreal handedness conversion: swap Y and Z + flip triangle winding.
        swapped=[]
        for i in range(0,len(sequence),3):swapped.extend([sequence[i],sequence[i+2],sequence[i+1]])
        fmt='H' if max(swapped)<65536 else 'I'
        idx=ac(view(struct.pack('<'+str(len(swapped))+fmt,*swapped),34963),5123 if fmt=='H' else 5125,len(swapped),'SCALAR')
        material_name=sec['name']
        mats=mesh.skins[0]['materials'] if mesh.skins else []
        section_idx=mesh.sections.index(sec)
        if section_idx<len(mats):material_name=mats[section_idx]
        materials.append({'name':material_name,'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[0.65,0.78,0.90,1.0],
                          'metallicFactor':0,'roughnessFactor':0.9},'extras':{'placeholderColor':True}})
        primitives.append({'attributes':{'POSITION':pos,'NORMAL':nor,'TEXCOORD_0':uv},
                           'indices':idx,'material':len(materials)-1,'mode':4})
    if not primitives:raise ValueError('No visible triangle sections')
    doc={'asset':{'version':'2.0','generator':'DX2 SDK v0.4'},'scene':0,'scenes':[{'nodes':[0]}],
         'nodes':[{'mesh':0,'name':mesh.name}],'meshes':[{'name':mesh.name,'primitives':primitives}],
         'materials':materials,'buffers':[{'byteLength':0}],'bufferViews':views,'accessors':access}
    buff.extend(b'\0'*(-len(buff)%4));doc['buffers'][0]['byteLength']=len(buff)
    j=json.dumps(doc,separators=(',',':')).encode();j+=b' ' *(-len(j)%4)
    body=struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(buff),0x004e4942)+buff
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(struct.pack('<III',0x46546c67,2,len(body)+12)+body)
    return out


def main():
    a=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('command',choices=['stats','list','mesh-info','mesh-glb'])
    a.add_argument('bundle',type=Path)
    a.add_argument('name',nargs='?')
    a.add_argument('--type',choices=sorted(TYPE_IDS))
    a.add_argument('-o','--output',type=Path)
    args=a.parse_args()
    bundles=load_bundles(args.bundle)
    if args.command=='stats':
        for b in bundles:
            print(f'{b.name}: {len(b.resources)} resources, {b.part_count} parts, {len(b.data):,} bytes')
            for name,count in Counter(r.kind for r in b.resources).most_common():print(f'  {name:20s}{count:6d}')
        return
    if args.command=='list':
        for b in bundles:
            for r in b.resources:
                if args.type and r.typ!=TYPE_IDS[args.type]:continue
                print(f'{b.name:30s} {r.index:4d} {r.kind:18s} {r.size:9d} {r.name}')
        return
    if not args.name:raise ValueError('Give a mesh name (case insensitive)')
    candidates=[(b,r) for b in bundles if (r:=b.find(args.name,4))]
    if not candidates:raise ValueError(f'Static mesh {args.name!r} not found')
    b,r=candidates[0];mesh=parse_mesh(b,r)
    info={'source_bundle':b.name,'mesh_name':r.name,'source_sha256':hashlib.sha256(b.data).hexdigest(),
          'resource_size':r.size,'vertices':len(mesh.positions),'triangles':sum(s['triangles'] for s in mesh.sections),
          'skins':mesh.skins,'bounds':mesh.bounds,'sections':mesh.sections,'hardpoints':[h['name'] for h in mesh.hardpoints]}
    print(json.dumps(info,indent=2))
    if args.command=='mesh-glb':
        path=args.output or Path(mesh.name+'.glb');print('Wrote',glb_mesh(mesh,path))

if __name__=='__main__':main()
