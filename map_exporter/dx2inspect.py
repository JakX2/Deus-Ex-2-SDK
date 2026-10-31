#!/usr/bin/env python3
"""DX2 Inspector 0.1: read-only Unreal/Ion Storm package and actor inspector.

Use with user-owned Deus Ex: Invisible War .gmp / .d2u packages. Python 3.9+.
Only the standard library is required. The tool NEVER modifies input packages.

Commands:
  python dx2inspect.py summary map.gmp
  python dx2inspect.py actors map.gmp --json actors.json
  python dx2inspect.py viewer map.gmp --output penthouse.html
  python dx2inspect.py scripts Engine.d2u --output extracted-scripts

Unreal Engine package details cross-checked against Thief3-Decomp's upkg.py
and verified on DX2 v95 licensee 68/69. This implementation is independent.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct
import sys

TAG = 0x9E2A83C1
HAS_STACK = 0x02000000


class Cursor:
    def __init__(self, data, at=0, stop=None):
        self.data = data
        self.at = at
        self.stop = len(data) if stop is None else stop

    def get(self, size):
        if size < 0 or self.at + size > self.stop:
            raise ValueError(f"Read past bounds at 0x{self.at:x}, size {size}")
        chunk = self.data[self.at:self.at + size]
        self.at += size
        return chunk

    def u8(self): return self.get(1)[0]
    def u16(self): return struct.unpack('<H', self.get(2))[0]
    def u32(self): return struct.unpack('<I', self.get(4))[0]
    def i32(self): return struct.unpack('<i', self.get(4))[0]
    def u64(self): return struct.unpack('<Q', self.get(8))[0]

    def ci(self):
        # Unreal's signed variable-width compact index
        b = self.u8()
        sign = b & 0x80
        value = b & 0x3f
        shift = 6
        if b & 0x40:
            for _ in range(4):
                b = self.u8()
                value |= (b & 0x7f) << shift
                if not (b & 0x80): break
                shift += 7
            else: raise ValueError('Malformed compact integer')
        return -value if sign else value

    def fstr(self):
        length = self.ci()
        if length > 0:
            raw = self.get(length)
            return raw[:-1].decode('latin-1', errors='replace')
        if length < 0:
            raw = self.get(-length * 2)
            return raw[:-2].decode('utf-16-le', errors='replace')
        return ''


class Package:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        r = Cursor(self.data)
        if r.u32() != TAG: raise ValueError('Not an Unreal Engine package')
        self.version, self.licensee, self.flags = r.u16(), r.u16(), r.u32()
        nc, no = r.u32(), r.u32()
        ec, eo = r.u32(), r.u32()
        ic, io = r.u32(), r.u32()
        if any(c > 3_000_000 for c in (nc, ec, ic)):
            raise ValueError('Unreasonable table counts')
        self.guid = None
        self.generations = []
        self.extra_table_offset = None
        # Ion Storm's v95 files place one dword before the GUID and two
        # after the generation table. A table that begins at 0x4c indicates
        # this layout, but we test the actual boundary instead of guessing.
        start = r.at
        found = False
        for before, after in ((True, True), (False, True), (False, False)):
            try:
                t = Cursor(self.data, start)
                if before: t.u32()
                guid = t.get(16).hex()
                gens = t.u32()
                if gens > 4096: continue
                generations = [(t.u32(), t.u32()) for _ in range(gens)]
                extras = (t.u32(), t.u32()) if after else (None, None)
                if t.at == no:
                    self.guid, self.generations, self.extra_table_offset = guid, generations, extras[1]
                    found = True
                    break
            except ValueError:
                continue
        if not found: raise ValueError('Unsupported package header layout')
        r.at = no
        self.names = []
        for _ in range(nc):
            if self.version >= 64:
                name = r.fstr()
            else:
                end = self.data.index(b'\0', r.at)
                name = self.data[r.at:end].decode('latin-1')
                r.at = end + 1
            r.u32()  # name flags
            self.names.append(name)
        r.at = io
        self.imports = []
        for _ in range(ic):
            cp, cn, outer, name = r.ci(), r.ci(), r.i32(), r.ci()
            self.imports.append({'name': self.names[name], 'class': self.names[cn],
                                 'class_package': self.names[cp], 'outer': outer})
        r.at = eo
        self.exports = []
        for i in range(ec):
            class_ref, superclass, outer, name, flags = r.ci(), r.ci(), r.i32(), r.ci(), r.u32()
            size = r.ci()
            offset = r.ci() if size else 0
            if size < 0 or offset < 0 or offset + size > len(self.data):
                raise ValueError(f'Invalid export #{i+1} bounds')
            self.exports.append({'index': i+1, 'class_ref': class_ref, 'super': superclass,
                                 'outer': outer, 'name': self.names[name], 'flags': flags,
                                 'size': size, 'offset': offset})
        self.table_counts = (nc, ic, ec)

    def ref_name(self, ref):
        if ref < 0: return self.imports[-ref-1]['name']
        if ref > 0: return self.exports[ref-1]['name']
        return 'None'

    def class_name(self, export):
        ref = export['class_ref']
        return self.ref_name(ref) if ref else 'Class'

    def payload(self, exp):
        i, n = exp['offset'], exp['size']
        return self.data[i:i+n]

    def props(self, r, depth=0):
        if depth > 15: raise ValueError('Nested property depth exceeded')
        properties = {}
        for _ in range(100000):
            name_index = r.ci()
            name = self.names[name_index]
            if name == 'None': return properties
            info = r.u8()
            kind = info & 0x0f
            sz_kind = (info >> 4) & 0x07
            flag = bool(info & 0x80)
            struct_name = self.names[r.ci()] if kind == 10 else None
            if sz_kind < 5: size = [1,2,4,12,16][sz_kind]
            elif sz_kind == 5: size = r.u8()
            elif sz_kind == 6: size = r.u16()
            else: size = r.u32()
            arri = None
            if flag and kind != 3:
                b = r.u8()
                if b & 0x80:
                    if b & 0x40:
                        arri = ((b & 63) << 24) | (r.u8()<<16) | (r.u8()<<8) | r.u8()
                    else: arri = ((b & 127) << 8) | r.u8()
                else: arri = b
            raw = r.get(size)
            value = None
            try:
                if kind == 3: value = flag
                elif kind in (1,2,4) and size in (1,4):
                    value = {1: lambda: raw[0], 2: lambda: struct.unpack('<i',raw)[0],
                             4:lambda: struct.unpack('<f',raw)[0]}[kind]()
                elif kind in (5,8):
                    ref = Cursor(raw).ci()
                    value = self.ref_name(ref) if ref else None
                elif kind == 6: value = self.names[Cursor(raw).ci()]
                elif kind == 10:
                    sub = Cursor(raw)
                    nested = self.props(sub, depth+1)
                    value = nested if sub.at == len(raw) else None
                elif kind == 11 and size == 12: value = list(struct.unpack('<3f',raw))
                elif kind == 12 and size == 12: value = list(struct.unpack('<3i',raw))
                elif kind == 13: value = Cursor(raw).fstr()
            except (IndexError, ValueError, struct.error): pass
            if value is None:
                value = f'<{kind}: {len(raw)} bytes>'
            if arri is not None:
                if name not in properties or not isinstance(properties[name], dict): properties[name] = {}
                properties[name][str(arri)] = value
            else:
                properties[name] = value
        raise ValueError('Too many properties')

    def decode_object(self, exp):
        r = Cursor(self.data, exp['offset'], exp['offset'] + exp['size'])
        if exp['flags'] & HAS_STACK:
            node, state = r.ci(), r.ci()
            r.u64(); r.u32()
            if node: r.ci()
        p = self.props(r)
        return p

    def script_text(self, exp):
        if self.class_name(exp) != 'TextBuffer' or not exp['size']: return None
        r = Cursor(self.data, exp['offset'], exp['offset'] + exp['size'])
        self.props(r)
        for _ in range(100000):
            bid = r.u32()
            if bid == 0: break
            r.u32()
            r.get(r.u32())
        else: raise ValueError('Too many gamesys blocks')
        links = r.u32()
        if links > 100000: raise ValueError('Too many links')
        for _ in range(links): r.ci()
        r.u32();r.u32()  # cursor position, scroll top
        return r.fstr()

    def scene_actors(self):
        objects, failures = [], 0
        excluded = {'Model','StaticMesh','Level'}
        for e in self.exports:
            if e['size'] == 0 or self.class_name(e) in excluded: continue
            try:
                props = self.decode_object(e)
                loc = props.get('Location')
                if not isinstance(loc, dict): continue
                xyz = [loc.get(v) for v in ('X','Y','Z')]
                if not all(isinstance(v, (int,float)) for v in xyz): continue
                objects.append({'name':e['name'], 'class':self.class_name(e),
                                'export':e['index'], 'x':round(xyz[0],3),
                                'y':round(xyz[1],3), 'z':round(xyz[2],3)})
            except (ValueError, IndexError, struct.error): failures += 1
        return objects, failures


def make_viewer(path, package, actors):
    # Self-contained, local HTML and canvas. This is an object-position plot,
    # not a textured 3D reconstruction of a complete DX2 level.
    points = json.dumps(actors, ensure_ascii=True)
    page = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DX2 Inspector | __TITLE__</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{font:14px system-ui,sans-serif;background:#0b101b;color:#e5eaf3;margin:0}
header{padding:16px 20px;background:#151e2f;border-bottom:1px solid #33445b}h1{font-size:19px;margin:0 0 5px}
small{color:#9cb1cd}main{display:grid;grid-template-columns:minmax(0,1fr) 265px;min-height:calc(100vh - 75px)}
#chart{width:100%;height:calc(100vh - 75px);cursor:crosshair;display:block}
aside{padding:18px;border-left:1px solid #33445b;overflow-y:auto;max-height:calc(100vh - 75px)}
input{width:100%;background:#1b2840;color:#f0f6ff;border:1px solid #475a72;border-radius:6px;padding:9px}
.filter{display:flex;align-items:center;gap:8px;margin:9px 0;color:#ccd7e8}.filter input{width:auto}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%}
#detail{background:#162237;border-radius:8px;padding:12px;min-height:70px;margin:14px 0;overflow-wrap:anywhere}
button{border:1px solid #52647e;background:#243853;color:#e7f1ff;padding:7px 10px;border-radius:7px;cursor:pointer}
@media(max-width:700px){main{display:block}#chart{height:63vh}aside{max-height:unset;border-left:0;border-top:1px solid #33445b}}
</style></head><body><header><h1>DX2 level object inspector</h1><small>__TITLE__ | __COUNT__ positioned objects | top-down XY view, Z available on selection. Points are NOT polygon geometry.</small></header>
<main><canvas id="chart"></canvas><aside>
<input id="search" placeholder="Filter class or name…" aria-label="Search objects">
<p><small>Drag to pan • wheel to zoom • click a point to inspect</small></p>
<button id="reset">Reset view</button>
<div id="detail">Select an object to inspect.</div>
<div id="filters"></div>
<p><small>Read-only research prototype. Mesh surfaces, collision, textures, and BSP are not displayed.</small></p>
</aside></main><script>
const objects=__DATA__;
const groups=[['Static meshes',o=>o.class==='StaticMeshActor','#46c6b7'],['Brushes',o=>o.class==='Brush','#679cff'],['Lights',o=>o.class==='Light','#ffce64'],['NPCs and game objects',o=>o.class.startsWith('D_'),'#ef86c0'],['Player starts',o=>o.class==='PlayerStart','#fff29a'],['Other',o=>!['StaticMeshActor','Brush','Light','PlayerStart'].includes(o.class)&&!o.class.startsWith('D_'),'#adb3c8']];
let enabled=groups.map(()=>true),filter='',selected=null;
const canvas=document.getElementById('chart'),ctx=canvas.getContext('2d');
const bounds={minx:Math.min(...objects.map(o=>o.x)),maxx:Math.max(...objects.map(o=>o.x)),miny:Math.min(...objects.map(o=>o.y)),maxy:Math.max(...objects.map(o=>o.y))};
let view={cx:(bounds.minx+bounds.maxx)/2,cy:(bounds.miny+bounds.maxy)/2,scale:1};
let W=1,H=1;
function baseScale(){return Math.min(W/(bounds.maxx-bounds.minx+150),H/(bounds.maxy-bounds.miny+150))}
function screen(o){const k=baseScale()*view.scale;return {x:W/2+(o.x-view.cx)*k,y:H/2-(o.y-view.cy)*k}}
function visible(o){return enabled[groups.findIndex(g=>g[1](o))]&&(o.name+' '+o.class).toLowerCase().includes(filter)}
function render(){ctx.clearRect(0,0,W,H);ctx.fillStyle='#0b101b';ctx.fillRect(0,0,W,H);
const k=baseScale()*view.scale,step=200;ctx.lineWidth=1;ctx.strokeStyle='#1d2a3d';
const minx=view.cx-W/(2*k),maxx=view.cx+W/(2*k),miny=view.cy-H/(2*k),maxy=view.cy+H/(2*k);
for(let x=Math.ceil(minx/step)*step;x<=maxx;x+=step){const sx=screen({x,y:0}).x;ctx.beginPath();ctx.moveTo(sx,0);ctx.lineTo(sx,H);ctx.stroke()}
for(let y=Math.ceil(miny/step)*step;y<=maxy;y+=step){const sy=screen({x:0,y}).y;ctx.beginPath();ctx.moveTo(0,sy);ctx.lineTo(W,sy);ctx.stroke()}
for(const o of objects){if(!visible(o))continue;const p=screen(o),i=groups.findIndex(g=>g[1](o));if(p.x<0||p.x>W||p.y<0||p.y>H)continue;
ctx.beginPath();ctx.arc(p.x,p.y,o===selected?6:Math.max(2,Math.min(4.5,2.5*view.scale**0.25)),0,Math.PI*2);ctx.fillStyle=groups[i][2];ctx.fill();
if(o===selected){ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke()}}
ctx.font='11px system-ui';ctx.fillStyle='#8da4c4';ctx.fillText('Unreal units  |  top view (XY)',14,H-14)}
function resize(){const b=canvas.getBoundingClientRect();W=Math.max(1,Math.floor(b.width));H=Math.max(1,Math.floor(b.height));let dpr=window.devicePixelRatio||1;canvas.width=W*dpr;canvas.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);render()}
const section=document.getElementById('filters');groups.forEach((g,i)=>{let count=objects.filter(g[1]).length;
const label=document.createElement('label');label.className='filter';
const cb=document.createElement('input');cb.type='checkbox';cb.checked=true;cb.onchange=()=>{enabled[i]=cb.checked;render()};
const dot=document.createElement('span');dot.className='dot';dot.style.background=g[2];
const text=document.createTextNode(g[0]+' ('+count+')');label.append(cb,dot,text);section.appendChild(label)});
document.getElementById('search').oninput=e=>{filter=e.target.value.toLowerCase();render()};
document.getElementById('reset').onclick=()=>{view={cx:(bounds.minx+bounds.maxx)/2,cy:(bounds.miny+bounds.maxy)/2,scale:1};render()};
let dragging=false,origin=null,moved=false;
canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture(e.pointerId);dragging=true;moved=false;origin={x:e.offsetX,y:e.offsetY,cx:view.cx,cy:view.cy}});
canvas.addEventListener('pointermove',e=>{if(!dragging)return;let dx=e.offsetX-origin.x,dy=e.offsetY-origin.y;if(Math.abs(dx)+Math.abs(dy)>4)moved=true;
const k=baseScale()*view.scale;view.cx=origin.cx-dx/k;view.cy=origin.cy+dy/k;render()});
canvas.addEventListener('pointerup',e=>{dragging=false;if(moved)return;let best=null,dist=14;
for(const o of objects){if(!visible(o))continue;const p=screen(o),d=Math.hypot(e.offsetX-p.x,e.offsetY-p.y);if(d<dist){dist=d;best=o}}selected=best;
const el=document.getElementById('detail');el.textContent=best?`${best.name}\nClass: ${best.class}\nExport: #${best.export}\nX: ${best.x}\nY: ${best.y}\nZ: ${best.z}`:'Select an object to inspect.';el.style.whiteSpace='pre-line';render()});
canvas.addEventListener('wheel',e=>{e.preventDefault();let factor=Math.exp(-e.deltaY*0.001);view.scale=Math.max(0.15,Math.min(30,view.scale*factor));render()},{passive:false});
window.addEventListener('resize',resize);resize();
</script></body></html>'''
    page = page.replace('__TITLE__', path.name.replace('&','&amp;').replace('<','&lt;')).replace('__COUNT__',str(len(actors)))
    page = page.replace('__DATA__', points.replace('</','<\\/'))
    Path(package).write_text(page, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cmd = parser.add_subparsers(dest='command', required=True)
    for name in ('summary','actors','viewer','scripts'):
        sub=cmd.add_parser(name)
        sub.add_argument('package',type=Path)
        if name == 'actors': sub.add_argument('--json',type=Path)
        if name in ('viewer','scripts'): sub.add_argument('--output',type=Path,required=True)
    a = parser.parse_args()
    pkg = Package(a.package)
    if a.command == 'summary':
        print(f'Package: {pkg.path.name}\nSize: {len(pkg.data):,} bytes')
        print(f'Unreal file version: {pkg.version} | Ion licensee: {pkg.licensee}')
        print('Names: {:,} | Imports: {:,} | Exports: {:,}'.format(*pkg.table_counts))
        print('Most common classes:')
        for name,count in Counter(pkg.class_name(e) for e in pkg.exports).most_common(15):print(f'  {name:32} {count:5}')
    elif a.command in ('actors','viewer'):
        objects, failures=pkg.scene_actors()
        print(f'{pkg.path.name}: {len(objects)} objects with XYZ positions; {failures} actor parse errors')
        if a.command == 'actors':
            print('Classes:',dict(Counter(o['class'] for o in objects).most_common(15)))
            if a.json:
                a.json.write_text(json.dumps({'source':pkg.path.name,'objects':objects},indent=2),encoding='utf-8')
                print(f'Wrote {a.json}')
        else:
            make_viewer(pkg.path,a.output,objects)
            print(f'Wrote interactive viewer: {a.output}')
    elif a.command == 'scripts':
        a.output.mkdir(parents=True,exist_ok=True)
        extracted,errors=0,0
        for exp in pkg.exports:
            if pkg.class_name(exp) != 'TextBuffer':continue
            try: code=pkg.script_text(exp)
            except (ValueError,IndexError,struct.error):
                errors+=1;continue
            if not code:continue
            # Use class name from 'class Foo' if available; avoid unsanitized file paths.
            declaration=re.search(r'\bclass\s+(\w+)\b',code,re.I)
            if declaration: name=declaration.group(1)
            elif exp['outer']: name=pkg.ref_name(exp['outer'])
            else: name=exp['name']
            name=re.sub(r'[^A-Za-z0-9_-]','_',name)
            target=a.output / f'{name}_{exp["index"]}.uc'
            target.write_text(code,encoding='utf-8')
            extracted+=1
        print(f'Extracted {extracted} UnrealScript TextBuffers to {a.output} ({errors} failed).')

if __name__ == '__main__':
    try: main()
    except (OSError,ValueError,IndexError,KeyError) as ex:
        print(f'Error: {ex}',file=sys.stderr)
        sys.exit(1)