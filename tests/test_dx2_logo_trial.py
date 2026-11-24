"""Synthetic source-only regression tests for the three logo trial variants."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"maps"))
from dx2_logo_trial import prepare, TRIALS
from dx2_ibd_integrity import verify_bundle
from dx2_texture_writer import inspect_layout, marker_mips, select_texture
from test_dx2_texture_writer import make_fixture


def fixture():
    raw=bytearray(make_fixture())
    raw[52+41:52+41+16]=b"meta_iwlogo".ljust(16,b"\0")
    raw[32:52]=b"\0"*20
    raw[32:52]=hashlib.sha1(raw[:2048]).digest()
    return bytes(raw)


class LogoTrialTests(unittest.TestCase):
    def test_variants_combined_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            maps=root/"Maps"
            maps.mkdir()
            raw=fixture()
            pin=hashlib.sha256(raw).hexdigest()
            trials=tuple((variant,name,palette,pin) for variant,name,palette,_ in TRIALS)
            for _,name,_,_ in trials:
                (maps/name).write_bytes(raw)
            output=root/"Trial"
            receipt=prepare(maps,output,trials=trials)
            self.assertFalse(receipt["runtime_verified"])
            self.assertFalse(receipt["game_installation_modified"])
            self.assertEqual(json.loads((output/"trial.json").read_text()),receipt)
            old=verify_bundle(raw)
            layout=inspect_layout(old,select_texture(old,"meta_iwlogo"))
            for variant,name,palette,_ in trials:
                changed=(output/variant/name).read_bytes()
                self.assertEqual((output/"C_Both"/name).read_bytes(),changed)
                self.assertEqual((maps/name).read_bytes(),raw)
                parsed=verify_bundle(changed)
                updated=inspect_layout(parsed,select_texture(parsed,"meta_iwlogo"))
                self.assertEqual(tuple(updated.parts[i] for i in updated.pixel_slots),
                                 marker_mips(layout,palette))
            with self.assertRaisesRegex(ValueError,"isolated"):
                prepare(maps,output,trials=trials)

    def test_bad_source_preflight_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            maps=root/"Maps"
            maps.mkdir()
            raw=fixture()
            pin=hashlib.sha256(raw).hexdigest()
            trials=tuple((variant,name,palette,pin) for variant,name,palette,_ in TRIALS)
            for _,name,_,_ in trials:
                (maps/name).write_bytes(raw)
            (maps/trials[1][1]).write_bytes(raw+b"x")
            with self.assertRaisesRegex(ValueError,"pinned trial version"):
                prepare(maps,root/"Trial",trials=trials)
            self.assertFalse((root/"Trial").exists())


if __name__=="__main__":
    unittest.main()
