extends SceneTree
## Synthetic-only Godot 4.3 contract for v0.59 original StaticMeshActor unplace UI.
## Never reads or writes a GMP, never exercises native game-installation paths.

const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.59 unplace plan: " + message)
    quit(1)


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    var synthetic_scene := Node3D.new()
    synthetic_scene.name = "SyntheticLevelSource"
    editor.world_root.add_child(synthetic_scene)
    editor.scene_root = synthetic_scene
    var source_actor := MeshInstance3D.new()
    source_actor.name = "OriginalProp"
    source_actor.mesh = BoxMesh.new()
    source_actor.position = Vector3(1.0, 2.0, 3.0)
    synthetic_scene.add_child(source_actor)
    editor.meshes_by_actor[source_actor.name] = source_actor
    editor.actors_by_name[source_actor.name] = {
        "name": source_actor.name,
        "class": "StaticMeshActor",
        "export": 17,
        "mesh": "SyntheticCube",
    }
    editor.original_mesh_transforms[source_actor.name] = source_actor.global_transform
    editor.all_mesh_instances.append(source_actor)
    editor._select_mesh_only(source_actor)
    var expected := {"actor": "OriginalProp", "export": 17}
    if editor._native_unplace_draft_plan() != expected:
        _fail("One unmodified original StaticMeshActor was not eligible")
        return

    editor.property_overrides[source_actor.name] = {"12": 1}
    if not editor._native_unplace_draft_plan().is_empty():
        _fail("Native unplace silently discarded a staged property")
        return
    editor.property_overrides.clear()

    var private_copy := MeshInstance3D.new()
    private_copy.name = "DraftCopy"
    private_copy.mesh = BoxMesh.new()
    synthetic_scene.add_child(private_copy)
    editor.draft_prop_copies[private_copy.name] = private_copy
    if not editor._native_unplace_draft_plan().is_empty():
        _fail("Native unplace silently discarded an existing private duplicate")
        return
    editor.draft_prop_copies.clear()
    private_copy.free()

    editor.selected_group_names = ["UnsafePrivateGroup"]
    if not editor._native_unplace_draft_plan().is_empty():
        _fail("Private group selection was accepted by native unplace")
        return
    editor.selected_group_names.clear()

    source_actor.position.x += 1.0
    if not editor._native_unplace_draft_plan().is_empty():
        _fail("Moved original StaticMeshActor was accepted by native unplace")
        return
    source_actor.global_transform = editor.original_mesh_transforms[source_actor.name]

    editor.actors_by_name[source_actor.name]["class"] = "Light"
    if not editor._native_unplace_draft_plan().is_empty():
        _fail("Non-StaticMeshActor was accepted by native unplace")
        return
    editor.actors_by_name[source_actor.name]["class"] = "StaticMeshActor"

    editor._clear_selection()
    if not editor._native_unplace_draft_plan().is_empty():
        _fail("Unplace plan did not require exactly one selected original")
        return

    editor.queue_free()
    print("DX2Ed v0.59 original native StaticMeshActor unplace preview eligibility PASS")
    quit(0)
