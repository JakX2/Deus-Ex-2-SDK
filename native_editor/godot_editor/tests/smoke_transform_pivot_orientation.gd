extends SceneTree
## DX2Ed v0.55 transform pivot/orientation and private cursor round-trip smoke.
## Invented preview brushes only; no retail map or native writer.
const Guides = preload("res://orthographic_authoring_guides.gd")
const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.55 transform preferences: " + message)
    quit(1)


func _run() -> void:
    if (not Guides.valid_pivot_mode("median")
        or not Guides.valid_pivot_mode("active")
        or not Guides.valid_pivot_mode("cursor")
        or Guides.valid_pivot_mode("native")
        or not Guides.valid_orientation_mode("world")
        or not Guides.valid_orientation_mode("local")
        or Guides.valid_orientation_mode("source")):
        _fail("Pivot/orientation allowlists are incorrect")
        return
    if (Guides.validate_cursor_position([1.0, -2, 3]) != Vector3(1, -2, 3)
        or Guides.validate_cursor_position([1.0, 2.0]) != null
        or Guides.validate_cursor_position([INF, 0.0, 0.0]) != null
        or Guides.validate_cursor_position([1000001.0, 0.0, 0.0]) != null):
        _fail("3D cursor bounds or finite validation failed")
        return

    var rotated := Basis(Vector3.UP, PI * 0.5)
    var local_basis: Basis = Guides.gizmo_basis(Guides.PERSPECTIVE, "local", rotated)
    if not local_basis.is_equal_approx(rotated.orthonormalized()):
        _fail("Perspective local orientation did not use the active object's orthonormal basis")
        return
    if not Guides.gizmo_basis(Guides.TOP, "local", rotated).is_equal_approx(Basis.IDENTITY):
        _fail("Top orthographic view did not remain world-plane constrained")
        return
    if not Guides.gizmo_basis(Guides.PERSPECTIVE, "world", rotated).is_equal_approx(Basis.IDENTITY):
        _fail("World orientation did not return the identity basis")
        return
    if not Guides.gizmo_basis(
        Guides.PERSPECTIVE, "local",
        Basis(Vector3.ZERO, Vector3.ZERO, Vector3.ZERO)).is_equal_approx(Basis.IDENTITY):
        _fail("Singular active-object basis was not safely rejected")
        return

    var editor := Editor.new()
    get_root().add_child(editor)
    var fake_scene := Node3D.new()
    editor.world_root.add_child(fake_scene)
    editor.scene_root = fake_scene
    editor.current_folder = ProjectSettings.globalize_path("user://v055_transform_pivot_orientation")
    var first := editor._new_draft_copy(
        "Brush::Polygon", "DraftProp_55", Transform3D(Basis.IDENTITY, Vector3(2, 0, 0)))
    var second := editor._new_draft_copy(
        "Brush::Polygon", "DraftProp_56", Transform3D(rotated, Vector3(4, 0, 0)))
    if not is_instance_valid(first) or not is_instance_valid(second):
        _fail("Could not create synthetic private Polygon previews")
        return
    if (not editor._set_brush_spec("DraftProp_55", Brush.default_spec("Polygon"))
        or not editor._set_brush_spec("DraftProp_56", Brush.default_spec("Polygon"))):
        _fail("Synthetic private Polygon failed authoring preflight")
        return
    editor._select_mesh_only(first)
    editor._add_selection_mesh(second)
    editor._refresh_selection_inspector()
    if editor._selection_nodes().size() != 2:
        _fail("Multi-selection did not retain both private preview brushes")
        return

    editor._set_transform_pivot_mode("median")
    if not editor._selection_pivot().is_equal_approx(Vector3(3, 0, 0)):
        _fail("Median pivot did not average selected object origins")
        return
    editor._set_transform_pivot_mode("active")
    if not editor._selection_pivot().is_equal_approx(Vector3(4, 0, 0)):
        _fail("Active pivot did not use the last selected object")
        return
    editor.transform_cursor_position = Vector3(9, 1, 2)
    editor._set_transform_pivot_mode("cursor")
    if (not editor._selection_pivot().is_equal_approx(Vector3(9, 1, 2))
        or not editor.transform_cursor_marker.visible
        or not editor.transform_cursor_marker.global_position.is_equal_approx(Vector3(9, 1, 2))):
        _fail("3D Cursor pivot or visible editor cursor marker failed")
        return

    editor._activate_view("perspective", false, false, true)
    editor._set_transform_orientation_mode("local")
    editor._update_gizmo_pose()
    var expected_local: Basis = second.global_basis.orthonormalized()
    if not editor.gizmo_root.global_basis.orthonormalized().is_equal_approx(expected_local):
        _fail("Perspective gizmo did not follow the active selected object's local basis")
        return
    editor._activate_view("top", false, false, true)
    editor._update_gizmo_pose()
    if not editor.gizmo_root.global_basis.orthonormalized().is_equal_approx(Basis.IDENTITY):
        _fail("Top view gizmo leaked local orientation outside its world XZ plane")
        return

    # Cursor placement is one undoable action; preference toggles are workspace settings.
    editor.transform_cursor_position = Vector3(9, 1, 2)
    editor._set_transform_pivot_mode("median")
    editor._set_transform_cursor_from_selection()
    if not editor.transform_cursor_position.is_equal_approx(Vector3(3, 0, 0)):
        _fail("Set 3D cursor did not use the selection median")
        return
    if editor.undo_stack.is_empty() or str(editor.undo_stack.back().get("label", "")) != "Set 3D cursor":
        _fail("Set 3D cursor did not create one named Undo transaction")
        return
    editor._undo_edit()
    if not editor.transform_cursor_position.is_equal_approx(Vector3(9, 1, 2)):
        _fail("Undo did not restore the previous 3D cursor position")
        return
    editor._redo_edit()
    if not editor.transform_cursor_position.is_equal_approx(Vector3(3, 0, 0)):
        _fail("Redo did not restore the selection-derived 3D cursor position")
        return

    editor._activate_view("perspective", false, false, true)
    editor._set_transform_pivot_mode("cursor")
    editor._set_transform_orientation_mode("local")
    editor.transform_cursor_position = Vector3(7, 8, 9)
    editor._refresh_transform_cursor_marker()
    editor._save_prop_draft()
    var draft_path := editor._draft_file_path()
    if draft_path.is_empty() or not FileAccess.file_exists(draft_path):
        _fail("Private draft did not save transform workspace settings")
        return
    editor._set_transform_pivot_mode("median")
    editor._set_transform_orientation_mode("world")
    editor.transform_cursor_position = Vector3.ZERO
    editor._load_prop_draft(true)
    if (editor.transform_pivot_mode != "cursor"
        or editor.transform_orientation_mode != "local"
        or not editor.transform_cursor_position.is_equal_approx(Vector3(7, 8, 9))
        or not editor.transform_cursor_marker.visible):
        _fail("Private Save/reopen did not restore pivot, orientation and 3D cursor")
        return

    var workspace := editor._capture_draft_workspace()
    if editor._validated_draft_workspace(workspace) == null:
        _fail("New nine-field workspace failed validation")
        return
    var old_six := workspace.duplicate(true)
    old_six.erase("pivot_mode")
    old_six.erase("orientation_mode")
    old_six.erase("cursor_position")
    if editor._validated_draft_workspace(old_six) == null:
        _fail("Legacy v0.53/v0.54 six-field workspace was not migrated")
        return
    var old_three := {
        "view_mode": Guides.PERSPECTIVE,
        "grid_step": 0.25,
        "grid_enabled": true
    }
    if editor._validated_draft_workspace(old_three) == null:
        _fail("Legacy three-field workspace was not migrated")
        return
    var bad := workspace.duplicate(true)
    bad["pivot_mode"] = "native"
    if editor._validated_draft_workspace(bad) != null:
        _fail("Unrecognized pivot mode was accepted")
        return
    bad = workspace.duplicate(true)
    bad["orientation_mode"] = "source"
    if editor._validated_draft_workspace(bad) != null:
        _fail("Unrecognized orientation mode was accepted")
        return
    bad = workspace.duplicate(true)
    bad["cursor_position"] = [NAN, 0.0, 0.0]
    if editor._validated_draft_workspace(bad) != null:
        _fail("Nonfinite cursor workspace was accepted")
        return
    bad = workspace.duplicate(true)
    bad["cursor_position"] = [1000001.0, 0.0, 0.0]
    if editor._validated_draft_workspace(bad) != null:
        _fail("Out-of-bounds cursor workspace was accepted")
        return

    for suffix in ["", ".bak", ".pending"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    editor.queue_free()
    print("DX2Ed v0.55 median/active/cursor pivots, world/local orientation, cursor Undo/Redo and private workspace migration PASS")
    quit(0)
