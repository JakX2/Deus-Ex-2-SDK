"""Optional retail-data regression tests. Supply these via env; never ship assets."""
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'map_exporter'))
from dx2_map_exporter import resolve_map,run_export,load_transform_overrides
from dx2level import actor_matrix

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'Trier_transform_example.json'
if not EXAMPLE.is_file():
    EXAMPLE=ROOT/'map_exporter'/'Trier_transform_example.json'
@unittest.skipUnless(os.environ.get('DX2_TEST_TRIER'),'Set DX2_TEST_TRIER to directory holding original Trier GMP and IBD')
class TrierMapTests(unittest.TestCase):
    def test_trier_export_and_material_provenance(self):
        src=Path(os.environ['DX2_TEST_TRIER'])
        mapszip=Path(os.environ['DX2_TEST_SHARED'])
        original=(src/'M3_Germany_Trier.gmp').read_bytes()
        with tempfile.TemporaryDirectory() as td:
            result=run_export(resolve_map(src,'M3_Germany_Trier.gmp'),Path(td)/'Trier.glb',manual=[src/'m3_trier.ibd',mapszip],transform_overrides=EXAMPLE)
            self.assertEqual(result['placed_real_mesh_actors'],956)
            self.assertEqual(result['missing_mesh_actors'],[])
            self.assertEqual(result['alternate_skin_previews'],{'0_pipes-brownrust':'0_pipes-orange','0_pipes-brownrustdark':'0_pipes-orange'})
            self.assertIn('GO_globe-holo',result['shader_approximations'])
            self.assertIn('GEN_MEMBRANE-holocyan',result['shader_approximations'])
            self.assertEqual({x['actor'] for x in result['actor_transform_overrides_applied']},{'StaticMeshActor__92','StaticMeshActor__146'})
            glb=Path(td,'Trier.glb').read_bytes()
            self.assertEqual(glb[:4],b'glTF')
            self.assertEqual(struct.unpack_from('<I',glb,8)[0],len(glb))
            jlen=struct.unpack_from('<I',glb,12)[0]
            gltf=json.loads(glb[20:20+jlen])
            self.assertEqual(len([n for n in gltf['nodes'] if n['name']=='StaticMeshActor__92']),1)
            for name in ('StaticMeshActor__92','StaticMeshActor__146'):
                node=next(n for n in gltf['nodes'] if n['name']==name)
                self.assertEqual(node['extras']['DX2ExportScaleOverride'],[1,-1,1])
            for name in ('GO_globe-holo','GEN_MEMBRANE-holocyan'):
                material=next(m for m in gltf['materials'] if m['name']==name)
                self.assertEqual(material['alphaMode'],'BLEND')
            self.assertEqual((src/'M3_Germany_Trier.gmp').read_bytes(),original)

class OverrideValidationTests(unittest.TestCase):
    def test_exact_actor_ids(self):
        x=load_transform_overrides(EXAMPLE,'M3_Germany_Trier.gmp')
        self.assertEqual(sorted(x),['StaticMeshActor__146','StaticMeshActor__92'])
        self.assertEqual(x['StaticMeshActor__92'],(1,-1,1))
if __name__=='__main__': unittest.main()