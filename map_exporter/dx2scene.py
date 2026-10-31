#!/usr/bin/env python3
"""DX2 SDK 0.4: BSP, shared .ibd mesh geometry, and actor-editor preview.

Uses standard-library Python and the independent dx2inspect.py package reader.
References: research published by Veradictus/Thief3-Decomp, verified against
user-supplied Deus Ex: Invisible War retail map data.

Usage:
  python dx2scene.py MAP.gmp [-c dx2_property_catalog.json] [-o ./out]
The original game data is never modified or executed.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
from dx2inspect import Package, Cursor, HAS_STACK
from dx2bundles import load_bundles, parse_mesh

SCALE = 0.01905   # 16 Unreal units per foot; metres per unit (Thief reference)
MARKER = struct.pack('<IiI', 1, -32, 0)
TYPES = {1:'class',2:'object',4:'string',8:'struct',16:'float',32:'int',128:'bool',256:'name',512:'byte',1024:'array',2048:'bitfield'}


def unreal_to_world(xyz):
    return [xyz[0]*SCALE, xyz[2]*SCALE, xyz[1]*SCALE]


def mesh_metadata(pkg):
    """DX2 map StaticMesh exports carry a resource name and *local* bounding box.

    Bounding box is the final 24 bytes before one trailing status byte. Data
    before the bounding box varies with the number of mesh sections/skins.
    The bounds are only a proxy, not polygon data.
    """
    ret={}
    for e in pkg.exports:
        if pkg.class_name(e) != 'StaticMesh' or e['size'] < 40:
            continue
        d=pkg.payload(e)
        try:
            r=Cursor(d,9)
            name=r.fstr()
            variants=r.u32()
            nums=struct.unpack_from('<6f',d,len(d)-25)
            if not name or not (1<=variants<=64) or d[-1]!=1:
                continue
            if not all(math.isfinite(n) and abs(n)<100000 for n in nums):
                continue
            if not all(a<=b for a,b in zip(nums[:3],nums[3:])):
                continue
            ret[e['index']]={'name':name,'bounds':[list(nums[:3]),list(nums[3:])], 'variants':variants}
        except (ValueError,struct.error,IndexError):
            continue
    return ret


def decode_gamesys(pkg, raw, bid):
    kind=TYPES.get((bid>>16)&0xfff,'unknown')
    try:
        r=Cursor(raw)
        if kind in ('class','object'):
            ref=r.ci()
            if r.at==len(raw):return kind, {'ref':ref,'name':pkg.ref_name(ref)} if ref else None
        elif kind=='string':
            result=r.fstr()
            if r.at==len(raw):return kind,result
        elif kind=='name':
            index=r.ci()
            if r.at==len(raw):return kind,pkg.names[index]
        elif kind in ('float','int','bitfield') and len(raw)==4:
            fmt={'float':'f','int':'i','bitfield':'I'}[kind]
            return kind,struct.unpack('<'+fmt,raw)[0]
        elif kind in ('bool','byte') and len(raw)==1:
            return kind,bool(raw[0]) if kind=='bool' else raw[0]
        elif kind=='struct':
            props=pkg.props(r)
            if r.at==len(raw):return kind,props
        elif kind=='array':
            count=r.ci()
            if 0<=count<=5000:
                start=r.at
                for style in ('index','string'):
                    r.at=start
                    items=[]
                    try:
                        for _ in range(count):
                            items.append(r.ci() if style=='index' else r.fstr())
                        if r.at==len(raw):return kind,{'items':items,'interpretation':style}
                    except (ValueError,IndexError):
                        pass
    except (ValueError,IndexError,struct.error):
        pass
    return kind,{'raw_hex':raw[:80].hex(),'byte_length':len(raw),'incomplete':len(raw)>80}


def decode_full_actor(pkg, exp, catalog):
    r=Cursor(pkg.data,exp['offset'],exp['offset']+exp['size'])
    if exp['flags'] & HAS_STACK:
        node=r.ci();r.ci();r.u64();r.u32()
        if node:r.ci()
    tagged=pkg.props(r)
    blocks=[]
    for _ in range(20000):
        if r.stop-r.at<4:break
        bid=r.u32()
        if bid==0:break
        ver=r.u32()
        size=r.u32()
        if size>r.stop-r.at:raise ValueError('gamesys block exceeds export')
        raw=r.get(size)
        kind,value=decode_gamesys(pkg,raw,bid)
        pid=bid&0xffff
        decl=catalog.get(str(pid),{})
        blocks.append({'id':pid,'name':decl.get('name',f'Property_{pid:04x}'),
                       'type':decl.get('type',kind),'encoding':kind,
                       'version':ver,'value':value, 'runtime':bool(bid&0x40000000)})
    return tagged,blocks


def find_bsp(pkg):
    """Locate validated packed BSP render blocks inside a Level export.

    Uses Ion Storm's 80-byte render header, packed 32-byte vertices, indices,
    and named material sections. Marker alone is insufficient; validate all
    offsets, size limits, triangle indices, and bounds to reject false hits.
    """
    level=next((e for e in pkg.exports if pkg.class_name(e)=='Level' and e['size']>0),None)
    if not level:raise ValueError('This package contains no Level export')
    data=pkg.payload(level)
    hits=[]
    pos=0
    while True:
        marker=data.find(MARKER,pos)
        if marker<0:break
        pos=marker+1
        start=marker-0x44
        if start<4:continue
        try:
            lo=struct.unpack_from('<3f',data,start)
            hi=struct.unpack_from('<3f',data,start+12)
            counts=struct.unpack_from('<10I',data,start+0x28)
            nv,ni,nt,ns,nsi,nst,nsv,unknown,stride,other=counts
            if (stride != 0xffffffe0 or unknown!=1 or other!=0 or
                not (3<=nv<=200_000) or not (3<=ni<=1_000_000) or
                not (1<=ns<=5000) or nsv>500000 or nsi>1_000_000 or
                not all(math.isfinite(v) and abs(v)<1_000_000 for v in lo+hi) or
                not all(a<=b for a,b in zip(lo,hi))):
                continue
            at=start+80
            index_at=at+nv*32+nsv*16+nsi*2
            sec_at=index_at+ni*2
            if sec_at>=len(data):continue
            vertices=[]
            for i in range(nv):
                base=at+i*32
                coords=struct.unpack_from('<3f',data,base)
                if not all(math.isfinite(v) and abs(v)<1_000_000 for v in coords):raise ValueError('bad vertex')
                packed=data[base+12:base+16]
                normal=[(packed[2]-128)/127.,(packed[1]-128)/127.,(packed[0]-128)/127.]
                uv=struct.unpack_from('<2f',data,base+16)
                vertices.append((coords,normal,uv))
            indices=struct.unpack_from('<'+str(ni)+'H',data,index_at)
            sections=[]; k=sec_at
            for _ in range(ns):
                if k>=len(data):raise ValueError('section beyond EOF')
                n=data[k]
                if n<2 or n>=64:raise ValueError('bad material name')
                name=data[k+1:k+n].decode('ascii')
                k+=1+n+24
                tri,first_v,num_v,first_i,num_i,extra=struct.unpack_from('<6I',data,k-24)
                if not (first_v+num_v<=nv and first_i+num_i<=ni and num_i%3==0):
                    raise ValueError('bad section range')
                seq=indices[first_i:first_i+num_i]
                if not all(first_v<=idx<first_v+num_v for idx in seq):
                    raise ValueError('invalid index')
                sections.append({'material':name,'indices':seq,'first_vertex':first_v,'vertex_count':num_v})
            hits.append({'offset':start,'end':k,'id':struct.unpack_from('<I',data,start-4)[0],
                         'vertices':vertices,'sections':sections})
        except (ValueError,IndexError,UnicodeError,struct.error):
            continue
    good=[];end=-1
    for b in sorted(hits,key=lambda q:q['offset']):
        if b['offset']>=end:
            good.append(b);end=b['end']
    return good


def tint(label):
    d=hashlib.sha256(label.lower().encode('utf-8')).digest()
    return [0.35+0.53*d[i]/255 for i in range(3)]


def scene_data(pkg, blocks, meshes, catalog):
    actors,failures=pkg.scene_actors()
    full=[];meshrefs=0;errors=0
    for a in actors:
        exp=pkg.exports[a['export']-1]
        try:
            tagged,gs=decode_full_actor(pkg,exp,catalog)
        except (ValueError,IndexError,struct.error):
            errors+=1;tagged={};gs=[]
        a['tagged']=tagged
        # Preserve original float32 values for exact patch-manifest 'from' checks.
        source_location=tagged.get('Location')
        if isinstance(source_location, dict) and all(isinstance(source_location.get(k),(int,float)) for k in ('X','Y','Z')):
            a['x'],a['y'],a['z']=(source_location[k] for k in ('X','Y','Z'))
        a['game_properties']=gs
        rot=tagged.get('Rotation',{})
        if isinstance(rot,dict):
            a['rotation']=[rot.get('Pitch',0),rot.get('Yaw',0),rot.get('Roll',0)]
        mesh_entry=next((p for p in gs if p['id']==43 and isinstance(p['value'],dict)),None)
        if mesh_entry:
            ref=mesh_entry['value'].get('ref',0)
            if ref in meshes:
                a['mesh']=meshes[ref]
                meshrefs+=1
        n=tagged.get('Tag')
        if isinstance(n,str):a['tag']=n
        full.append(a)
    geom={'sections':[],'blocks':len(blocks),'raw_vertices':sum(len(b['vertices']) for b in blocks)}
    for bi,b in enumerate(blocks):
        for sec in b['sections']:
            is_hidden=sec['material'].lower()=='bf'
            vertices=[];col=tint(sec['material'])
            for tri in range(0,len(sec['indices']),3):
                # Unreal handedness: swap Y/Z, reverse winding for right-handed output.
                for vid in (sec['indices'][tri],sec['indices'][tri+2],sec['indices'][tri+1]):
                    coords,normal,uv=b['vertices'][vid]
                    vertices.append(unreal_to_world(coords))
            geom['sections'].append({'block':bi,'id':b['id'],'name':sec['material'],
                                     'hidden':is_hidden,'color':col,'vertices':vertices})
    stats={'actors':len(full),'actor_errors':errors,'position_failures':failures,'mesh_metadata':len(meshes),
           'mesh_actors_resolved':meshrefs,'geometry_blocks':len(blocks),
           'geometry_vertices':geom['raw_vertices'],
           'geometry_sections':len(geom['sections']),
           'geometry_triangles':sum(len(s['vertices'])//3 for s in geom['sections']),
           'visible_triangles':sum(len(s['vertices'])//3 for s in geom['sections'] if not s['hidden']),
           'materials':len({s['name'] for s in geom['sections']})}
    return full,geom,stats


def add_bundle_meshes(actors, geom, stats, bundles_path):
    """Add genuine shared static mesh triangles for recognizable placed actors.

    Geometry/skin payloads are decoded from user-supplied .ibd resources.
    Translation is from the map, and the Euler rotation is a provisional UE
    rotator interpretation (Yaw about +Z, Pitch about -Y, Roll about +X).
    Game-specific mesh offsets and collision are NOT yet verified in-game.
    """
    paths=bundles_path if isinstance(bundles_path, (tuple,list)) else [bundles_path]
    bundles=[b for path in paths for b in load_bundles(path)]
    resources={}
    for bundle in bundles:
        for resource in bundle.resources:
            if resource.typ==4:
                resources.setdefault(resource.name.casefold(),(bundle,resource))
    cache={}; sections=[];found=0;missing=set();triangles=0
    for actor in actors:
        metadata=actor.get('mesh')
        if not metadata:continue
        mesh_name=metadata['name']
        entry=resources.get(mesh_name.casefold())
        if not entry:
            missing.add(mesh_name);continue
        if mesh_name.casefold() not in cache:
            cache[mesh_name.casefold()]=parse_mesh(*entry)
        mesh=cache[mesh_name.casefold()]
        found+=1
        actor['real_mesh_from_bundle']=True
        actor['mesh_source_bundle']=entry[0].name
        rot=actor.get('rotation') or [0,0,0]
        pitch,yaw,roll=[(v or 0)*math.pi/32768 for v in rot]
        cy,sy=math.cos(yaw),math.sin(yaw)
        cp,sp=math.cos(-pitch),math.sin(-pitch)
        cr,sr=math.cos(roll),math.sin(roll)
        def placed(v):
            x,y,z=v
            # Rx(roll), then Ry(-pitch), then Rz(yaw)
            x,y,z=x,cr*y-sr*z,sr*y+cr*z
            x,y,z=cp*x+sp*z,y,-sp*x+cp*z
            x,y,z=cy*x-sy*y,sy*x+cy*y,z
            return unreal_to_world((x+actor['x'],y+actor['y'],z+actor['z']))
        mats=mesh.skins[0]['materials'] if mesh.skins else []
        for si,sec in enumerate(mesh.sections):
            if not sec['index_count']:continue
            material=mats[si] if si<len(mats) else sec['name']
            inds=mesh.indices[sec['first_index']:sec['first_index']+sec['index_count']]
            verts=[]
            for i in range(0,len(inds),3):
                for j in (inds[i],inds[i+2],inds[i+1]):
                    verts.append(placed(mesh.positions[j]))
            triangles+=len(verts)//3
            sections.append({'actor_export':actor['export'],'mesh':mesh_name,'name':material,
                             'vertices':verts,'color':tint(material),'hidden':False})
    geom['mesh_sections']=sections
    stats['shared_mesh_bundles']=len(bundles)
    stats['shared_mesh_resource_names']=len(resources)
    stats['mesh_actors_with_real_polygons']=found
    stats['real_mesh_triangles']=triangles
    stats['mesh_actors_missing_resource']=stats['mesh_actors_resolved']-found
    stats['unique_map_meshes_missing_shared_resources']=len(missing)
    return {'source':[str(p) for p in paths],'matched_actor_count':found,'triangles':triangles,
            'unique_resolved_meshes':sorted(cache),'missing_mesh_names':sorted(missing)}


def write_glb(dest, blocks):
    """Emit standard glTF 2.0 GLB, no textures; preserve original material names."""
    data=bytearray()
    doc={'asset':{'version':'2.0','generator':'DX2 SDK prototype 0.3'},
         'scene':0,'scenes':[{'nodes':[]}], 'nodes':[], 'meshes':[], 'materials':[],
         'accessors':[], 'bufferViews':[]}
    matids={}
    def buffer_view(binary,target):
        data.extend(b'\0'*(-len(data)%4))
        at=len(data);data.extend(binary)
        doc['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':len(binary),'target':target})
        return len(doc['bufferViews'])-1
    def accessor(buf,component,count,typ,mn=None,mx=None):
        v={'bufferView':buf,'componentType':component,'count':count,'type':typ}
        if mn is not None:v['min']=mn;v['max']=mx
        doc['accessors'].append(v)
        return len(doc['accessors'])-1
    def material(name):
        if name not in matids:
            col=tint(name)
            doc['materials'].append({'name':name,'doubleSided':True,
                'pbrMetallicRoughness':{'baseColorFactor':col+[1.0],'metallicFactor':0,'roughnessFactor':0.9},
                'extras':{'placeholderColor':True}})
            matids[name]=len(doc['materials'])-1
        return matids[name]
    for bi,b in enumerate(blocks):
        primitives=[]
        for sec in b['sections']:
            if sec['material'].lower()=='bf':continue
            seq=sec['indices']
            if not seq:continue
            lo=sec['first_vertex'];hi=lo+sec['vertex_count']
            xyz=[unreal_to_world(p) for p,_,_ in b['vertices'][lo:hi]]
            normals=[unreal_to_world(n) for _,n,_ in b['vertices'][lo:hi]]
            normals=[[v / SCALE for v in n] for n in normals]
            uv=[v[2] for v in b['vertices'][lo:hi]]
            pos=buffer_view(struct.pack('<'+str(len(xyz)*3)+'f',*(v for p in xyz for v in p)),34962)
            nor=buffer_view(struct.pack('<'+str(len(normals)*3)+'f',*(v for p in normals for v in p)),34962)
            tex=buffer_view(struct.pack('<'+str(len(uv)*2)+'f',*(v for p in uv for v in p)),34962)
            local=[]
            for ti in range(0,len(seq),3):
                local.extend([seq[ti]-lo,seq[ti+2]-lo,seq[ti+1]-lo])
            inds=buffer_view(struct.pack('<'+str(len(local))+'H',*local),34963)
            primitives.append({'attributes':{'POSITION':accessor(pos,5126,len(xyz),'VEC3',
                            [min(p[i] for p in xyz) for i in range(3)], [max(p[i] for p in xyz) for i in range(3)]),
                         'NORMAL':accessor(nor,5126,len(xyz),'VEC3'),
                         'TEXCOORD_0':accessor(tex,5126,len(xyz),'VEC2')},
                         'indices':accessor(inds,5123,len(local),'SCALAR'),
                         'mode':4,'material':material(sec['material'])})
        if primitives:
            doc['meshes'].append({'name':f'BSP_block_{bi:03d}','primitives':primitives,
                'extras':{'block_id':b['id'],'offset':b['offset']}})
            doc['nodes'].append({'name':f'BSP_block_{bi:03d}','mesh':len(doc['meshes'])-1})
            doc['scenes'][0]['nodes'].append(len(doc['nodes'])-1)
    doc['buffers']=[{'byteLength':len(data)}]
    js=json.dumps(doc,separators=(',',':')).encode('utf-8')
    js+=b' '*(-len(js)%4)
    data.extend(b'\x00'*(-len(data)%4))
    binary=bytes(data)
    body=struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary
    dest.write_bytes(struct.pack('<III',0x46546c67,2,12+len(body))+body)


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map',type=Path)
    ap.add_argument('-c','--catalog',type=Path,help='catalog JSON from dx2catalog.py')
    ap.add_argument('-o','--output',type=Path,default=Path('dx2_scene_export'))
    ap.add_argument('--bundles',type=Path,action='append',help='User-owned .ibd or ZIP (repeat option for more; first matching mesh wins)')
    args=ap.parse_args()
    pkg=Package(args.map)
    if pkg.version!=95:raise ValueError('This preview is tested only on v95 Ion Storm maps')
    catalog=json.loads(args.catalog.read_text('utf-8'))['properties'] if args.catalog else {}
    mesh=mesh_metadata(pkg)
    bsp=find_bsp(pkg)
    actors,geom,stats=scene_data(pkg,bsp,mesh,catalog)
    bundle_info=add_bundle_meshes(actors,geom,stats,args.bundles) if args.bundles else None
    args.output.mkdir(parents=True,exist_ok=True)
    js={'source':args.map.name,'sha256':hashlib.sha256(pkg.data).hexdigest(),'version':pkg.version,'licensee':pkg.licensee,'stats':stats,'actors':actors}
    (args.output/'actors_full.json').write_text(json.dumps(js,indent=2,ensure_ascii=False),encoding='utf-8')
    if bundle_info:
        (args.output/'bundle_match_report.json').write_text(json.dumps(bundle_info,indent=2),encoding='utf-8')
    (args.output/'geometry_stats.json').write_text(json.dumps({'source':args.map.name,**stats,
         'material_counts':dict(Counter(s['name'] for s in geom['sections']))},indent=2),encoding='utf-8')
    write_glb(args.output/'penthouse_bsp_untextured.glb',bsp)
    template=Path(__file__).with_name('viewer_template.html').read_text(encoding='utf-8')
    template=template.replace('/*DX2_SCENE_DATA*/',json.dumps({'title':args.map.name,'sha256':hashlib.sha256(pkg.data).hexdigest(),'package_version':pkg.version,'licensee':pkg.licensee,'actors':actors,'geometry':geom,'stats':stats},ensure_ascii=True,separators=(',',':')).replace('</','<\\/'))
    (args.output/'DX2_Penthouse_Actor_Editor.html').write_text(template,encoding='utf-8')
    print(json.dumps(stats,indent=2))
    print('Wrote:',args.output.resolve())

if __name__=='__main__':main()
