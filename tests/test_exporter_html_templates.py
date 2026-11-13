"""Source-free regression for standalone exporter HTML templates.

The pages were extracted verbatim from the old inline Python literals.
These tests ensure the file-based templates load regardless of cwd, retain
interactive contracts and embed correctly escaped actor/texture data.
"""
from __future__ import annotations

import base64
from pathlib import Path
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'map_exporter'))

from dx2inspect import make_viewer
from dx2textures import Texture, gallery, to_png


class ExporterTemplateTests(unittest.TestCase):
    def test_inspector_template_loads_from_module_not_cwd(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            out=root/'positions.html'
            source=Path('Synthetic<&>_Map.gmp')
            actors=[{
                "name":"SyntheticActor </script><script>alert(1)</script>",
                "class":"StaticMeshActor","export":7,
                "x":10.5,"y":-3.0,"z":0.,
            }]
            previous=Path.cwd()
            try:
                os.chdir(root)
                make_viewer(source,out,actors)
            finally:
                os.chdir(previous)
            contents=out.read_text(encoding='utf-8')
            self.assertTrue(contents.startswith('<!DOCTYPE html>'))
            self.assertIn('DX2 level object inspector',contents)
            self.assertIn('Synthetic&lt;>',contents)
            self.assertIn('1 positioned objects',contents)
            self.assertIn('const objects=[',contents)
            self.assertIn('<\\/script>',contents)  # embedded data cannot close script
            self.assertNotIn('__DATA__',contents)
            self.assertNotIn('__COUNT__',contents)
            self.assertNotIn('__TITLE__',contents)
            self.assertIn('getElementById(\'chart\')',contents)
            self.assertIn('pointerdown',contents)

    def test_gallery_template_works_outside_repo_and_keeps_embedded_png(self):
        tex=Texture(
            'Synthetic <texture>', 'BGRX8', 2, 2, 0,
            [(2,2,bytes.fromhex(
                '00 00 ff 00 00 ff 00 01 ff 00 00 02 ff ff ff 03'))],
            'SYNTHETIC_ONLY',
        )
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            out=root/'textures.html'
            previous=Path.cwd()
            try:
                os.chdir(root)
                written=gallery({'synthetic':tex},{},out)
            finally:
                os.chdir(previous)
            self.assertEqual(written,out)
            page=out.read_text(encoding='utf-8')
            self.assertIn('DX2 Texture Explorer',page)
            self.assertIn('SYNTHETIC_ONLY',page)
            self.assertIn('data:image/png;base64,',page)
            self.assertIn(base64.b64encode(to_png(tex)).decode('ascii'),page)
            self.assertIn('Synthetic <texture>',page)
            self.assertIn('grid.replaceChildren()',page)
            self.assertNotIn('/*DATA*/',page)

    def test_missing_template_is_not_silently_replaced_by_empty_html(self):
        # The two templates are explicit runtime files. A partial deployment
        # must be detected as a missing package file, not an empty view.
        source=ROOT/'map_exporter'/'templates'
        self.assertTrue((source/'dx2inspect_viewer.html').is_file())
        self.assertTrue((source/'texture_gallery.html').is_file())
        for filename in ('dx2inspect_viewer.html','texture_gallery.html'):
            self.assertGreater((source/filename).stat().st_size,1000)


if __name__=='__main__':
    unittest.main()
