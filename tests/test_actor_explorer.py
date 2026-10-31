"""Fixture-free read-only DX2Ed Actor Explorer tests."""
import sys
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "actor_explorer"))
import dx2_actor_explorer as explorer

class TestActorExplorer(unittest.TestCase):
    def test_html_escapes_script_terminator(self):
        text = explorer.render_html({'actors': 1}, [{'name': '</script><script>alert(1)</script>', 'location': [0,0,0], 'class': 'Test'}])
        self.assertEqual(text.count('</script>'), 2)
        self.assertIn('<\/script>', text)

    def test_catalog_schema_is_validated(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'catalog.json'
            p.write_text('{"schema":"bad","properties":{}}')
            with self.assertRaises(ValueError):
                explorer.catalog_from_source(p)

    def test_synthetic_actor_script_link(self):
        class FakePackage:
            version = 95
            licensee = 68
            data = b'fake'
            exports = [{'index': 1}]
            def __init__(self, path):
                pass
            def scene_actors(self):
                return ([{'name':'Actor__0','class':'Actor','export':1,'x':1,'y':2,'z':3}], 0)
        with tempfile.TemporaryDirectory() as td:
            map_path = Path(td) / 'Demo.gmp'
            map_path.write_bytes(b'fake')
            logic_path = Path(td) / 'logic.json'
            logic_path.write_text(json.dumps({'schema':'DX2-SDK-0.17','actors':[
                {'map':'Demo.gmp','export':1,'scripts':['TS_42'],'definitions':[
                    {'id':'TS_42','title':'Test','actions':[], 'conditions':[]}
                ]}
            ]}))
            with patch.object(explorer,'Package',FakePackage), \
                patch.object(explorer,'mesh_metadata',return_value={}), \
                patch.object(explorer,'game_props_for_export',return_value=({'Location':{'X':1.25,'Y':2,'Z':3}},[])):
                meta, actors = explorer.actor_records(map_path, logic_index=logic_path)
            self.assertEqual(meta['actors'], 1)
            self.assertEqual(actors[0]['script_ids'], ['TS_42'])
            self.assertEqual(actors[0]['location'], [1.25,2,3])

if __name__=="__main__":
    unittest.main()
