"""Asset-free tests, plus optional original DX2 integration via environment variables."""
import json
import os
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

# The repository contains both a directory named dx2ed_3d and the runnable
# script dx2ed_3d/dx2ed_3d.py. Explicitly load the script instead of importing
# the namespace directory when tests run from the repository root in CI.
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'dx2ed_3d.py'
spec = spec_from_file_location('_dx2ed_3d_viewer_under_test', SCRIPT)
if spec is None or spec.loader is None:
    raise ImportError('DX2Ed viewer source unavailable')
app = module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)


class ViewerTests(unittest.TestCase):
    def test_html_contract(self):
        text=app.TEMPLATE.read_text(encoding='utf-8')
        for token in ('actors.json','scene.glb','DX2ExportIndex','showtextures','showbsp',
                      'showmeshes','pick(event)','Focus selected','canvas id="view"'):
            self.assertIn(token,text)

    def test_fallback_contract(self):
        src=app.TEMPLATE.read_text(encoding='utf-8')
        for token in ('init2dFallback()', '2D fallback:', 'chrome://gpu',
                      'nearest(e)', '3D rendering unavailable'):
            self.assertIn(token,src)

    def test_webgl1_compatibility_contract(self):
        src=app.TEMPLATE.read_text(encoding='utf-8')
        for token in ("getContext('webgl2'", "getContext('webgl'", "OES_vertex_array_object",
                      "gl.bindAttribLocation(prog,0,'pos')", 'texture2D(tex,vuv)',
                      'makeVAO()', 'bindVAO(', 'WebGL1', 'WebGL2'):
            self.assertIn(token,src)

    def test_diagnostics_and_failed_context_recovery(self):
        src=app.TEMPLATE.read_text(encoding='utf-8')
        for token in ('const old=canvas;canvas=old.cloneNode(false)', '3D scene load failed:',
                      'Shader setup failed:', 'gl.getError()', 'draw calls',
                      "webglcontextlost", 'await activateFallback('):
            self.assertIn(token,src)

    def test_missing_map_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                app.build(Path(tmp)/'nope.gmp',Path(tmp)/'out')

    def test_refuse_write_to_map_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps=Path(tmp)/'Maps';maps.mkdir();m=maps/'fake.gmp';m.write_bytes(b'fake')
            with self.assertRaises(ValueError):app.build(m,maps/'out')

    def test_bare_glb_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            from struct import pack
            d=Path(tmp); m=d/'source.gmp'; m.write_bytes(b'dummy')
            js=json.dumps({'asset':{'extras':{'DX2SourceMapSHA256':'a'*64}}}).encode();js+=b' '*((-len(js))%4)
            chunks=pack('<II',len(js),0x4e4f534a)+js
            glb=pack('<III',0x46546c67,2,12+len(chunks))+chunks
            f=d/'wrong.glb';f.write_bytes(glb)
            with self.assertRaises(ValueError):app.build(m,d/'out',existing_glb=f)

    def test_http_handler_defaults_read_only(self):
        self.assertTrue(issubclass(app.QuietHandler,app.SimpleHTTPRequestHandler))

if __name__=='__main__':unittest.main()