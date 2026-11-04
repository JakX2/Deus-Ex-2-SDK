extends SceneTree
## Source-only Godot 4.3 exact welded edge links and DX2Ed navigation.
## All vertices are synthetic. No original game geometry or Havok runtime.

const SourcePicker = preload("res://collision_source_picker.gd")
const Analyzer = preload("res://source_edge_transition_diagnostics.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed exact source edge links: " + message)
    quit(1)

func _doc() -> Dictionary:
    return {
        "schema": SourcePicker.SCHEMA,
        "source_map":"Fixture.gmp",
        "source_sha256":SHA,
        "read_only":true,
        "not_a_native_collision_writer":true,
        "physics_materials_verified":false,
        "coordinate_system":"Godot preview (Level.x/10, Level.z/10, Level.y/10)",
        "edge_provenance_schema":SourcePicker.EDGE_SCHEMA,
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
            "max_triangles_using_one_edge":2,
        },
        # Raw source indices duplicated, but exact source XYZ weld IDs agree.
        "vertices_godot_xyz":[
            [0.,0.,0.],[2.,0.,0.],[0.,0.,2.],
            [2.,0.,0.],[2.,0.,2.],[0.,0.,2.]],
        "render_material_names":["MatA","MatB"],
        "leaf_triangles":[
            {"triangle_id":0, "vertex_indices":[0,1,2],
             "source_weld_ids":[0,1,2], "source_edge_kinds":[1,2,1],
             "source_block_id":2,"render_block_ordinal":0,
             "render_section_ordinal":0,"render_material_id":0},
            {"triangle_id":1, "vertex_indices":[3,4,5],
             "source_weld_ids":[1,3,2], "source_edge_kinds":[1,1,2],
             "source_block_id":2,"render_block_ordinal":0,
             "render_section_ordinal":1,"render_material_id":1},
        ],
    }

