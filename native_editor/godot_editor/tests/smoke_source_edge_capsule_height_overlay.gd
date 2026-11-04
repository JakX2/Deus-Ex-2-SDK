extends SceneTree
## No retail maps or worker launches. Synthetic, source-bound profile viewport.
const HeightOverlay = preload("res://source_edge_capsule_height_overlay.gd")
const SweepPanel = preload("res://capsule_sweep_panel.gd")
const SHA := "4444444444444444444444444444444444444444444444444444444444444444"
const A := Vector3(.8, .1, .8)
const B := Vector3(1.2, .1, 1.2)
const OFFSETS := [0., .5, 1.]

class FakePicker:
    extends RefCounted
    var ready := true
    var source_map := "Fixture.gmp"
    var source_sha256 := "4444444444444444444444444444444444444444444444444444444444444444"
    var face_index_by_id := {0: 0, 1: 1}

class FakeHost:
    extends Control
    var source_collision_mode := true
    var current_source_map_name := "Fixture.gmp"
    var source_gamesys_sha256 := "4444444444444444444444444444444444444444444444444444444444444444"
    var source_collision_picker = FakePicker.new()
    var world_root: Node3D
    var status_label := Label.new()

func _initialize() -> void:
    call_deferred("_run")

func _fail(reason: String) -> void:
    push_error("DX2Ed source edge height profile overlay: " + reason)
    quit(1)

func _document() -> Dictionary:
    return {
        "schema": HeightOverlay.SCHEMA,
        "source_map": "Fixture.gmp",
        "source_sha256": SHA,
        "read_only": true,
        "not_a_native_collision_writer": true,
        "original_game_assets_modified": false,
        "havok_runtime_contact_verified": false,
        "physics_materials_verified": false,
        "coordinate_system": HeightOverlay.COORD,
        "height_direction_original_Level": "positive Z",
        "height_offsets_relative_to_baseline": true,
        "contact_is_not_a_blocking_classifier": true,
        "no_contact_is_not_proof_of_walkability": true,
        "baseline_capsule_start_godot_xyz": [.8, .1, .8],
        "baseline_capsule_end_godot_xyz": [1.2, .1, 1.2],
        "capsule_radius_level_units": .2,
        "capsule_axis_half_length_level_units": .5,
        "profile_samples": [
            {"relative_height_level_units": 0.,
             "geometric_source_triangle_hits": 1,
             "first_hit_original_triangle_id": 0,
             "first_contact_path_t": .3,
             "first_contact_initial_overlap": false,
             "first_contact_near_tangency": false},
            {"relative_height_level_units": .5,
             "geometric_source_triangle_hits": 0,
             "first_hit_original_triangle_id": null,
             "first_contact_path_t": null,
             "first_contact_initial_overlap": null,
             "first_contact_near_tangency": null},
            {"relative_height_level_units": 1.,
             "geometric_source_triangle_hits": 1,
             "first_hit_original_triangle_id": 1,
             "first_contact_path_t": 0.,
             "first_contact_initial_overlap": true,
             "first_contact_near_tangency": false},
        ],
    }

func _accept(visual: RefCounted, data: Dictionary, sha: String = SHA) -> bool:
    return visual.load_document(
        data, "Fixture.gmp", sha, A, B, OFFSETS, .2, .5, {0:0, 1:1})

func _run() -> void:
    var visual = HeightOverlay.new()
    if not _accept(visual, _document()) or not visual.ready:
        _fail("Authenticated synthetic source-bound height data rejected: " + visual.last_error)
        return
    if (visual.profile_rows.size() != 3
        or int(visual.profile_rows[0]["count"]) != 1
        or int(visual.profile_rows[1]["count"]) != 0
        or int(visual.profile_rows[2]["first_id"]) != 1):
        _fail("Validated independent source contact summaries are missing")
        return
    var mesh: ImmediateMesh = visual.make_mesh()
    if mesh == null or mesh.get_surface_count() != 1:
        _fail("Read-only 3D line mesh missing")
        return
    var vertices: PackedVector3Array = mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    if vertices.size() != 26:
        _fail("Unexpected number of profile lines, endpoint ticks or hit crosses")
        return
    var examples := [
        ["source_sha256", "deadbeef"],
        ["source_map", "Other.gmp"],
        ["original_game_assets_modified", true],
        ["havok_runtime_contact_verified", true],
        ["height_direction_original_Level", "negative Z"],
        ["baseline_capsule_start_godot_xyz", [20., 20., 20.]],
        ["capsule_radius_level_units", 2.],
        ["profile_samples", []],
    ]
    for entry in examples:
        var forged := _document()
        forged[entry[0]] = entry[1]
        if _accept(visual, forged):
            _fail("Forged or invalid original collision profile header was accepted")
            return
    var bad_count := _document()
    bad_count["profile_samples"][0]["geometric_source_triangle_hits"] = 3
    if _accept(visual, bad_count):
        _fail("Impossible contact count above source triangle domain accepted")
        return
    var forged_id := _document()
    forged_id["profile_samples"][0]["first_hit_original_triangle_id"] = 77
    if _accept(visual, forged_id):
        _fail("Unknown original triangle ID used for a contact marker")
        return
    var fake_free := _document()
    fake_free["profile_samples"][1]["first_contact_path_t"] = .5
    if _accept(visual, fake_free):
        _fail("No-contact path invented first-contact time")
        return
    var forged_offset := _document()
    forged_offset["profile_samples"][1]["relative_height_level_units"] = .75
    if _accept(visual, forged_offset):
        _fail("Worker returned a height not in the submitted profile")
        return
    var nan_time := _document()
    nan_time["profile_samples"][0]["first_contact_path_t"] = NAN
    if _accept(visual, nan_time):
        _fail("Nonfinite first-contact time accepted")
        return
    if not _accept(visual, _document()):
        _fail("Could not restore synthetic profile for viewport")
        return
    var host := FakeHost.new()
    root.add_child(host)
    var world := Node3D.new()
    root.add_child(world)
    host.world_root = world
    var sweep := SweepPanel.new()
    host.add_child(sweep)
    sweep.initialize(host)
    sweep.activate()
    if not _accept(sweep.height_overlay, _document()):
        _fail("Capsule panel rejected profile geometry")
        return
    if not sweep._show_height_overlay():
        _fail("Authenticated profile did not create editor-only wireframe")
        return
    if world.get_child_count() != 1 or sweep.height_overlay_marker == null:
        _fail("Preview marker was not attached strictly to editor world")
        return
    if sweep.height_overlay_marker.name != (
        "ResearchOnly_SourceEdgeCapsuleHeightPaths_NOT_GamePhysics"):
        _fail("Profile marker is not explicitly research-only")
        return
    host.source_gamesys_sha256 = "2222222222222222222222222222222222222222222222222222222222222222"
    if sweep._show_height_overlay():
        _fail("Stale original GMP SHA was accepted by viewport")
        return
    host.source_gamesys_sha256 = SHA
    sweep.reset()
    await process_frame
    if world.get_child_count() != 0 or sweep.height_overlay.ready:
        _fail("Source collision reset leaked private height-path wireframe")
        return
    if sweep.clear_profile_button == null or not sweep.clear_profile_button.disabled:
        _fail("Clear overlay control remained actionable without valid profile")
        return
    if load("res://main.gd") == null:
        _fail("DX2Ed scene cannot parse with new capsule height overlay")
        return
    print("DX2Ed source edge capsule multi-height viewport overlay: PASS")
    quit(0)
