"""Synthetic tests for per-actor mesh skins and shared geometry.

No retail game mesh or material assets are bundled.
"""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "map_exporter"))
from dx2level import Builder, actor_requested_skin, resolve_skin_variant


def fake_stair():
    return SimpleNamespace(
        name="SyntheticTestStair",
        positions=[(0.0,0.0,0.0),(1.0,0.0,0.0),(0.0,1.0,0.0)],
        normals=[(0.0,0.0,1.0)] * 3,
        uv=[(0.0,0.0),(1.0,0.0),(0.0,1.0)],
        indices=[0,1,2],
        sections=[{"first_index":0,"index_count":3,"name":"Default"}],
        skins=[
            {"name":"Default","materials":["SyntheticGray"]},
            {"name":"Tan Stones","materials":["SyntheticTan"]},
        ],
    )


class ActorSkinsTests(unittest.TestCase):
    def test_property_56_selects_requested_variant(self):
        actor={"game_properties":[{"id":56,"value":{
            "Name":"SyntheticTestStair","Skin":"Tan Stones"}}]}
        self.assertEqual(actor_requested_skin(actor), "Tan Stones")
        self.assertEqual(resolve_skin_variant(fake_stair(), actor_requested_skin(actor)),
                         (1,"Tan Stones","matched"))

    def test_variant_names_case_insensitive(self):
        self.assertEqual(resolve_skin_variant(fake_stair(), "  tan stones  "),
                         (1,"Tan Stones","matched"))

    def test_default_without_override(self):
        self.assertEqual(resolve_skin_variant(fake_stair()),(0,"Default","mesh_default"))
        self.assertIsNone(actor_requested_skin({"game_properties": []}))

    def test_unknown_skin_falls_back_and_reports_it(self):
        self.assertEqual(resolve_skin_variant(fake_stair(),"Missing Variant"),
                         (0,"Default","requested_skin_missing"))

    def test_same_mesh_can_export_two_distinct_skin_materials(self):
        mesh=fake_stair()
        builder=Builder({}, {}, {})
        default_mesh=builder.mesh_data(mesh,"synthetic_bundle.ibd",0)
        tan_mesh=builder.mesh_data(mesh,"synthetic_bundle.ibd",1)
        self.assertNotEqual(default_mesh,tan_mesh)
        def matname(mid):
            prim=builder.doc["meshes"][mid]["primitives"][0]
            return builder.doc["materials"][prim["material"]]["name"]
        self.assertEqual(matname(default_mesh),"SyntheticGray")
        self.assertEqual(matname(tan_mesh),"SyntheticTan")
        self.assertEqual(builder.doc["meshes"][tan_mesh]["extras"]["DX2SkinVariant"],
                         "Tan Stones")

    def test_invalid_variant_index_rejected(self):
        builder=Builder({}, {}, {})
        with self.assertRaisesRegex(ValueError,"Invalid skin index"):
            builder.mesh_data(fake_stair(),"synthetic_bundle.ibd",3)

    def test_report_is_explicit_about_skin_choice(self):
        src=(ROOT/"map_exporter"/"dx2level.py").read_text(encoding="utf-8")
        self.assertIn("'actor_skin_selections':selected_actor_skins",src)
        self.assertIn("'actor_skin_variant_missing':missing_actor_skins",src)
        self.assertIn("'DX2SelectedSkin':skin_name",src)

    def test_actor_diagnostics_explain_skins(self):
        src=(ROOT/"native_editor"/"godot_editor"/"main.gd").read_text(encoding="utf-8")
        self.assertIn('lines.append("Requested skin: "',src)
        self.assertIn('lines.append("Exported skin: "',src)
        self.assertIn('current_source_map_name',src)


if __name__=="__main__":
    unittest.main()
