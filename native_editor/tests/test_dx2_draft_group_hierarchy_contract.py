"""Source contract checks for DX2Ed's v0.56 editor-private group hierarchy."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DX2EdDraftGroupHierarchyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / "native_editor/godot_editor/main.gd").read_text("utf-8")
        cls.smoke = (ROOT / "native_editor/godot_editor/tests/smoke_draft_group_hierarchy.gd").read_text("utf-8")
        cls.launcher = (ROOT / "prototype/START_DX2ED.cmd").read_text("utf-8")
        cls.workflow = (ROOT / ".github/workflows/native-dx2ed.yml").read_text("utf-8")
        cls.parity = json.loads((ROOT / "native_editor/t3ed_parity.json").read_text("utf-8"))

    def test_real_private_parent_nodes_preserve_world_transforms(self):
        self.assertIn('draft_groups_root.name = "DX2Ed_DraftGroups_EDITOR_ONLY"', self.main)
        self.assertIn('root.set_meta("dx2ed_group_name", group_name)', self.main)
        self.assertIn("node.reparent(root, true)", self.main)
        self.assertIn("child.reparent(target_parent, true)", self.main)
        self.assertIn("func _selection_transform_targets() -> Array[Node3D]", self.main)
        self.assertIn("func _gizmo_root_basis() -> Basis:", self.main)

    def test_hierarchy_selection_and_group_actions_are_wired(self):
        self.assertIn('group_create_button.pressed.connect(_group_selected)', self.main)
        self.assertIn('group_ungroup_button.pressed.connect(_ungroup_selected)', self.main)
        self.assertIn('"@group::" + group_name', self.main)
        self.assertIn("func _apply_hierarchy_selection() -> void:", self.main)
        self.assertIn("func _duplicate_selected_prop() -> void:", self.main)
        self.assertIn("selected_group_names = duplicate_group_names", self.main)

    def test_private_save_validation_and_history_include_groups(self):
        self.assertIn('"groups": groups', self.main)
        self.assertIn('"selected_groups": selected_group_names.duplicate()', self.main)
        self.assertIn('"groups": _capture_draft_group_state()', self.main)
        self.assertIn('before.get("groups", []) == after.get("groups", [])', self.main)
        self.assertIn("func _validated_draft_groups(value: Variant, copies: Array) -> Variant:", self.main)
        self.assertIn("seen_members.has(member)", self.main)
        self.assertIn("absf(determinant) < 0.000001", self.main)
        self.assertIn("Nothing loaded.", self.main)
        self.assertIn('"editor_only", true', self.main)

    def test_real_godot_smoke_covers_group_workflow_and_malicious_documents(self):
        for marker in (
            "_group_selected()", "_selection_transform_targets()",
            "_save_prop_draft()", "_load_prop_draft(true)",
            "Duplicate group membership", "Singular group transform",
            "_undo_edit()", "_redo_edit()", "_reset_selected_prop()",
        ):
            self.assertIn(marker, self.smoke)
        self.assertIn("smoke_draft_group_hierarchy.gd", self.launcher)
        self.assertIn("smoke_draft_group_hierarchy.gd", self.workflow)

    def test_v057_private_rename_keeps_group_identity_local(self):
        self.assertIn('group_rename_button.pressed.connect(_rename_selected_group)', self.main)
        self.assertIn('func _rename_selected_group() -> void:', self.main)
        self.assertIn('if selected_group_names.size() != 1:', self.main)
        self.assertIn('if not _valid_draft_group_name(new_name):', self.main)
        self.assertIn('if draft_groups.has(new_name):', self.main)
        self.assertIn('group.set_meta("dx2ed_group_name", new_name)', self.main)
        self.assertIn('selected_group_names = [new_name]', self.main)
        self.assertIn('_record_edit("Rename group " + old_name + " to " + new_name, before)', self.main)
        for marker in (
            '_rename_selected_group()', 'Renamed_Group',
            'Rename did not preserve the same parent node',
            'Undo did not restore the original group name',
            'Redo did not restore the renamed group',
            'Invalid group name was accepted',
        ):
            self.assertIn(marker, self.smoke)

    def test_parity_record_keeps_native_group_writer_unverified(self):
        transforms = next(row for row in self.parity["capabilities"] if row["id"] == "transforms")
        self.assertEqual(transforms["status"], "partial")
        self.assertIn("v0.56", transforms["evidence"])
        self.assertIn("native", transforms["next_step"].lower())


if __name__ == "__main__":
    unittest.main()
