extends SceneTree
## P111 regression: real Godot 4.3 JSON parser must not turn authentic
## original actor export IDs into false "not StaticMeshActor" refusals.
const Editor = preload("res://main.gd")

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed P111 JSON source export identity: " + message)
    quit(1)

func _run() -> void:
    var input: Variant = JSON.parse_string(
        "{\"export\":151,\"name\":\"StaticMeshActor__151\"}")
    if typeof(input) != TYPE_DICTIONARY or typeof(input["export"]) != TYPE_FLOAT:
        _fail("Expected actual Godot 4.3 JSON numeric export field to be FLOAT")
        return
    var editor := Editor.new()
    get_root().add_child(editor)
    if (editor._source_export_id_from_json(input["export"]) != 151
        or editor._source_export_id_from_json(151) != 151
        or editor._source_export_id_from_json(151.5) != -1
        or editor._source_export_id_from_json(0.0) != -1
        or editor._source_export_id_from_json(-12.0) != -1
        or editor._source_export_id_from_json("151") != -1
        or editor._source_export_id_from_json(INF) != -1
        or editor._source_export_id_from_json(NAN) != -1
        or editor._source_export_id_from_json(2147483648.0) != -1):
        _fail("Strict original JSON export ID normalization failed")
        return

    var scene := Node3D.new()
    scene.name = "OriginalActorTestScene"
    editor.world_root.add_child(scene)
    editor.scene_root = scene

    for name in ["StaticMeshActor__151", "D_2494", "OriginalFractional"]:
        var mesh := MeshInstance3D.new()
        mesh.mesh = BoxMesh.new()
        mesh.name = name
        scene.add_child(mesh)
        editor.meshes_by_actor[name] = mesh
        editor.original_mesh_transforms[name] = mesh.global_transform

    var root := ProjectSettings.globalize_path("user://p111_json_actor_fixture")
    if DirAccess.make_dir_recursive_absolute(root) != OK:
        _fail("Cannot create synthetic source fixture directory")
        return
    var actor_path := root.path_join("actors.json")
    var actor_doc := {
        "meta": {"source_map": "Synthetic.gmp",
                 "source_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"},
        "actors": [
            {"name": "StaticMeshActor__151", "class": "StaticMeshActor",
             "export": 151, "mesh": "BOX", "location": [0,0,0],
             "rotation": [0,0,0], "game_properties": []},
            {"name": "D_2494", "class": "D_2494",
             "export": 2494, "mesh": "DOOR", "location": [0,0,0],
             "rotation": [0,0,0], "game_properties": []},
            {"name": "OriginalFractional", "class": "StaticMeshActor",
             "export": 12.5, "mesh": "BOX", "location": [0,0,0],
             "rotation": [0,0,0], "game_properties": []}
        ]
    }
    var f := FileAccess.open(actor_path, FileAccess.WRITE)
    if f == null:
        _fail("Could not open synthetic actors.json fixture")
        return
    f.store_string(JSON.stringify(actor_doc))
    f.close()
    editor.load_actors(actor_path)
    if not editor.actors_by_name.has("StaticMeshActor__151"):
        _fail("Original actor was not loaded from actual JSON")
        return
    var original: Dictionary = editor.actors_by_name["StaticMeshActor__151"]
    if (typeof(original.get("export")) != TYPE_INT
        or int(original.get("export", -1)) != 151):
        _fail("Original StaticMeshActor JSON export ID remains floating-point")
        return
    if typeof(editor.actors_by_name["D_2494"].get("export")) != TYPE_INT:
        _fail("Other original source identities were not normalized")
        return
    if typeof(editor.actors_by_name["OriginalFractional"].get("export")) == TYPE_INT:
        _fail("Untrusted fractional source export was incorrectly promoted")
        return

    for name in ["StaticMeshActor__151", "D_2494", "OriginalFractional"]:
        var node: MeshInstance3D = editor.meshes_by_actor[name]
        node.global_position.x += editor.NATIVE_CLONE_UNREAL_METRES * 25.0
    var clone := MeshInstance3D.new()
    clone.name = "EditorCopy__1"
    clone.mesh = BoxMesh.new()
    scene.add_child(clone)
    clone.global_transform = editor.original_mesh_transforms["StaticMeshActor__151"]
    clone.global_position.z += editor.NATIVE_CLONE_UNREAL_METRES * 45.0
    editor.draft_prop_copies[clone.name] = clone
    editor.draft_prop_sources[clone.name] = "StaticMeshActor__151"
    var report := editor._native_bulk_preview()
    var plan: Dictionary = report["plan"]
    if (report["native_count"] != 2
        or plan["moves"].size() != 1
        or plan["copies"].size() != 1
        or plan["moves"][0]["export"] != 151
        or plan["copies"][0]["export"] != 151):
        _fail("Authentic JSON-loaded original static prop and clone still excluded: "
            + str(report))
        return
    var excluded := "\n".join(report["omitted"])
    if (excluded.find("D_2494: source class D_2494") < 0
        or excluded.find("OriginalFractional: original native export ID missing or invalid") < 0):
        _fail("Unsupported sources were not accurately labeled: " + excluded)
        return
    # No binary writer is invoked: synthetic export 151 is not an actual
    # package from retail and must never be treated as runtime-verified.
    DirAccess.remove_absolute(actor_path)
    editor.queue_free()
    print("DX2Ed P111 real JSON integral export and native bulk preview PASS")
    quit(0)
