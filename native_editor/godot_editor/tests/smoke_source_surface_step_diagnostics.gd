extends SceneTree
## Asset-free Godot 4.3 source Level slope/edge/elevation diagnostics.
## There are NO retail triangles, no Havok runtime and no native GMP writes.

const Analyze = preload("res://source_surface_diagnostics.gd")
const InspectPanel = preload("res://source_surface_panel.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

class FakePicker:
    extends RefCounted
    var ready := true
    var source_map := "Fixture.gmp"
    var source_sha256 := "1111111111111111111111111111111111111111111111111111111111111111"
    var face_index_by_id := {0:0, 1:1, 5:2, 9:3}
    var samples: Dictionary = {}

    func triangle_details(original_id: int) -> Dictionary:
        return samples.get(original_id, {})

func _initialize() -> void:
    call_deferred("_run")

func _fail(why: String) -> void:
    push_error("DX2Ed slope and step research fixture: " + why)
    quit(1)

func _picker() -> FakePicker:
    var p := FakePicker.new()
    # One level floor, one upper floor, a slope and a vertical wall.
    p.samples[0] = {
        "vertices_godot": [
            Vector3(0,0,0), Vector3(2,0,0), Vector3(0,0,2)],
        "source_edge_kinds": [1,2,1],
        "original_level_triangle_id":0,
    }
    p.samples[1] = {
        "vertices_godot": [
            Vector3(0,1,0), Vector3(2,1,0), Vector3(0,1,2)],
        "source_edge_kinds": [1,0,1],
        "original_level_triangle_id":1,
    }
    p.samples[5] = {
        "vertices_godot": [
            Vector3(0,0,0), Vector3(2,1,0), Vector3(0,0,2)],
        "source_edge_kinds": [1,1,3],
        "original_level_triangle_id":5,
    }
    p.samples[9] = {
        "vertices_godot": [
            Vector3(0,0,0), Vector3(0,2,0), Vector3(0,0,2)],
        "source_edge_kinds": [1,1,1],
        "original_level_triangle_id":9,
    }
    return p

func _hit(tid:int, point:Vector3, ray:bool=true) -> Dictionary:
    return {
        "original_level_triangle_id":tid,
        "point_godot":point,
        "selection_is_ray_hit":ray,
    }

func _run() -> void:
    var geometry := Analyze.new()
    var picker := _picker()
    var flat: Dictionary = geometry.inspect(picker, _hit(0,Vector3(.5,0,.5)))
    if flat.is_empty() or absf(float(flat["unsigned_plane_slope_degrees"]))>1e-6:
        _fail("Source floor should be unsigned 0-degree plane")
        return
    if flat["edge_classes"][1].find("render-material seam")<0 or flat["edge_classes"][0]!="open boundary":
        _fail("Exact source edge classifications lost or guessed as physics materials")
        return
    if flat["gameplay_walkability_verified"] or flat["render_material_is_physical_material"]:
        _fail("Research slope must not become an authenticated Havok floor")
        return
    if flat["nearest_edge_ab_bc_ca"] not in [0,1,2]:
        _fail("Missing nearest source edge")
        return
    var slope: Dictionary = geometry.inspect(picker, _hit(5,Vector3(.5,.25,.5)))
    if slope.is_empty() or absf(float(slope["unsigned_plane_slope_degrees"])-26.565051)>0.001:
        _fail("Inclined source plane slope does not match analytic rise/run")
        return
    if absf(float(slope["edge_incline_degrees"][0])-26.565051)>0.001:
        _fail("Source AB edge rise/run angle incorrect")
        return
    if slope["edge_classes"][2].find("non-manifold")<0:
        _fail("Source non-manifold edge metadata missing")
        return
    var wall: Dictionary = geometry.inspect(picker, _hit(9,Vector3(0,.5,.5)))
    if wall.is_empty() or absf(float(wall["unsigned_plane_slope_degrees"])-90.)>1e-6:
        _fail("Vertical geometric wall must have unsigned slope 90 degrees")
        return
    if not geometry.inspect(picker, _hit(99,Vector3(.2,0,.2))).is_empty():
        _fail("Unknown original Level triangle ID accepted")
        return
    if not geometry.inspect(picker, _hit(0,Vector3(.2,.5,.2))).is_empty():
        _fail("Fake point off source triangle plane accepted")
        return
    if not geometry.inspect(picker, _hit(0,Vector3(2,0,2))).is_empty():
        _fail("Fake point outside source triangle accepted")
        return
    var upper: Dictionary = geometry.inspect(picker, _hit(1,Vector3(.5,1,.5)))
    var comparison: Dictionary = geometry.compare(flat, upper, 1., 12., 45.)
    if comparison.is_empty():
        _fail("Same footprint stacked surfaces should yield an elevation comparison")
        return
    if (absf(float(comparison["signed_height_difference_level_units"])-10.)>1e-6
        or absf(float(comparison["horizontal_gap_level_units"]))>1e-6
        or not comparison["vertical_discontinuity_proxy_only"]
        or not comparison["within_user_step_height_threshold"]
        or comparison["gameplay_step_or_walkability_verified"]):
        _fail("Signed height or step-limit proxy classification incorrect")
        return
    var small: Dictionary = geometry.compare(flat, upper, 1., 2., 45.)
    if not small["vertical_discontinuity_proxy_only"] or small["within_user_step_height_threshold"]:
        _fail("Height exceeding user's selected proxy threshold should be reported")
        return
    var reverse: Dictionary = geometry.compare(upper, flat, 1., 12., 45.)
    if absf(float(reverse["signed_height_difference_level_units"])+10.)>1e-6:
        _fail("Signed elevation does not reverse with pick order")
        return
    var far: Dictionary = geometry.inspect(picker, _hit(1,Vector3(1.5,1,.2)))
    if geometry.compare(flat,far,1.,12.,45.)["nearby_sampled_footprints"]:
        _fail("Distant horizontal samples misclassified as a local step")
        return
    var same: Dictionary = geometry.inspect(picker, _hit(0,Vector3(.7,0,.4)))
    if geometry.compare(flat,same,5.,10.,45.)["vertical_discontinuity_proxy_only"]:
        _fail("Two picks on same triangle cannot be promoted to a distinct step")
        return
    if geometry.compare(flat,slope,3.,12.,15.)["vertical_discontinuity_proxy_only"]:
        _fail("Sloped surface should exceed configured unsigned slope threshold")
        return
    picker.source_sha256 = "2222222222222222222222222222222222222222222222222222222222222222"
    var foreign: Dictionary = geometry.inspect(picker,_hit(1,Vector3(.5,1,.5)))
    if not geometry.compare(flat,foreign,1.,12.,45.).is_empty():
        _fail("Cross-map original SHA comparison must fail closed")
        return
    picker.source_sha256 = SHA
    var world := Node3D.new()
    root.add_child(world)
    var panel := InspectPanel.new()
    var container := Control.new()
    root.add_child(container)
    container.add_child(panel)
    panel.initialize(world)
    if panel.visible:
        _fail("Source surface diagnostic panel should start disabled")
        return
    panel.activate(picker)
    panel.observe_hit(_hit(0,Vector3(.5,0,.5)))
    if panel.current.is_empty() or panel.pin_button.disabled:
        _fail("Authentic source ray pick not shown in surface diagnostics")
        return
    panel.pin_reference()
    panel.observe_hit(_hit(1,Vector3(.5,1,.5)))
    if panel.reference.is_empty() or not is_instance_valid(panel.marker):
        _fail("Pinned surfaces did not create editor-only elevation line")
        return
    if not panel.note.text.contains("Vertical-offset proxy"):
        _fail("Inspector must explain that the step test is a proxy, not Havok")
        return
    if panel.marker.mesh == null or panel.marker.mesh.get_surface_count()!=1:
        _fail("Source elevation difference outline is empty")
        return
    panel.clear_reference()
    if not panel.reference.is_empty() or panel.marker != null:
        _fail("Clear reference retained source marker or comparison state")
        return
    panel.observe_hit(_hit(0,Vector3(.5,0,.5),false))
    if not panel.pin_button.disabled:
        _fail("Section centroid must not be pinnable as an actual ray hit")
        return
    panel.pin_reference()
    if not panel.reference.is_empty():
        _fail("Navigation centroid incorrectly promoted to real source sample")
        return
    panel.reset()
    if panel.visible or not panel.current.is_empty() or panel.marker != null:
        _fail("Source-scene change did not clear diagnostic state")
        return
    if load("res://main.gd")==null:
        _fail("DX2Ed main.gd integration cannot parse")
        return
    print("DX2Ed original surface slope/edge/step research fixture: PASS")
    quit(0)
