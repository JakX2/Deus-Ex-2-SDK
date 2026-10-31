#!/usr/bin/env python3
"""Export instanced DX2 Penthouse geometry and diffuse textures to a self-contained GLB.

Example:
  python dx2level.py M1_Seattle_Hub_Penthouse_Upper.gmp --bundle m1_hub_penthouse_upper.ibd --bundle Maps.zip -o output/Penthouse_Full_Level.glb

- Static mesh references are read from the supplied GMP, NOT inferred from names.
- Read-only. Original game package/bundles are never modified.
- Node transforms use a provisional UE rotator interpretation; not in-game verified.
- Embedded diffuse PNG textures approximate only the first DX2 material stage.
- This is an inspection/export pipeline, not an engine-compatible re-importer.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
from dx2scene import Package,find_bsp,mesh_metadata,scene_data,SCALE,unreal_to_world
from dx2bundles import load_bundles,parse_mesh
from dx2textures import parse_material,parse_texture,to_png


def rotation_matrix(rot):
    """Rz(yaw) * Ry(-pitch) * Rx(roll), in UE x,y,z basis."""
    pitch,yaw,roll=[float(x or 0)*math.pi/32768 for x in (rot or [0,0,0])]
    cp,sp=math.cos(-pitch),math.sin(-pitch)
    cy,sy=math.cos(yaw),math.sin(yaw)
    cr,sr=math.cos(roll),math.sin(roll)
    # Apply Rx -> Ry -> Rz in that order
    rx=((1,0,0),(0,cr,-sr),(0,sr,cr))
    ry=((cp,0,sp),(0,1,0),(-sp,0,cp))
    rz=((cy,-sy,0),(sy,cy,0),(0,0,1))
    def multiply(a,b):return tuple(tuple(sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    return multiply(rz,multiply(ry,rx))


def actor_matrix(actor):
    R=rotation_matrix(actor.get('rotation'))
    # Gltf coordinate basis = UE (x,z,y), with coordinate swap on both sides
    P=(0,2,1)
    a=[[R[P[i]][P[j]] for j in range(3)] for i in range(3)]
    t=unreal_to_world((actor['x'],actor['y'],actor['z']))
    return [a[0][0],a[1][0],a[2][0],0,
            a[0][1],a[1][1],a[2][1],0,
            a[0][2],a[1][2],a[2][2],0,
            t[0],t[1],t[2],1]


class Builder:
    def __init__(self,resources,materials,textures):
        self.resources=resources;self.material_sources=materials;self.texture_sources=textures
        self.binary=bytearray()
        self.doc={'asset':{'version':'2.0','generator':'DX2 SDK Research 0.11',
                 'extras':{'nonNativeShader':True,'coordinateTransformsProvisional':True}},
                  'scene':0,'scenes':[{'name':'Deus Ex Invisible War scene','nodes':[]}],
                  'nodes':[],'meshes':[],'materials':[],'images':[],'textures':[],
                  'accessors':[],'bufferViews':[],'buffers':[]}
        self.mat_cache={};self.image_cache={};self.texture_cache={}
        self.texture_success=set();self.texture_missing=set();self.mat_missing=set()
        self.direct_texture_materials=set();self.material_aliases={}
        self.shader_approximations=set()
    def buf(self,raw,target=None):
        self.binary.extend(b'\0'*(-len(self.binary)%4))
        at=len(self.binary);self.binary.extend(raw)
        rec={'buffer':0,'byteOffset':at,'byteLength':len(raw)}
        if target:rec['target']=target
        self.doc['bufferViews'].append(rec)
        return len(self.doc['bufferViews'])-1
    def acc(self,view,typ,count,kind,lo=None,hi=None):
        rec={'bufferView':view,'componentType':typ,'count':count,'type':kind}
        if lo is not None:rec['min']=lo;rec['max']=hi
        self.doc['accessors'].append(rec)
        return len(self.doc['accessors'])-1
    def vectors(self,vectors,width,typ='VEC3'):
        if not vectors:raise ValueError('Empty vertices')
        if any(len(vec)!=width or any(not math.isfinite(float(x)) for x in vec) for vec in vectors):
            raise ValueError('Invalid vertex data')
        b=struct.pack('<'+str(len(vectors)*width)+'f',*(float(x) for vec in vectors for x in vec))
        kwargs={}
        if typ=='VEC3':
            kwargs={'lo':[min(x[i] for x in vectors) for i in range(3)],
                    'hi':[max(x[i] for x in vectors) for i in range(3)]}
        return self.acc(self.buf(b,34962),5126,len(vectors),typ,**kwargs)
    def material(self,name,source=None):
        key=(name.casefold(),source or '')
        if key in self.mat_cache:return self.mat_cache[key]
        entry={'name':name,'doubleSided':True,
               'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],
                     'metallicFactor':0.0,'roughnessFactor':.94}}
        # Ion Storm sometimes stores a section's skin name as a raw texture
        # name instead of a MatLib record.  Many Penthouse columns/trim pieces
        # use 'M1club2_goodness01' this way.  Do NOT force a gray fallback if
        # an exact resource texture exists under that name.
        md_record=self.material_sources.get(name.casefold())
        alias=None
        if not md_record and name.lower().endswith(('.dds','.tga','.png')):
            candidate=name.rsplit('.',1)[0]
            md_record=self.material_sources.get(candidate.casefold())
            if md_record:
                alias=candidate
                self.material_aliases[name]=candidate
        md=parse_material(*md_record) if md_record else None
        diffuse=md.get('diffuse') if md else None
        if not md:
            if name.casefold() in self.texture_sources:
                diffuse=name
                self.direct_texture_materials.add(name)
            else:
                self.mat_missing.add(name)
        if alias:entry['extras']={'resolvedMaterialAlias':alias}
        if not md and diffuse:entry['extras']={'directTexture':diffuse}
        # The GEN_GLASS-03 diffuse is an 8x8 DXT3 texture whose alpha is
        # entirely zero. It relies on a native cubemap stage for appearance.
        # An opaque glTF material would turn glass into solid black; instead
        # use a visibly labeled, translucent approximation (NOT the DX2 shader).
        if md and md['name'].casefold()=='gen_glass-03' and any(md['stages'][6:7]):
            entry['alphaMode']='BLEND'
            entry['pbrMetallicRoughness']['baseColorFactor']=[0.72,0.82,0.9,0.22]
            entry['extras']={**entry.get('extras',{}),
                'shaderApproximation':'Translucent glass approximation; native cubemap unavailable'}
            self.shader_approximations.add(name)
            idx=len(self.doc['materials']);self.doc['materials'].append(entry)
            self.mat_cache[key]=idx
            return idx
        texrec=self.texture_sources.get(diffuse.casefold()) if diffuse else None
        if texrec:
            bundle,res=texrec
            tex_key=(bundle.name,res.index)
            if tex_key not in self.texture_cache:
                tex=parse_texture(bundle,res)
                if tex.faces is None:
                    png=to_png(tex)
                    imgid=len(self.doc['images'])
                    self.doc['images'].append({'name':f'{tex.name} ({bundle.name})',
                                               'mimeType':'image/png','bufferView':self.buf(png)})
                    self.doc['textures'].append({'source':imgid})
                    self.texture_cache[tex_key]=len(self.doc['textures'])-1
                else:self.texture_cache[tex_key]=None
            imageid=self.texture_cache[tex_key]
            if imageid is not None:
                entry['pbrMetallicRoughness']['baseColorTexture']={'index':imageid}
                self.texture_success.add(name)
                # Do not globally enable blend merely from texture storage format:
                # DX2 native material flags determine blending behavior.
            else:self.texture_missing.add(name)
        else:self.texture_missing.add(name)
        if not entry['pbrMetallicRoughness'].get('baseColorTexture'):
            entry['pbrMetallicRoughness']['baseColorFactor']=[.63,.7,.77,1]
            entry['extras']={'missingDiffuse':diffuse,'sourceMaterial':md['source_bundle'] if md else None}
        idx=len(self.doc['materials']);self.doc['materials'].append(entry)
        self.mat_cache[key]=idx
        return idx
    def mesh_data(self,mesh,source_bundle):
        xyz=[unreal_to_world(x) for x in mesh.positions]
        normal=[(n[0],n[2],n[1]) for n in mesh.normals]
        attrs={'POSITION':self.vectors(xyz,3),'NORMAL':self.vectors(normal,3),
               'TEXCOORD_0':self.vectors(mesh.uv,2,'VEC2')}
        skin=mesh.skins[0]['materials'] if mesh.skins else []
        prim=[]
        for si,sec in enumerate(mesh.sections):
            inds=mesh.indices[sec['first_index']:sec['first_index']+sec['index_count']]
            if not inds:continue
            inds=[inds[k+j] for k in range(0,len(inds),3) for j in (0,2,1)]
            accessor=self.acc(self.buf(struct.pack('<'+str(len(inds))+'H',*inds),34963),5123,len(inds),'SCALAR')
            name=skin[si] if si<len(skin) else sec['name']
            prim.append({'attributes':attrs,'indices':accessor,'material':self.material(name,source_bundle),'mode':4})
        if not prim:return None
        idx=len(self.doc['meshes']);self.doc['meshes'].append({'name':mesh.name,'primitives':prim,
                              'extras':{'bundle':source_bundle,'meshTriangles':sum(s['index_count']//3 for s in mesh.sections)}})
        return idx
    def bsp_block(self,block,index):
        prim=[]
        for sec in block['sections']:
            if sec['material'].lower()=='bf':continue
            lo=sec['first_vertex'];hi=lo+sec['vertex_count']
            vs=block['vertices'][lo:hi]
            if not vs:continue
            xyz=[unreal_to_world(p) for p,_,_ in vs]
            normals=[(n[0],n[2],n[1]) for _,n,_ in vs]
            uv=[uv for _,_,uv in vs]
            attrs={'POSITION':self.vectors(xyz,3),'NORMAL':self.vectors(normals,3),
                   'TEXCOORD_0':self.vectors(uv,2,'VEC2')}
            indices=[v-lo for t in range(0,len(sec['indices']),3) for v in
                       (sec['indices'][t],sec['indices'][t+2],sec['indices'][t+1])]
            accessor=self.acc(self.buf(struct.pack('<'+str(len(indices))+'H',*indices),34963),5123,len(indices),'SCALAR')
            prim.append({'attributes':attrs,'indices':accessor,'mode':4,'material':self.material(sec['material'])})
        if prim:
            mid=len(self.doc['meshes']);self.doc['meshes'].append({'name':f'BSP_{index:03}', 'primitives':prim})
            self.node({'name':f'BSP_{index:03}','mesh':mid,
                       'extras':{'mapRenderBlock':index,'blockId':block['id']}})
    def node(self,node):
        nid=len(self.doc['nodes']);self.doc['nodes'].append(node)
        self.doc['scenes'][0]['nodes'].append(nid)
    def save(self,path):
        self.binary.extend(b'\0'*(-len(self.binary)%4))
        self.doc['buffers']=[{'byteLength':len(self.binary)}]
        j=json.dumps(self.doc,separators=(',',':'),ensure_ascii=True).encode('utf-8')
        j+=b' '*(-len(j)%4)
        payload=struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(self.binary),0x004e4942)+self.binary
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(struct.pack('<III',0x46546c67,2,12+len(payload))+payload)


def load_resource_index(paths):
    # Priority: listed --bundle order. Upper should come before shared.
    bundles=[]
    for path in paths:bundles.extend(load_bundles(path))
    indexes={4:{},8:{},10:{}}
    collisions=Counter()
    for bundle in bundles:
        for res in bundle.resources:
            if res.typ not in indexes:continue
            key=res.name.casefold()
            if key in indexes[res.typ]:collisions[res.typ]+=1
            else:indexes[res.typ][key]=(bundle,res)
    return bundles,indexes,collisions


def export_level(map_path,bundles,output,report):
    pkg=Package(map_path)
    if pkg.version!=95:raise ValueError('This exporter is tested only with Ion Storm package version 95')
    blocks=find_bsp(pkg)
    actors,_,scene_stats=scene_data(pkg,blocks,mesh_metadata(pkg),{})
    allbundles,idx,collisions=load_resource_index(bundles)
    builder=Builder(idx[4],idx[10],idx[8])
    builder.doc['asset']['extras'].update({'DX2SourceMapSHA256':hashlib.sha256(pkg.data).hexdigest(),
                                              'DX2SourceMapName':pkg.path.name,
                                              'DX2UnitsToMetres':SCALE})
    unique_meshes={};actors_real=[];miss=[];triangles=0
    for actor in actors:
        met=actor.get('mesh')
        if not met:continue
        name=met['name'];key=name.casefold();source=idx[4].get(key)
        if not source:
            miss.append({'export':actor['export'],'mesh':name});continue
        if key not in unique_meshes:
            b,r=source
            m=parse_mesh(b,r)
            unique_meshes[key]={'mesh':m,'bundle':b.name,
                'gltf':builder.mesh_data(m,b.name)}
        m=unique_meshes[key]['mesh'];triangles+=len(m.indices)//3
        mid=unique_meshes[key]['gltf']
        if mid is not None:
            builder.node({'name':actor['name'],'mesh':mid,'matrix':actor_matrix(actor),
              'extras':{'DX2ExportIndex':actor['export'],'DX2Class':actor['class'],
                        'DX2MeshName':name,'DX2MapLocation':[actor['x'],actor['y'],actor['z']]}})
            actors_real.append(actor)
    for i,block in enumerate(blocks):builder.bsp_block(block,i)
    builder.save(output)
    bsp_tris=sum(len(s['indices'])//3 for b in blocks for s in b['sections'] if s['material'].lower()!='bf')
    out={'source_map':Path(map_path).name,'source_map_sha256':hashlib.sha256(pkg.data).hexdigest(),
         'used_bundles':[b.name for b in allbundles],
         'bundle_resource_name_collisions':{str(k):v for k,v in collisions.items()},
         'source_actor_positions':len(actors),
         'mesh_linked_actors':sum('mesh' in a for a in actors),
         'placed_real_mesh_actors':len(actors_real),'missing_mesh_actors':miss,
         'unique_placed_meshes':len(unique_meshes),
         'placed_mesh_triangles':triangles,'visible_bsp_triangles':bsp_tris,
         'total_scene_triangles':triangles+bsp_tris,
         'gltf_mesh_definitions':len(builder.doc['meshes']),
         'gltf_scene_nodes':len(builder.doc['nodes']),
         'gltf_materials':len(builder.doc['materials']),
         'embedded_diffuse_images':len(builder.doc['images']),
         'materials_with_diffuse':len(builder.texture_success),
         'materials_without_diffuse':sorted(builder.texture_missing),
         'material_records_missing':sorted(builder.mat_missing),
         'materials_resolved_as_direct_textures':sorted(builder.direct_texture_materials),
         'materials_resolved_via_alias':builder.material_aliases,
         'shader_approximations':sorted(builder.shader_approximations),
         'output_glb_bytes':Path(output).stat().st_size,
         'warnings':['Actor rotation conventions and source mesh pivots have not been verified in-game.',
                     'Diffuse stage only; no normal/specular, alpha handling, animation, collision, lightmaps, or Ion Storm shader reconstruction.',
                     'glTF output is a visualization/export, NOT a game-compatible reimport format.']}
    Path(report).parent.mkdir(parents=True,exist_ok=True)
    Path(report).write_text(json.dumps(out,indent=2),encoding='utf-8')
    return out


def main():
    a=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('map',type=Path)
    a.add_argument('--bundle',action='append',required=True,type=Path,
                   help='Can repeat; listed order determines precedence for duplicate names. Put upper before Maps.zip.')
    a.add_argument('-o','--output',type=Path,required=True)
    a.add_argument('--report',type=Path)
    args=a.parse_args()
    report=args.report or args.output.with_suffix('.report.json')
    result=export_level(args.map,args.bundle,args.output,report)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
