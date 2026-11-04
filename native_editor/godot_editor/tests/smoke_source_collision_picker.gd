extends SceneTree
## Fixture-only Godot 4.3 test: source-hash-gated triangle selection and BVH.
## No retail GMP, GLB, Havok executable, collision material or write operation.

const Picker = preload("res://collision_source_picker.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

func _initialize() -> void:
    call_deferred("_run")

func _fail(reason: String) -> void:
    push_error("DX2Ed source collision picker smoke: " + reason)
    quit(1)

func _fixture() -> Dictionary:
    return {
        "schema": Picker.SCHEMA,
        "source_map": "Fixture.gmp",
        "source_sha256": SHA,
        "read_only": true,
        "not_a_native_collision_writer": true,
        "physics_materials_verified": false,
        "coordinate_system": "Godot preview (Level.x/10, Level.z/10, Level.y/10)",
        "source_flat_vertex_count": 4,
        "source_triangle_count": 2,
        "mopp_leaf_triangle_count": 2,
        "vertices_godot_xyz": [[0.0,0.0,0.0],[2.0,0.0,0.0],
                               [0.0,0.0,2.0],[2.0,0.0,2.0]],
        "render_material_names": ["MatA", "MatB"],
        "leaf_triangles": [
            {"triangle_id": 0, "vertex_indices": [0,1,2], "source_block_id": 3,
             "render_block_ordinal": 0, "render_section_ordinal": 0,
             "render_material_id": 0},
            {"triangle_id": 1, "vertex_indices": [1,3,2], "source_block_id": 3,
             "render_block_ordinal": 0, "render_section_ordinal": 1,
             "render_material_id": 1},
        ],
    }

func _run() -> void:
    var picker := Picker.new()
    var doc := _fixture()
    # JSON parsing can turn numbers into floats. This must not break original IDs.
    var decoded: Variant = JSON.parse_string(JSON.stringify(doc))
    if not picker.load_document(decoded, SHA, "Fixture.gmp"):
        _fail("Valid JSON round-trip refused: " + picker.last_error)
        return
    if not picker.ready or picker.tree.size() == 0:
        _fail("Valid source collision cache missing BVH")
        return
    var hit: Dictionary = picker.ray_pick(Vector3(0.4, 3, 0.3), Vector3.DOWN)
    if (hit.is_empty() or hit["original_level_triangle_id"] != 0
        or hit["render_material_name"] != "MatA"
        or hit["source_block_id"] != 3
        or abs(float(hit["distance_godot_units"])-3.0) > 0.00001):
        _fail("Ray does not preserve triangle zero and its source provenance")
        return
    var other := picker.ray_pick(Vector3(1.6, 3, 1.7), Vector3.DOWN)
    if other.is_empty() or other["original_level_triangle_id"] != 1 or other["render_material_name"] != "MatB":
        _fail("Second triangle did not retain source material")
        return
    if picker.ray_pick(Vector3(10, 3, 10), Vector3.DOWN).size() != 0:
        _fail("Ray misses must not create a false source triangle")
        return
    if picker.ray_pick(Vector3(0.3, -3, 0.3), Vector3.UP).is_empty():
        _fail("Geometric selection must support backfaces")
        return
    if picker.ray_pick(Vector3(0,0,0), Vector3.ZERO).size() != 0:
        _fail("Zero-length ray must be rejected")
        return
    if picker.load_document(decoded, "0".repeat(64), "Fixture.gmp") or picker.ready:
        _fail("Stale source digest accepted")
        return
    if picker.load_document(decoded, SHA, "Another.gmp") or picker.ready:
        _fail("Wrong map accepted")
        return
    var gap := _fixture()
    gap["leaf_triangles"].remove_at(0)
    gap["mopp_leaf_triangle_count"] = 1
    if not picker.load_document(gap, SHA, "Fixture.gmp"):
        _fail("MOPP omission gaps must be preserved: " + picker.last_error)
        return
    if picker.ray_pick(Vector3(0.4, 3, 0.3), Vector3.DOWN).size() != 0:
        _fail("Omitted non-MOPP triangle must not be selectable")
        return
    if picker.ray_pick(Vector3(1.6, 3, 1.7), Vector3.DOWN).get("original_level_triangle_id", -1) != 1:
        _fail("Sparse original triangle ID must be retained")
        return
    var invalid := _fixture()
    invalid["leaf_triangles"][0]["vertex_indices"] = [0,1,9999]
    if picker.load_document(invalid, SHA, "Fixture.gmp"):
        _fail("Out-of-range source vertex accepted")
        return
    invalid = _fixture()
    invalid["physics_materials_verified"] = true
    if picker.load_document(invalid, SHA, "Fixture.gmp"):
        _fail("Unproven physical material accepted")
        return
    # Verify the actual DX2Ed toolbar/inspector integration as well as the
    # independent BVH, using a synthetic sidecar under user:// only.
    var editor = load("res://main.gd").new()
    root.add_child(editor)
    if editor.source_collision_button == null or not editor.source_collision_button.disabled:
        _fail("Source collision mode must exist and default to disabled")
        return
    var cache_path := "user://fixture_source_collision_pick.json"
    var fixture_file := FileAccess.open(cache_path, FileAccess.WRITE)
    if fixture_file == null:
        _fail("Unable to write private synthetic collision picker sidecar")
        return
    fixture_file.store_string(JSON.stringify(_fixture()))
    fixture_file.close()
    editor.current_source_map_name = "Fixture.gmp"
    editor.source_gamesys_sha256 = SHA
    editor.source_collision_button.disabled = false
    editor._activate_source_collision_cache(ProjectSettings.globalize_path(cache_path))
    if (not editor.source_collision_mode or not editor.source_collision_picker.ready
        or not editor.source_collision_button.button_pressed
        or not editor.source_collision_details.visible
        or not editor.source_collision_details.text.contains("READ-ONLY")):
        _fail("DX2Ed did not enable source collision inspector on authenticated fixture")
        return
    editor.source_collision_button.set_pressed_no_signal(false)
    editor._toggle_source_collision_inspection()
    if (editor.source_collision_mode or editor.source_collision_picker.ready
        or editor.source_collision_details.visible):
        _fail("Turning off collision inspect must restore independent actor selection")
        return
    editor.queue_free()
    DirAccess.remove_absolute(ProjectSettings.globalize_path(cache_path))
    print("DX2Ed source collision picker fixture: PASS")
    quit(0)