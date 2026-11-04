extends SceneTree
## Fixture-only Godot 4.3 smoke test for DX2Ed capsule contact RESEARCH overlay.
## No retail GMP, runtime Havok, contact manifold or native map writing.

const Preview = preload("res://capsule_contact_preview.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed capsule research preview smoke: " + message)
    quit(1)

func _fixture() -> Dictionary:
    return {
        "schema": Preview.SCHEMA,
        "source_map": "Fixture.gmp",
        "source_sha256": SHA,
        "read_only": true,
        "not_a_native_collision_writer": true,
        "havok_runtime_contact_verified": false,
        "time_of_impact_exact_havok": false,
        "physics_materials_verified": false,
        "original_game_assets_modified": false,
        "coordinate_system": Preview.COORD,
        "capsule_start_godot_xyz": [0.05, 0.2, 0.05],
        "capsule_end_godot_xyz": [0.05, -0.2, 0.05],
        "capsule_axis_unit_godot_xyz": [0.0, 1.0, 0.0],
        "capsule_radius_godot_units": 0.025,
        "capsule_axis_half_length_godot_units": 0.0,
        "geometric_source_triangle_hits": 1,
        "source_verified_mopp_leaf_ids": 1,
        "first_hit": {
            "original_level_triangle_id": 3,
            "t_first_inside": 0.43750001,
            "t_last_outside": 0.437500005,
            "contact_triangle_point_godot_xyz": [0.05, 0.0, 0.05],
            "contact_capsule_axis_point_godot_xyz": [0.05, 0.025, 0.05],
            "contact_normal_godot_xyz": [0.0, 1.0, 0.0],
            "contact_normal_resolved": true,
            "initial_overlap": false,
            "near_tangency": false,
            "numerical_contact_only": false,
            "signed_gap_at_contact_level_units": 0.00000004,
            "original_mopp_candidate_included": true,
        },
    }

func _run() -> void:
    var overlay = Preview.new()
    var data: Variant = JSON.parse_string(JSON.stringify(_fixture()))
    # One original terminal leaf in this fixture, matching the sidecar metadata.
    var known_faces := {3: 0}
    if not overlay.load_document(data, SHA, "Fixture.gmp", known_faces):
        _fail("Valid source-hash-bound research preview refused: " + overlay.last_error)
        return
    if (not overlay.ready or overlay.contact_triangle_id != 3
        or absf(overlay.contact_t - 0.43750001) > 0.000001
        or not overlay.normal_resolved
        or overlay.description().find("NOT Havok") < 0):
        _fail("Original triangle ID, timing, normal or explicit limits missing")
        return
    var mesh: ImmediateMesh = overlay.make_mesh()
    if mesh == null or mesh.get_surface_count() != 1:
        _fail("Read-only research path/ring/normal overlay was not generated")
        return
    if mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size() < 100:
        _fail("No meaningful capsule outline or contact marker was emitted")
        return
    var malformed := _fixture()
    malformed["source_sha256"] = "2222222222222222222222222222222222222222222222222222222222222222"
    if overlay.load_document(malformed, SHA, "Fixture.gmp", known_faces) or overlay.ready:
        _fail("Stale or foreign source hash accepted")
        return
    malformed = _fixture()
    malformed["first_hit"]["original_level_triangle_id"] = 9
    if overlay.load_document(malformed, SHA, "Fixture.gmp", known_faces):
        _fail("Unknown original Level triangle ID accepted")
        return
    malformed = _fixture()
    malformed["first_hit"]["contact_normal_godot_xyz"] = [0.0, 40.0, 0.0]
    if overlay.load_document(malformed, SHA, "Fixture.gmp", known_faces):
        _fail("Unnormalized or invented contact normal accepted")
        return
    malformed = _fixture()
    malformed["first_hit"]["t_last_outside"] = -1.0
    if overlay.load_document(malformed, SHA, "Fixture.gmp", known_faces):
        _fail("Invalid numerical first-contact time bracket accepted")
        return
    malformed = _fixture()
    malformed["first_hit"]["contact_normal_resolved"] = false
    malformed["first_hit"]["contact_normal_godot_xyz"] = null
    if not overlay.load_document(malformed, SHA, "Fixture.gmp", known_faces) or overlay.normal_resolved:
        _fail("Unresolved normal should remain legitimate and explicit")
        return
    malformed = _fixture()
    malformed["first_hit"] = null
    malformed["geometric_source_triangle_hits"] = 0
    if not overlay.load_document(malformed, SHA, "Fixture.gmp", known_faces):
        _fail("No-contact motion should be previewable as no-contact")
        return
    if overlay.contact_triangle_id != -1 or overlay.description().find("No geometric contact") < 0:
        _fail("No-contact preview fabricated a triangle hit")
        return
    if overlay.make_mesh() == null:
        _fail("No-contact path should still render")
        return
    if load("res://main.gd") == null:
        _fail("Main DX2Ed integration script cannot be parsed")
        return
    print("DX2Ed capsule contact research preview: PASS")
    quit(0)
