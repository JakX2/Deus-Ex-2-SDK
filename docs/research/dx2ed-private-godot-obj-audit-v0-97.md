# DX2Ed v0.97: Verify an exported private Box OBJ inside the Godot Inspector

**Scope:** verify one preexisting local Wavefront OBJ against the exact selected, editor-created clipped `Brush::Box`. This is a read-only source-private geometry and provenance test, **not an OBJ importer or native map writer**.

## Workflow

1. In Godot 4.3 DX2Ed, create and clip one editor-private `Brush::Box` (one to eight valid local planes), then use **Export private Box OBJ...** to choose a new OBJ path.
2. Keep or reselect that same private Box and click **Verify exported Box OBJ...** in the Inspector.
3. Select the **existing** `.obj`. The separate Python audit independently parses bounded triangles, reciprocal winding and closed volume, re-preflights the Box and requires byte-for-byte equality to the canonical private export.
4. Success reports the triangle count and SHA-256 prefix. If the Box changes, the selected item changes while the FileDialog is open, the OBJ has been edited, or the file is malformed, the audit is refused without changing editor geometry, OBJ or Undo history.

The editor binds the pending dialog to the exact **private brush name and complete private brush spec**. Imported original StaticMeshActor selections and BSP overlay geometry are excluded, even if the dialog was opened while a private Box was selected.

## Implementation

- `native_editor/godot_editor/private_box_obj_audit_bridge.gd` validates the source-private Box, creates a unique ephemeral `user://private_box_obj_stage/private_audit_*.json` with **only** the normalized local brush specification, and calls the Python worker without a shell.
- `native_editor/godot_editor/backend/dx2_private_obj_audit_worker.py` resolves its own package root in a source checkout or Windows prototype ZIP and calls the independently tested `dx2sdk.private_brush_obj_audit` CLI.
- The Python audit opens only the limited private JSON and the user-selected `.obj`, reads them, produces a small JSON report on stdout, and writes **no files**. The editor deletes its temporary JSON following success and refusal, then verifies the reported OBJ SHA-256 against the actual chosen file.
- The actual Godot 4.3 fixture `tests/smoke_private_box_obj_audit.gd` checks button and FileDialog signals, successful round-trip, malformed OBJ refusal, brush-spec mutation between dialog and selection, imported actor switching, no leaked staging JSON, unchanged undo count during read-only operations and unchanged synthetic original GMP bytes.

## Test and feature boundaries

The new Godot integration fixture runs in the native-DX2Ed GitHub Actions workflow. Windows prototype source manifests, offline package doctor and ZIP validation require the bridge, worker, test and v0.96 Python audit module. This does **not** imply an ability to import OBJ, compile original DX2 World BSP, assign retail game UVs/materials, rebuild Havok/MOPP collision, generate `.gmp`/`.ibd`, or run a retail mission. T3Ed import/export remains partial.
