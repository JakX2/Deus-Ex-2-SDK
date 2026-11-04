extends SceneTree
## Synthetic one-height replay parity against PR #52 multi-height output.
## No GMP worker or original assets; never claims native DX2 controller behavior.
const Height = preload("res://source_edge_capsule_height_overlay.gd")
const Replay = preload("res://source_edge_capsule_height_replay.gd")
const SHA := "4444444444444444444444444444444444444444444444444444444444444444"
const A := Vector3(.8, .1, .8)
const B := Vector3(1.2, .1, 1.2)
const OFFSETS := [0., .5, 1.]

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed authenticated source edge height replay: " + message)
    quit(1)

func _profile() -> Dictionary:
    return {
        "schema": Height.SCHEMA,
        "source_map": "Fixture.gmp", "source_sha256": SHA,
        "read_only": true, "not_a_native_collision_writer": true,
        "original_game_assets_modified": false,
        "havok_runtime_contact_verified": false, "physics_materials_verified": false,
        "coordinate_system": Height.COORD,
        "height_direction_original_Level": "positive Z",
        "height_offsets_relative_to_baseline": true,
        "contact_is_not_a_blocking_classifier": true,
        "no_contact_is_not_proof_of_walkability": true,
        "baseline_capsule_start_godot_xyz": [.8,.1,.8],
        "baseline_capsule_end_godot_xyz": [1.2,.1,1.2],
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

func _chord() -> Dictionary:
    return {
        "schema": "DX2Ed-source-exact-edge-capsule-chord-v1",
        "source_map": "Fixture.gmp",
        "source_sha256": SHA,
        "source_exact_welded_connectivity": true,
        "start_godot_xyz": A,
        "end_godot_xyz": B,
        "radius_level_units": .2,
        "axis_half_length_level_units": .5,
    }

func _contact(start: Vector3, finish: Vector3, hit_id: int,
              t: float, first_overlap: bool = false) -> Dictionary:
    var record: Variant = null
    if hit_id >= 0:
        record = {
            "original_level_triangle_id": hit_id,
            "t_first_inside": t,
            "t_last_outside": null if first_overlap else t-.000000005,
            "contact_triangle_point_godot_xyz": [.9, .1, .9],
            "contact_capsule_axis_point_godot_xyz": [.9, .12, .9],
            "contact_normal_godot_xyz": [0., 1., 0.],
            "contact_normal_resolved": true,
            "initial_overlap": first_overlap,
            "near_tangency": false,
            "numerical_contact_only": false,
            "signed_gap_at_contact_level_units": 0.0,
            "original_mopp_candidate_included": true,
        }
    return {
        "schema": "DX2Ed-capsule-first-contact-preview-v1",
        "source_map": "Fixture.gmp", "source_sha256": SHA,
        "read_only": true, "not_a_native_collision_writer": true,
        "havok_runtime_contact_verified": false,
        "time_of_impact_exact_havok": false,
        "physics_materials_verified": false,
        "original_game_assets_modified": false,
        "coordinate_system": Height.COORD,
        "capsule_start_godot_xyz": [start.x, start.y, start.z],
        "capsule_end_godot_xyz": [finish.x, finish.y, finish.z],
        "capsule_axis_unit_godot_xyz": [0.,1.,0.],
        "capsule_radius_godot_units": .02,
        "capsule_axis_half_length_godot_units": .05,
        "geometric_source_triangle_hits": 0 if hit_id < 0 else 1,
        "source_verified_mopp_leaf_ids": 2,
        "first_hit": record,
    }

func _run() -> void:
    var model = Height.new()
    if not model.load_document(_profile(), "Fixture.gmp", SHA, A, B,
                               OFFSETS, .2, .5, {0:0, 1:1}):
        _fail("Synthetic private profile rejected: " + model.last_error)
        return
    var checker = Replay.new()
    var path := "C:/Synthetic/Maps/Fixture.gmp"
    var output := "C:/Synthetic/Private/replay.json"
    var first: Dictionary = checker.plan(
        model, 0, path, output, "Fixture.gmp", SHA, _chord())
    if first.is_empty() or not bool(first["research_only"]):
        _fail("First source-validated height replay plan missing: " + checker.last_error)
        return
    if first["start_godot_xyz"] != A or first["end_godot_xyz"] != B:
        _fail("Replay baseline shifted independently of authenticated profile")
        return
    var args: PackedStringArray = first["arguments"]
    if (args.find("--expected-sha256") < 0 or args.find(SHA) < 0
        or args.find("--radius") < 0 or args.find("--axis-half-length") < 0
        or args.find("--height-offsets") >= 0):
        _fail("Single-height replay has invalid worker arguments")
        return
    if not checker.verify_replay_document(
        _contact(A,B,0,.3), first, {0:0,1:1}):
        _fail("Matching original first-contact result refused: " + checker.last_error)
        return
    var high: Dictionary = checker.plan(
        model, 1, path, output, "Fixture.gmp", SHA, _chord())
    if high.is_empty():
        _fail("No-contact height should still allow detailed replay")
        return
    var up := Vector3.UP * .05
    if high["start_godot_xyz"].distance_to(A+up) > .000001:
        _fail("Height offset was not translated into Godot UP from original Level Z")
        return
    if not checker.verify_replay_document(
        _contact(A+up,B+up,-1,0.), high, {0:0,1:1}):
        _fail("No-contact replay contradicted its source profile")
        return
    var third: Dictionary = checker.plan(
        model, 2, path, output, "Fixture.gmp", SHA, _chord())
    var up2 := Vector3.UP * .1
    if not checker.verify_replay_document(
        _contact(A+up2,B+up2,1,0.,true), third, {0:0,1:1}):
        _fail("Initial-overlap height sample could not be replayed")
        return
    var forged := _contact(A,B,0,.3)
    forged["first_hit"]["original_level_triangle_id"] = 1
    if checker.verify_replay_document(forged, first, {0:0,1:1}):
        _fail("Different original triangle ID accepted from independent worker")
        return
    forged = _contact(A,B,0,.4)
    if checker.verify_replay_document(forged, first, {0:0,1:1}):
        _fail("Different first-entry path time accepted")
        return
    forged = _contact(A,B,0,.3)
    forged["first_hit"]["near_tangency"] = true
    if checker.verify_replay_document(forged, first, {0:0,1:1}):
        _fail("Different tangency evidence accepted")
        return
    forged = _contact(A+up,B+up,0,.3)
    if checker.verify_replay_document(forged, high, {0:0,1:1}):
        _fail("Contact fabricated on no-contact profile lane")
        return
    forged = _contact(A+Vector3.UP,B,0,.3)
    if checker.verify_replay_document(forged, first, {0:0,1:1}):
        _fail("Changed source trajectory accepted after replay")
        return
    forged = _contact(A,B,0,.3)
    forged["capsule_radius_godot_units"] = .1
    if checker.verify_replay_document(forged, first, {0:0,1:1}):
        _fail("Changed player capsule size accepted after replay")
        return
    forged = _contact(A,B,0,.3)
    forged["source_sha256"] = "2222222222222222222222222222222222222222222222222222222222222222"
    if checker.verify_replay_document(forged, first, {0:0,1:1}):
        _fail("Foreign map contact accepted")
        return
    var wrong_chord := _chord()
    wrong_chord["start_godot_xyz"] = Vector3(99.,99.,99.)
    if not checker.plan(model,0,path,output,"Fixture.gmp",SHA,wrong_chord).is_empty():
        _fail("Forged baseline source chord created a replay")
        return
    if not checker.plan(model,9,path,output,"Fixture.gmp",SHA,_chord()).is_empty():
        _fail("Out-of-bounds sampled height created a replay")
        return
    if not checker.plan(model,0,path,output,"Fixture.gmp",
                        "2222222222222222222222222222222222222222222222222222",
                        _chord()).is_empty():
        _fail("Stale authenticated profile SHA replay permitted")
        return
    if load("res://main.gd") == null:
        _fail("DX2Ed main scene fails to parse with replay worker")
        return
    print("DX2Ed source-exact multi-height detailed capsule replay: PASS")
    quit(0)
