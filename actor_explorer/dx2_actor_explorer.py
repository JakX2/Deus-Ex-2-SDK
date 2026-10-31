#!/usr/bin/env python3
"""DX2Ed Actor Explorer 0.1: read-only GMP -> searchable offline actor map.

Command-line examples:
  python dx2_actor_explorer.py --map M3_Germany_Trier.gmp --output Trier_Actors.html
  python dx2_actor_explorer.py --map my.gmp --system 'C:/.../System' --output my.html

No game files are modified, no game assets are redistributed, and no web access is used.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

# In the standalone ZIP the parsers sit beside this file. In the GitHub checkout,
# reuse the same parsers from the map_exporter directory instead of copying code.
try:
    from dx2inspect import Package
    from dx2scene import decode_full_actor, mesh_metadata
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'map_exporter'))
    from dx2inspect import Package
    from dx2scene import decode_full_actor, mesh_metadata


def catalog_from_source(system_path: Path | None) -> dict:
    if system_path is None:
        return {}
    system_path = system_path.expanduser().resolve()
    if system_path.suffix.lower() == '.json':
        doc = json.loads(system_path.read_text(encoding='utf-8'))
        if doc.get('schema') != 'dx2-catalog-0.1' or not isinstance(doc.get('properties'), dict):
            raise ValueError('Catalog JSON must use schema dx2-catalog-0.1')
        return doc['properties']
    from dx2catalog import build_catalog
    return build_catalog(system_path)['properties']


def game_props_for_export(pkg: Package, exp: dict, catalog: dict) -> tuple[dict, list]:
    tagged, game = decode_full_actor(pkg, exp, catalog)
    return tagged, game


def actor_records(map_path: Path, system: Path | None = None, logic_index: Path | None = None) -> tuple[dict, list[dict]]:
    map_path = map_path.expanduser().resolve()
    pkg = Package(map_path)
    if pkg.version != 95:
        raise ValueError('Only the DX2 Ion Storm v95 package layout has been validated.')
    catalog = catalog_from_source(system)
    mesh_by_ref = mesh_metadata(pkg)
    short, failures = pkg.scene_actors()
    linked: dict[tuple[str, int], dict] = {}
    if logic_index is not None:
        doc = json.loads(logic_index.read_text(encoding='utf-8'))
        if doc.get('schema') != 'DX2-SDK-0.17':
            raise ValueError('Unsupported mission logic index schema')
        for item in doc.get('actors', []):
            if Path(item.get('map','')).name.casefold() == map_path.name.casefold():
                linked[(map_path.name.casefold(), item['export'])] = item
    output = []
    decode_errors = []
    for a in short:
        exp = pkg.exports[a['export']-1]
        try:
            tagged, game = game_props_for_export(pkg, exp, catalog)
        except (ValueError, IndexError, KeyError) as ex:
            tagged, game = {}, []
            decode_errors.append({'export':a['export'], 'error':str(ex)[:160]})
        where=tagged.get('Location')
        x,y,z=(where.get(k,a[k.lower()]) for k in ('X','Y','Z')) if isinstance(where,dict) else (a['x'],a['y'],a['z'])
        rot = tagged.get('Rotation') if isinstance(tagged.get('Rotation'),dict) else {}
        mesh_prop=next((g for g in game if g['id']==43 and isinstance(g['value'],dict)),None)
        mesh=mesh_by_ref.get(mesh_prop['value']['ref']) if mesh_prop else None
        scripts_prop=next((g for g in game if g['id']==92),None)
        link=linked.get((map_path.name.casefold(),a['export']))
        rec={
          'name':a['name'], 'class':a['class'], 'export':a['export'],
          'location':[x,y,z], 'rotation':[rot.get(k,0) for k in ('Pitch','Yaw','Roll')],
          'tagged':tagged, 'game_properties':game, 'mesh':mesh['name'] if mesh else None,
          'mesh_bounds':mesh['bounds'] if mesh else None,
          'trigger_script_serialized':scripts_prop['value'] if scripts_prop else None,
          'scripts':[{'id':d['id'], 'title':d.get('title'), 'actions':d.get('actions',[]), 'conditions':d.get('conditions',[])} for d in link.get('definitions',[])] if link else [],
          'script_ids':link.get('scripts',[]) if link else [],
        }
        output.append(rec)
    meta={'schema':'DX2Ed-ActorExplorer-0.1','map':map_path.name,
          'map_sha256':hashlib.sha256(pkg.data).hexdigest(),'package_version':pkg.version,
          'licensee_version':pkg.licensee,'actors':len(output), 'classes':len({a['class'] for a in output}),
          'mesh_linked_actors':sum(bool(a['mesh']) for a in output),
          'actors_with_serialized_script_field':sum(x['trigger_script_serialized'] is not None for x in output),
          'actors_with_resolved_script_names':sum(bool(x['script_ids']) for x in output),
          'property_catalog_loaded':bool(catalog), 'logic_index_loaded':logic_index is not None,
          'scene_parse_failures':failures,'game_property_decode_errors':decode_errors,
          'read_only':True,'warnings':['TriggerScript name mapping requires a separately generated mission logic index. Raw serialized TriggerScripts values are not script names.',
                '2D map plots actor X/Y coordinates, not a navigable 3D scene.',
                'Game properties are unverified read-only data; numeric ID labels may be used when no catalog is supplied.']}
    return meta,output


def render_html(meta: dict, records: list[dict]) -> str:
    # Avoid a string such as </script> in a game-owned property breaking the HTML document.
    payload = json.dumps({'meta':meta,'actors':records},separators=(',',':'),ensure_ascii=True).replace('</','<\\/')
    template = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DX2Ed Actor Explorer</title><style>
:root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#e6eaf0;background:#10151e;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;overflow:hidden}header{height:64px;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:0 19px;background:#17202d;border-bottom:1px solid #2d3d50}
h1{font-size:16px;margin:0;color:#ecf4ff}header small{font-size:12px;color:#9eaec3}header .meta{text-align:right}button,select,input{font:inherit;border-radius:7px;border:1px solid #34465b;background:#202c3c;color:#e6eaf0;padding:9px 10px}button{cursor:pointer}button:hover{background:#293e54}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #5abbff}
main{display:grid;grid-template-columns:minmax(230px,310px) minmax(300px,1fr) minmax(305px,410px);height:calc(100vh - 64px)}section{min-width:0;border-right:1px solid #2d3d50;display:flex;flex-direction:column}section:last-child{border-right:0}.toolbar{padding:12px;background:#182231;border-bottom:1px solid #2b3b50;display:grid;gap:9px}.toolbar input,.toolbar select{width:100%}.stats{color:#92a6be;font-size:12px}.listing{overflow:auto;flex:1}.item{padding:11px 13px;cursor:pointer;border-bottom:1px solid #263343;display:grid;gap:4px}.item:hover{background:#223448}.item.selected{background:#193954;border-left:3px solid #57c0f8;padding-left:10px}.item .name{font-weight:600;font-size:13px;overflow-wrap:anywhere}.item .secondary{font-size:11px;color:#8fa7bf}.viewport{position:relative;background:radial-gradient(ellipse at center,#1e3245 0%,#101922 73%);overflow:hidden;flex:1;min-height:200px}#map{width:100%;height:100%;display:block;cursor:crosshair}.map-overlay{position:absolute;top:11px;left:13px;pointer-events:none;color:#bdcfe2;background:#111b2ac9;padding:8px 10px;border-radius:7px;font-size:12px}.map-tools{position:absolute;right:12px;bottom:12px;display:flex;gap:6px}.map-tools button{width:38px;height:38px;font-size:19px;padding:0}.detail{overflow:auto;flex:1;padding:14px}h2{font-size:16px;margin:0 0 9px}h3{font-size:13px;letter-spacing:.045em;text-transform:uppercase;color:#85b7dd;margin:22px 0 8px}.tag{font-size:12px;color:#89a1b9}.pills{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.pill{font-size:11px;background:#26455a;color:#b7e4fb;padding:5px 8px;border-radius:6px}.kv{display:grid;grid-template-columns:115px minmax(0,1fr);gap:8px;padding:7px 0;border-bottom:1px solid #263647;font-size:12px}.kv .key{color:#a3b4ca;overflow-wrap:anywhere}.kv .val{color:#edf2f8;overflow-wrap:anywhere}.group{border:1px solid #2b4155;border-radius:8px;margin:7px 0;overflow:hidden}.group summary{cursor:pointer;padding:10px;background:#1c3042;font-size:12px;font-weight:600}.group pre{margin:0;padding:12px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;background:#141e2b;color:#bfd6e9}footer{font-size:11px;color:#7e9cb6;padding:11px;background:#182231;border-top:1px solid #2b3b50}.empty{color:#98aac0;padding:18px;font-size:13px} .warn{color:#ffcf90;font-size:11px}
@media(max-width:1100px){main{grid-template-columns:240px minmax(240px,1fr) 300px}}@media(max-width:780px){body{overflow:auto}main{height:auto;grid-template-columns:1fr}section{height:420px;border-bottom:1px solid #34445a}.detail{height:350px}}
</style></head><body>
<header><div><h1>◈ DX2Ed Actor Explorer <span class="tag">0.1</span></h1><small id="mapname">Loading map...</small></div><div class="meta"><small id="summary"></small></div></header>
<main><section><div class="toolbar"><input id="search" placeholder="Find actor, mesh, property, script..." aria-label="Search actors"><select id="classfilter" aria-label="Filter actor class"><option value="">All actor classes</option></select><div class="stats" id="matches"></div></div><div id="list" class="listing"></div></section>
<section><div class="viewport"><canvas id="map"></canvas><div class="map-overlay">Top-down actor map · X/Y<br>Click a point to inspect · Wheel to zoom<br>Drag to pan · <span style="color:#46bff7">●</span> selected actor</div><div class="map-tools"><button id="zoomout" title="Zoom out">−</button><button id="zoomin" title="Zoom in">+</button><button id="reset" title="Reset view">⤢</button></div></div><footer>Read-only preview. Game files are never modified.</footer></section>
<section><div class="toolbar"><strong style="font-size:13px">Actor Inspector</strong><div class="stats" id="selectmsg">Select an actor from the list or map</div></div><div id="detail" class="detail"><div class="empty">Select an actor to inspect its class, location, tagged properties, gameplay properties and script references.</div></div></section></main>
<script id="embedded-data" type="application/json">__DX2_DATA__</script>
<script>
(()=>{'use strict';const data=JSON.parse(document.getElementById('embedded-data').textContent),actors=data.actors;
const $=id=>document.getElementById(id), el=(tag,text,css)=>{let e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(css)e.className=css;return e};
const meta=data.meta;$('mapname').textContent=meta.map;$('summary').textContent=`${meta.actors} actors · ${meta.classes} classes · ${meta.mesh_linked_actors} meshes`;
const names=[...new Set(actors.map(a=>a.class))].sort((a,b)=>a.localeCompare(b));names.forEach(s=>{let o=el('option',s);o.value=s;$('classfilter').append(o)});
let visible=actors.slice(),chosen=null,scale=1,panx=0,pany=0,drag=false,prev=null,candidates=[];
const coord=actors.filter(a=>a.location.every(Number.isFinite)),ext={xmin:Infinity,xmax:-Infinity,ymin:Infinity,ymax:-Infinity};coord.forEach(a=>{let [x,y]=a.location;ext.xmin=Math.min(x,ext.xmin);ext.xmax=Math.max(x,ext.xmax);ext.ymin=Math.min(y,ext.ymin);ext.ymax=Math.max(y,ext.ymax)});
if(!isFinite(ext.xmin)){ext.xmin=0;ext.xmax=1;ext.ymin=0;ext.ymax=1}
const cv=$('map'),ctx=cv.getContext('2d');let width=1,height=1;
function project(a){let x=a.location[0],y=a.location[1],dx=Math.max(1,ext.xmax-ext.xmin),dy=Math.max(1,ext.ymax-ext.ymin),base=Math.min((width-50)/dx,(height-50)/dy);base=Math.max(.000001,base);return [(x-(ext.xmin+ext.xmax)*.5)*base*scale+width*.5+panx, -(y-(ext.ymin+ext.ymax)*.5)*base*scale+height*.5+pany]}
function paint(){const dpr=Math.min(2,window.devicePixelRatio||1);let r=cv.getBoundingClientRect();width=Math.max(1,r.width);height=Math.max(1,r.height);cv.width=Math.round(width*dpr);cv.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
ctx.strokeStyle='#253a4a';ctx.lineWidth=1;for(let x=width/2+panx%40;x<width;x+=40){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke()}for(let x=width/2+panx%40;x>0;x-=40){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke()}for(let y=height/2+pany%40;y<height;y+=40){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke()}for(let y=height/2+pany%40;y>0;y-=40){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke()}
candidates=[];visible.forEach(a=>{let [x,y]=project(a);if(x<-12||y<-12||x>width+12||y>height+12)return;candidates.push({a,x,y});ctx.beginPath();ctx.arc(x,y,a===chosen?6:2.8,0,Math.PI*2);ctx.fillStyle=a===chosen?'#54cbff':a.script_ids.length?'#edbe76':a.mesh?'#89a6bf':'#577c91';ctx.globalAlpha=a===chosen?1:.75;ctx.fill();ctx.globalAlpha=1;if(a===chosen){ctx.strokeStyle='#e9fbff';ctx.lineWidth=2;ctx.stroke();ctx.font='12px Segoe UI,Arial';ctx.fillStyle='#def5ff';ctx.fillText(a.name,x+12,y-9)}})};
const kv=(parent,k,v)=>{let line=el('div',undefined,'kv');line.append(el('div',k,'key'),el('div',typeof v==='string'?v:JSON.stringify(v),'val'));parent.append(line)};
function details(a){const box=$('detail');box.replaceChildren();$('selectmsg').textContent=a.name;box.append(el('h2',a.name),el('div',`Class: ${a.class} · Export #${a.export}`,'tag'));let p=el('div',undefined,'pills');p.append(el('span',a.mesh?'Mesh linked':'No mesh','pill'));if(a.trigger_script_serialized)p.append(el('span','Serialized script field','pill'));if(a.script_ids.length)p.append(el('span',a.script_ids.length+' identified scripts','pill'));box.append(p);kv(box,'Location (UE)',a.location.map(n=>Number(n.toFixed(3))));kv(box,'Rotation (raw)',a.rotation);if(a.mesh)kv(box,'Static Mesh',a.mesh);if(a.mesh_bounds)kv(box,'Mesh local bounds',a.mesh_bounds);
if(a.script_ids.length){box.append(el('h3','Identified TriggerScripts'));a.scripts.forEach(s=>{let group=el('details',undefined,'group'),sum=el('summary',`${s.id} · ${s.title||'Untitled'}`);group.append(sum,el('pre',JSON.stringify({conditions:s.conditions,actions:s.actions},null,2)));box.append(group)})}
if(a.trigger_script_serialized){box.append(el('h3','Serialized TriggerScript property'));box.append(el('div','Raw indices shown below are not script names unless a separate mission-logic index is supplied.','warn'));let pre=el('pre',JSON.stringify(a.trigger_script_serialized,null,2));pre.style.whiteSpace='pre-wrap';pre.style.overflowWrap='anywhere';box.append(pre)}
for(const [title,records] of [['Tagged engine properties',a.tagged],['Gameplay property blocks',a.game_properties]]){box.append(el('h3',title));if(Array.isArray(records)){for(let g of records){let dd=el('details',undefined,'group');dd.append(el('summary',`${g.name} (#${g.id}) · ${g.type}`),el('pre',JSON.stringify({value:g.value,encoding:g.encoding,version:g.version,runtime:g.runtime},null,2)));box.append(dd)}}else{let dd=el('details',undefined,'group');dd.open=true;dd.append(el('summary',`${Object.keys(records).length} decoded properties`),el('pre',JSON.stringify(records,null,2)));box.append(dd)}}}
function select(a){chosen=a;details(a);for(let e of $('list').children)e.classList.toggle('selected',e.dataset.export===String(a.export));paint()}
function filter(){const needle=$('search').value.toLowerCase().trim(),cls=$('classfilter').value;visible=actors.filter(a=>(!cls||a.class===cls)&&(!needle||(a.name+' '+a.class+' '+(a.mesh||'')+' '+a.game_properties.map(g=>g.name).join(' ')+' '+a.script_ids.join(' ')).toLowerCase().includes(needle)));$('matches').textContent=`${visible.length.toLocaleString()} / ${actors.length.toLocaleString()} actors`;let list=$('list');list.replaceChildren();const frag=document.createDocumentFragment();for(const a of visible){let item=el('div',undefined,'item');item.dataset.export=String(a.export);if(a===chosen)item.classList.add('selected');item.append(el('div',a.name,'name'),el('div',`${a.class}${a.mesh?' · '+a.mesh:''}`,'secondary'));item.addEventListener('click',()=>select(a));frag.append(item)}list.append(frag);if(visible.length&&(!chosen||!visible.includes(chosen))){select(visible[0])}else if(!visible.length){chosen=null;$('detail').replaceChildren(el('div','No matching actors','empty'));$('selectmsg').textContent='No matching actors'}paint()}
$('search').addEventListener('input',filter);$('classfilter').addEventListener('change',filter);cv.addEventListener('pointerdown',e=>{drag=false;prev=[e.clientX,e.clientY];cv.setPointerCapture(e.pointerId)});cv.addEventListener('pointermove',e=>{if(!prev)return;let dx=e.clientX-prev[0],dy=e.clientY-prev[1];if(Math.abs(dx)+Math.abs(dy)>1){drag=true;panx+=dx;pany+=dy;paint()}prev=[e.clientX,e.clientY]});cv.addEventListener('pointerup',e=>{let wasDrag=drag;prev=null;if(wasDrag)return;let r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;let nearest=null,best=14*14;for(let p of candidates){let d=(p.x-x)**2+(p.y-y)**2;if(d<best){best=d;nearest=p.a}}if(nearest)select(nearest)});cv.addEventListener('wheel',e=>{e.preventDefault();scale=Math.min(75,Math.max(.05,scale*(e.deltaY>0?.83:1.2)));paint()},{passive:false});$('zoomin').addEventListener('click',()=>{scale=Math.min(75,scale*1.3);paint()});$('zoomout').addEventListener('click',()=>{scale=Math.max(.05,scale/1.3);paint()});$('reset').addEventListener('click',()=>{scale=1;panx=0;pany=0;paint()});window.addEventListener('resize',paint);
filter();if(visible.length)select(visible[0]);
})();</script></body></html>'''
    return template.replace('__DX2_DATA__', payload)


def export_browser(map_path: Path, out: Path, system: Path | None = None, logic_index: Path | None = None, json_path: Path | None = None) -> dict:
    meta, records = actor_records(map_path,system,logic_index)
    out = out.expanduser().resolve()
    if out.suffix.lower() != '.html':
        raise ValueError('Output must be an HTML file')
    if out == map_path.resolve():
        raise ValueError('Cannot overwrite the map')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(render_html(meta,records),encoding='utf-8')
    if json_path is not None:
        json_path=json_path.expanduser().resolve()
        json_path.parent.mkdir(parents=True,exist_ok=True)
        json_path.write_text(json.dumps({'meta':meta,'actors':records},indent=2),encoding='utf-8')
    return meta


def run_gui():
    import tkinter as tk
    from tkinter import filedialog,messagebox,ttk
    import webbrowser
    root=tk.Tk();root.title('DX2Ed Actor Explorer 0.1');root.geometry('680x300')
    vars={k:tk.StringVar() for k in ('map','system','out','logic')}
    for row,(key,label,types) in enumerate((('map','DX2 .gmp map',[('DX2 map','*.gmp')]),('system','Optional System folder / System.zip / catalog JSON',[('System zip or catalog','*.zip *.json'),('All files','*.*')]),('out','Output .html',[('HTML document','*.html')]),('logic','Optional logic index JSON',[('JSON','*.json')]))):
        ttk.Label(root,text=label).grid(row=row*2,column=0,columnspan=2,sticky='w',padx=18,pady=(13,0))
        ttk.Entry(root,textvariable=vars[key],width=84).grid(row=row*2+1,column=0,sticky='we',padx=(18,5),pady=3)
        def choose(k=key,t=types):
            if k=='out':selected=filedialog.asksaveasfilename(defaultextension='.html',filetypes=t)
            elif k=='system':selected=filedialog.askdirectory(title='Choose installed System folder (Cancel to choose zip or JSON)') or filedialog.askopenfilename(filetypes=t)
            else:selected=filedialog.askopenfilename(filetypes=t)
            if selected:
                vars[k].set(selected)
                if k=='map' and not vars['out'].get():vars['out'].set(str(Path(selected).with_suffix('.actors.html')))
        ttk.Button(root,text='Browse',command=choose).grid(row=row*2+1,column=1,padx=(0,18))
    root.grid_columnconfigure(0,weight=1)
    def generate():
        try:
            if not vars['map'].get() or not vars['out'].get():raise ValueError('Choose a GMP map and output HTML path')
            meta=export_browser(Path(vars['map'].get()),Path(vars['out'].get()),Path(vars['system'].get()) if vars['system'].get() else None,Path(vars['logic'].get()) if vars['logic'].get() else None)
            messagebox.showinfo('Actor Explorer created',f"{meta['actors']} actors, {meta['classes']} classes. Opening browser...")
            webbrowser.open(Path(vars['out'].get()).resolve().as_uri())
        except Exception as exc:messagebox.showerror('Could not build actor explorer',str(exc))
    ttk.Button(root,text='Create and open Actor Explorer',command=generate).grid(row=8,column=0,columnspan=2,pady=15)
    root.mainloop()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--map',type=Path,help='Original .gmp file')
    ap.add_argument('--system',type=Path,help='Optional installed System folder, System.zip, or property catalog JSON')
    ap.add_argument('--logic-index',type=Path,help='Optional locally generated DX2 v0.17 mission logic index')
    ap.add_argument('--output','-o',type=Path,help='Output offline HTML')
    ap.add_argument('--json',type=Path,help='Optional full actor JSON export')
    ap.add_argument('--gui',action='store_true')
    args=ap.parse_args()
    if args.gui or not args.map:run_gui();return
    out=args.output or args.map.with_suffix('.actors.html')
    meta=export_browser(args.map,out,args.system,args.logic_index,args.json)
    print(json.dumps({'output':str(out.resolve()),**meta},indent=2))

if __name__=='__main__':main()