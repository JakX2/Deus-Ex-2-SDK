extends SceneTree
## Synthetic-only Godot 4.3 test for interactive two-point capsule picking.
## No retail GMP, subprocess, collision shape, native Save As, or Havok runtime.

const PickState = preload("res://capsule_sweep_picks.gd")
const SweepPanel = preload("res://capsule_sweep_panel.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

class MockPicker:
    extends RefCounted
    var ready := true
    var source_map := "Fixture.gmp"
    var source_sha256 := "1111111111111111111111111111111111111111111111111111111111111111"
    var face_index_by_id := {3: 0}

class MockHost:
    extends Control
    var source_collision_picker = MockPicker.new()
    var source_collision_mode := true
    var current_source_map_name := "Fixture.gmp"
    var source_gamesys_sha256 := "1111111111111111111111111111111111111111111111111111111111111111"
    var last_gmp_path := "C:/Research/Maps/Fixture.gmp"
    var current_folder := "C:/Research/PrivateCache"
    var status_label := Label.new()

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed interactive capsule sweep smoke: " + message)
    quit(1)

func _hit(point: Vector3, tid: int = 3) -> Dictionary:
    return {
        "selection_is_ray_hit": true,
        "original_level_triangle_id": tid,
        "point_godot": point,
        "normal_godot": Vector3.UP,
    }

func _run() -> void:
    var host := MockHost.new()
    root.add_child(host)
    var panel := SweepPanel.new()
    host.add_child(panel)
    panel.initialize(host)
    if panel.visible or panel.run_button == null or not panel.run_button.disabled:
        _fail("Inactive interactive sweep controls must default off")
        return
    panel.activate()
    if not panel.visible or panel.start_button.disabled or panel.end_button.disabled:
        _fail("Source-authenticated picker did not enable live selection")
        return
    panel._begin(1)
    if not panel.capture_pending() or not panel.accept_source_hit(_hit(Vector3(.4,0.,.3))):
        _fail("Valid start pick missing")
        return
    if panel.picks.start_preview.distance_to(Vector3(.4,.2,.3)) > .000001:
        _fail("Start offset ignored or Level/Godot scale incorrect")
        return
    panel._begin(2)
    if not panel.accept_source_hit(_hit(Vector3(.4,0.,.3))):
        _fail("Valid end pick missing")
        return
    if panel.picks.end_preview.distance_to(Vector3(.4,-.2,.3)) > .000001:
        _fail("End offset ignored or wrong signed normal")
        return
    if not panel.picks.can_run() or panel.run_button.disabled:
        _fail("A valid signed-offset sweep was not enabled")
        return
    var args := panel.picks.export_arguments(
        host.last_gmp_path, host.current_folder.path_join("preview.json"), .2, .5)
    if args.is_empty() or not args.has("--expected-sha256"):
        _fail("Original source hash and private path are absent from exporter arguments")
        return
    var start_idx := args.find("--start")
    var end_idx := args.find("--end")
    if (start_idx < 0 or end_idx < 0
        or absf(float(args[start_idx+1]) - 4.) > .000001
        or absf(float(args[start_idx+2]) - 3.) > .000001
        or absf(float(args[start_idx+3]) - 2.) > .000001
        or absf(float(args[end_idx+3]) + 2.) > .000001):
        _fail("Original Level XYZ was not recovered from Godot preview axes")
        return
    panel._begin(1)
    if panel.accept_source_hit(_hit(Vector3(.4,0.,.3), 999)):
        _fail("An unknown original source triangle ID was accepted")
        return
    if not panel.capture_pending():
        _fail("An invalid ray pick must not complete the pending surface selection")
        return
    panel.reset()
    if panel.visible or panel.picks.can_run() or panel.capture_pending():
        _fail("Map reset retained interactive capsule pick state")
        return
    panel.activate()
    panel._begin(1)
    host.source_gamesys_sha256 = "2222222222222222222222222222222222222222222222222222222222222222"
    if panel.accept_source_hit(_hit(Vector3(.4,0.,.3))):
        _fail("Switched original source SHA must invalidate picking")
        return
    if load("res://main.gd") == null:
        _fail("DX2Ed main.gd integration cannot parse")
        return
    panel.finish()
    print("DX2Ed interactive capsule sweep picker fixture: PASS")
    quit(0)