func _run() -> void:
    var picker = SourcePicker.new()
    var doc: Dictionary = _doc()
    if not picker.load_document(doc,SHA,"Fixture.gmp"):
        _fail("Valid original source exact-weld cache rejected: "+picker.last_error)
        return
    var connected: Array[Dictionary] = picker.edge_connected_original_triangles(0)
    if (connected.size()!=3 or connected[0]["original_incident_triangle_count"]!=1
        or connected[1]["source_class_code"]!=2
        or connected[1]["neighbor_original_triangle_ids"]!=[1]
        or connected[1]["neighbor_source_edge_slots"]!=[2]
        or connected[2]["neighbor_original_triangle_ids"]!=[]):
        _fail("Duplicated raw indices lost authentic welded source edge connection")
        return
    var back: Array[Dictionary] = picker.edge_connected_original_triangles(1)
    if back[2]["neighbor_original_triangle_ids"]!=[0]:
        _fail("Source exact-weld edge link not symmetric")
        return
    var analyze = Analyzer.new()
    var geometry: Dictionary = analyze.inspect(picker,0)
    if (geometry.is_empty()
        or not geometry["all_connections_use_source_exact_welds"]
        or geometry["native_Havok_traversal_verified"]):
        _fail("Missing research-only original-source exact edge evidence")
        return
    var mid: Dictionary = geometry["edges"][1]
    if (not mid["one_unique_neighbor"]
        or absf(float(mid["preview_normal_bend_degrees"]))>0.0001
        or mid["horizontal_opposite_side_test"]!="opposite sides"
        or not mid["smooth_floorlike_geometric_proxy"]):
        _fail("Coplanar triangle-edge neighbor not classified as a geometric proxy")
        return
    # A synthetic hinge: shared edge stays exact but opposite face rises.
    var hinge: Dictionary = _doc()
    hinge["vertices_godot_xyz"][4] = [2.,1.,2.]
    if not picker.load_document(hinge,SHA,"Fixture.gmp"):
        _fail("Geometrically hinged source edge refused: "+picker.last_error)
        return
    var bent: Dictionary = analyze.inspect(picker,0,15.,45.)
    if (bent.is_empty() or float(bent["edges"][1]["preview_normal_bend_degrees"])<15.
        or bent["edges"][1]["smooth_floorlike_geometric_proxy"]):
        _fail("Sharp hinged original triangles incorrectly marked smooth")
        return
    # Near-coincident PREVIEW positions cannot manufacture a source-exact link.
    var false_weld: Dictionary = _doc()
    false_weld["source_topology_summary"]["source_exact_welded_vertex_count"]=6
    false_weld["source_topology_summary"]["unique_source_edges"]=6
    false_weld["source_topology_summary"]["open_boundary_edges"]=6
    false_weld["source_topology_summary"]["two_triangle_render_material_seams"]=0
    false_weld["source_topology_summary"]["max_triangles_using_one_edge"]=1
    false_weld["leaf_triangles"][0]["source_edge_kinds"]=[1,1,1]
    false_weld["leaf_triangles"][1]["source_edge_kinds"]=[1,1,1]
    false_weld["leaf_triangles"][1]["source_weld_ids"]=[3,4,5]
    if not picker.load_document(false_weld,SHA,"Fixture.gmp"):
        _fail("Source-exact distinct vertices should not be welded by rounded preview: "
            +picker.last_error)
        return
    if picker.edge_connected_original_triangles(0)[1]["neighbor_original_triangle_ids"]!=[]:
        _fail("Godot-coincident positions manufactured non-original edge link")
        return
    var corrupt: Dictionary = _doc()
    corrupt["leaf_triangles"][1]["source_weld_ids"]=[3,4,5]
    if picker.load_document(corrupt,SHA,"Fixture.gmp"):
        _fail("Contradictory original source edge classifications accepted")
        return
    if picker.ready or not picker.original_edge_incidence.is_empty():
        _fail("Failed cache must clear partial source adjacency state")
        return
    var old: Dictionary = _doc()
    old["schema"]="DX2Ed-source-MOPP-collision-selection-cache-v2"
    if picker.load_document(old,SHA,"Fixture.gmp"):
        _fail("Old v2 cache without authenticated welded edge metadata accepted")
        return
    # Full DX2Ed integration: source picker, new panel, neighbor navigation and
    # reset. The cached JSON is synthetic and lives only under user://.
    var cache := "user://fixture_source_exact_edge_v3.json"
    var f := FileAccess.open(cache,FileAccess.WRITE)
    if f==null:
        _fail("Unable to write synthetic private v3 fixture")
        return
    f.store_string(JSON.stringify(_doc()))
    f.close()
    var editor = load("res://main.gd").new()
    root.add_child(editor)
    editor.current_source_map_name="Fixture.gmp"
    editor.source_gamesys_sha256=SHA
    editor.source_collision_button.disabled=false
    editor._activate_source_collision_cache(ProjectSettings.globalize_path(cache))
    if not editor.source_collision_mode or not editor.source_edge_transition_panel.visible:
        _fail("Source edge transition Inspector panel not enabled on original v3 cache")
        return
    var picked: Dictionary = editor.source_collision_picker.ray_pick(
        Vector3(.4,3.,.3),Vector3.DOWN)
    if picked.is_empty() or picked["original_level_triangle_id"]!=0:
        _fail("Original source fixture triangle cannot be selected")
        return
    picked["selection_is_ray_hit"]=true
    editor._show_source_collision_hit(picked)
    var panel = editor.source_edge_transition_panel
    panel._on_select_edge(1)
    if panel.follow_button.disabled or panel.overlay==null:
        _fail("Original exact edge neighbor should be highlighted and navigable")
        return
    panel.follow_neighbor()
    if (editor.source_collision_last_hit.get("original_level_triangle_id",-1)!=1
        or editor.source_collision_last_hit.get("selection_is_ray_hit",true)):
        _fail("Following an edge must navigate by source centroid, not fake a ray hit")
        return
    editor.source_collision_button.set_pressed_no_signal(false)
    editor._toggle_source_collision_inspection()
    if (panel.visible or not panel.current.is_empty() or panel.overlay!=null
        or not editor.source_edge_transition_panel.source_picker==null):
        _fail("Disabling source inspection left stale exact-edge link overlay")
        return
    editor.queue_free()
    DirAccess.remove_absolute(ProjectSettings.globalize_path(cache))
    print("DX2Ed exact source welded edge transitions: PASS")
    quit(0)
