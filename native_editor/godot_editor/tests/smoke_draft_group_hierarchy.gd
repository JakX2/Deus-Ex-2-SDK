extends SceneTree
## DX2Ed v0.56 private group hierarchy, parent transforms and JSON round-trip smoke.
## Synthetic meshes only. Group nodes are editor-only; no native DX2 ownership/writer.

const Editor = preload("res://main.gd")
const Brush = preload("res://brush_geometry.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.56 group hierarchy: " + message)
    quit(1)


func _write_document(path: String, payload: String) -> bool:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(payload)
    file.flush()
    file.close()
    return true


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    var fake_scene := Node3D.new()
    fake_scene.name = "SyntheticOriginalScene"
    editor.world_root.add_child(fake_scene)
    editor.scene_root = fake_scene
    editor.current_folder = ProjectSettings.globalize_path("user://v056_group_hierarchy")

    var source_actor := MeshInstance3D.new()
    source_actor.name = "SyntheticActor"
    source_actor.mesh = BoxMesh.new()
    source_actor.position = Vector3(6, 0, 0)
    fake_scene.add_child(source_actor)
    editor.meshes_by_actor[source_actor.name] = source_actor
    editor.actors_by_name[source_actor.name] = {"name": source_actor.name, "class": "SyntheticStaticMesh"}
    editor.original_mesh_transforms[source_actor.name] = source_actor.global_transform
    editor.all_mesh_instances.append(source_actor)

    var first := editor._new_draft_copy(
        "Brush::Polygon", "DraftProp_1",
        Transform3D(Basis.IDENTITY, Vector3(2, 0, 0)))
    var second := editor._new_draft_copy(
        "Brush::Polygon", "DraftProp_2",
        Transform3D(Basis(Vector3.UP, PI * 0.25), Vector3(4, 0, 0)))
    if not is_instance_valid(first) or not is_instance_valid(second):
        _fail("Could not create synthetic private Polygon previews")
        return
    if (not editor._set_brush_spec("DraftProp_1", Brush.default_spec("Polygon"))
        or not editor._set_brush_spec("DraftProp_2", Brush.default_spec("Polygon"))):
        _fail("Synthetic Polygon previews failed brush validation")
        return

    var original_world := {
        "DraftProp_1": first.global_transform,
        "DraftProp_2": second.global_transform,
        "SyntheticActor": source_actor.global_transform
    }
    editor._select_mesh_only(first)
    editor._add_selection_mesh(second)
    editor._add_selection_mesh(source_actor)
    editor.group_name_edit.text = "TestGroup"
    editor._group_selected()
    if not editor.draft_groups.has("TestGroup"):
        _fail("Group selected did not create the private parent node")
        return
    var group: Node3D = editor.draft_groups["TestGroup"]
    if (editor._group_member_nodes("TestGroup").size() != 3
        or editor.selected_group_names != ["TestGroup"]
        or editor._selection_transform_targets().size() != 1
        or editor._selection_transform_targets()[0] != group):
        _fail("Group hierarchy did not become one selectable transform target")
        return
    for name in original_world:
        var member: MeshInstance3D = editor.draft_prop_copies.get(
            name, editor.meshes_by_actor.get(name, null))
        if not is_instance_valid(member) or member.get_parent() != group:
            _fail("A selected preview mesh was not parented under the new group: " + name)
            return
        if not member.global_transform.is_equal_approx(original_world[name]):
            _fail("Grouping changed a member's world transform: " + name)
            return
    if not group.global_position.is_equal_approx(Vector3(4, 0, 0)):
        _fail("New group pivot was not initialized at the selected mesh-origin median")
        return

    var before_move := editor._capture_edit_state()
    var initial_group_transform := group.global_transform
    var initial_member_world := {}
    for member in editor._group_member_nodes("TestGroup"):
        initial_member_world[str(member.name)] = member.global_transform
    group.global_position += Vector3(2, 1, -3)
    editor._record_edit("Synthetic group parent transform", before_move)
    for member in editor._group_member_nodes("TestGroup"):
        var name := str(member.name)
        if not member.global_position.is_equal_approx(
            initial_member_world[name].origin + Vector3(2, 1, -3)):
            _fail("Moving the group parent did not move its child in world space")
            return
    editor._undo_edit()
    group = editor.draft_groups.get("TestGroup", null)
    if not is_instance_valid(group) or not group.global_transform.is_equal_approx(initial_group_transform):
        _fail("Undo did not restore the group parent transform")
        return
    editor._redo_edit()
    group = editor.draft_groups.get("TestGroup", null)
    if not is_instance_valid(group) or not group.global_position.is_equal_approx(
        initial_group_transform.origin + Vector3(2, 1, -3)):
        _fail("Redo did not reapply the group parent transform")
        return

    editor._refresh_hierarchy()
    var group_item: TreeItem = editor.hierarchy_group_items.get("TestGroup", null)
    if group_item == null:
        _fail("Private group was not represented in the Hierarchy tree")
        return
    editor.hierarchy_tree.deselect_all()
    group_item.select(0)
    editor._apply_hierarchy_selection()
    if (editor.selected_group_names != ["TestGroup"]
        or editor._selection_nodes().size() != 3
        or editor._selection_transform_targets().size() != 1):
        _fail("Selecting the hierarchy group did not select its members and parent transform")
        return

    editor._save_prop_draft()
    var draft_path := editor._draft_file_path()
    if draft_path.is_empty() or not FileAccess.file_exists(draft_path):
        _fail("Private group draft did not save")
        return
    var saved_json := FileAccess.get_file_as_string(draft_path)
    var saved_doc: Variant = JSON.parse_string(saved_json)
    if (typeof(saved_doc) != TYPE_DICTIONARY or not saved_doc.has("groups")
        or saved_doc["groups"].size() != 1
        or saved_doc["groups"][0].get("name", "") != "TestGroup"
        or saved_doc.get("selected_groups", []) != ["TestGroup"]):
        _fail("Private JSON did not include group identity and selection")
        return
    var saved_group_transform := editor.draft_groups["TestGroup"].global_transform
    var saved_member_world := {}
    for member in editor._group_member_nodes("TestGroup"):
        saved_member_world[str(member.name)] = member.global_transform

    editor._ungroup_selected()
    if editor.draft_groups.has("TestGroup"):
        _fail("Ungroup did not remove the selected parent node")
        return
    if source_actor.get_parent() != fake_scene:
        _fail("Ungroup did not restore the original actor's source-scene parent")
        return
    editor._load_prop_draft(true)
    group = editor.draft_groups.get("TestGroup", null)
    if not is_instance_valid(group) or not group.global_transform.is_equal_approx(saved_group_transform):
        _fail("Private Save/reopen did not restore the group parent transform")
        return
    for name in saved_member_world:
        var member: MeshInstance3D = editor.draft_prop_copies.get(
            name, editor.meshes_by_actor.get(name, null))
        if (not is_instance_valid(member) or member.get_parent() != group
            or not member.global_transform.is_equal_approx(saved_member_world[name])):
            _fail("Private Save/reopen did not restore grouped member transforms: " + name)
            return

    # Malicious duplicate membership and singular group matrices must be rejected
    # before the live editor scene or its current group hierarchy is changed.
    var stable_group_transform := group.global_transform
    var bad_doc: Dictionary = JSON.parse_string(saved_json)
    bad_doc["groups"][0]["members"].append(bad_doc["groups"][0]["members"][0])
    if not _write_document(draft_path, JSON.stringify(bad_doc)):
        _fail("Could not write synthetic duplicate-membership fixture")
        return
    editor._load_prop_draft(true)
    group = editor.draft_groups.get("TestGroup", null)
    if not is_instance_valid(group) or not group.global_transform.is_equal_approx(stable_group_transform):
        _fail("Duplicate group membership mutated the live editor before rejection")
        return
    bad_doc = JSON.parse_string(saved_json)
    bad_doc["groups"][0]["transform"] = [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    ]
    if not _write_document(draft_path, JSON.stringify(bad_doc)):
        _fail("Could not write synthetic singular-transform fixture")
        return
    editor._load_prop_draft(true)
    group = editor.draft_groups.get("TestGroup", null)
    if not is_instance_valid(group) or not group.global_transform.is_equal_approx(stable_group_transform):
        _fail("Singular group transform mutated the live editor before rejection")
        return
    if not _write_document(draft_path, saved_json):
        _fail("Could not restore the valid private group document")
        return

    editor._ungroup_selected()
    if not editor.draft_groups.is_empty():
        _fail("Explicit Ungroup left a private group parent behind")
        return
    editor._undo_edit()
    if not editor.draft_groups.has("TestGroup"):
        _fail("Undo did not restore group membership after Ungroup")
        return
    editor._redo_edit()
    if editor.draft_groups.has("TestGroup"):
        _fail("Redo did not remove group membership after Ungroup")
        return
    editor._undo_edit()
    if not editor.draft_groups.has("TestGroup"):
        _fail("Could not restore group before duplication regression")
        return

    editor._duplicate_selected_prop()
    if editor.draft_groups.size() != 2 or editor.selected_group_names.size() != 1:
        _fail("Duplicating a selected group did not create a second selectable group")
        return
    var duplicate_group_name := editor.selected_group_names[0]
    if (duplicate_group_name == "TestGroup"
        or editor._group_member_nodes(duplicate_group_name).size() != 3):
        _fail("Duplicated group did not preserve all selected members")
        return
    editor._undo_edit()
    if editor.draft_groups.size() != 1 or editor.draft_prop_copies.size() != 2:
        _fail("Undo did not remove duplicated group and copies")
        return
    editor._redo_edit()
    if editor.draft_groups.size() != 2 or editor.draft_prop_copies.size() != 5:
        _fail("Redo did not restore duplicated group and copies")
        return
    editor._reset_selected_prop()
    if editor.draft_groups.size() != 1 or editor.draft_prop_copies.size() != 2:
        _fail("Reset selected group did not ungroup and delete only its private copies")
        return

    for suffix in ["", ".bak", ".pending"]:
        if FileAccess.file_exists(draft_path + suffix):
            DirAccess.remove_absolute(draft_path + suffix)
    editor.queue_free()
    print("DX2Ed v0.56 private hierarchy groups, parent transforms, tree selection, Undo/Redo, duplicate, reset, safe JSON reopen and malicious preflight PASS")
    quit(0)
