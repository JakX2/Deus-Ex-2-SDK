#!/usr/bin/env python3
"""Build an optional read-only property-name catalog from owned game packages."""
from collections import Counter
import json
import pathlib
import re
import tempfile
import zipfile
from dx2inspect import Package

PACKAGE_FILES = ['AICore.d2u', 'Core.d2u', 'DX2AI.d2u', 'DX2Game.d2u',
                 'DX2Gamesys.d2u', 'Editor.d2u', 'Engine.d2u', 'Fire.d2u']

def source_packages(path):
    path = pathlib.Path(path)
    if path.is_dir():
        for name in PACKAGE_FILES:
            target = path / name
            if target.is_file():
                yield target, name
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix='dx2cat_') as tmp:
            for member in archive.namelist():
                basename = pathlib.PurePosixPath(member).name
                if basename not in PACKAGE_FILES:
                    continue
                dest = pathlib.Path(tmp) / basename
                dest.write_bytes(archive.read(member))
                yield dest, basename
    else:
        raise FileNotFoundError('Provide your own System folder or .zip of .d2u packages')

def parse_declarations(script):
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', script, flags=re.S)
    for stmt in re.finditer(r'\bvar\b[^;]*;', clean, flags=re.I):
        item = stmt.group()
        ident = re.search(r'\b(inherited|runtimeinstantiated)\s*\(\s*(\d+)\s*\)', item, re.I)
        if not ident:
            continue
        tail = item[ident.end():].strip().rstrip(';').strip()
        tail = re.sub(r'".*$', '', tail, flags=re.S)
        tail = re.sub(r'\s*\[\s*\w+\s*\]\s*$', '', tail)
        name_match = re.search(r'([A-Za-z_]\w*)\s*$', tail)
        if not name_match:
            continue
        prop_name = name_match.group(1)
        type_part = tail[:name_match.start()].strip()
        bf = re.search(r'\bbitfield\s+(\w+)\s*\{', type_part, re.I)
        en = re.search(r'\benum\s+(\w+)\s*\{', type_part, re.I)
        if bf:
            type_name = 'bitfield<' + bf.group(1) + '>'
        elif en:
            type_name = 'enum<' + en.group(1) + '>'
        else:
            match = re.search(r'(?:array|class)\s*<[^>]+>|[A-Za-z_]\w*\s*$', type_part, re.I)
            type_name = match.group(0).strip() if match else 'unknown'
        yield {'id': int(ident.group(2)), 'name': prop_name, 'type': type_name,
               'kind': ident.group(1).lower()}

def build_catalog(path):
    path = pathlib.Path(path)
    catalog = {'schema': 'dx2-catalog-0.1', 'source': path.name, 'packages': {},
               'classes': {}, 'properties': {}, 'warnings': []}
    for file, name in source_packages(path):
        pkg = Package(file)
        found = 0
        declarations = 0
        for exp in pkg.exports:
            if pkg.class_name(exp) != 'TextBuffer' or not exp['size']:
                continue
            try:
                source = pkg.script_text(exp)
            except (ValueError, IndexError) as ex:
                catalog['warnings'].append(f'{name} export #{exp["index"]}: {ex}')
                continue
            if not source:
                continue
            found += 1
            m = re.search(r'\bclass\s+(\w+)\s+extends\s+(\w+)', source, re.I)
            if m:
                class_name, parent = m.groups()
            else:
                class_name = pkg.ref_name(exp['outer']) if exp['outer'] else exp['name']
                parent = None
            qual = f'{pathlib.Path(name).stem}.{class_name}'
            catalog['classes'][qual] = {'base': parent, 'package': name}
            for prop in parse_declarations(source):
                pid = str(prop['id'])
                prop['declared_in'] = qual
                if pid in catalog['properties']:
                    if catalog['properties'][pid]['name'] != prop['name']:
                        catalog['warnings'].append(
                            f'ID {pid} declared as {prop["name"]} and {catalog["properties"][pid]["name"]}')
                else:
                    catalog['properties'][pid] = prop
                declarations += 1
        catalog['packages'][name] = {'version': pkg.version, 'licensee': pkg.licensee,
                                      'text_buffers': found, 'declarations': declarations,
                                      'exports': len(pkg.exports)}
    catalog['stats'] = {'text_buffers': sum(v['text_buffers'] for v in catalog['packages'].values()),
                        'classes': len(catalog['classes']),
                        'property_ids': len(catalog['properties']),
                        'warnings': len(catalog['warnings'])}
    return catalog
