extends SceneTree
## P109 source-free bulk-preview authoring: original identity and skip disclosure.
const Editor = preload("res://main.gd")

func _initialize() -> void:
    call_deferred("_run")

func _fail(reason: String) -> void:
    push_error("DX2Ed P109 bulk GMP UI: " + reason)
    quit(1)

func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    if editor.native_bulk_dialog == null or editor.native_bulk_confirmation == null:
        _fail("Bulk native GMP dialogs missing from editor")
        return
    var native_menu: MenuButton = editor.compact_menus["Native GMP (test)"]
    var has_bulk := false
    for idx in range(native_menu.get_popup().get_item_count()):
        if native_menu.get_popup().get_item_text(idx) == "Experimental Save Supported GMP...":
            has_bulk = true
    if not has_bulk:
        _fail("Bulk GMP action is not exposed in the compact Native GMP menu")
        return
    var scene := Node3D.new()
    editor.world_root.add_child(scene)
    editor.scene_root = scene
    for i in range(2):
        var mesh := MeshInstance3D.new()
        mesh.name = "Source_" + str(i)
        mesh.mesh = BoxMesh.new()
        mesh.position = Vector3(float(i) * 5.0, 0.0, 0.0)
        scene.add_child(mesh)
        editor.meshes_by_actor[mesh.name] = mesh
        editor.actors_by_name[mesh.name] = {
            "name": mesh.name, "class": "StaticMeshActor", "export": 10 + i
        }
        editor.original_mesh_transforms[mesh.name] = mesh.global_transform
    var first: MeshInstance3D = editor.meshes_by_actor["Source_0"]
    first.global_position.x += editor.NATIVE_CLONE_UNREAL_METRES * 20.0
    var copied := MeshInstance3D.new()
    copied.name = "DraftProp_1"
    copied.mesh = BoxMesh.new()
    scene.add_child(copied)
    copied.global_transform = editor.original_mesh_transforms["Source_0"]
    copied.global_position.z += editor.NATIVE_CLONE_UNREAL_METRES * 40.0
    editor.draft_prop_copies[copied.name] = copied
    editor.draft_prop_sources[copied.name] = "Source_0"
    var brush := MeshInstance3D.new()
    brush.name = "DraftProp_2"
    brush.mesh = BoxMesh.new()
    scene.add_child(brush)
    editor.draft_prop_copies[brush.name] = brush
    editor.draft_prop_sources[brush.name] = "Brush::Box"
    editor.draft_brush_specs[brush.name] = {"kind": "Box"}
    editor.property_overrides["Source_0"] = {"2": 3}

    var preview := editor._native_bulk_preview()
    var plan: Dictionary = preview["plan"]
    if (preview["native_count"] != 2 or not preview["within_limit"]
        or plan["schema"] != "DX2Ed-experimental-native-bulk-prop-plan-v1"
        or plan["moves"].size() != 1 or plan["copies"].size() != 1
        or preview["omitted"].size() != 2):
        _fail("Bulk preview did not separate eligible moves/clones from preview-only edits: "
            + str(preview))
        return
    # Old combined action must remain fail-closed, not suddenly include extras.
    if not editor._native_combined_draft_plan().is_empty():
        _fail("Legacy combined writer accepted unsupported draft changes")
        return
    copied.rotate_y(0.3)
    var blocked := editor._native_bulk_preview()
    if (blocked["native_count"] != 1
        or blocked["omitted"].size() != 3):
        _fail("Rotated cloned object was not explicitly excluded")
        return
    first.global_transform = editor.original_mesh_transforms["Source_0"]
    blocked = editor._native_bulk_preview()
    if blocked["native_count"] != 0:
        _fail("Bulk native save incorrectly found exportable edit after reset")
        return
    editor.queue_free()
    print("DX2Ed P109 source-only bulk save candidate classification PASS")
    quit(0)
