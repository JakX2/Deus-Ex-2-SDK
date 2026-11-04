extends SceneTree
## Asset-free v3 exact-weld source-edge capsule chord and UI regression.
## NEVER launches a retail-map worker or claims Havok character traversal.
const Picker = preload("res://collision_source_picker.gd")
const Chord = preload("res://source_edge_capsule_chord.gd")
const EdgePanel = preload("res://source_edge_transition_panel.gd")
const SweepPanel = preload("res://capsule_sweep_panel.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

class FakeHost:
    extends Control
    var source_collision_mode := true
    var current_source_map_name := "Fixture.gmp"
    var source_gamesys_sha256 := "1111111111111111111111111111111111111111111111111111111111111111"
    var last_gmp_path := "C:/Synthetic/Maps/Fixture.gmp"
    var current_folder := "C:/Synthetic/PrivateCache"
    var source_collision_picker
    var interactive_capsule_panel
    var status_label := Label.new()

func _initialize() -> void:
    call_deferred("_run")

func _fail(text: String) -> void:
    push_error("DX2Ed exact source edge capsule crossing: " + text)
    quit(1)

func _doc() -> Dictionary:
    return {
        "schema": Picker.SCHEMA,
        "source_map": "Fixture.gmp",
        "source_sha256": SHA,
        "read_only":true,
        "not_a_native_collision_writer":true,
        "physics_materials_verified":false,
        "coordinate_system":"Godot preview (Level.x/10, Level.z/10, Level.y/10)",
        "edge_provenance_schema":Picker.EDGE_SCHEMA,
        "source_edge_welding":"exact_original_Level_XYZ_no_epsilon",
        "source_flat_vertex_count":6,
        "source_triangle_count":2,
        "mopp_leaf_triangle_count":2,
        "source_topology_summary":{
            "source_exact_welded_vertex_count":4,
            "unique_source_edges":5,
            "open_boundary_edges":4,
            "two_triangle_same_material_edges":0,
            "two_triangle_render_material_seams":1,
            "three_or_more_triangle_edges":0,
            "max_triangles_using_one_edge":2},
        "vertices_godot_xyz":[
            [0.,0.,0.],[2.,0.,0.],[0.,0.,2.],
            [2.,0.,0.],[2.,0.,2.],[0.,0.,2.]],
        "render_material_names":["MatA","MatB"],
        "leaf_triangles":[
            {"triangle_id":0,"vertex_indices":[0,1,2],
             "source_weld_ids":[0,1,2],"source_edge_kinds":[1,2,1],
             "source_block_id":2,"render_block_ordinal":0,
             "render_section_ordinal":0,"render_material_id":0},
            {"triangle_id":1,"vertex_indices":[3,4,5],
             "source_weld_ids":[1,3,2],"source_edge_kinds":[1,1,2],
             "source_block_id":2,"render_block_ordinal":0,
             "render_section_ordinal":1,"render_material_id":1},
        ]}

func _run() -> void:
    var p = Picker.new()
    var doc := _doc()
    if not p.load_document(doc,SHA,"Fixture.gmp"):
        _fail("Authenticated exact-source v3 fixture refused: " + p.last_error)
        return
    var geometry = Chord.new()
    var c: Dictionary = geometry.build(p,0,1)
    if (c.is_empty() or not c["source_exact_welded_connectivity"]
        or c["walkability_or_Havok_runtime_verified"]
        or c["swept_capsule_contact_tested"]
        or c["game_original_assets_written"]):
        _fail("Exact interior-to-interior edge crossing evidence missing")
        return
    if (c["source_original_triangle_id"]!=0
        or c["neighbor_original_triangle_id"]!=1
        or absf(float(c["crossing_path_normalized_t"])-.5)>.00001
        or absf(float(c["crossing_shared_edge_normalized_u"])-.5)>.00001):
        _fail("Shared edge mid-crossing or original Level triangle provenance wrong")
        return
    var start: Vector3 = c["start_godot_xyz"]
    var finish: Vector3 = c["end_godot_xyz"]
    if (start.distance_to(Vector3(.8,.1,.8))>.00001
        or finish.distance_to(Vector3(1.2,.1,1.2))>.00001
        or absf(float(c["vertical_chord_deviation_from_edge_level_units"]))>.00001):
        _fail("Crossing chord is not interior to both flat source triangles")
        return
    for slot in [0,2]:
        if not geometry.build(p,0,slot).is_empty():
            _fail("Original open-boundary edge must not create invented neighbor crossing")
            return
    for invalid in [0.,-.1,.9,float("nan")]:
        if not geometry.build(p,0,1,invalid).is_empty():
            _fail("Invalid interior fraction accepted")
            return
    if not geometry.build(p,0,1,.2,-1.).is_empty():
        _fail("Negative source clearance offset accepted")
        return
    # A genuine hinge must obey the selected bend and slope research limits.
    var hinge := _doc()
    hinge["vertices_godot_xyz"][4]=[2.,1.,2.]
    if not p.load_document(hinge,SHA,"Fixture.gmp"):
        _fail("Synthetic tilted adjacent floor refused: " + p.last_error)
        return
    if not geometry.build(p,0,1,.2,1.,.2,.5,5.,45.).is_empty():
        _fail("Sharp source hinge passed artificially tight geometric angle limit")
        return
    if geometry.build(p,0,1,.2,1.,.2,.5,60.,60.).is_empty():
        _fail("Legitimate hinged source edge did not admit broader research settings")
        return
    # A visual overlap is NOT a valid edge link when source exact weld IDs differ.
    var separate := _doc()
    separate["leaf_triangles"][0]["source_edge_kinds"]=[1,1,1]
    separate["leaf_triangles"][1]["source_edge_kinds"]=[1,1,1]
    separate["leaf_triangles"][1]["source_weld_ids"]=[3,4,5]
    separate["source_topology_summary"]["source_exact_welded_vertex_count"]=6
    separate["source_topology_summary"]["unique_source_edges"]=6
    separate["source_topology_summary"]["open_boundary_edges"]=6
    separate["source_topology_summary"]["two_triangle_render_material_seams"]=0
    separate["source_topology_summary"]["max_triangles_using_one_edge"]=1
    if not p.load_document(separate,SHA,"Fixture.gmp"):
        _fail("Original distinct source weld identities should not be preview-welded")
        return
    if not geometry.build(p,0,1).is_empty():
        _fail("Preview-coincident vertices forged original shared edge crossing")
        return
    if not p.load_document(doc,SHA,"Fixture.gmp"):
        _fail("Could not restore verified fixture: " + p.last_error)
        return
    var host := FakeHost.new()
    root.add_child(host)
    host.source_collision_picker=p
    var sweep := SweepPanel.new()
    host.add_child(sweep)
    host.interactive_capsule_panel=sweep
    sweep.initialize(host)
    sweep.activate()
    if not sweep.prepare_exact_edge_chord(c) or not sweep.picks.can_run():
        _fail("Exact edge path was not accepted by existing source-verified sweep picker")
        return
    if (sweep.picks.start_triangle_id!=0 or sweep.picks.end_triangle_id!=1
        or sweep.picks.picking!=0):
        _fail("Generated source chord must NOT fake a mouse ray-hit interaction")
        return
    var oldhash: String=host.source_gamesys_sha256
    host.source_gamesys_sha256="2222222222222222222222222222222222222222222222222222222222222222"
    if sweep.prepare_exact_edge_chord(c):
        _fail("Stale source SHA accepted for capsule edge crossing")
        return
    host.source_gamesys_sha256=oldhash
    var forged: Dictionary = c.duplicate(true)
    forged["end_godot_xyz"]=Vector3(20.,10.,20.)
    if sweep.prepare_exact_edge_chord(forged):
        _fail("Forged crossing point was not independently reconstructed from original source")
        return
    if not sweep.prepare_exact_edge_chord(c):
        _fail("Restored source chord rejected")
        return
    var edge_panel := EdgePanel.new()
    host.add_child(edge_panel)
    var world := Node3D.new()
    root.add_child(world)
    edge_panel.initialize(host,world)
    edge_panel.activate(p)
    edge_panel.observe_hit({"original_level_triangle_id":0})
    edge_panel._on_select_edge(1)
    if edge_panel.probe_button.disabled:
        _fail("Exact opposite-side coplanar edge probe UI stayed disabled")
        return
    edge_panel._on_select_edge(0)
    if not edge_panel.probe_button.disabled:
        _fail("Open source boundary incorrectly offered capsule crossing probe")
        return
    edge_panel.reset()
    sweep.reset()
    if not sweep.picks.source_sha256.is_empty() or edge_panel.visible:
        _fail("Original source scene reset retained crossing probe identity")
        return
    if load("res://main.gd")==null:
        _fail("DX2Ed main.gd could not parse with crossing probe")
        return
    print("DX2Ed exact source edge capsule crossing probe: PASS")
    quit(0)
