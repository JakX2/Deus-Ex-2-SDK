extends SceneTree
## DX2Ed v0.60 synthetic-only Godot combined native move/copy/unplace planning.
## Never opens or modifies a GMP or queries any retail game source.

const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.60 native plan: " + message)
    quit(1)


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    var scene := Node3D.new()
    scene.name = "SyntheticNativePlanScene"
    editor.world_root.add_child(scene)
    editor.scene_root = scene
    for idx in range(2):
        var prop := MeshInstance3D.new()
        prop.name = "SourceA" if idx == 0 else "SourceB"
        prop.mesh = BoxMesh.new()
        prop.position = Vector3(float(idx) * 4.0, 0.0, 0.0)
        scene.add_child(prop)
        editor.meshes_by_actor[prop.name] = prop
        editor.actors_by_name[prop.name] = {
            "name": prop.name, "class": "StaticMeshActor",
            "export": 17 + idx,
        }
        editor.original_mesh_transforms[prop.name] = prop.global_transform
        editor.all_mesh_instances.append(prop)
    var first: MeshInstance3D = editor.meshes_by_actor["SourceA"]
    var second: MeshInstance3D = editor.meshes_by_actor["SourceB"]

    # One movement in Godot X is native X; 50 Unreal Y becomes Godot Z.
    first.global_position.x += 20.0 * editor.NATIVE_CLONE_UNREAL_METRES
    var copy := MeshInstance3D.new()
    copy.name = "PrivateCopyA"
    copy.mesh = BoxMesh.new()
    scene.add_child(copy)
    copy.global_transform = editor.original_mesh_transforms["SourceA"]
    copy.global_position.z += 50.0 * editor.NATIVE_CLONE_UNREAL_METRES
    editor.draft_prop_copies[copy.name] = copy
    editor.draft_prop_sources[copy.name] = "SourceA"
    editor.native_staged_unplaces["SourceB"] = 18
    var plan := editor._native_combined_draft_plan()
    if plan.is_empty() or plan.get("schema", "") != "DX2Ed-experimental-native-prop-change-plan-v1":
        _fail("Valid three-operation native plan was rejected")
        return
    if (plan["moves"].size() != 1 or plan["copies"].size() != 1
        or plan["unplaces"] != [{"actor": "SourceB", "export": 18}]):
        _fail("Native plan dropped a move/copy/unplace")
        return
    var moved: Array = plan["moves"][0]["delta"]
    var copied: Array = plan["copies"][0]["delta"]
    if (abs(float(moved[0]) - 20.0) > 0.001 or abs(float(moved[1])) > 0.001
        or abs(float(moved[2])) > 0.001
        or abs(float(copied[0])) > 0.001
        or abs(float(copied[1]) - 50.0) > 0.001
        or abs(float(copied[2])) > 0.001):
        _fail("Combined plan Godot-to-native XYZ conversion was wrong")
        return

    editor.property_overrides["SourceA"] = {"2": 3}
    if not editor._native_combined_draft_plan().is_empty():
        _fail("Combined native plan discarded a staged property edit")
        return
    editor.property_overrides.clear()

    editor.draft_groups["UnsafeGroup"] = Node3D.new()
    if not editor._native_combined_draft_plan().is_empty():
        _fail("Combined native plan discarded a private parent group")
        return
    editor.draft_groups.clear()

    first.rotate_y(0.25)
    if not editor._native_combined_draft_plan().is_empty():
        _fail("Combined native plan silently discarded actor rotation")
        return
    first.global_transform = editor.original_mesh_transforms["SourceA"]
    first.global_position.x += 20.0 * editor.NATIVE_CLONE_UNREAL_METRES

    editor.native_staged_unplaces["SourceA"] = 17
    if not editor._native_combined_draft_plan().is_empty():
        _fail("Combined native plan accepted a moved-and-unplaced original")
        return
    editor.native_staged_unplaces.erase("SourceA")

    editor.native_staged_unplaces.clear()
    first.global_transform = editor.original_mesh_transforms["SourceA"]
    if not editor._native_combined_draft_plan().is_empty():
        _fail("Combined plan allowed only one operation kind")
        return

    editor.queue_free()
    print("DX2Ed v0.60 combined native move/copy/unplace draft and refusal smoke PASS")
    quit(0)
