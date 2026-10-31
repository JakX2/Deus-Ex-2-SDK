#!/usr/bin/env python3
"""DX2Ed 3D Actor Explorer 0.2, read-only GMP/IBD -> GLB + actor inspector.

No Node/npm/network/third-party Python packages required. WebGL2 browser required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import threading
import time
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Works as a self-contained ZIP or inside the multi-tool GitHub checkout.
for _folder in ('map_exporter', 'actor_explorer'):
    _candidate = Path(__file__).resolve().parents[1] / _folder
    if _candidate.is_dir():
        sys.path.insert(0, str(_candidate))
from dx2_map_exporter import list_levels, run_export
from dx2_actor_explorer import actor_records

TEMPLATE = Path(__file__).with_name('viewer.html')


def build(map_file: Path, output_dir: Path, *, bundles=(), system=None, logic_index=None,
          override_json=None, existing_glb=None) -> dict:
    """Build standalone viewer directory without altering game-owned files."""
    map_file = Path(map_file).expanduser().resolve()
    if not map_file.is_file() or map_file.suffix.lower() != '.gmp':
        raise FileNotFoundError(f'Expected an original .gmp map: {map_file}')
    output_dir = Path(output_dir).expanduser().resolve()
    if output_dir == map_file.parent or (map_file.parent.name.casefold() == 'maps' and output_dir.is_relative_to(map_file.parent)):
        raise ValueError('Do not write the generated viewer into the game Maps folder')
    if not TEMPLATE.is_file():
        raise FileNotFoundError('viewer.html is missing from the installation')
    output_dir.mkdir(parents=True, exist_ok=True)
    glb_path = output_dir/'scene.glb'
    report_path = output_dir/'scene.report.json'
    if existing_glb is None:
        manual = [Path(b).expanduser().resolve() for b in bundles]
        matches = [x for x in list_levels(map_file.parent) if x.path.resolve() == map_file]
        if not matches:
            raise ValueError('Map could not be found during resource lookup')
        level = matches[0]
        if not manual and not level.mission_bundle:
            raise ValueError('Matching IBD bundle not found. Supply one with --bundle.')
        report = run_export(level, glb_path, manual=manual,
                            transform_overrides=Path(override_json) if override_json else None)
    else:
        src = Path(existing_glb).expanduser().resolve()
        if not src.is_file() or src.suffix.lower() != '.glb':
            raise FileNotFoundError(f'Expected an existing exported .glb: {src}')
        # Reuse only GLBs created by DX2Ed for the same map hash. Guard against stale actor IDs.
        with src.open('rb') as f:
            import struct
            if f.read(4) != b'glTF':
                raise ValueError('Existing scene is not a GLB')
            f.seek(12)
            ln, typ = struct.unpack('<II', f.read(8))
            if typ != 0x4e4f534a or ln > 150_000_000:
                raise ValueError('Unsupported GLB JSON chunk')
            doc = json.loads(f.read(ln))
        extras = doc.get('asset', {}).get('extras', {})
        if extras.get('DX2SourceMapSHA256') != hashlib.sha256(map_file.read_bytes()).hexdigest():
            raise ValueError('Existing GLB source map SHA-256 does not match the chosen GMP')
        if src != glb_path:
            shutil.copyfile(src, glb_path)
        report = {'reused_existing_glb': src.name, 'placed_real_mesh_actors': sum(1 for n in doc.get('nodes', []) if 'DX2ExportIndex' in n.get('extras', {})),
                  'output_glb_bytes': glb_path.stat().st_size}
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    meta, actors = actor_records(map_file, Path(system) if system else None,
                                 Path(logic_index) if logic_index else None)
    meta.update({'schema': 'DX2Ed-ActorExplorer-3D-0.2', '3d_scene': True, 'glb': 'scene.glb',
                 'rendering': 'local WebGL2; no external JS libraries', 'exported_mesh_nodes': report['placed_real_mesh_actors']})
    (output_dir/'actors.json').write_text(json.dumps({'meta': meta, 'actors': actors}, ensure_ascii=True), encoding='utf-8')
    shutil.copyfile(TEMPLATE, output_dir/'index.html')
    (output_dir/'scene.report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return {'folder':str(output_dir), 'map':map_file.name, 'actors':len(actors),
            'renderable_actor_meshes':report['placed_real_mesh_actors'],
            'scene_bytes':glb_path.stat().st_size, 'read_only':True,
            'open_command':f'python dx2ed_3d.py serve --folder "{output_dir}"'}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        super().end_headers()


def serve(folder:Path, *, open_browser=True):
    folder = Path(folder).expanduser().resolve()
    for name in ('index.html','actors.json','scene.glb'):
        if not (folder/name).is_file():
            raise FileNotFoundError(f'Viewer folder is missing {name}: {folder}')
    with ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(folder))) as httpd:
        url = f'http://127.0.0.1:{httpd.server_port}/index.html'
        print(f'DX2Ed 3D viewer: {url}', flush=True)
        print('Read-only viewer. Leave this window open; Ctrl+C to stop.', flush=True)
        if open_browser:
            threading.Timer(.5, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    import queue
    root = tk.Tk(); root.title('DX2Ed 3D Actor Explorer 0.2'); root.geometry('840x485')
    vars = {x:tk.StringVar() for x in ('map','output','bundle','system','logic','existing')}
    vars['output'].set(str(Path.home()/'Documents'/'DX2Ed_3D_Exports'))
    jobs=queue.Queue(); working=False
    rows=[('map','DX2 map (.gmp)', False),('bundle','Optional matching .ibd bundle (if not auto detected)',False),
          ('output','Generated viewer directory',True),('system','Optional System folder / System.zip / property catalog',False),
          ('logic','Optional DX2 mission logic index JSON',False),('existing','Optional existing GLB from DX2Ed map exporter',False)]
    for i,(key,label,isdir) in enumerate(rows):
        ttk.Label(root,text=label).grid(row=i*2,column=0,columnspan=2,sticky='w',padx=15,pady=(9,0))
        ttk.Entry(root,textvariable=vars[key],width=100).grid(row=i*2+1,column=0,sticky='ew',padx=(15,4))
        def choose(k=key,d=isdir):
            if k in ('output', 'system'):
                p=filedialog.askdirectory(title='Select directory')
            else:
                filt={'map':[('DX2 maps','*.gmp')], 'bundle':[('Resources','*.ibd *.zip')],
                      'logic':[('JSON','*.json')], 'existing':[('GLB','*.glb')]}.get(k,[('All files','*.*')])
                p=filedialog.askopenfilename(filetypes=filt)
            if p:vars[k].set(p)
        ttk.Button(root,text='Browse...',command=choose).grid(row=i*2+1,column=1,padx=(0,15))
    root.columnconfigure(0,weight=1)
    label=tk.StringVar(value='Select a DX2 map and generate the textured 3D viewer. No game files will be modified.')
    def begin():
        nonlocal working
        if working:return
        if not vars['map'].get():messagebox.showwarning('Choose a map','Select a .gmp first');return
        working=True;go.configure(state='disabled');label.set('Exporting and reading actors...')
        args={k: v.get().strip() for k,v in vars.items()}
        def worker():
            try:
                folder=Path(args['output'])/Path(args['map']).stem
                result=build(Path(args['map']), folder, bundles=[args['bundle']] if args['bundle'] else [],
                             system=args['system'] or None,logic_index=args['logic'] or None,existing_glb=args['existing'] or None)
                jobs.put(('ok',result))
            except Exception as exc:jobs.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True).start()
    def pump():
        nonlocal working
        try:
            kind,payload=jobs.get_nowait();working=False;go.configure(state='normal')
            if kind=='error':label.set('Export failed.');messagebox.showerror('DX2Ed 3D export',payload)
            else:
                label.set(f"Created {payload['actors']} actors, {payload['renderable_actor_meshes']} 3D actor meshes")
                messagebox.showinfo('Ready', '3D scene created. The browser will open. Keep the viewer window running until finished.')
                threading.Thread(target=serve,args=(Path(payload['folder']),),daemon=True).start()
        except queue.Empty:pass
        root.after(150,pump)
    go=ttk.Button(root,text='Build and open 3D Actor Explorer',command=begin)
    go.grid(row=len(rows)*2,column=0,columnspan=2,pady=14)
    ttk.Label(root,textvariable=label,wraplength=790).grid(row=len(rows)*2+1,column=0,columnspan=2,padx=12)
    root.after(150,pump);root.mainloop()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='command')
    b=subs.add_parser('build', help='Create a textured viewer folder from a DX2 map')
    b.add_argument('--map',required=True,type=Path)
    b.add_argument('--output-dir',required=True,type=Path)
    b.add_argument('--bundle',action='append',type=Path,default=[])
    b.add_argument('--system',type=Path)
    b.add_argument('--logic-index',type=Path)
    b.add_argument('--overrides',type=Path)
    b.add_argument('--existing-glb',type=Path)
    s=subs.add_parser('serve',help='Open a generated viewer on localhost')
    s.add_argument('--folder',required=True,type=Path)
    s.add_argument('--no-open',action='store_true')
    subs.add_parser('gui',help='Open the Windows graphical launcher')
    args=parser.parse_args()
    if args.command=='build':
        result=build(args.map,args.output_dir,bundles=args.bundle,system=args.system,
                     logic_index=args.logic_index,override_json=args.overrides,
                     existing_glb=args.existing_glb)
        print(json.dumps(result, indent=2))
    elif args.command=='serve':serve(args.folder,open_browser=not args.no_open)
    else:gui()


if __name__=='__main__':main()