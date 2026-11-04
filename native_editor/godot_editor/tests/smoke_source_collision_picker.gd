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
        "edge_provenance_schema": Picker.EDGE_SCHEMA,
        "source_topology_summary": {
            "source_exact_welded_vertex_count": 4,
            "unique_source_edges": 5,
            "open_boundary_edges": 4,
            "two_triangle_same_material_edges": 0,
            "two_triangle_render_material_seams": 1,
            "three_or_more_triangle_edges": 0,
            "max_triangles_using_one_edge": 2,
        },
        "vertices_godot_xyz": [[0.0,0.0,0.0],[2.0,0.0,0.0],
                               [0.0,0.0,2.0],[2.0,0.0,2.0]],
        "render_material_names": ["MatA", "MatB"],
        "leaf_triangles": [
            {"triangle_id": 0, "vertex_indices": [0,1,2], "source_block_id": 3,
             "render_block_ordinal": 0, "render_section_ordinal": 0,
             "render_material_id": 0, "source_edge_kinds": [1,2,1]},
            {"triangle_id": 1, "vertex_indices": [1,3,2], "source_block_id": 3,
             "render_block_ordinal": 0, "render_section_ordinal": 1,
             "render_material_id": 1, "source_edge_kinds": [1,1,2]},
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
        or hit.get("source_edge_kinds", []) != [1,2,1]
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
    var single_section: Dictionary = picker.section_details(0)
    if (single_section.get("triangle_count", -1) != 1
        or single_section.get("next_triangle_id", -1) != 0
        or single_section.get("outline_vertices_godot", PackedVector3Array()).size() != 6):
        _fail("Original section grouping lost a single source triangle")
        return
    if picker.triangle_details(1).get("render_material_name", "") != "MatB":
        _fail("Direct original triangle lookup did not retain render provenance")
        return
    var grouped := _fixture()
    grouped["leaf_triangles"][1]["render_section_ordinal"] = 0
    grouped["leaf_triangles"][1]["render_material_id"] = 0
    grouped["leaf_triangles"][0]["source_edge_kinds"] = [1,0,1]
    grouped["leaf_triangles"][1]["source_edge_kinds"] = [1,1,0]
    grouped["source_topology_summary"]["two_triangle_same_material_edges"] = 1
    grouped["source_topology_summary"]["two_triangle_render_material_seams"] = 0
    if not picker.load_document(grouped, SHA, "Fixture.gmp"):
        _fail("Two triangles in the same verified render section rejected: " + picker.last_error)
        return
    var section: Dictionary = picker.section_details(0)
    if (section.get("triangle_count", -1) != 2
        or section.get("next_triangle_id", -1) != 1
        or section.get("previous_triangle_id", -1) != 1
        or section.get("outline_vertices_godot", PackedVector3Array()).size() != 12):
        _fail("Original render-section ordering or geometry preview failed")
        return
    var capped: Dictionary = picker.section_details(0, 1)
    if (not capped.get("preview_skipped_for_size", false)
        or not capped.get("outline_vertices_godot", PackedVector3Array()).is_empty()
        or capped.get("triangle_count", -1) != 2):
        _fail("Large render sections must not silently produce partial outlines")
        return
    if not picker.section_details(-1).is_empty() or not picker.triangle_details(666).is_empty():
        _fail("Out-of-range original triangle ID lookup must refuse")
        return
    var conflicted := _fixture()
    conflicted["leaf_triangles"][1]["render_section_ordinal"] = 0
    if picker.load_document(conflicted, SHA, "Fixture.gmp"):
        _fail("Contradictory render material in one source section was accepted")
        return
    if not picker.load_document(decoded, SHA, "Fixture.gmp"):
        _fail("Failed to restore default picker after section checks")
        return
    var bad_edges := _fixture()
    bad_edges["leaf_triangles"][0]["source_edge_kinds"] = [1,1,1]
    if picker.load_document(bad_edges, SHA, "Fixture.gmp"):
        _fail("Inconsistent source edge incidence totals were accepted")
        return
    var old_cache := _fixture()
    old_cache["schema"] = "DX2Ed-source-MOPP-collision-selection-cache-v1"
    if picker.load_document(old_cache, SHA, "Fixture.gmp"):
        _fail("Old v1 cache without mandatory topology metadata was accepted")
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
    gap["leaf_triangles"][0]["source_edge_kinds"] = [1,1,1]
    gap["source_topology_summary"]["unique_source_edges"] = 3
    gap["source_topology_summary"]["open_boundary_edges"] = 3
    gap["source_topology_summary"]["two_triangle_render_material_seams"] = 0
    gap["source_topology_summary"]["max_triangles_using_one_edge"] = 1
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
    if editor.source_collision_section_actions.visible:
        _fail("Section navigation must remain hidden before first source triangle selection")
        return
    var chosen: Dictionary = editor.source_collision_picker.ray_pick(
        Vector3(0.4, 3, 0.3), Vector3.DOWN)
    chosen["selection_is_ray_hit"] = true
    editor._show_source_collision_hit(chosen)
    if (not editor.source_collision_section_actions.visible
        or editor.source_collision_last_hit.get("original_level_triangle_id", -1) != 0
        or not editor.source_collision_details.text.contains("1 of 1")
        or not editor.source_collision_details.text.contains("open boundary")
        or not is_instance_valid(editor.source_collision_marker)):
        _fail("Editor source-section controls did not activate on ray selection")
        return
    var evidence: Variant = JSON.parse_string(editor._source_collision_evidence_json())
    if (typeof(evidence) != TYPE_DICTIONARY
        or evidence.get("original_level_triangle_id", -1) != 0
        or evidence.get("source_sha256", "") != SHA
        or evidence.get("render_material_name", "") != "MatA"
        or evidence.get("source_edge_kinds_ab_bc_ca", []) != [1,2,1]
        or evidence.get("render_material_is_physics_material", true) != false):
        _fail("Copyable evidence lost source identity or mislabeled physics materials")
        return
    editor.source_collision_section_toggle.set_pressed_no_signal(true)
    editor._toggle_source_collision_section_outline(true)
    if not is_instance_valid(editor.source_collision_section_marker):
        _fail("Editor-only original render-section preview was not created")
        return
    editor._step_source_collision_triangle(1)
    if (editor.source_collision_last_hit.get("original_level_triangle_id", -1) != 0
        or editor.source_collision_last_hit.get("selection_is_ray_hit", true) != false
        or not editor.source_collision_details.text.contains("section navigation")):
        _fail("Navigating source section must use centroid and not fake a ray hit")
        return
    editor.source_collision_button.set_pressed_no_signal(false)
    editor._toggle_source_collision_inspection()
    if (editor.source_collision_mode or editor.source_collision_picker.ready
        or editor.source_collision_details.visible
        or editor.source_collision_section_actions.visible
        or not editor.source_collision_last_hit.is_empty()
        or editor.source_collision_marker != null
        or editor.source_collision_section_marker != null):
        _fail("Turning off collision inspect must clean up source-only overlays and navigation")
        return
    editor.queue_free()
    DirAccess.remove_absolute(ProjectSettings.globalize_path(cache_path))
    print("DX2Ed source collision picker fixture: PASS")
    quit(0)