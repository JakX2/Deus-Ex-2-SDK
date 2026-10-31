#!/usr/bin/env python3
"""Generate wholly original glTF cubes and DX2Ed-shaped actor metadata.

No retail game data, models, textures or copyrighted assets are used.
"""
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'godot_editor' / 'demo'


def generate_demo(root=ROOT):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    # Cube mesh with 8 vertices; double-sided material so every face can be seen.
    points = [(-1., -1., -1.), (1., -1., -1.), (1., 1., -1.), (-1., 1., -1.),
              (-1., -1., 1.), (1., -1., 1.), (1., 1., 1.), (-1., 1., 1.)]
    indices = [0,2,1,0,3,2, 4,5,6,4,6,7, 0,1,5,0,5,4, 2,3,7,2,7,6,
               1,2,6,1,6,5, 0,4,7,0,7,3]
    pbytes = b''.join(struct.pack('<fff', *p) for p in points)
    ibytes = b''.join(struct.pack('<H', i) for i in indices)
    buffer = pbytes + ibytes
    gltf = {
        'asset': {'version': '2.0', 'generator': 'DX2Ed native synthetic fixture'},
        'scene': 0,
        'scenes': [{'nodes': [0, 1]}],
        'nodes': [
            {'name': 'StaticMeshActor__1', 'mesh': 0, 'translation': [-3.5, 0., 0.]},
            {'name': 'StaticMeshActor__2', 'mesh': 0, 'translation': [3.5, 0., 0.]},
        ],
        'buffers': [{'byteLength': len(buffer)}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0, 'byteLength': len(pbytes), 'target': 34962},
            {'buffer': 0, 'byteOffset': len(pbytes), 'byteLength': len(ibytes), 'target': 34963},
        ],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': len(points), 'type': 'VEC3',
             'min': [-1., -1., -1.], 'max': [1., 1., 1.]},
            {'bufferView': 1, 'componentType': 5123, 'count': len(indices), 'type': 'SCALAR'},
        ],
        'materials': [{'name': 'Original demo yellow', 'doubleSided': True,
                       'pbrMetallicRoughness': {'baseColorFactor': [0.98, 0.72, 0.2, 1.0],
                                                'metallicFactor': 0.0, 'roughnessFactor': 0.7}}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1, 'material': 0}]}],
    }
    j = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    j += b' ' * (-len(j) % 4)
    buffer += b'\0' * (-len(buffer) % 4)
    glb = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(j) + 8 + len(buffer))
    glb += struct.pack('<II', len(j), 0x4E4F534A) + j
    glb += struct.pack('<II', len(buffer), 0x004E4942) + buffer
    (root / 'scene.glb').write_bytes(glb)
    actors = []
    for index in (1, 2):
        actors.append({'name': f'StaticMeshActor__{index}', 'class': 'StaticMeshActor',
                       'export': index, 'location': [-3.5 if index == 1 else 3.5, 0., 0.],
                       'rotation': [0, 0, 0], 'mesh': {'name': 'OriginalDemoCube'},
                       'tagged': {'test_note': 'Synthetic authored fixture; not a DX2 asset'},
                       'game_properties': [], 'scripts': []})
    (root / 'actors.json').write_text(json.dumps({
        'meta': {'schema': 'DX2Ed-fixture-original', 'actors': len(actors), 'read_only': True},
        'actors': actors}, indent=2), encoding='utf-8')
    return root


if __name__ == '__main__':
    print(generate_demo())
