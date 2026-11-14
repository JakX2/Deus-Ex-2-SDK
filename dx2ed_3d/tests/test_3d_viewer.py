"""Asset-free tests, plus optional original DX2 integration via environment variables."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
# ROOT already is dx2ed_3d; importing from ROOT/dx2ed_3d loaded a
# namespace package instead of the executable dx2ed_3d.py module.
sys.path.insert(0,str(ROOT))
import dx2ed_3d as app


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