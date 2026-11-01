extends SceneTree
## Read-only, asset-free DX2Ed picking smoke test.
## Run from repo root with:
## godot --headless --path native_editor/godot_editor --script res://tests/smoke_triangle_picking.gd

func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed triangle picking smoke: " + message)
    quit(1)


func _run() -> void:
    var script = load("res://main.gd")
    var viewer = script.new()
    root.add_child(viewer)

    # A normal triangle mesh should be selectable by its real surface.
    var solid := MeshInstance3D.new()
    solid.name = "TestSolid"
    var cube := BoxMesh.new()
    cube.size = Vector3(2.0, 2.0, 2.0)
    solid.mesh = cube
    root.add_child(solid)
    var ray_origin := Vector3(0.0, 0.0, 5.0)
    var ray_dir := Vector3(0.0, 0.0, -1.0)
    var hit: Dictionary = viewer._ray_mesh_triangles(solid, ray_origin, ray_dir)
    if hit.is_empty() or abs(float(hit.get("distance", -1.0)) - 4.0) > 0.001:
        _fail("solid box front face should be 4 Godot units away")
        return

    # Ensure transformed instances are handled in local coordinates.
    solid.scale = Vector3(1.2, 1.5, 0.5)
    solid.rotation_degrees = Vector3(0.0, 35.0, 0.0)
    hit = viewer._ray_mesh_triangles(solid, ray_origin, ray_dir)
    if hit.is_empty() or float(hit["distance"]) <= 0.0:
        _fail("rotated and non-uniformly scaled box should be hittable")
        return

    # A ray can intersect an AABB without intersecting either of its triangles.
    # This is the original selection problem with sprawling BSP bounds.
    var arrays := []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array([
        Vector3(-10.0, -1.0, 0.0), Vector3(-8.0, -1.0, 0.0), Vector3(-10.0, 1.0, 0.0),
        Vector3(8.0, -1.0, 0.0), Vector3(10.0, -1.0, 0.0), Vector3(10.0, 1.0, 0.0)
    ])
    var sparse_mesh := ArrayMesh.new()
    sparse_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    var sparse := MeshInstance3D.new()
    sparse.mesh = sparse_mesh
    root.add_child(sparse)
    if viewer._ray_aabb(ray_origin, ray_dir, viewer._mesh_world_aabb(sparse)) < 0.0:
        _fail("fixture error: central ray must intersect sparse mesh AABB")
        return
    if not viewer._ray_mesh_triangles(sparse, ray_origin, ray_dir).is_empty():
        _fail("AABB-only false positive: central ray does not intersect triangles")
        return

    # Retail Actor Explorer JSON uses a string mesh and separate mesh_bounds.
    var diagnosis: String = viewer._format_actor_diagnostic({
        "name": "TestActor", "class": "StaticMeshActor", "export": 7,
        "mesh": "FixtureMesh", "mesh_bounds": [[-1, -1, -1], [1, 1, 1]],
        "location": [10, 20, 30], "rotation": [0, 16384, 0]
    })
    if not diagnosis.contains("Mesh resource: FixtureMesh") or not diagnosis.contains("10, 20, 30"):
        _fail("Actor Explorer schema did not reach diagnostic")
        return

    print("DX2Ed triangle picking smoke: PASS (faces, transforms, sparse AABB, actor schema)")
    quit(0)
