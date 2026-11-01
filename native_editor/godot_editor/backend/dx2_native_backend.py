#!/usr/bin/env python3
"""DX2Ed native 0.2: read-only retail GMP + IBD -> cached Godot scene + actors.

No game data is redistributed. All output is written to a separate user-selected
cache. No changes to the source GMP, IBD, or other game files are made.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

# Support both the standalone ZIP (sibling modules) and the GitHub repository
# (where existing parsers live in map_exporter/ and actor_explorer/).
root = Path(__file__).resolve().parents[3]
for relative in ('map_exporter', 'actor_explorer'):
    folder = root / relative
    if folder.is_dir():
        sys.path.insert(0, str(folder))
from dx2_map_exporter import list_levels, choose_bundles, run_export
from dx2_actor_explorer import actor_records
from dx2_asset_catalog import catalog_from_paths
from dx2_archetype_catalog import catalog_for_map
from dx2placement import analyze_mesh_placement, summarize_placement
from dx2level import load_resource_index
from dx2bundles import parse_mesh

CACHE_VERSION = 'DX2Ed-Native-map-cache-v0.2.6-actor-skins-v1'

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def map_inputs(map_path: Path, manual_bundles: list[Path]):
    map_path = map_path.expanduser().resolve()
    if map_path.suffix.lower() != '.gmp' or not map_path.is_file():
        raise ValueError(f'Map must be an existing .gmp file: {map_path}')
    matches = [x for x in list_levels(map_path.parent) if x.path.resolve() == map_path]
    if len(matches) != 1:
        raise ValueError('Could not uniquely identify this map in its Maps folder')
    level = matches[0]
    if not level.mission_bundle and not manual_bundles:
        raise ValueError('Matching .ibd bundle not found; place it alongside the .gmp or specify --bundle')
    bundles = choose_bundles(level, manual_bundles)
    return level, bundles

def get_cache_key(map_path: Path, bundles: list[Path], system_path: Path | None = None, preview_club_stairs: bool = False):
    sources = {'map': {'name': map_path.name, 'sha256': sha256(map_path)},
               'bundles': [{'name': p.name, 'sha256': sha256(p)} for p in bundles]}
    if system_path is not None:
        if system_path.is_dir():
            system_files = sorted(p for p in system_path.rglob('*')
                                  if p.is_file() and p.suffix.lower() in ('.d2u', '.u', '.ini'))
            sources['system'] = [(p.relative_to(system_path).as_posix(),
                                  p.stat().st_size, p.stat().st_mtime_ns) for p in system_files]
        else:
            sources['system'] = {'name': system_path.name, 'sha256': sha256(system_path)}
    payload = json.dumps({'version': CACHE_VERSION, 'inputs': sources, 'preview_club_stairs': bool(preview_club_stairs)}, sort_keys=True)
    return hashlib.sha256(payload.encode('utf8')).hexdigest()[:20], sources

def enrich_placement_report(actors: list[dict], bundles: list[Path], report: dict) -> bool:
    """Attach source bounds evidence by original export index, never by display name.

    Existing caches are upgraded without changing their key or visual drafts.
    Failures remain explicit diagnostic gaps rather than guessed transforms.
    """
    details = report.get('placement_actor_details')
    if not isinstance(details, list):
        _, indexes, _ = load_resource_index(bundles)
        cache = {}
        details = []
        for actor in actors:
            mesh_name = actor.get('mesh')
            if not isinstance(mesh_name, str) or not mesh_name:
                continue
            resource_key = mesh_name.casefold()
            if resource_key not in cache:
                source = indexes[4].get(resource_key)
                if source is None:
                    cache[resource_key] = None
                else:
                    try:
                        cache[resource_key] = (parse_mesh(*source), source[0].name)
                    except (ValueError, IndexError, OSError, TypeError):
                        cache[resource_key] = None
            mesh_pair = cache[resource_key]
            if mesh_pair is None:
                continue
            mesh, bundle_name = mesh_pair
            entry = {'name': actor['name'], 'export': actor.get('export'),
                     'x': actor['location'][0], 'y': actor['location'][1],
                     'z': actor['location'][2],
                     'rotation': actor.get('rotation'), 'mesh': {
                         'name': mesh_name, 'bounds': actor.get('mesh_bounds'),
                     }}
            details.append(analyze_mesh_placement(entry, mesh, bundle_name))
        report['placement_actor_details'] = details
        report['placement_audit'] = summarize_placement(details)
    by_export = {item.get('export'): item for item in details
                 if isinstance(item, dict) and type(item.get('export')) is int}
    changed = False
    for actor in actors:
        diagnostic = by_export.get(actor.get('export'))
        if diagnostic is not None and actor.get('placement_diagnostic') != diagnostic:
            actor['placement_diagnostic'] = diagnostic
            changed = True
    return changed


def build(map_path: Path, output_root: Path, *, manual_bundles: list[Path] | None = None,
          system_path: Path | None = None, force: bool = False,
          preview_club_stairs: bool = False) -> dict:
    level, bundles = map_inputs(map_path, manual_bundles or [])
    map_path = level.path.resolve()
    output_root = Path(output_root).expanduser().resolve()
    if output_root == map_path.parent or output_root.is_relative_to(map_path.parent):
        raise ValueError('Output cache must be outside the retail Maps folder')
    if system_path is not None:
        system_path = Path(system_path).expanduser().resolve()
        if not system_path.exists():
            raise FileNotFoundError(f'System source not found: {system_path}')
    key, source_hashes = get_cache_key(map_path, bundles, system_path, preview_club_stairs)
    folder = output_root / (map_path.stem + '_' + key)
    glb = folder / 'scene.glb'
    actor_json = folder / 'actors.json'
    report_json = folder / 'scene.report.json'
    assets_json = folder / 'assets.json'
    archetypes_json = folder / 'archetypes.json'
    manifest_path = folder / 'source_manifest.json'
    if not force and all(p.is_file() for p in (glb, actor_json, assets_json, report_json, manifest_path)):
        try:
            doc = json.loads(manifest_path.read_text(encoding='utf8'))
            actors_doc = json.loads(actor_json.read_text(encoding='utf8'))
            if (doc.get('key') == key and doc.get('version') == CACHE_VERSION and
                glb.stat().st_size > 20 and
                actors_doc.get('meta', {}).get('source_sha256') == source_hashes['map']['sha256']):
                # Upgrade older private caches in place without changing the
                # cache key (and thus without abandoning saved prop drafts).
                asset_doc = json.loads(assets_json.read_text(encoding='utf8'))
                expected_sources = [str(p.resolve()) for p in bundles]
                if asset_doc.get('source_paths') != expected_sources:
                    asset_doc['source_paths'] = expected_sources
                    assets_json.write_text(json.dumps(asset_doc, indent=2), encoding='utf8')
                if not archetypes_json.is_file():
                    archetypes_json.write_text(
                        json.dumps(catalog_for_map(actors_doc['actors'], system_path), ensure_ascii=True),
                        encoding='utf8')
                cached_report = json.loads(report_json.read_text(encoding='utf8'))
                had_audit = isinstance(cached_report.get('placement_actor_details'), list)
                if enrich_placement_report(actors_doc['actors'], bundles, cached_report):
                    actor_json.write_text(json.dumps(actors_doc, ensure_ascii=True), encoding='utf8')
                if not had_audit:
                    report_json.write_text(json.dumps(cached_report, indent=2), encoding='utf8')
                return {'status': 'ok', 'cached': True, 'folder': str(folder),
                        'glb': str(glb), 'actors_json': str(actor_json),
                        'assets_json': str(assets_json),
                        'archetypes_json': str(archetypes_json),
                        'map': map_path.name, 'actors': len(actors_doc['actors'])}
        except (OSError, ValueError, KeyError, TypeError):
            pass
    folder.mkdir(parents=True, exist_ok=True)
    try:
        report = run_export(level, glb, manual=bundles,
                            preview_club_stairs=preview_club_stairs)
        meta, actors = actor_records(map_path, system_path)
        # Match exporter decisions by the original package export index, not
        # by the display name. Keep original game properties intact.
        decisions = {int(item['export']): {
            'requested': item['requested'],
            'selected': item['selected'],
            'status': item['status'],
            'materials': item.get('material_status', [])}
            for item in report.get('actor_skin_selections', [])}
        for actor in actors:
            choice = decisions.get(int(actor.get('export', -1)))
            if choice:
                actor['render_skin'] = choice
        enrich_placement_report(actors, bundles, report)
        meta.update({'cache_version': CACHE_VERSION,
                     'source_sha256': source_hashes['map']['sha256'],
                     'source_map': map_path.name, 'glb': 'scene.glb'})
        actor_json.write_text(json.dumps({'meta': meta, 'actors': actors}, ensure_ascii=True), encoding='utf8')
        asset_doc = catalog_from_paths(bundles)
        # Local-only paths are required for later on-demand GLB previews.
        # They are never part of GitHub, glTF, or the game's retail files.
        asset_doc['source_paths'] = [str(p.resolve()) for p in bundles]
        assets_json.write_text(json.dumps(asset_doc, ensure_ascii=True), encoding='utf8')
        archetypes_json.write_text(json.dumps(
            catalog_for_map(actors, system_path), ensure_ascii=True), encoding='utf8')
        report_json.write_text(json.dumps(report, indent=2), encoding='utf8')
        manifest_path.write_text(json.dumps({'version': CACHE_VERSION, 'key': key,
                                             'sources': source_hashes,
                                             'actors': len(actors)}, indent=2), encoding='utf8')
    except Exception:
        for path in (glb, actor_json, assets_json, archetypes_json, report_json, manifest_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return {'status': 'ok', 'cached': False, 'folder': str(folder),
            'glb': str(glb), 'actors_json': str(actor_json),
            'assets_json': str(assets_json),
            'archetypes_json': str(archetypes_json),
            'map': map_path.name, 'actors': len(actors),
            'mesh_actors': report.get('placed_real_mesh_actors'),
            'missing_mesh_actors': len(report.get('missing_mesh_actors', []))}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, action='append', default=[])
    parser.add_argument('--system', type=Path)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--preview-club-stairs', action='store_true',
                        help='Experimental Seattle Club stair Roll preview; changes GLB only')
    parser.add_argument('--inspect', action='store_true',
                        help='Only locate required resource bundles; do not export')
    args = parser.parse_args(argv)
    try:
        if args.inspect:
            level, bundles = map_inputs(args.map, args.bundle)
            result = {'status': 'ok', 'map': str(level.path),
                      'confidence': level.confidence,
                      'bundles': [str(p) for p in bundles]}
        else:
            result = build(args.map, args.output_root,
                           manual_bundles=args.bundle,
                           system_path=args.system, force=args.force,
                           preview_club_stairs=args.preview_club_stairs)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'error', 'message': str(error)}), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
