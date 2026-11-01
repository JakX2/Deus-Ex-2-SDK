#!/usr/bin/env python3
"""DX2 Map Exporter: read-only retail GMP/IBD to textured GLB and JSON report.

Requires Python 3.9+; no non-standard dependencies. Run with `gui` or `list`
or `export`. Use game-owned files, never modify them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dx2level import export_level

MESH_SUFFIX = '.gmp'
SHARED_BUNDLES = ('Kernel_GFXALL.ibd', 'MainMenu_GFXALL.ibd')


@dataclass(frozen=True)
class LevelChoice:
    path: Path
    mission_bundle: Path | None
    shared_bundles: tuple[Path, ...]
    confidence: float


def locate_maps_dir(source: Path) -> Path:
    """Accept direct Maps directory, Content/DX2 directory or game install root."""
    source = source.expanduser().resolve()
    if source.is_file() and source.suffix.casefold() == '.gmp':
        source = source.parent
    candidates = [source, source/'Maps', source/'Content'/'DX2'/'Maps',
                  source/'DX2'/'Maps', source/'Content'/'Maps']
    for path in candidates:
        if path.is_dir() and any(p.suffix.casefold() == '.gmp' for p in path.iterdir() if p.is_file()):
            return path
    raise FileNotFoundError('No .gmp maps found. Select the game root, Content\\DX2 or Content\\DX2\\Maps folder.')


def _tokens(name: str) -> set[str]:
    return set(re.findall(r'[a-z]+\d*|\d+', Path(name).stem.lower()))


def _bundle_confidence(gmp: Path, ibd: Path) -> float:
    # DX2 filenames often omit the geographic label: M1_Seattle_Hub_Penthouse_Upper
    # is backed by m1_hub_penthouse_upper.ibd.
    a, b = _tokens(gmp.name), _tokens(ibd.name)
    if not a or not b:
        return 0
    shared = a & b
    if not shared or not any(t.startswith('m') and t[1:].isdigit() for t in shared):
        return 0
    return len(shared)/len(b) * 0.75 + len(shared)/len(a) * 0.25


def list_levels(source: Path) -> list[LevelChoice]:
    maps_dir = locate_maps_dir(source)
    maps = sorted((p for p in maps_dir.iterdir() if p.is_file() and p.suffix.casefold() == MESH_SUFFIX), key=lambda p:p.name.lower())
    ibds = [p for p in maps_dir.iterdir() if p.is_file() and p.suffix.casefold() == '.ibd']
    shared = tuple(p for name in SHARED_BUNDLES for p in ibds if p.name.casefold() == name.casefold())
    mission = [p for p in ibds if p not in shared and not p.stem.lower().endswith(('_gfxall','_phyall','_tsdall'))]
    rows = []
    for game_map in maps:
        scored = sorted(((_bundle_confidence(game_map,b),b) for b in mission), key=lambda r:(-r[0],r[1].name))
        score,bundle = scored[0] if scored else (0,None)
        # Do not silently select an unrelated mission bundle.
        if score < .67:
            score,bundle = 0,None
        rows.append(LevelChoice(game_map,bundle,shared,round(score,4)))
    return rows


def resolve_map(source: Path, name: str) -> LevelChoice:
    rows = list_levels(source)
    target = Path(name).name.casefold()
    choices = [r for r in rows if r.path.name.casefold() == target or r.path.stem.casefold() == Path(target).stem.casefold()]
    if len(choices)!=1:
        raise ValueError(f'Cannot uniquely find {name!r}. Use `list` to show available maps.')
    return choices[0]


def choose_bundles(level: LevelChoice, manual: Iterable[Path]) -> list[Path]:
    sources = [Path(x).expanduser().resolve() for x in manual]
    if not sources and level.mission_bundle:
        sources.append(level.mission_bundle)
    for shared in level.shared_bundles:
        if shared not in sources:
            sources.append(shared)
    if not sources:
        raise FileNotFoundError('No bundles found. Place .ibd resources in the Maps folder or pass --bundle path.')
    for p in sources:
        if not p.is_file():
            raise FileNotFoundError(f'Missing resource bundle: {p}')
    return sources



def load_transform_overrides(path: Path, map_name: str) -> dict[str, tuple[float,float,float]]:
    """Validate a per-map, export-only correction file. Never patch retail maps."""
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise ValueError(f'Invalid transform override JSON: {error}') from error
    if not isinstance(data,dict) or data.get('schema') != 'DX2Ed-transform-overrides-v1':
        raise ValueError('Expected schema DX2Ed-transform-overrides-v1')
    if data.get('map') != map_name:
        raise ValueError(f'Override map must be {map_name!r}; received {data.get("map")!r}')
    entries=data.get('actors')
    if not isinstance(entries,dict):
        raise ValueError('Transform override actors must be an object mapping actor names to scale arrays')
    if len(entries)>20000:
        raise ValueError('Too many overrides')
    from math import isfinite
    corrected={}
    for name, record in entries.items():
        if not isinstance(name,str) or not name.strip() or not isinstance(record,dict) or set(record) != {'scale'}:
            raise ValueError(f'Invalid override record for {name!r}: only scale is supported')
        values=record['scale']
        if not isinstance(values,list) or len(values)!=3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) or v==0 or abs(v)>100 for v in values):
            raise ValueError(f'Invalid scale for actor {name!r}: supply three finite, nonzero numbers (maximum magnitude 100)')
        corrected[name]=tuple(float(v) for v in values)
    return corrected

def run_export(level: LevelChoice, output: Path, manual: list[Path] | None=None, strict: bool=False, transform_overrides: Path | None=None, alternate_skin_fallback: bool=True, preview_club_stairs: bool=False) -> dict:
    output = output.expanduser().resolve()
    if output.suffix.casefold() != '.glb':
        raise ValueError('Output must end in .glb')
    if output == level.path:
        raise ValueError('Cannot overwrite source map')
    bundles = choose_bundles(level, manual or [])
    if not level.mission_bundle and not manual:
        raise ValueError('Mission bundle not confidently found. Pass --bundle MISSION.ibd manually.')
    if not level.shared_bundles and not any(p.suffix.casefold() == '.zip' for p in bundles):
        print('WARNING: No shared graphics bundle found; some models or materials may be missing.',file=sys.stderr)
    report_path = output.with_suffix('.report.json')
    # The original exporter runs read-only and embeds PNGs in the GLB.
    overrides=load_transform_overrides(transform_overrides,level.path.name) if transform_overrides else {}
    report = export_level(level.path,bundles,output,report_path,overrides,alternate_skin_fallback=alternate_skin_fallback,preview_club_stairs=preview_club_stairs)
    if report['missing_mesh_actors']:
        msg=f"WARNING: {len(report['missing_mesh_actors'])} placed static meshes were missing. Inspect {report_path}."
        print(msg,file=sys.stderr)
        if strict:
            raise ValueError(msg)
    return report


def run_gui(initial: Path | None = None) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    import threading
    import queue

    root=tk.Tk()
    root.title('DX2 Map Exporter 0.2 | Deus Ex: Invisible War')
    root.geometry('865x610')
    root.minsize(710,490)
    root.columnconfigure(0,weight=1)
    root.rowconfigure(3,weight=1)

    path_var=tk.StringVar(value=str(initial or Path.home()))
    out_var=tk.StringVar(value=str(Path.home()/'Desktop'/'DX2_Exports'))
    overrides_var=tk.StringVar(value='')
    alt_skins_var=tk.BooleanVar(value=True)
    status=tk.StringVar(value='Choose your Deus Ex Invisible War installation to scan for maps.')
    rows=[]
    events=queue.Queue()
    working=False

    def browse_game():
        val=filedialog.askdirectory(title='Select DX2 install, Content/DX2 or Maps')
        if val:path_var.set(val);scan()

    def browse_output():
        val=filedialog.askdirectory(title='Select export directory')
        if val:out_var.set(val)

    def browse_overrides():
        val=filedialog.askopenfilename(title='Optional map-specific transform overrides',filetypes=[('JSON files','*.json')])
        if val:overrides_var.set(val)

    def scan():
        nonlocal rows
        try: rows=list_levels(Path(path_var.get()))
        except Exception as e:
            rows=[]; status.set(str(e))
            messagebox.showerror('Cannot find game maps',str(e))
        tree.delete(*tree.get_children())
        for n,lv in enumerate(rows):
            tree.insert('','end',iid=str(n),values=(lv.path.name,lv.mission_bundle.name if lv.mission_bundle else 'NOT FOUND',
                                     ', '.join(x.name for x in lv.shared_bundles) or 'NOT FOUND'))
        status.set(f'{len(rows)} maps found. Pick one and click Export to GLB.' if rows else 'No maps found.')
        if rows:tree.selection_set('0')

    def export_selected():
        nonlocal working
        if working:return
        sel=tree.selection()
        if not sel:
            messagebox.showwarning('Select a map','Select a map from the list first.');return
        lv=rows[int(sel[0])]
        if not lv.mission_bundle:
            messagebox.showerror('Missing mission bundle','No matching mission .ibd could be identified. Use the CLI --bundle option.');return
        outdir=Path(out_var.get()).expanduser()
        output=outdir/(lv.path.stem+'.glb')
        if output.exists() and not messagebox.askyesno('Overwrite export?',f'Export file already exists:\n{output}\n\nReplace only this generated export?'):
            return
        working=True;button.config(state='disabled');bar.start(13)
        log.insert('end',f'Exporting {lv.path.name}...\n');log.see('end')
        status.set('Exporting; decoding meshes and textures. This may take a little while.')
        def worker():
            try:
                result=run_export(lv,output,transform_overrides=Path(overrides_var.get()) if overrides_var.get().strip() else None,alternate_skin_fallback=alt_skins_var.get())
                events.put(('ok',output,result))
            except Exception as e:events.put(('error',str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def pump():
        nonlocal working
        try:
            while True:
                kind,*data=events.get_nowait()
                working=False;button.config(state='normal');bar.stop()
                if kind=='error':
                    log.insert('end',f'ERROR: {data[0]}\n');status.set('Export failed. See log.');messagebox.showerror('Export error',data[0])
                else:
                    path,r=data
                    msg=(f'DONE: {path}\n{r["placed_real_mesh_actors"]} static mesh actors, '
                         f'{r["total_scene_triangles"]} triangles, {r["embedded_diffuse_images"]} embedded textures.\n'
                         f'Report: {path.with_suffix(".report.json")}\n')
                    log.insert('end',msg);status.set(f'Export completed: {path.name}')
                    messagebox.showinfo('GLB export complete',msg+'\nImport the .glb file in Blender via File > Import > glTF 2.0.')
                log.see('end')
        except queue.Empty:pass
        root.after(150,pump)

    top=ttk.LabelFrame(root,text='Game installation',padding=12);top.grid(row=0,column=0,sticky='ew',padx=12,pady=(10,5));top.columnconfigure(0,weight=1)
    ttk.Entry(top,textvariable=path_var).grid(row=0,column=0,sticky='ew')
    ttk.Button(top,text='Browse...',command=browse_game).grid(row=0,column=1,padx=6)
    ttk.Button(top,text='Scan maps',command=scan).grid(row=0,column=2)
    dst=ttk.LabelFrame(root,text='Export output folder',padding=12);dst.grid(row=1,column=0,sticky='ew',padx=12,pady=5);dst.columnconfigure(0,weight=1)
    ttk.Entry(dst,textvariable=out_var).grid(row=0,column=0,sticky='ew')
    ttk.Button(dst,text='Browse...',command=browse_output).grid(row=0,column=1,padx=6)
    ttk.Label(dst,text='Optional transform overrides JSON (per map):').grid(row=1,column=0,sticky='w',pady=(8,2))
    ttk.Entry(dst,textvariable=overrides_var).grid(row=2,column=0,sticky='ew')
    ttk.Button(dst,text='Browse...',command=browse_overrides).grid(row=2,column=1,padx=6)
    ttk.Checkbutton(dst,text='Approximate missing materials using available alternate mesh skins',variable=alt_skins_var).grid(row=3,column=0,sticky='w',pady=(7,0))
    ttk.Label(root,text='Select the map to export (mission resource bundle detected automatically):').grid(row=2,column=0,sticky='w',padx=15,pady=(8,2))
    mid=ttk.Frame(root);mid.grid(row=3,column=0,sticky='nsew',padx=12,pady=5);mid.columnconfigure(0,weight=1);mid.rowconfigure(0,weight=1)
    tree=ttk.Treeview(mid,columns=('map','mission','shared'),show='headings',selectmode='browse')
    for key,label,width in [('map','Map (.gmp)',280),('mission','Mission bundle (.ibd)',205),('shared','Shared resources',230)]:
        tree.heading(key,text=label);tree.column(key,width=width,stretch=True)
    tree.grid(row=0,column=0,sticky='nsew')
    ttk.Scrollbar(mid,orient='vertical',command=tree.yview).grid(row=0,column=1,sticky='ns')
    footer=ttk.Frame(root);footer.grid(row=4,column=0,sticky='ew',padx=12,pady=5)
    button=ttk.Button(footer,text='Export selected map to GLB',command=export_selected)
    button.pack(side='left')
    bar=ttk.Progressbar(footer,mode='indeterminate',length=200);bar.pack(side='left',padx=15)
    ttk.Label(root,textvariable=status,wraplength=800).grid(row=5,column=0,sticky='w',padx=15,pady=4)
    log=tk.Text(root,height=6,wrap='word');log.grid(row=6,column=0,sticky='ew',padx=12,pady=(3,10))
    root.after(150,pump)
    if initial:scan()
    root.mainloop()


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    a=sub.add_parser('list',help='List installed GMP maps and auto-matched resource bundles')
    a.add_argument('--game-root',type=Path,required=True)
    a.add_argument('--json',action='store_true',help='Output JSON rather than a text table')
    e=sub.add_parser('export',help='Export one map as textured GLB')
    e.add_argument('--game-root',type=Path,required=True)
    e.add_argument('--map',required=True,help='Map filename from the list command')
    e.add_argument('--output','-o',required=True,type=Path,help='New .glb output path')
    e.add_argument('--bundle',action='append',default=[],type=Path,help='Override/extra resource bundle; repeat in priority order')
    e.add_argument('--transform-overrides',type=Path,help='Per-map JSON with optional actor scale/mirror corrections')
    e.add_argument('--no-alternate-skins',action='store_true',help='Preserve unresolved original material placeholders rather than preview alternate mesh skins')
    e.add_argument('--strict',action='store_true',help='Fail if placed static meshes are missing (export/report still created)')
    g=sub.add_parser('gui',help='Open a desktop graphical map chooser')
    g.add_argument('--game-root',type=Path)
    args=parser.parse_args(argv)
    if args.command=='gui':
        run_gui(args.game_root)
    elif args.command=='list':
        rows=list_levels(args.game_root)
        if args.json:
            print(json.dumps([{'map':str(r.path),'mission_bundle':str(r.mission_bundle) if r.mission_bundle else None,
                               'shared_bundles':list(map(str,r.shared_bundles)), 'confidence':r.confidence} for r in rows],indent=2))
        else:
            for r in rows: print(f'{r.path.name:55} | {(r.mission_bundle.name if r.mission_bundle else "MISSING"):35} | match={r.confidence:.2f}')
            print(f'Found {len(rows)} maps.')
    elif args.command=='export':
        level=resolve_map(args.game_root,args.map)
        report=run_export(level,args.output,args.bundle,args.strict,args.transform_overrides,not args.no_alternate_skins)
        print(json.dumps({'status':'ok','glb':str(args.output.resolve()),'report':str(args.output.with_suffix('.report.json').resolve()),
                          'actors':report['placed_real_mesh_actors'],'triangles':report['total_scene_triangles'],
                          'embedded_textures':report['embedded_diffuse_images'],
                          'missing_mesh_actors':len(report['missing_mesh_actors']),
                          'transform_overrides_applied':len(report['actor_transform_overrides_applied'])},indent=2))
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (FileNotFoundError,ValueError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);sys.exit(2)