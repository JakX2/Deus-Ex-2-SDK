extends Control
const BrushGeometry = preload("res://brush_geometry.gd")
## DX2Ed native viewer: a READ-ONLY Godot 4 GLB + GMP actor inspector.
## Can open an original DX2 .gmp using the bundled read-only Python backend.
## No runtime game assets bundled. Exports are cached outside the game folder.

var world_view: SubViewport
var view_container: SubViewportContainer
var world_root: Node3D
var scene_root: Node3D
var camera: Camera3D
var actor_list: ItemList
var search_box: LineEdit
var category_filter: OptionButton
var hierarchy_tree: Tree
var asset_filter: LineEdit
var asset_kind_filter: OptionButton
var asset_list: ItemList
var asset_details: Label
var asset_catalog: Dictionary = {}
var assets_visible: Array = []
var selected_asset: Dictionary = {}
var archetype_catalog: Dictionary = {}
var archetype_visible: Array = []
var archetype_filter: LineEdit
var archetype_list: ItemList
var archetype_details: Label
var selected_archetype: Dictionary = {}
# Optional source-hash-bound original DX2 GameSys research sidecar.
# Kept separate from class templates, draft properties and native Save As.
var source_gamesys_catalog: Dictionary = {}
var source_gamesys_sha256 := ""
var source_gamesys_panel: VBoxContainer
var source_gamesys_filter: LineEdit
var source_gamesys_list: ItemList
var source_gamesys_details: Label
var source_gamesys_visible: Array = []
var source_gamesys_current_export := -1
var source_gamesys_selected_field: Dictionary = {}
var source_gamesys_light_button: Button
var source_gamesys_light_dialog: FileDialog
var source_gamesys_light_confirmation: ConfirmationDialog
var source_gamesys_light_pending: Dictionary = {}
var source_archetype_filter: LineEdit
var source_archetype_list: ItemList
var source_archetype_details: TextEdit
var source_archetype_visible: Array = []
var draft_template_provenance: Dictionary = {} # draft name -> qualified class + template export
var asset_mesh_resources: Dictionary = {}
var asset_thread: Thread = null
var asset_pending_name := ""
var asset_pending_folder := ""
var hierarchy_items: Dictionary = {}
var hierarchy_syncing := false
var inspector_title: Label
var inspector_summary: Label
var inspector_details: Label
var placement_inspector: Label
var inspector_transform_section: VBoxContainer
var inspector_spins: Dictionary = {}
var inspector_syncing := false
var property_editor_panel: VBoxContainer
var property_editor_rows: VBoxContainer
var property_editor_note: Label
var property_filter: LineEdit
var property_overrides: Dictionary = {} # Actor name -> decimal property ID -> scalar
var property_editor_syncing := false
var property_editor_last_key := ""
var rotation_lab_panel: VBoxContainer
var rotation_lab_modes: OptionButton
var rotation_lab_hint: Label
var inspector: TextEdit
var status_label: Label
var glb_dialog: FileDialog
var json_dialog: FileDialog
var gmp_dialog: FileDialog
var gmp_save_as_dialog: FileDialog
var native_clone_dialog: FileDialog
var native_clone_confirmation: ConfirmationDialog
var native_clone_pending: Dictionary = {}
var native_multi_dialog: FileDialog
var native_multi_confirmation: ConfirmationDialog
var native_multi_pending: Dictionary = {}
var gmp_verify_dialog: FileDialog
var native_export_thread: Thread = null
var native_export_target := ""
var native_audit_dialog: AcceptDialog
var bundle_dialog: FileDialog
var club_zip_dialog: FileDialog
var shared_zip_dialog: FileDialog
var system_zip_dialog: FileDialog
var direct_system_dialog: FileDialog
var chosen_direct_system_path := ""
var chosen_ibd: String = ""
var chosen_shared_zip: String = ""
var chosen_system_zip: String = ""
var chosen_system_path: String = ""
var preview_club_stairs := false
var preview_auto_roll := true # GLB visualization hypothesis; never retail GMP
var last_gmp_path: String = ""
# Original source-only TriggerScript/AI browser; native spawn disabled.
var gameplay_zip_dialog: FileDialog
var gameplay_thread: Thread = null
var gameplay_catalog: Dictionary = {}
var gameplay_filter: LineEdit
var gameplay_list: ItemList
var gameplay_details: TextEdit
var gameplay_visible: Array = []
var loaded_actors_json_path: String = ""
var prop_edit_step: SpinBox
var original_mesh_transforms: Dictionary = {}
var draft_prop_copies: Dictionary = {}
var draft_prop_sources: Dictionary = {}
var draft_brush_specs: Dictionary = {} # draft name -> validated dimensions and type
var brush_kind_control: OptionButton
var brush_size_controls: Array[SpinBox] = []
var brush_steps_control: SpinBox
var brush_inspector_panel: VBoxContainer
var brush_inspector_sizes: Array[SpinBox] = []
var brush_inspector_steps: SpinBox
var brush_inspector_syncing := false
var next_prop_copy_id := 1
# In-memory session history. Each operation stores only edited actor transforms
# and draft clones, never the large imported GLB or retail resources.
const HISTORY_LIMIT := 100
var undo_stack: Array[Dictionary] = []
var redo_stack: Array[Dictionary] = []
var gizmo_undo_before: Dictionary = {}
var undo_button: Button
var redo_button: Button
var restore_all_dialog: ConfirmationDialog
var build_thread: Thread = null
var actors: Array = []
var visible_actors: Array = []
var actors_by_name: Dictionary = {}
var meshes_by_actor: Dictionary = {}
var all_mesh_instances: Array[MeshInstance3D] = []
# Read-only preview diagnostics: never mutate source GMP, shared GLB mesh or
# material resources. Stored per-node state is restored on toggle/import.
var geometry_isolation_visibility: Dictionary = {}
var geometry_isolation_target: MeshInstance3D
var geometry_all_faces_target: MeshInstance3D
var geometry_all_faces_previous_override: Material
var geometry_isolation_button: Button
var geometry_all_faces_button: Button
# Faces are shared by instances of the same imported mesh; cache per mesh resource.
var pick_faces_by_mesh: Dictionary = {}
var selected_diagnostic: String = ""
var selected_mesh: MeshInstance3D
# Multi-selection preserves each original material overlay independently.
var selected_meshes: Dictionary = {}   # name -> MeshInstance3D
var selection_original_overlays: Dictionary = {} # name -> Material or null
var gizmo_start_transforms: Dictionary = {} # name -> Transform3D
var selected_actor: Dictionary = {}
var selected_overlay_original: Material
var overlay_material: StandardMaterial3D
var current_folder: String = ""
var current_source_map_name: String = ""
var camera_target := Vector3.ZERO
var orbit_yaw := 0.8
var orbit_pitch := 0.37
var orbit_distance := 25.0
var dragging := false
var drag_mode := ""
var drag_distance := 0.0
var fly_looking := false
var fly_speed := 8.0
var editor_tool := "move"  # W/E/R
var gizmo_root: Node3D
var gizmo_handles: Array[MeshInstance3D] = []
var gizmo_drag_axis := Vector3.ZERO
var gizmo_drag_pivot := Vector3.ZERO
var gizmo_start_transform := Transform3D.IDENTITY
var gizmo_drag_start_scalar := 0.0
var gizmo_drag_start_screen := Vector2.ZERO
var gizmo_drag_active := false
var scene_bounds := AABB()
var scene_bounds_valid := false
var mesh_count := 0

func _exit_tree() -> void:
    # Never destroy a worker Thread handle while Python still owns it.
    # Exported previews and game files remain in the private cache.
    if asset_thread != null:
        asset_thread.wait_to_finish()
        asset_thread = null
    if build_thread != null:
        build_thread.wait_to_finish()
        build_thread = null
    if native_export_thread != null:
        native_export_thread.wait_to_finish()
        native_export_thread = null
    if gameplay_thread != null:
        gameplay_thread.wait_to_finish()
        gameplay_thread = null


func _ready() -> void:
    _make_ui()
    _make_world()
    _make_material()
    _update_camera()
    status_label.text = "Ready. Open an original DX2 .gmp map (Python 3 required) or an existing GLB."
    var args := OS.get_cmdline_user_args()
    if args.size() > 0:
        call_deferred("open_export_folder", str(args[0]))

func _make_ui() -> void:
    var base := VBoxContainer.new()
    base.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    add_child(base)
    # Flow instead of an unbounded horizontal row: the old toolbars forced
    # the entire workspace wider than a 1440px viewport, clipping Inspector.
    var toolbar := HFlowContainer.new()
    toolbar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    base.add_child(toolbar)
    var gmp_btn := Button.new()
    gmp_btn.text = "Open DX2 map (.gmp)"
    gmp_btn.tooltip_text = "Automatically convert the original DX2 map and matching IBD resources to a private cache"
    gmp_btn.pressed.connect(func(): gmp_dialog.popup_centered_ratio(0.78))
    toolbar.add_child(gmp_btn)
    var bundle_btn := Button.new()
    bundle_btn.text = "IBD override..."
    bundle_btn.tooltip_text = "Optional: select a matching .ibd bundle when the automatic lookup cannot find it"
    bundle_btn.pressed.connect(func(): bundle_dialog.popup_centered_ratio(0.72))
    toolbar.add_child(bundle_btn)
    var demo_btn := Button.new()
    demo_btn.text = "Load demo cubes"
    demo_btn.pressed.connect(func(): load_glb(ProjectSettings.globalize_path("res://demo/scene.glb")))
    toolbar.add_child(demo_btn)
    var audit_gmp_btn := Button.new()
    audit_gmp_btn.text = "Audit native GMP"
    audit_gmp_btn.tooltip_text = "Check original map actors for writable Location fields, without changing game files"
    audit_gmp_btn.pressed.connect(_audit_current_native_map)
    toolbar.add_child(audit_gmp_btn)
    var verify_gmp_btn := Button.new()
    verify_gmp_btn.text = "Verify GMP copy..."
    verify_gmp_btn.tooltip_text = "Independently compare a saved GMP against its original and manifest"
    verify_gmp_btn.pressed.connect(_open_native_verify_dialog)
    toolbar.add_child(verify_gmp_btn)
    var save_gmp_btn := Button.new()
    save_gmp_btn.text = "Experimental GMP Save As..."
    save_gmp_btn.tooltip_text = "Translation-only existing static mesh actors; separate folder; not game-tested"
    save_gmp_btn.pressed.connect(_open_native_save_as_dialog)
    toolbar.add_child(save_gmp_btn)
    var direct_system_btn := Button.new()
    direct_system_btn.text = "DX2 System folder..."
    direct_system_btn.tooltip_text = "Optional original System folder for direct .gmp imports. Unlocks source-verified read-only GameSys data, not general editing."
    direct_system_btn.pressed.connect(func(): direct_system_dialog.popup_centered_ratio(0.72))
    toolbar.add_child(direct_system_btn)
    var load_btn := Button.new()
    load_btn.text = "Open exported GLB"
    load_btn.pressed.connect(func(): glb_dialog.popup_centered_ratio(0.72))
    toolbar.add_child(load_btn)
    var data_btn := Button.new()
    data_btn.text = "Load actors.json"
    data_btn.pressed.connect(func(): json_dialog.popup_centered_ratio(0.72))
    toolbar.add_child(data_btn)
    var frame_btn := Button.new()
    frame_btn.text = "Frame scene"
    frame_btn.pressed.connect(frame_whole_scene)
    toolbar.add_child(frame_btn)
    var focus_btn := Button.new()
    focus_btn.text = "Focus actor"
    focus_btn.pressed.connect(focus_selected)
    toolbar.add_child(focus_btn)
    var copy_btn := Button.new()
    copy_btn.text = "Copy mesh info"
    copy_btn.tooltip_text = "Copy selected DX2 actor/mesh name, original rotation and world bounds for reporting an export issue"
    copy_btn.pressed.connect(_copy_selection_details)
    toolbar.add_child(copy_btn)
    var hint := Label.new()
    hint.text = "  Ctrl+click multi-select  |  RMB+WASD fly  |  Alt+LMB orbit  |  F focus"
    toolbar.add_child(hint)

    var zip_bar := HFlowContainer.new()
    zip_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    base.add_child(zip_bar)
    var shared_zip_btn := Button.new()
    shared_zip_btn.text = "Shared ZIP..."
    shared_zip_btn.tooltip_text = "Select maps.zip containing Kernel_GFXALL and MainMenu_GFXALL bundles"
    shared_zip_btn.pressed.connect(func(): shared_zip_dialog.popup_centered_ratio(0.73))
    zip_bar.add_child(shared_zip_btn)
    var system_zip_btn := Button.new()
    system_zip_btn.text = "System ZIP... (optional)"
    system_zip_btn.tooltip_text = "Select System.zip for game-system actor metadata"
    system_zip_btn.pressed.connect(func(): system_zip_dialog.popup_centered_ratio(0.73))
    zip_bar.add_child(system_zip_btn)
    var club_zip_btn := Button.new()
    club_zip_btn.text = "Open DX2 map ZIP..."
    club_zip_btn.tooltip_text = "Safely stage any ZIP with exactly one GMP and one mission IBD (Seattle Hub/Club), then import the map"
    club_zip_btn.pressed.connect(func(): club_zip_dialog.popup_centered_ratio(0.73))
    zip_bar.add_child(club_zip_btn)
    var stairs_toggle := CheckBox.new()
    stairs_toggle.text = "Experimental stair Roll"
    stairs_toggle.tooltip_text = "Compare the unmodified retail transform preview with a reversible Seattle Club-only test. Reloads the level."
    stairs_toggle.button_pressed = false
    stairs_toggle.toggled.connect(_set_stair_preview)
    zip_bar.add_child(stairs_toggle)
    var auto_roll_toggle := CheckBox.new()
    auto_roll_toggle.text = "Auto Roll preview"
    auto_roll_toggle.tooltip_text = "Experimental: invert source roll where it really changes the basis. Applies across maps, not a proven misalignment detector. Reimports to a separate cache. Original GMP untouched."
    auto_roll_toggle.button_pressed = preview_auto_roll
    auto_roll_toggle.toggled.connect(_set_auto_roll_preview)
    zip_bar.add_child(auto_roll_toggle)
    var zip_hint := Label.new()
    zip_hint.text = "  Select shared resources, optional System, then a mission ZIP"
    zip_bar.add_child(zip_hint)

    var prop_bar := HFlowContainer.new()
    prop_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    base.add_child(prop_bar)
    var draft_label := Label.new()
    draft_label.text = "Prop drafts:"
    prop_bar.add_child(draft_label)
    var transform_heading := Label.new()
    transform_heading.text = "  Tools:"
    prop_bar.add_child(transform_heading)
    for definition in [["Move W", "move"], ["Rotate E", "rotate"], ["Scale R", "scale"]]:
        var tool_button := Button.new()
        tool_button.text = definition[0]
        tool_button.tooltip_text = "Choose 3D axis gizmo; keyboard shortcut " + definition[0].right(1)
        tool_button.pressed.connect(_set_editor_tool.bind(definition[1]))
        prop_bar.add_child(tool_button)
    var duplicate_button := Button.new()
    duplicate_button.text = "Duplicate"
    duplicate_button.tooltip_text = "Clone selected rendered prop in the viewer. Does not write the GMP."
    duplicate_button.pressed.connect(_duplicate_selected_prop)
    prop_bar.add_child(duplicate_button)
    var native_clone_button := Button.new()
    native_clone_button.text = "Experimental native Duplicate Save As..."
    native_clone_button.tooltip_text = "Export exactly ONE translated duplicate of an original StaticMeshActor. Isolated GMP only; game folder writes refused."
    native_clone_button.pressed.connect(_open_native_clone_dialog)
    prop_bar.add_child(native_clone_button)
    var native_multi_button := Button.new()
    native_multi_button.text = "Experimental Multi Duplicate Save As..."
    native_multi_button.tooltip_text = "Save 2 to 8 translated preview StaticMeshActor copies in ONE isolated GMP. No game installation writes."
    native_multi_button.pressed.connect(_open_native_multi_dialog)
    prop_bar.add_child(native_multi_button)
    prop_edit_step = SpinBox.new()
    prop_edit_step.min_value = 0.05
    prop_edit_step.max_value = 10.0
    prop_edit_step.step = 0.05
    prop_edit_step.value = 0.25
    prop_edit_step.custom_minimum_size.x = 83
    prop_edit_step.tooltip_text = "Distance for X/Y/Z buttons, in Godot metres"
    prop_bar.add_child(prop_edit_step)
    for entry in [
        ["X-", Vector3(-1, 0, 0)], ["X+", Vector3(1, 0, 0)],
        ["Y-", Vector3(0, -1, 0)], ["Y+", Vector3(0, 1, 0)],
        ["Z-", Vector3(0, 0, -1)], ["Z+", Vector3(0, 0, 1)]
    ]:
        var move_button := Button.new()
        move_button.text = str(entry[0])
        move_button.tooltip_text = "Move selected prop along Godot world axis"
        move_button.pressed.connect(_move_selected_prop.bind(entry[1]))
        prop_bar.add_child(move_button)
    for angle in [-15.0, 15.0]:
        var rotate_button := Button.new()
        rotate_button.text = "Turn " + str(int(angle)) + "°"
        rotate_button.pressed.connect(_rotate_selected_prop.bind(angle))
        prop_bar.add_child(rotate_button)
    var reset_button := Button.new()
    reset_button.text = "Reset / Delete copy"
    reset_button.pressed.connect(_reset_selected_prop)
    prop_bar.add_child(reset_button)
    undo_button = Button.new()
    undo_button.text = "Undo"
    undo_button.tooltip_text = "Undo the last prop edit (Ctrl+Z)"
    undo_button.pressed.connect(_undo_edit)
    prop_bar.add_child(undo_button)
    redo_button = Button.new()
    redo_button.text = "Redo"
    redo_button.tooltip_text = "Redo the last undone edit (Ctrl+Y or Ctrl+Shift+Z)"
    redo_button.pressed.connect(_redo_edit)
    prop_bar.add_child(redo_button)
    var restore_all_button := Button.new()
    restore_all_button.text = "Restore All"
    restore_all_button.tooltip_text = "Restore every original prop transform and delete draft copies. Also clears saved draft edits."
    restore_all_button.pressed.connect(func(): restore_all_dialog.popup_centered())
    prop_bar.add_child(restore_all_button)
    _refresh_history_buttons()
    var save_button := Button.new()
    save_button.text = "Save draft"
    save_button.tooltip_text = "Save only the preview changes as JSON in user://. Never write the game files."
    save_button.pressed.connect(_save_prop_draft)
    prop_bar.add_child(save_button)
    var reload_button := Button.new()
    reload_button.text = "Load draft"
    reload_button.pressed.connect(_load_prop_draft)
    prop_bar.add_child(reload_button)

    var horizontal := HSplitContainer.new()
    horizontal.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    horizontal.size_flags_vertical = Control.SIZE_EXPAND_FILL
    base.add_child(horizontal)
    var sidebar := VBoxContainer.new()
    sidebar.custom_minimum_size = Vector2(250, 0)
    horizontal.add_child(sidebar)
    var actor_heading := Label.new()
    actor_heading.text = "DX2 Actors"
    sidebar.add_child(actor_heading)
    search_box = LineEdit.new()
    search_box.placeholder_text = "Filter name, class, mesh..."
    search_box.text_changed.connect(func(_value): _refresh_actor_list())
    sidebar.add_child(search_box)
    category_filter = OptionButton.new()
    for choice in [
        "All actors", "Static meshes", "Brushes", "Lights",
        "Volumes / triggers", "Item candidates", "Physics candidates",
        "Gameplay / other", "Review mesh placement", "Original AI layer (NPC candidates)"
    ]:
        category_filter.add_item(choice)
    category_filter.selected = 0
    category_filter.item_selected.connect(func(_index): _refresh_actor_list())
    sidebar.add_child(category_filter)
    hierarchy_tree = Tree.new()
    hierarchy_tree.columns = 1
    hierarchy_tree.hide_root = false
    hierarchy_tree.select_mode = Tree.SELECT_MULTI
    hierarchy_tree.size_flags_vertical = Control.SIZE_EXPAND_FILL
    hierarchy_tree.multi_selected.connect(_hierarchy_multi_selected)
    hierarchy_tree.item_activated.connect(func(): focus_selected())
    var left_tabs := TabContainer.new()
    left_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
    sidebar.add_child(left_tabs)
    var hierarchy_tab := VBoxContainer.new()
    hierarchy_tab.name = "Hierarchy"
    left_tabs.add_child(hierarchy_tab)
    hierarchy_tab.add_child(hierarchy_tree)
    var assets_tab := VBoxContainer.new()
    assets_tab.name = "Assets"
    left_tabs.add_child(assets_tab)
    asset_filter = LineEdit.new()
    asset_filter.placeholder_text = "Search IBD resources..."
    asset_filter.text_changed.connect(func(_text): _refresh_asset_list())
    assets_tab.add_child(asset_filter)
    asset_kind_filter = OptionButton.new()
    for kind in ["All resources", "Static meshes", "Textures", "Materials", "Physics hulls", "TriggerScript", "Other"]:
        asset_kind_filter.add_item(kind)
    asset_kind_filter.item_selected.connect(func(_index): _refresh_asset_list())
    assets_tab.add_child(asset_kind_filter)
    asset_list = ItemList.new()
    asset_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    asset_list.item_selected.connect(_asset_selected)
    assets_tab.add_child(asset_list)
    asset_details = Label.new()
    asset_details.text = "Import a DX2 mission to browse its IBD resources."
    asset_details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    assets_tab.add_child(asset_details)
    var place_resource := Button.new()
    place_resource.text = "Place preview mesh"
    place_resource.tooltip_text = "Place a cataloged static mesh as an editable draft; does not create native DX2 actors"
    place_resource.pressed.connect(_place_selected_asset)
    assets_tab.add_child(place_resource)
    var focus_resource := Button.new()
    focus_resource.text = "Find placed instance"
    focus_resource.pressed.connect(_focus_asset_instance)
    assets_tab.add_child(focus_resource)
    var copy_resource := Button.new()
    copy_resource.text = "Copy resource name"
    copy_resource.pressed.connect(_copy_asset_name)
    assets_tab.add_child(copy_resource)

    var class_tab := VBoxContainer.new()
    class_tab.name = "Classes"
    left_tabs.add_child(class_tab)
    archetype_filter = LineEdit.new()
    archetype_filter.placeholder_text = "Search Gamesys and map actor classes..."
    archetype_filter.text_changed.connect(func(_text): _refresh_archetype_list())
    class_tab.add_child(archetype_filter)
    archetype_list = ItemList.new()
    archetype_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    archetype_list.item_selected.connect(_archetype_selected)
    class_tab.add_child(archetype_list)
    archetype_details = Label.new()
    archetype_details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    archetype_details.text = "Open a DX2 map to inspect its observed classes."
    class_tab.add_child(archetype_details)
    var locate_template := Button.new()
    locate_template.text = "Inspect example actor"
    locate_template.pressed.connect(_inspect_archetype_template)
    class_tab.add_child(locate_template)
    var place_template := Button.new()
    place_template.text = "Place template draft"
    place_template.tooltip_text = "Visual copy of an existing actor, not native Gamesys spawning"
    place_template.pressed.connect(_place_archetype_template)
    class_tab.add_child(place_template)
    var gamesys_tab := VBoxContainer.new()
    gamesys_tab.name = "GameSys"
    left_tabs.add_child(gamesys_tab)
    var gamesys_tab_header := Label.new()
    gamesys_tab_header.text = "Original DX2Gamesys archetypes | Read-only"
    gamesys_tab.add_child(gamesys_tab_header)
    source_archetype_filter = LineEdit.new()
    source_archetype_filter.placeholder_text = "Search D_* class, display or parent..."
    source_archetype_filter.text_changed.connect(func(_q): _refresh_source_archetype_list())
    gamesys_tab.add_child(source_archetype_filter)
    source_archetype_list = ItemList.new()
    source_archetype_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    source_archetype_list.item_selected.connect(_source_archetype_selected)
    gamesys_tab.add_child(source_archetype_list)
    source_archetype_details = TextEdit.new()
    source_archetype_details.editable = false
    source_archetype_details.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
    source_archetype_details.custom_minimum_size.y = 210
    source_archetype_details.text = "Import an original map with its System folder to browse the source archetypes. No native actor spawning."
    gamesys_tab.add_child(source_archetype_details)

    # These original .tsd definitions are source evidence, NOT an actor
    # script binding nor an executable gameplay compiler.
    var gameplay_tab := VBoxContainer.new()
    gameplay_tab.name = "Scripts"
    left_tabs.add_child(gameplay_tab)
    var scripts_note := Label.new()
    scripts_note.text = "Original TriggerScripts and AI actors | Read-only"
    gameplay_tab.add_child(scripts_note)
    var open_gameplay_scripts := Button.new()
    open_gameplay_scripts.text = "Open original TriggerScript.zip..."
    open_gameplay_scripts.tooltip_text = "Inspect original Defs/*.tsd. Neither game scripts nor GMPs are changed."
    open_gameplay_scripts.pressed.connect(func(): gameplay_zip_dialog.popup_centered_ratio(0.7))
    gameplay_tab.add_child(open_gameplay_scripts)
    gameplay_filter = LineEdit.new()
    gameplay_filter.placeholder_text = "Search original script ID, title or action..."
    gameplay_filter.text_changed.connect(func(_q): _refresh_gameplay_script_list())
    gameplay_tab.add_child(gameplay_filter)
    gameplay_list = ItemList.new()
    gameplay_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    gameplay_list.item_selected.connect(_gameplay_script_selected)
    gameplay_tab.add_child(gameplay_list)
    var actor_script_button := Button.new()
    actor_script_button.text = "Inspect selected actor script fields"
    actor_script_button.tooltip_text = "Raw serialized indices are NOT verified TS_ script IDs."
    actor_script_button.pressed.connect(_inspect_selected_actor_scripts)
    gameplay_tab.add_child(actor_script_button)
    gameplay_details = TextEdit.new()
    gameplay_details.editable = false
    gameplay_details.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
    gameplay_details.custom_minimum_size.y = 180
    gameplay_details.text = "Open a GMP and its original TriggerScript.zip. No native script binding or NPC spawning yet."
    gameplay_tab.add_child(gameplay_details)

    var brushes_tab := VBoxContainer.new()
    brushes_tab.name = "Brushes"
    left_tabs.add_child(brushes_tab)
    var brushes_heading := Label.new()
    brushes_heading.text = "Primitive brushes (preview only)"
    brushes_tab.add_child(brushes_heading)
    brush_kind_control = OptionButton.new()
    for kind in BrushGeometry.TYPES:
        brush_kind_control.add_item(kind)
    brush_kind_control.item_selected.connect(func(index): _update_brush_form(int(index)))
    brushes_tab.add_child(brush_kind_control)
    var dimensions_title := Label.new()
    dimensions_title.text = "Size X / Y / Z (metres)"
    brushes_tab.add_child(dimensions_title)
    var dimensions_row := HBoxContainer.new()
    brushes_tab.add_child(dimensions_row)
    for axis in range(3):
        var spin := SpinBox.new()
        spin.min_value = 0.05
        spin.max_value = 256.0
        spin.step = 0.05
        spin.custom_minimum_size.x = 70
        dimensions_row.add_child(spin)
        brush_size_controls.append(spin)
    var steps_row := HBoxContainer.new()
    brushes_tab.add_child(steps_row)
    var steps_label := Label.new()
    steps_label.text = "Stair steps"
    steps_row.add_child(steps_label)
    brush_steps_control = SpinBox.new()
    brush_steps_control.min_value = 1.0
    brush_steps_control.max_value = 64.0
    brush_steps_control.step = 1.0
    steps_row.add_child(brush_steps_control)
    _update_brush_form(0)
    var create_brush_btn := Button.new()
    create_brush_btn.text = "Create preview brush"
    create_brush_btn.pressed.connect(_place_preview_brush)
    brushes_tab.add_child(create_brush_btn)
    var brush_note := Label.new()
    brush_note.text = "Editor geometry only. No Unreal CSG, native BSP, lightmaps or collision generated."
    brush_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    brushes_tab.add_child(brush_note)
    # Retain the old list as a hidden compatibility model for existing picker
    # diagnostics; the new Hierarchy is the visible selection surface.
    actor_list = ItemList.new()
    actor_list.visible = false
    actor_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    actor_list.select_mode = ItemList.SELECT_MULTI
    actor_list.multi_selected.connect(_actor_list_multi_selected)
    actor_list.item_activated.connect(func(_index): focus_selected())
    sidebar.add_child(actor_list)

    # Godot SplitContainer supports exactly two content children.
    # The prior three-child version dropped the Inspector offscreen.
    var content_split := HSplitContainer.new()
    content_split.split_offset = -315
    content_split.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    content_split.size_flags_vertical = Control.SIZE_EXPAND_FILL
    horizontal.add_child(content_split)
    var scene_pane := VBoxContainer.new()
    scene_pane.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    scene_pane.custom_minimum_size.x = 360
    content_split.add_child(scene_pane)
    var scene_label := Label.new()
    scene_label.text = "Scene  |  Godot preview, read-only source assets"
    scene_pane.add_child(scene_label)
    view_container = SubViewportContainer.new()
    view_container.stretch = true
    view_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
    view_container.custom_minimum_size = Vector2(400, 360)
    scene_pane.add_child(view_container)

    # The Inspector content can be taller than the window, especially when
    # editing actor properties. Scroll vertically instead of cutting off the
    # material details and the original read-only property dump.
    var inspector_scroll := ScrollContainer.new()
    inspector_scroll.custom_minimum_size.x = 315
    inspector_scroll.size_flags_horizontal = Control.SIZE_FILL
    inspector_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
    inspector_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
    content_split.add_child(inspector_scroll)
    var inspector_pane := VBoxContainer.new()
    inspector_pane.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    inspector_scroll.add_child(inspector_pane)
    var heading := Label.new()
    heading.text = "Inspector"
    inspector_pane.add_child(heading)
    inspector_title = Label.new()
    inspector_title.text = "Nothing selected"
    inspector_pane.add_child(inspector_title)
    inspector_summary = Label.new()
    inspector_summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    inspector_summary.text = "Geometry: none selected\nMaterial: select a mesh"
    inspector_pane.add_child(inspector_summary)
    inspector_details = Label.new()
    inspector_details.text = "Select an actor or rendered mesh in the Scene or Hierarchy."
    inspector_details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    inspector_pane.add_child(inspector_details)
    placement_inspector = Label.new()
    placement_inspector.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    placement_inspector.visible = false
    inspector_pane.add_child(placement_inspector)
    var copy_placement := Button.new()
    copy_placement.text = "Copy placement evidence"
    copy_placement.tooltip_text = "Copy GMP vs IBD vs mesh vertex bounds and original pivot information"
    copy_placement.pressed.connect(_copy_placement_evidence)
    inspector_pane.add_child(copy_placement)
    var geometry_debug_row := HFlowContainer.new()
    inspector_pane.add_child(geometry_debug_row)
    geometry_isolation_button = Button.new()
    geometry_isolation_button.text = "Isolate selected"
    geometry_isolation_button.tooltip_text = "Reversible inspection: hide other rendered meshes including glass, without changing their materials or game files."
    geometry_isolation_button.pressed.connect(_toggle_geometry_isolation)
    geometry_debug_row.add_child(geometry_isolation_button)
    geometry_all_faces_button = Button.new()
    geometry_all_faces_button.text = "Inspect both faces"
    geometry_all_faces_button.tooltip_text = "Reversible: render only the selected mesh unshaded with backface culling OFF. Never changes source or shared GLB materials."
    geometry_all_faces_button.pressed.connect(_toggle_geometry_all_faces)
    geometry_debug_row.add_child(geometry_all_faces_button)
    inspector_transform_section = VBoxContainer.new()
    inspector_pane.add_child(inspector_transform_section)
    var inspector_transform_heading := Label.new()
    inspector_transform_heading.text = "Transform  |  Preview only"
    inspector_transform_section.add_child(inspector_transform_heading)
    var transform_grid := GridContainer.new()
    transform_grid.columns = 4
    inspector_transform_section.add_child(transform_grid)
    for mode in ["Position", "Rotation", "Scale"]:
        var label := Label.new()
        label.text = mode
        transform_grid.add_child(label)
        for axis in range(3):
            var spin := SpinBox.new()
            spin.min_value = -1000000.0
            spin.max_value = 1000000.0
            spin.step = 0.01 if mode != "Rotation" else 1.0
            spin.custom_minimum_size.x = 67
            spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
            spin.tooltip_text = mode + " " + ["X", "Y", "Z"][axis] + " (Godot coordinates)"
            spin.value_changed.connect(_inspector_transform_changed.bind(mode, axis))
            transform_grid.add_child(spin)
            inspector_spins[mode + str(axis)] = spin
    rotation_lab_panel = VBoxContainer.new()
    inspector_pane.add_child(rotation_lab_panel)
    var rotation_lab_heading := Label.new()
    rotation_lab_heading.text = "Rotation Lab  |  Source evidence"
    rotation_lab_panel.add_child(rotation_lab_heading)
    rotation_lab_modes = OptionButton.new()
    for hypothesis in [
        "Original export", "Yaw -90 degrees", "Yaw +90 degrees",
        "Yaw 180 degrees", "Invert Pitch sign", "Invert Roll sign"
    ]:
        rotation_lab_modes.add_item(hypothesis)
    rotation_lab_panel.add_child(rotation_lab_modes)
    var rotation_lab_row := HBoxContainer.new()
    rotation_lab_panel.add_child(rotation_lab_row)
    var apply_candidate := Button.new()
    apply_candidate.text = "Preview orientation"
    apply_candidate.tooltip_text = "Apply selected hypothesis as undoable GLB preview, not native map edit"
    apply_candidate.pressed.connect(_preview_rotation_hypothesis)
    rotation_lab_row.add_child(apply_candidate)
    var copy_rotation := Button.new()
    copy_rotation.text = "Copy evidence"
    copy_rotation.tooltip_text = "Copy actor source rotator and candidate spatial relationships"
    copy_rotation.pressed.connect(_copy_rotation_research)
    rotation_lab_row.add_child(copy_rotation)
    rotation_lab_hint = Label.new()
    rotation_lab_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    rotation_lab_panel.add_child(rotation_lab_hint)
    rotation_lab_panel.visible = false
    rotation_lab_modes.item_selected.connect(func(_index): _update_rotation_lab_hint())
    property_editor_panel = VBoxContainer.new()
    inspector_pane.add_child(property_editor_panel)
    var property_heading_edit := Label.new()
    property_heading_edit.text = "Actor properties  |  Draft edits only"
    property_editor_panel.add_child(property_heading_edit)
    var property_toolbar := HBoxContainer.new()
    property_editor_panel.add_child(property_toolbar)
    property_filter = LineEdit.new()
    property_filter.placeholder_text = "Filter property ID, name or type..."
    property_filter.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    property_filter.text_changed.connect(func(_query):
        property_editor_last_key = ""
        _refresh_actor_property_editor())
    property_toolbar.add_child(property_filter)
    var reset_actor_properties := Button.new()
    reset_actor_properties.text = "Reset values"
    reset_actor_properties.tooltip_text = "Discard this actor's draft scalar overrides, with Ctrl+Z support"
    reset_actor_properties.pressed.connect(_reset_actor_property_edits)
    property_toolbar.add_child(reset_actor_properties)
    property_editor_note = Label.new()
    property_editor_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    property_editor_panel.add_child(property_editor_note)
    var property_scroll := ScrollContainer.new()
    property_scroll.custom_minimum_size.y = 140
    property_editor_panel.add_child(property_scroll)
    property_editor_rows = VBoxContainer.new()
    property_editor_rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    property_scroll.add_child(property_editor_rows)
    property_editor_panel.visible = false

    source_gamesys_panel = VBoxContainer.new()
    source_gamesys_panel.visible = false
    inspector_pane.add_child(source_gamesys_panel)
    var source_gamesys_heading := Label.new()
    source_gamesys_heading.text = "Original GameSys | Verified read-only data"
    source_gamesys_panel.add_child(source_gamesys_heading)
    source_gamesys_filter = LineEdit.new()
    source_gamesys_filter.placeholder_text = "Filter original property ID, name or type..."
    source_gamesys_filter.text_changed.connect(func(_q): _refresh_source_gamesys_inspector())
    source_gamesys_panel.add_child(source_gamesys_filter)
    source_gamesys_list = ItemList.new()
    source_gamesys_list.custom_minimum_size.y = 150
    source_gamesys_list.item_selected.connect(_source_gamesys_selected)
    source_gamesys_panel.add_child(source_gamesys_list)
    source_gamesys_details = Label.new()
    source_gamesys_details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    source_gamesys_panel.add_child(source_gamesys_details)
    # Deliberately separate from normal GMP Save As and draft-property editing.
    source_gamesys_light_button = Button.new()
    source_gamesys_light_button.text = "Experimental light Boolean Save As..."
    source_gamesys_light_button.tooltip_text = "Isolated copy of ONE verified original bLightOn byte; never writes into retail Maps."
    source_gamesys_light_button.visible = false
    source_gamesys_light_button.pressed.connect(_open_source_light_bool_dialog)
    source_gamesys_panel.add_child(source_gamesys_light_button)

    brush_inspector_panel = VBoxContainer.new()
    brush_inspector_panel.visible = false
    inspector_pane.add_child(brush_inspector_panel)
    var brush_inspector_heading := Label.new()
    brush_inspector_heading.text = "Brush parameters (preview only)"
    brush_inspector_panel.add_child(brush_inspector_heading)
    var brush_dims_row := HBoxContainer.new()
    brush_inspector_panel.add_child(brush_dims_row)
    for axis in range(3):
        var editor := SpinBox.new()
        editor.min_value = 0.05
        editor.max_value = 256.0
        editor.step = 0.05
        editor.custom_minimum_size.x = 70
        editor.value_changed.connect(_change_brush_dimension.bind(axis))
        brush_dims_row.add_child(editor)
        brush_inspector_sizes.append(editor)
    brush_inspector_steps = SpinBox.new()
    brush_inspector_steps.min_value = 1
    brush_inspector_steps.max_value = 64
    brush_inspector_steps.step = 1
    brush_inspector_steps.value_changed.connect(_change_brush_steps)
    brush_inspector_panel.add_child(brush_inspector_steps)
    var property_heading := Label.new()
    property_heading.text = "Source actor details (read-only)"
    inspector_pane.add_child(property_heading)
    inspector = TextEdit.new()
    inspector.editable = false
    inspector.custom_minimum_size.y = 210
    inspector.size_flags_vertical = Control.SIZE_FILL
    inspector.text = "Select an actor to inspect original DX2 properties."
    inspector_pane.add_child(inspector)
    inspector_transform_section.visible = false
    restore_all_dialog = ConfirmationDialog.new()
    restore_all_dialog.title = "Restore all prop edits?"
    restore_all_dialog.dialog_text = "Restore all original prop transforms and remove every draft copy?\nThis also clears the saved draft for this map.\nYou can undo during this session."
    restore_all_dialog.confirmed.connect(_restore_all_edits)
    add_child(restore_all_dialog)
    var bottom := PanelContainer.new()
    base.add_child(bottom)
    status_label = Label.new()
    status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    bottom.add_child(status_label)

    gmp_dialog = FileDialog.new()
    gmp_dialog.access = FileDialog.ACCESS_FILESYSTEM
    gmp_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    gmp_dialog.filters = PackedStringArray(["*.gmp ; Deus Ex Invisible War map"])
    gmp_dialog.file_selected.connect(_open_gmp_file)
    add_child(gmp_dialog)
    direct_system_dialog = FileDialog.new()
    direct_system_dialog.access = FileDialog.ACCESS_FILESYSTEM
    direct_system_dialog.file_mode = FileDialog.FILE_MODE_OPEN_DIR
    direct_system_dialog.dir_selected.connect(_select_direct_system_folder)
    add_child(direct_system_dialog)
    gmp_save_as_dialog = FileDialog.new()
    gmp_save_as_dialog.access = FileDialog.ACCESS_FILESYSTEM
    gmp_save_as_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    gmp_save_as_dialog.filters = PackedStringArray(["*.gmp ; Experimental location-only DX2 GMP"])
    gmp_save_as_dialog.file_selected.connect(_export_native_gmp_copy)
    add_child(gmp_save_as_dialog)
    native_clone_dialog = FileDialog.new()
    native_clone_dialog.access = FileDialog.ACCESS_FILESYSTEM
    native_clone_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    native_clone_dialog.filters = PackedStringArray(["*.gmp ; Experimental ONE native StaticMeshActor clone GMP"])
    native_clone_dialog.file_selected.connect(_stage_native_clone_export)
    add_child(native_clone_dialog)
    native_clone_confirmation = ConfirmationDialog.new()
    native_clone_confirmation.title = "Confirm isolated DX2 StaticMeshActor duplication"
    native_clone_confirmation.confirmed.connect(_execute_native_clone_export)
    add_child(native_clone_confirmation)
    native_multi_dialog = FileDialog.new()
    native_multi_dialog.access = FileDialog.ACCESS_FILESYSTEM
    native_multi_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    native_multi_dialog.filters = PackedStringArray(["*.gmp ; Experimental 2..8 native StaticMeshActor clones"])
    native_multi_dialog.file_selected.connect(_stage_native_multi_export)
    add_child(native_multi_dialog)
    native_multi_confirmation = ConfirmationDialog.new()
    native_multi_confirmation.title = "Confirm 2..8 experimental static prop clones"
    native_multi_confirmation.confirmed.connect(_execute_native_multi_export)
    add_child(native_multi_confirmation)
    source_gamesys_light_dialog = FileDialog.new()
    source_gamesys_light_dialog.access = FileDialog.ACCESS_FILESYSTEM
    source_gamesys_light_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    source_gamesys_light_dialog.filters = PackedStringArray(["*.gmp ; Experimental single-light DX2 GMP"])
    source_gamesys_light_dialog.file_selected.connect(_stage_source_light_bool_export)
    add_child(source_gamesys_light_dialog)
    source_gamesys_light_confirmation = ConfirmationDialog.new()
    source_gamesys_light_confirmation.title = "Confirm isolated light Boolean test"
    source_gamesys_light_confirmation.confirmed.connect(_execute_source_light_bool_export)
    add_child(source_gamesys_light_confirmation)
    gmp_verify_dialog = FileDialog.new()
    gmp_verify_dialog.access = FileDialog.ACCESS_FILESYSTEM
    gmp_verify_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    gmp_verify_dialog.filters = PackedStringArray(["*.gmp ; Experimental DX2 GMP copy"])
    gmp_verify_dialog.file_selected.connect(_verify_native_gmp_file)
    add_child(gmp_verify_dialog)
    native_audit_dialog = AcceptDialog.new()
    native_audit_dialog.title = "DX2Ed native Location audit (read-only)"
    native_audit_dialog.dialog_text = "Import a retail GMP before running the source audit."
    add_child(native_audit_dialog)
    bundle_dialog = FileDialog.new()
    bundle_dialog.access = FileDialog.ACCESS_FILESYSTEM
    bundle_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    bundle_dialog.filters = PackedStringArray(["*.ibd ; Invisible War resource bundle"])
    bundle_dialog.file_selected.connect(_select_ibd)
    add_child(bundle_dialog)
    glb_dialog = FileDialog.new()
    glb_dialog.access = FileDialog.ACCESS_FILESYSTEM
    glb_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    glb_dialog.filters = PackedStringArray(["*.glb ; DX2Ed glTF binary scene"])
    glb_dialog.file_selected.connect(load_glb)
    add_child(glb_dialog)
    json_dialog = FileDialog.new()
    json_dialog.access = FileDialog.ACCESS_FILESYSTEM
    json_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    json_dialog.filters = PackedStringArray(["*.json ; DX2Ed actor metadata"])
    json_dialog.file_selected.connect(load_actors)
    add_child(json_dialog)
    gameplay_zip_dialog = FileDialog.new()
    gameplay_zip_dialog.access = FileDialog.ACCESS_FILESYSTEM
    gameplay_zip_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    gameplay_zip_dialog.filters = PackedStringArray(["*.zip ; Original TriggerScript definitions ZIP"])
    gameplay_zip_dialog.file_selected.connect(_open_original_gameplay_scripts)
    add_child(gameplay_zip_dialog)

    shared_zip_dialog = FileDialog.new()
    shared_zip_dialog.access = FileDialog.ACCESS_FILESYSTEM
    shared_zip_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    shared_zip_dialog.filters = PackedStringArray(["*.zip ; DX2 shared map resources ZIP"])
    shared_zip_dialog.file_selected.connect(_select_shared_zip)
    add_child(shared_zip_dialog)
    system_zip_dialog = FileDialog.new()
    system_zip_dialog.access = FileDialog.ACCESS_FILESYSTEM
    system_zip_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    system_zip_dialog.filters = PackedStringArray(["*.zip ; DX2 System ZIP"])
    system_zip_dialog.file_selected.connect(_select_system_zip)
    add_child(system_zip_dialog)
    club_zip_dialog = FileDialog.new()
    club_zip_dialog.access = FileDialog.ACCESS_FILESYSTEM
    club_zip_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    club_zip_dialog.filters = PackedStringArray(["*.zip ; DX2 Seattle Club ZIP"])
    club_zip_dialog.file_selected.connect(_open_club_zip)
    add_child(club_zip_dialog)

func _select_ibd(path: String) -> void:
    chosen_ibd = path
    status_label.text = "Optional IBD selected: " + path.get_file()

func _dx2_system_folder_valid(folder: String) -> bool:
    if folder.is_empty():
        return false
    return (FileAccess.file_exists(folder.path_join("Engine.d2u"))
        and FileAccess.file_exists(folder.path_join("DX2Gamesys.d2u")))


func _direct_map_system_folder(map_path: String) -> String:
    # Standard retail layout: <install>/Content/DX2/Maps/<map>.gmp,
    # with <install>/System/Engine.d2u and DX2Gamesys.d2u.
    var maps_dir := map_path.get_base_dir()
    if (maps_dir.get_file().to_lower() == "maps"
        and maps_dir.get_base_dir().get_file().to_lower() == "dx2"
        and maps_dir.get_base_dir().get_base_dir().get_file().to_lower() == "content"):
        var install_root := maps_dir.get_base_dir().get_base_dir().get_base_dir()
        var auto_system := install_root.path_join("System")
        if _dx2_system_folder_valid(auto_system):
            return auto_system
    if _dx2_system_folder_valid(chosen_direct_system_path):
        return chosen_direct_system_path
    return ""


func _select_direct_system_folder(path: String) -> void:
    if not _dx2_system_folder_valid(path):
        status_label.text = "System folder refused: Engine.d2u and DX2Gamesys.d2u are both required."
        return
    chosen_direct_system_path = path
    status_label.text = "Original DX2 System selected. Reopen the GMP to refresh GameSys audit: " + path


func _open_gmp_file(path: String) -> void:
    # Do not reuse ZIP-staged System data across unrelated direct map imports.
    # Prefer the exact installed System sibling; otherwise a deliberately chosen folder.
    chosen_system_path = _direct_map_system_folder(path)
    open_gmp(path)

func _set_auto_roll_preview(enabled: bool) -> void:
    if preview_auto_roll == enabled:
        return
    preview_auto_roll = enabled
    if build_thread != null:
        status_label.text = "Auto Roll preference changed. Reopen the map after import completes."
    elif last_gmp_path != "" and FileAccess.file_exists(last_gmp_path):
        # Each mode has an isolated cache; saved drafts in either cache
        # remain available on switching back.
        open_gmp(last_gmp_path)
    else:
        status_label.text = "Auto Roll preview " + ("ON" if enabled else "OFF") + ". Original GMP is unchanged."


func _set_stair_preview(enabled: bool) -> void:
    preview_club_stairs = enabled
    if build_thread != null:
        status_label.text = "Stair preview changed. Reopen the map after the current import completes."
    elif last_gmp_path != "" and FileAccess.file_exists(last_gmp_path):
        open_gmp(last_gmp_path)
    else:
        status_label.text = "Stair Roll preview: " + ("experimental" if enabled else "original") + ". Open a DX2 map."

func _select_shared_zip(path: String) -> void:
    chosen_shared_zip = path
    status_label.text = "Shared map resources selected: " + path.get_file()

func _select_system_zip(path: String) -> void:
    chosen_system_zip = path
    status_label.text = "Optional System ZIP selected: " + path.get_file()

func _open_club_zip(path: String) -> void:
    if build_thread != null:
        status_label.text = "Already processing a map or archive."
        return
    if chosen_shared_zip.is_empty() or not FileAccess.file_exists(chosen_shared_zip):
        status_label.text = "Choose Shared ZIP (maps.zip) before opening the Club ZIP."
        return
    if not FileAccess.file_exists(path):
        status_label.text = "Club ZIP not found: " + path
        return
    var backend := ProjectSettings.globalize_path("res://backend/dx2_zip_stage.py")
    if not FileAccess.file_exists(backend):
        status_label.text = "ZIP staging script is missing: " + backend
        return
    var cache_root := OS.get_user_data_dir().path_join("zip_staging")
    build_thread = Thread.new()
    status_label.text = "Preparing DX2 mission archives in a private cache..."
    var result := build_thread.start(_run_zip_stage.bind(backend, path, chosen_shared_zip, chosen_system_zip, cache_root))
    if result != OK:
        build_thread = null
        status_label.text = "Could not start ZIP worker: " + error_string(result)

func _run_zip_stage(script: String, club: String, shared: String, system_zip: String, cache_root: String) -> void:
    var args := PackedStringArray([script, "--club", club, "--maps", shared, "--map-name", "auto", "--mission-name", "auto", "--output-root", cache_root])
    if system_zip != "":
        args.append_array(PackedStringArray(["--system", system_zip]))
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        var py_args := PackedStringArray(["-3"])
        py_args.append_array(args)
        output.clear()
        code = OS.execute("py", py_args, output, true)
    call_deferred("_zip_stage_finished", code, "\n".join(output))

func _zip_stage_finished(code: int, output: String) -> void:
    if build_thread != null:
        build_thread.wait_to_finish()
        build_thread = null
    var parsed: Variant = null
    for line in output.strip_edges().split("\n"):
        var candidate: Variant = JSON.parse_string(line.strip_edges())
        if typeof(candidate) == TYPE_DICTIONARY and candidate.has("status"):
            parsed = candidate
    if code != 0 or typeof(parsed) != TYPE_DICTIONARY or parsed.get("status") != "ok":
        var description := "ZIP staging failed. Verify source ZIP files and Python installation."
        if typeof(parsed) == TYPE_DICTIONARY:
            description = str(parsed.get("message", description))
        status_label.text = description
        return
    var map_path := str(parsed.get("map", ""))
    if not FileAccess.file_exists(map_path):
        status_label.text = "ZIP staging completed but the map is missing: " + map_path
        return
    chosen_ibd = ""
    var system_value: Variant = parsed.get("system", null)
    chosen_system_path = str(system_value) if typeof(system_value) == TYPE_STRING else ""
    # The existing GMP importer now sees the original Club IBD and the shared
    # IBD packages side by side. Source ZIPs remain untouched.
    open_gmp(map_path)

func open_gmp(path: String) -> void:
    if build_thread != null:
        status_label.text = "Already processing a map. Please finish this load first."
        return
    if not FileAccess.file_exists(path):
        status_label.text = "Map not found: " + path
        return
    var backend := ProjectSettings.globalize_path("res://backend/dx2_native_backend.py")
    if not FileAccess.file_exists(backend):
        status_label.text = "Missing Python backend: " + backend
        return
    last_gmp_path = path
    var cache_root := OS.get_user_data_dir().path_join("map_cache")
    status_label.text = "Processing " + path.get_file() + " ... First load creates a cached 3D scene and actor metadata."
    build_thread = Thread.new()
    var result := build_thread.start(_run_backend.bind(backend, path, cache_root, chosen_ibd, chosen_system_path, preview_club_stairs, preview_auto_roll))
    if result != OK:
        build_thread = null
        status_label.text = "Could not start map worker: " + error_string(result)

func _run_backend(script: String, gmp_path: String, cache_root: String, ibd_path: String, system_path: String, stair_preview: bool, auto_roll: bool) -> void:
    var args := PackedStringArray([script, "--map", gmp_path, "--output-root", cache_root])
    if ibd_path != "":
        args.append_array(PackedStringArray(["--bundle", ibd_path]))
    if system_path != "":
        args.append_array(PackedStringArray(["--system", system_path]))
    if stair_preview:
        args.append("--preview-club-stairs")
    if auto_roll:
        args.append("--preview-auto-roll")
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        # On Windows the Python launcher may be on PATH even if python.exe isn't.
        var py_args := PackedStringArray(["-3"])
        py_args.append_array(args)
        output.clear()
        code = OS.execute("py", py_args, output, true)
    call_deferred("_backend_finished", code, "\n".join(output))

func _backend_finished(code: int, output: String) -> void:
    if build_thread != null:
        build_thread.wait_to_finish()
        build_thread = null
    var message := ""
    var parsed: Variant = null
    for line in output.strip_edges().split("\n"):
        var record := line.strip_edges()
        if record.begins_with("{"):
            var candidate: Variant = JSON.parse_string(record)
            if typeof(candidate) == TYPE_DICTIONARY and candidate.has("status"):
                parsed = candidate
    if typeof(parsed) == TYPE_DICTIONARY and parsed.get("status") == "ok" and code == 0:
        var scene_path := str(parsed.get("glb", ""))
        var actor_path := str(parsed.get("actors_json", ""))
        if not FileAccess.file_exists(scene_path) or not FileAccess.file_exists(actor_path):
            status_label.text = "Map backend succeeded but output files are missing."
            return
        load_glb(scene_path)
        if scene_root == null:
            return # Keep the descriptive GLB error instead of reporting success.
        # load_glb automatically loads the adjacent actors.json.
        var roll_info := ""
        if bool(parsed.get("auto_roll", false)):
            roll_info = " | Auto Roll preview: " + str(int(parsed.get("auto_roll_count", 0))) + " rotated actors (unverified)"
        status_label.text = "%s: %d actors, %d meshes (%s)%s. Read-only." % [str(parsed.get("map", "DX2 map")), int(parsed.get("actors", 0)), mesh_count, "cached" if parsed.get("cached", false) else "new export", roll_info]
        return
    if typeof(parsed) == TYPE_DICTIONARY and parsed.has("message"):
        message = str(parsed.get("message", ""))
    elif output.strip_edges() != "":
        message = output.strip_edges().substr(0, 400)
    else:
        message = "Python not available. Install Python 3 and ensure python or py is on PATH."
    status_label.text = "Could not open DX2 map: " + message
    push_warning("DX2Ed map importer: " + message)

func _make_world() -> void:
    world_view = SubViewport.new()
    world_view.transparent_bg = false
    world_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    view_container.add_child(world_view)
    world_root = Node3D.new()
    world_root.name = "Scene"
    world_view.add_child(world_root)
    camera = Camera3D.new()
    camera.current = true
    camera.near = 0.05
    camera.far = 100000.0
    world_root.add_child(camera)
    gizmo_root = Node3D.new()
    gizmo_root.name = "EditorGizmo"
    world_root.add_child(gizmo_root)
    _create_transform_gizmo()
    var light := DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-45, 25, 0)
    light.light_energy = 1.6
    world_root.add_child(light)
    var env := WorldEnvironment.new()
    var world_environment := Environment.new()
    world_environment.background_mode = Environment.BG_COLOR
    world_environment.background_color = Color(0.12, 0.16, 0.2)
    world_environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    world_environment.ambient_light_color = Color(0.75, 0.8, 0.9)
    world_environment.ambient_light_energy = 1.1
    env.environment = world_environment
    world_root.add_child(env)

func _make_material() -> void:
    overlay_material = StandardMaterial3D.new()
    overlay_material.albedo_color = Color(1.0, 0.55, 0.05, 0.28)
    overlay_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    overlay_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    overlay_material.cull_mode = BaseMaterial3D.CULL_DISABLED

func open_export_folder(folder: String) -> void:
    var path := folder.simplify_path().path_join("scene.glb")
    if not FileAccess.file_exists(path):
        status_label.text = "No scene.glb in: " + folder
        return
    load_glb(path)

func load_glb(path: String) -> void:
    if not FileAccess.file_exists(path):
        status_label.text = "File not found: " + path
        return
    _clear_current_scene()
    var document := GLTFDocument.new()
    var gltf_state := GLTFState.new()
    var error := document.append_from_file(path, gltf_state)
    if error != OK:
        status_label.text = "GLB import failed: " + error_string(error) + " | " + path
        return
    var imported := document.generate_scene(gltf_state)
    if imported == null:
        status_label.text = "GLB parsed but scene generation failed: " + path
        return
    scene_root = imported
    world_root.add_child(scene_root)
    _index_meshes(scene_root)
    frame_whole_scene()
    current_folder = path.get_base_dir()
    _load_asset_catalog(current_folder.path_join("assets.json"))
    _load_archetype_catalog(current_folder.path_join("archetypes.json"))
    var actor_path := current_folder.path_join("actors.json")
    if FileAccess.file_exists(actor_path):
        load_actors(actor_path)
    _load_prop_draft(true)
    _refresh_hierarchy()
    _refresh_inspector_panel()
    if not FileAccess.file_exists(actor_path):
        status_label.text = "3D loaded (%d meshes). Open its actors.json to inspect entities." % mesh_count
    print("DX2Ed native: GLB loaded with ", mesh_count, " mesh instances")

func load_actors(path: String) -> void:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        status_label.text = "Cannot open actor metadata: " + path
        return
    var result: Variant = JSON.parse_string(file.get_as_text())
    if typeof(result) != TYPE_DICTIONARY or not result.has("actors") or typeof(result["actors"]) != TYPE_ARRAY:
        status_label.text = "Invalid actor JSON: " + path
        return
    actors = result["actors"]
    loaded_actors_json_path = path
    var metadata: Variant = result.get("meta", {})
    current_source_map_name = str(metadata.get("source_map", "")) if typeof(metadata) == TYPE_DICTIONARY else ""
    source_gamesys_sha256 = str(metadata.get("source_sha256", metadata.get("map_sha256", ""))) if typeof(metadata) == TYPE_DICTIONARY else ""
    actors_by_name.clear()
    for actor in actors:
        if typeof(actor) == TYPE_DICTIONARY and actor.has("name"):
            actors_by_name[str(actor["name"])] = actor
    _refresh_actor_list()
    _load_source_gamesys_catalog(path.get_base_dir().path_join("gamesys_inspector.json"))
    status_label.text = "Loaded %d actors, %d meshes. Click a mesh or select an actor." % [actors.size(), mesh_count]

func _clear_current_scene() -> void:
    _restore_geometry_all_faces()
    _restore_geometry_isolation()
    _clear_selection()
    asset_catalog.clear()
    selected_asset.clear()
    archetype_catalog.clear()
    selected_archetype.clear()
    source_gamesys_catalog.clear()
    source_gamesys_sha256 = ""
    source_gamesys_visible.clear()
    source_gamesys_current_export = -1
    source_gamesys_selected_field.clear()
    source_gamesys_light_pending.clear()
    if source_gamesys_light_button != null:
        source_gamesys_light_button.visible = false
    source_archetype_visible.clear()
    if source_gamesys_panel != null:
        source_gamesys_panel.visible = false
    _refresh_source_archetype_list()
    draft_template_provenance.clear()
    _refresh_archetype_list()
    asset_mesh_resources.clear()
    asset_pending_name = ""
    asset_pending_folder = ""
    _refresh_asset_list()
    actors.clear()
    actors_by_name.clear()
    loaded_actors_json_path = ""
    gameplay_catalog.clear()
    gameplay_visible.clear()
    if gameplay_list != null:
        gameplay_list.clear()
    if gameplay_details != null:
        gameplay_details.text = "Open a source-matched original GMP and TriggerScript.zip."
    meshes_by_actor.clear()
    current_source_map_name = ""
    original_mesh_transforms.clear()
    property_overrides.clear()
    property_editor_last_key = ""
    draft_prop_copies.clear()
    draft_prop_sources.clear()
    draft_brush_specs.clear()
    native_clone_pending.clear()
    native_multi_pending.clear()
    next_prop_copy_id = 1
    undo_stack.clear()
    redo_stack.clear()
    gizmo_undo_before.clear()
    gizmo_drag_active = false
    _refresh_history_buttons()
    all_mesh_instances.clear()
    pick_faces_by_mesh.clear()
    visible_actors.clear()
    actor_list.clear()
    if hierarchy_tree != null:
        hierarchy_tree.clear()
        hierarchy_items.clear()
    scene_bounds_valid = false
    mesh_count = 0
    if scene_root != null:
        scene_root.queue_free()
        scene_root = null

func _index_meshes(node: Node) -> void:
    if node is MeshInstance3D:
        var mesh_node := node as MeshInstance3D
        mesh_count += 1
        all_mesh_instances.append(mesh_node)
        if mesh_node.mesh != null:
            var box := _mesh_world_aabb(mesh_node)
            if not scene_bounds_valid:
                scene_bounds = box
                scene_bounds_valid = true
            else:
                scene_bounds = scene_bounds.merge(box)
            var actor_name := str(mesh_node.name)
            if not original_mesh_transforms.has(actor_name):
                original_mesh_transforms[actor_name] = mesh_node.global_transform
            if not meshes_by_actor.has(actor_name):
                meshes_by_actor[actor_name] = mesh_node
    for child in node.get_children():
        _index_meshes(child)

func _mesh_world_aabb(instance: MeshInstance3D) -> AABB:
    var local := instance.get_aabb()
    var first := instance.global_transform * local.get_endpoint(0)
    var result := AABB(first, Vector3.ZERO)
    for i in range(1, 8):
        result = result.expand(instance.global_transform * local.get_endpoint(i))
    return result

## Gameplay metadata is source-bound and strictly read-only.
func _actor_on_original_ai_layer(actor: Dictionary) -> bool:
    var props: Variant = actor.get("game_properties", [])
    if typeof(props) != TYPE_ARRAY:
        return false
    for prop in props:
        if (typeof(prop) == TYPE_DICTIONARY
            and int(prop.get("id", -1)) == 82
            and prop.get("value", "") == "AI"):
            return true
    return false


func _open_original_gameplay_scripts(zip_path: String) -> void:
    if (gameplay_thread != null or build_thread != null
        or last_gmp_path.is_empty() or loaded_actors_json_path.is_empty()
        or not FileAccess.file_exists(last_gmp_path)
        or not FileAccess.file_exists(loaded_actors_json_path)
        or FileAccess.get_sha256(last_gmp_path) != source_gamesys_sha256):
        status_label.text = "Script browser refused: import an unchanged original GMP first."
        return
    var script := ProjectSettings.globalize_path("res://backend/dx2_gameplay_catalog.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Original gameplay catalog backend missing."
        return
    var target := OS.get_user_data_dir().path_join("original_gameplay_catalog.json")
    gameplay_thread = Thread.new()
    var err := gameplay_thread.start(_run_original_gameplay_scripts.bind(
        script, last_gmp_path, loaded_actors_json_path, zip_path, target))
    if err != OK:
        gameplay_thread = null
        status_label.text = "Could not start original TriggerScript browser."
        return
    status_label.text = "Reading original compiled TriggerScripts and AI actor metadata..."


func _run_original_gameplay_scripts(script: String, map_file: String,
        actors_file: String, archive: String, target: String) -> void:
    var args := PackedStringArray([
        script, "--map", map_file, "--actors", actors_file,
        "--scripts", archive, "--output", target
    ])
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        var pyargs := PackedStringArray(["-3"])
        pyargs.append_array(args)
        output.clear()
        code = OS.execute("py", pyargs, output, true)
    call_deferred("_original_gameplay_scripts_finished", code, "\n".join(output))


func _original_gameplay_scripts_finished(code: int, response: String) -> void:
    if gameplay_thread != null:
        gameplay_thread.wait_to_finish()
        gameplay_thread = null
    var answer: Variant = JSON.parse_string(response.strip_edges())
    if (code != 0 or typeof(answer) != TYPE_DICTIONARY
        or answer.get("status") != "ok"
        or answer.get("schema") != "DX2Ed-original-gameplay-catalog-v1"):
        status_label.text = "Original gameplay browse refused: " + response.strip_edges().substr(0, 400)
        return
    var file := str(answer.get("output", ""))
    if not FileAccess.file_exists(file):
        status_label.text = "Gameplay browser did not save its private report."
        return
    var doc: Variant = JSON.parse_string(FileAccess.get_file_as_string(file))
    if (typeof(doc) != TYPE_DICTIONARY
        or doc.get("schema") != "DX2Ed-original-gameplay-catalog-v1"
        or doc.get("read_only") != true
        or doc.get("bindings_verified") != false
        or doc.get("spawn_enabled") != false
        or doc.get("map_sha256") != source_gamesys_sha256
        or typeof(doc.get("script_definitions")) != TYPE_ARRAY):
        status_label.text = "Original gameplay catalog identity failed validation."
        return
    gameplay_catalog = doc
    _refresh_gameplay_script_list()
    var counts: Dictionary = doc.get("counts", {})
    status_label.text = (
        "Read-only gameplay: " + str(counts.get("scripts", 0))
        + " original scripts, " + str(counts.get("ai_candidates", 0))
        + " AI-layer candidates, " + str(counts.get("raw_script_fields", 0))
        + " raw script fields. No gameplay writes enabled."
    )


func _refresh_gameplay_script_list() -> void:
    if gameplay_list == null:
        return
    gameplay_list.clear()
    gameplay_visible.clear()
    var query := gameplay_filter.text.strip_edges().to_lower()
    for script in gameplay_catalog.get("script_definitions", []):
        if typeof(script) != TYPE_DICTIONARY:
            continue
        var searchable := str(script.get("id", "")) + " " + str(script.get("title", ""))
        for action in script.get("actions", []):
            searchable += " " + str(action)
        for condition in script.get("conditions", []):
            searchable += " " + str(condition)
        if not query.is_empty() and query not in searchable.to_lower():
            continue
        gameplay_visible.append(script)
        gameplay_list.add_item(str(script.get("id", "?")) + " | " + str(script.get("title", "")))
    if not gameplay_visible.is_empty():
        gameplay_list.select(0)
        _gameplay_script_selected(0)


func _gameplay_script_selected(index: int) -> void:
    if index < 0 or index >= gameplay_visible.size() or gameplay_details == null:
        return
    var script: Dictionary = gameplay_visible[index]
    var lines: PackedStringArray = [
        "ORIGINAL COMPILED TRIGGERSCRIPT | READ ONLY",
        "ID: " + str(script.get("id", "")),
        "Description: " + str(script.get("title", "")),
        "Source: " + str(script.get("archive_member", "")),
        "Format: " + str(script.get("format", "")), "",
        "Conditions (original symbols):"
    ]
    for condition in script.get("conditions", []):
        lines.append("  " + str(condition))
    lines.append("Actions (original symbols):")
    for action in script.get("actions", []):
        lines.append("  " + str(action))
    lines.append("")
    lines.append("Not bound to a specific map actor. No executable edits.")
    gameplay_details.text = "\n".join(lines)


func _inspect_selected_actor_scripts() -> void:
    if gameplay_details == null:
        return
    var actor: Dictionary = selected_actor
    if is_instance_valid(selected_mesh) and actors_by_name.has(str(selected_mesh.name)):
        actor = actors_by_name[str(selected_mesh.name)]
    if actor.is_empty():
        gameplay_details.text = "First select an original actor in the Hierarchy."
        return
    var raw: Variant = actor.get("trigger_script_serialized", null)
    gameplay_details.text = (
        "Original actor: " + str(actor.get("name", "?"))
        + "\nClass: " + str(actor.get("class", "?"))
        + "\nExport: " + str(actor.get("export", "?"))
        + "\nOriginal AI layer: " + str(_actor_on_original_ai_layer(actor))
        + "\nSerialized TriggerScript data: " + JSON.stringify(raw, "  ")
        + "\n\nRaw integer indices are NOT verified TS_ IDs."
        + "\nNo NPC spawning or script assignment is enabled."
    )


func _actor_category(actor: Dictionary) -> String:
    # This is class-name *discovery*, NOT proof of rigid-body physics,
    # inventory behavior, or final in-game script inheritance.
    var raw := str(actor.get("class", ""))
    var kind := raw.to_lower()
    if kind == "staticmeshactor": return "Static mesh"
    if kind == "brush": return "Brush"
    if kind == "light" or kind.ends_with("light"): return "Light"
    if "volume" in kind or "trigger" in kind: return "Volume / trigger"
    if "pickup" in kind or "inventory" in kind or "item" in kind: return "Item candidate"
    if "physicsprop" in kind or "rigidbody" in kind or "kactor" in kind or "pushable" in kind:
        return "Physics candidate"
    return "Gameplay / other"


func _category_visible(category: String, actor: Dictionary = {}) -> bool:
    if category_filter == null or category_filter.selected <= 0:
        return true
    if category_filter.selected == 8:
        var evidence: Variant = actor.get("placement_diagnostic", {})
        return typeof(evidence) == TYPE_DICTIONARY and bool(evidence.get("needs_review", false))
    if category_filter.selected == 9:
        return _actor_on_original_ai_layer(actor)
    var values := [
        "All actors", "Static mesh", "Brush", "Light",
        "Volume / trigger", "Item candidate", "Physics candidate", "Gameplay / other"
    ]
    return category == values[category_filter.selected]


func _refresh_actor_list() -> void:
    actor_list.clear()
    visible_actors.clear()
    var query := search_box.text.strip_edges().to_lower()
    for actor in actors:
        if typeof(actor) != TYPE_DICTIONARY:
            continue
        var name := str(actor.get("name", ""))
        var kind := str(actor.get("class", ""))
        var group := _actor_category(actor)
        if not _category_visible(group, actor):
            continue
        var meshname := ""
        var mesh_metadata: Variant = actor.get("mesh")
        if typeof(mesh_metadata) == TYPE_DICTIONARY:
            meshname = str(mesh_metadata.get("name", ""))
        elif typeof(mesh_metadata) == TYPE_STRING:
            meshname = str(mesh_metadata)
        if query != "" and query not in (name + " " + kind + " " + meshname + " " + group).to_lower():
            continue
        visible_actors.append(actor)
        actor_list.add_item(name + "  [" + kind + " | " + group + "]")
    _sync_actor_list_selection()
    _refresh_hierarchy()
    if visible_actors.is_empty() and not actors.is_empty():
        status_label.text = "No actors match search."

func _load_archetype_catalog(path: String) -> void:
    archetype_catalog.clear()
    selected_archetype.clear()
    if FileAccess.file_exists(path):
        var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
        if typeof(parsed) == TYPE_DICTIONARY and parsed.get("schema") == "DX2Ed-archetype-catalog-v1":
            var classes: Variant = parsed.get("classes", [])
            if typeof(classes) == TYPE_ARRAY and classes.size() < 30000:
                archetype_catalog = parsed
    _refresh_archetype_list()


## The source GameSys Inspector never feeds actor draft/native-save controls.
## A map-specific sidecar is accepted only with the actors.json source SHA.
func _load_source_gamesys_catalog(path: String) -> void:
    source_gamesys_catalog.clear()
    if FileAccess.file_exists(path) and not source_gamesys_sha256.is_empty():
        var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
        if (typeof(parsed) == TYPE_DICTIONARY
            and parsed.get("schema") == "DX2Ed-gamesys-inspector-sidecar-v1"
            and parsed.get("read_only") == true
            and parsed.get("native_game_editing_enabled") == false
            and str(parsed.get("source_sha256", "")) == source_gamesys_sha256
            and str(parsed.get("source_map", "")).to_lower() == current_source_map_name.to_lower()
            and typeof(parsed.get("actors", null)) == TYPE_DICTIONARY
            and typeof(parsed.get("archetypes", null)) == TYPE_ARRAY):
            var classes: Array = parsed["archetypes"]
            if classes.size() <= 12000:
                source_gamesys_catalog = parsed
    source_gamesys_current_export = -1
    source_gamesys_selected_field.clear()
    source_gamesys_light_pending.clear()
    if source_gamesys_light_button != null:
        source_gamesys_light_button.visible = false
    _refresh_source_archetype_list()
    _refresh_source_gamesys_inspector()


func _refresh_source_archetype_list() -> void:
    if source_archetype_list == null:
        return
    source_archetype_list.clear()
    source_archetype_visible.clear()
    var query := source_archetype_filter.text.strip_edges().to_lower() if source_archetype_filter != null else ""
    var classes: Variant = source_gamesys_catalog.get("archetypes", [])
    if typeof(classes) != TYPE_ARRAY:
        return
    for rec in classes:
        if typeof(rec) != TYPE_DICTIONARY:
            continue
        var searchable := str(rec.get("class", "")) + " " + str(rec.get("display_name", "")) + " " + str(rec.get("parent", ""))
        if query != "" and query not in searchable.to_lower():
            continue
        source_archetype_visible.append(rec)
        source_archetype_list.add_item(str(rec.get("display_name", "?")) + "  [" + str(rec.get("class", "?")) + "]")
    if source_archetype_details != null:
        if classes.is_empty():
            source_archetype_details.text = "No original DX2Gamesys archetype source for this cache. Import with its original System folder or ZIP. Existing Classes and visual templates remain available."
        else:
            source_archetype_details.text = "%d original classes (%d filtered). Select one to inspect read-only source defaults. Archetype-to-map-actor bindings and native spawning are unverified." % [classes.size(), source_archetype_visible.size()]


func _source_archetype_selected(index: int) -> void:
    if index < 0 or index >= source_archetype_visible.size() or source_archetype_details == null:
        return
    var rec: Dictionary = source_archetype_visible[index]
    var chain: Variant = rec.get("source_ancestry", [])
    var lines := [
        "Original archetype: " + str(rec.get("display_name", "?")),
        "Class: " + str(rec.get("class", "?")),
        "Immediate parent: " + str(rec.get("parent", "?")),
        "Source ancestry: " + (" -> ".join(PackedStringArray(chain)) if typeof(chain) == TYPE_ARRAY else "unavailable"),
        "Inheritance verified: " + str(rec.get("inheritance_complete", false)),
        "DX2 grouped-array decoder: " + str(rec.get("recovered_dx2_layout", false)),
        "Local defaults: " + str(rec.get("local_property_count", 0)),
        "Native actor construction: NOT SUPPORTED", ""
    ]
    var defaults: Variant = rec.get("local_defaults", [])
    if typeof(defaults) == TYPE_ARRAY:
        for item in defaults:
            if typeof(item) != TYPE_DICTIONARY:
                continue
            lines.append("#" + str(item.get("property_id", "?")) + " " + str(item.get("source_declared_name", "(source name unknown)")) +
                " (" + str(item.get("source_declared_type", item.get("encoding", "?"))) + ")" +
                " | " + str(item.get("element_count", 1)) + " element(s)")
            var elements: Variant = item.get("elements", [])
            if typeof(elements) == TYPE_ARRAY:
                for element in elements:
                    if typeof(element) != TYPE_DICTIONARY:
                        continue
                    var detail := ""
                    if element.has("typed_fields"):
                        var pairs := []
                        for field in element.get("typed_fields", []):
                            if typeof(field) == TYPE_DICTIONARY:
                                pairs.append(str(field.get("name", "?")) + "=" + str(field.get("value", "?")))
                        detail = ", ".join(pairs)
                    elif element.has("string_value"):
                        detail = str(element["string_value"])
                    lines.append("  [" + str(element.get("element_index", "?")) + "] " + detail.substr(0, 300))
    source_archetype_details.text = "\n".join(lines).substr(0, 30000)


func _refresh_source_gamesys_inspector() -> void:
    if source_gamesys_panel == null or source_gamesys_list == null:
        return
    source_gamesys_panel.visible = false
    source_gamesys_list.clear()
    source_gamesys_visible.clear()
    source_gamesys_current_export = -1
    source_gamesys_selected_field.clear()
    source_gamesys_light_pending.clear()
    if source_gamesys_light_button != null:
        source_gamesys_light_button.visible = false
    if source_gamesys_catalog.is_empty():
        return
    var nodes := _selection_nodes()
    var actor: Dictionary = {}
    if nodes.size() == 1 and actors_by_name.has(str(nodes[0].name)):
        actor = actors_by_name[str(nodes[0].name)]
    elif nodes.is_empty() and not selected_actor.is_empty():
        actor = selected_actor
    if actor.is_empty():
        return
    var export_id := int(actor.get("export", -1))
    var source_actor: Variant = source_gamesys_catalog.get("actors", {}).get(str(export_id), {})
    if (typeof(source_actor) != TYPE_DICTIONARY
        or str(source_actor.get("name", "")) != str(actor.get("name", ""))
        or int(source_actor.get("export", -2)) != export_id):
        return
    source_gamesys_panel.visible = true
    source_gamesys_current_export = export_id
    var query := source_gamesys_filter.text.strip_edges().to_lower() if source_gamesys_filter != null else ""
    var fields: Variant = source_actor.get("properties", [])
    if typeof(fields) != TYPE_ARRAY:
        return
    for rec in fields:
        if typeof(rec) != TYPE_DICTIONARY:
            continue
        var label := "#" + str(rec.get("id", "?")) + " " + str(rec.get("name", "Unknown"))
        var searchable := label + " " + str(rec.get("declared_type", "")) + " " + str(rec.get("encoding", ""))
        if query != "" and query not in searchable.to_lower():
            continue
        source_gamesys_visible.append(rec)
        source_gamesys_list.add_item(label + " [" + str(rec.get("encoding", "?")) + "]")
    source_gamesys_details.text = "%d verified original blocks (%d matching). Select a field to inspect the source value and byte evidence. No native GameSys editing." % [fields.size(), source_gamesys_visible.size()]


func _source_gamesys_selected(index: int) -> void:
    if index < 0 or index >= source_gamesys_visible.size() or source_gamesys_details == null:
        return
    var rec: Dictionary = source_gamesys_visible[index]
    source_gamesys_selected_field = rec.duplicate(true)
    source_gamesys_light_pending.clear()
    var light_context := _selected_source_light_bool_context()
    if source_gamesys_light_button != null:
        source_gamesys_light_button.visible = not light_context.is_empty()
        if not light_context.is_empty():
            source_gamesys_light_button.text = "Experimental Save As: light " + ("OFF" if bool(light_context["expected"]) else "ON")
    var original_value := JSON.stringify(rec.get("source_value"))
    source_gamesys_details.text = (
        "Original #" + str(rec.get("id", "?")) + "  " + str(rec.get("name", "?")) +
        "\nDeclared type: " + str(rec.get("declared_type", "(unavailable)")) +
        "\nDeclared in: " + str(rec.get("declared_in", "(unavailable)")) +
        "\nSerialized encoding: " + str(rec.get("encoding", "?")) +
        "\nSource value: " + original_value.substr(0, 640) +
        "\nOriginal ID: " + str(rec.get("encoded_id", "?")) +
        "\nPayload offset: 0x" + ("%x" % int(rec.get("payload_offset", 0))) +
        "\nPayload bytes: " + str(rec.get("payload_bytes", "?")) +
        "\nSHA-256: " + str(rec.get("source_payload_sha256", "?")) +
        "\nRead-only source evidence. No native write or script bindings."
    )


## Experimental: one SOURCE-VERIFIED existing authored bLightOn per separate GMP.
## Never mutates draft-property values, original GameSys catalog or normal Save As.
func _selected_source_light_bool_context() -> Dictionary:
    if (source_gamesys_selected_field.is_empty()
        or source_gamesys_current_export < 1
        or source_gamesys_catalog.get("read_only") != true
        or source_gamesys_catalog.get("native_game_editing_enabled") != false
        or str(source_gamesys_catalog.get("source_sha256", "")) != source_gamesys_sha256
        or str(source_gamesys_catalog.get("source_map", "")).to_lower() != current_source_map_name.to_lower()):
        return {}
    var rec := source_gamesys_selected_field
    var encoded_id := int(rec.get("encoded_id", -1))
    if (int(rec.get("id", -1)) != 1487 or str(rec.get("name", "")) != "bLightOn"
        or str(rec.get("declared_type", "")).to_lower() != "bool"
        or str(rec.get("encoding", "")) != "bool"
        or int(rec.get("payload_bytes", -1)) != 1
        or (encoded_id & 65535) != 1487
        or ((encoded_id >> 16) & 65535) != 128
        or typeof(rec.get("source_value")) != TYPE_BOOL):
        return {}
    var source_actor: Variant = source_gamesys_catalog.get("actors", {}).get(str(source_gamesys_current_export), {})
    if typeof(source_actor) != TYPE_DICTIONARY:
        return {}
    var original_rows: Variant = source_actor.get("properties", [])
    if (typeof(original_rows) != TYPE_ARRAY or not original_rows.has(rec)
        or not source_gamesys_visible.has(rec)):
        return {}
    var actor_name := str(source_actor.get("name", ""))
    if (actor_name.is_empty()
        or int(source_actor.get("export", -1)) != source_gamesys_current_export
        or not actors_by_name.has(actor_name)
        or int(actors_by_name[actor_name].get("export", -2)) != source_gamesys_current_export):
        return {}
    var selected_name := ""
    var nodes := _selection_nodes()
    if nodes.size() == 1:
        selected_name = str(nodes[0].name)
    elif nodes.is_empty() and not selected_actor.is_empty():
        selected_name = str(selected_actor.get("name", ""))
    if selected_name != actor_name:
        return {}
    return {
        "export": source_gamesys_current_export,
        "actor": actor_name,
        "property_id": 1487,
        "expected": bool(rec["source_value"]),
        "source_sha256": source_gamesys_sha256,
        "source_map": current_source_map_name
    }


func _open_source_light_bool_dialog() -> void:
    var context := _selected_source_light_bool_context()
    if context.is_empty():
        status_label.text = "Light test refused: select a verified original authored bLightOn Boolean."
        return
    if (native_export_thread != null or build_thread != null
        or last_gmp_path.is_empty() or not FileAccess.file_exists(last_gmp_path)
        or last_gmp_path.get_file().to_lower() != current_source_map_name.to_lower()):
        status_label.text = "Light test refused: original GMP unavailable or a native operation is active."
        return
    var script := ProjectSettings.globalize_path("res://../package_writer/dx2_gamesys_bool_probe.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Experimental one-byte GameSys probe unavailable. Use a full DX2SDK repository checkout."
        return
    source_gamesys_light_dialog.current_file = last_gmp_path.get_file()
    source_gamesys_light_dialog.popup_centered_ratio(0.72)


func _stage_source_light_bool_export(destination: String) -> void:
    var context := _selected_source_light_bool_context()
    if context.is_empty() or destination.get_file().to_lower() != current_source_map_name.to_lower():
        status_label.text = "Light test refused: actor selection changed or target GMP filename differs."
        return
    source_gamesys_light_pending = context.duplicate(true)
    source_gamesys_light_pending["destination"] = destination
    source_gamesys_light_confirmation.dialog_text = (
        "EXPERIMENTAL, ONE ORIGINAL LIGHT ONLY\n\n"
        + "Actor: " + str(context["actor"]) + " | export #" + str(context["export"])
        + "\nbLightOn: " + str(context["expected"]) + " -> " + str(not bool(context["expected"]))
        + "\nOutput: " + destination
        + "\n\nThe strict serializer refuses source changes, existing output files,"
        + " runtime fields and any edits outside the original byte."
        + "\nUse only an isolated test installation. The game runtime is not automatically verified."
    )
    source_gamesys_light_confirmation.popup_centered(Vector2i(680, 310))


func _execute_source_light_bool_export() -> void:
    var context := _selected_source_light_bool_context()
    if (context.is_empty() or native_export_thread != null or build_thread != null
        or last_gmp_path.is_empty() or not FileAccess.file_exists(last_gmp_path)
        or last_gmp_path.get_file().to_lower() != current_source_map_name.to_lower()):
        status_label.text = "Light test refused: source, selection or worker changed."
        source_gamesys_light_pending.clear()
        return
    var destination := str(source_gamesys_light_pending.get("destination", ""))
    var frozen := source_gamesys_light_pending.duplicate(true)
    frozen.erase("destination")
    source_gamesys_light_pending.clear()
    if frozen != context or destination.get_file().to_lower() != current_source_map_name.to_lower():
        status_label.text = "Light test refused: verified actor field changed before confirmation."
        return
    var script := ProjectSettings.globalize_path("res://../package_writer/dx2_gamesys_bool_probe.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Light test refused: experimental one-byte Boolean probe not installed."
        return
    native_export_thread = Thread.new()
    var started := native_export_thread.start(_run_source_light_bool_export.bind(
        script, last_gmp_path, context, destination
    ))
    if started != OK:
        native_export_thread = null
        status_label.text = "Could not start experimental single-light worker."
        return
    status_label.text = "Building isolated single-light GMP; checking byte-exact T3SDK parity..."


func _run_source_light_bool_export(script: String, source: String, context: Dictionary, destination: String) -> void:
    var original := "true" if bool(context["expected"]) else "false"
    var replacement := "false" if bool(context["expected"]) else "true"
    var args := PackedStringArray([
        script, source,
        "--source-sha256", str(context["source_sha256"]),
        "--actor-export", str(context["export"]),
        "--actor-name", str(context["actor"]),
        "--property-id", str(context["property_id"]),
        "--expect", original, "--replace", replacement, "--output", destination
    ])
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        var launcher := PackedStringArray(["-3"])
        launcher.append_array(args)
        output.clear()
        code = OS.execute("py", launcher, output, true)
    call_deferred("_source_light_bool_finished", code, "\n".join(output))


func _source_light_bool_finished(code: int, output: String) -> void:
    if native_export_thread != null:
        native_export_thread.wait_to_finish()
        native_export_thread = null
    var result: Variant = JSON.parse_string(output.strip_edges())
    if (code == 0 and typeof(result) == TYPE_DICTIONARY
        and result.get("status") == "isolated-boolean-gmp-written-runtime-unverified"
        and result.get("independent_full_package_byte_match") == true
        and int(result.get("changed_bytes", -1)) == 1):
        status_label.text = (
            "Single-light GMP saved (one verified byte only): " + str(result.get("output", ""))
            + " | Runtime test and original restoration still required."
        )
        return
    var reason := str(result.get("reason", "Check source map, SHA, actor and isolated destination.")) if typeof(result) == TYPE_DICTIONARY else output.strip_edges().substr(0, 300)
    status_label.text = "Experimental light Boolean Save As refused: " + reason


func _refresh_archetype_list() -> void:
    if archetype_list == null:
        return
    archetype_list.clear()
    archetype_visible.clear()
    var query := archetype_filter.text.strip_edges().to_lower() if archetype_filter != null else ""
    var classes: Variant = archetype_catalog.get("classes", [])
    if typeof(classes) != TYPE_ARRAY:
        return
    for archetype in classes:
        if typeof(archetype) != TYPE_DICTIONARY:
            continue
        var search := str(archetype.get("qualified", "")) + " " + str(archetype.get("base", "")) + " " + str(archetype.get("template_mesh", ""))
        if query != "" and query not in search.to_lower():
            continue
        archetype_visible.append(archetype)
        archetype_list.add_item(str(archetype.get("class", "?")) + " [" + str(archetype.get("observed_actors", 0)) + "]")
    if archetype_details != null and selected_archetype.is_empty():
        archetype_details.text = str(archetype_visible.size()) + " class records. Declared classes aren't necessarily safe to instantiate."


func _archetype_selected(index: int) -> void:
    if index < 0 or index >= archetype_visible.size():
        return
    selected_archetype = archetype_visible[index]
    var rec := selected_archetype
    archetype_details.text = (
        "Class: " + str(rec.get("qualified", "?")) +
        "\nParent: " + str(rec.get("base", "unknown")) +
        "\nSource: " + str(rec.get("source", "unknown")) +
        "\nObserved actors: " + str(rec.get("observed_actors", 0)) +
        "\nExample: " + str(rec.get("template_actor", "(none)")) +
        "\nMesh: " + str(rec.get("template_mesh", "(none)")) +
        "\nProperties observed: " + str(rec.get("property_signatures", []).size()) +
        "\nPlacement requires a rendered example actor. No real DX2 actor is created."
    )


func _valid_template_provenance(prov: Dictionary, source_name: String) -> bool:
    if prov.is_empty():
        return true  # Older drafts and ordinary asset copies have no class.
    if not actors_by_name.has(source_name):
        return false
    if str(prov.get("source_actor", "")) != source_name:
        return false
    var original: Dictionary = actors_by_name[source_name]
    if int(prov.get("source_export", -1)) != int(original.get("export", -2)):
        return false
    var qualified := str(prov.get("qualified", ""))
    for rec in archetype_catalog.get("classes", []):
        if typeof(rec) != TYPE_DICTIONARY:
            continue
        if (str(rec.get("qualified", "")) == qualified
            and str(rec.get("template_actor", "")) == source_name
            and int(rec.get("template_export", -1)) == int(original.get("export", -2))):
            return true
    return false


func _inspect_archetype_template() -> void:
    var name := str(selected_archetype.get("template_actor", ""))
    if not actors_by_name.has(name):
        status_label.text = "No observed example for this class in the loaded map."
        return
    select_actor(actors_by_name[name])
    focus_selected()


func _place_archetype_template() -> void:
    var source := str(selected_archetype.get("template_actor", ""))
    var qualified := str(selected_archetype.get("qualified", ""))
    var template_export: Variant = selected_archetype.get("template_export", null)
    if typeof(template_export) not in [TYPE_INT, TYPE_FLOAT]:
        status_label.text = "Class has no verified original export index; visual placement unavailable."
        return
    var expected_export := int(template_export)
    if scene_root == null or not meshes_by_actor.has(source) or not actors_by_name.has(source):
        status_label.text = "Class lacks a rendered example; cannot create a safe visual draft."
        return
    if int(actors_by_name[source].get("export", -2)) != expected_export:
        status_label.text = "Template actor source does not match Gamesys/map catalog."
        return
    var before := _capture_edit_state()
    var copy_name := "DraftProp_" + str(next_prop_copy_id)
    next_prop_copy_id += 1
    var original: MeshInstance3D = meshes_by_actor[source]
    var pose := original.global_transform
    pose.origin = camera_target
    var draft := _new_draft_copy(source, copy_name, pose)
    if not is_instance_valid(draft):
        return
    draft_template_provenance[copy_name] = {
        "qualified": qualified, "source_actor": source, "source_export": expected_export
    }
    _clear_selection()
    _add_selection_mesh(draft)
    _refresh_selection_inspector()
    _record_edit("Place class template " + qualified, before)
    status_label.text = "Placed visual template for " + qualified + ". No native class spawned."


func _load_asset_catalog(path: String) -> void:
    asset_catalog.clear()
    selected_asset.clear()
    if not FileAccess.file_exists(path):
        _refresh_asset_list()
        return
    var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
    if typeof(parsed) != TYPE_DICTIONARY or parsed.get("schema") != "DX2Ed-asset-catalog-v1":
        _refresh_asset_list()
        status_label.text = "Unrecognized IBD asset catalog: " + path
        return
    var resources: Variant = parsed.get("assets", [])
    if typeof(resources) != TYPE_ARRAY or resources.size() > 100000:
        status_label.text = "Asset catalog has invalid resource entries."
        return
    asset_catalog = parsed
    _refresh_asset_list()


func _asset_kind_matches(kind: String) -> bool:
    if asset_kind_filter == null:
        return true
    match asset_kind_filter.selected:
        0: return true
        1: return kind == "staticmesh"
        2: return kind == "texture"
        3: return kind == "matlib"
        4: return kind == "physicshull"
        5: return kind == "triggerscriptdef"
        _: return kind not in ["staticmesh", "texture", "matlib", "physicshull", "triggerscriptdef"]


func _refresh_asset_list() -> void:
    if asset_list == null:
        return
    asset_list.clear()
    assets_visible.clear()
    var query := asset_filter.text.strip_edges().to_lower() if asset_filter != null else ""
    var resources: Variant = asset_catalog.get("assets", [])
    if typeof(resources) != TYPE_ARRAY:
        return
    for resource in resources:
        if typeof(resource) != TYPE_DICTIONARY:
            continue
        var name := str(resource.get("name", ""))
        var kind := str(resource.get("kind", "unknown"))
        var bundle := str(resource.get("bundle", ""))
        if not _asset_kind_matches(kind):
            continue
        if query != "" and query not in (name + " " + kind + " " + bundle).to_lower():
            continue
        assets_visible.append(resource)
        asset_list.add_item(name + "  [" + kind + "]")
    if asset_details != null and selected_asset.is_empty():
        asset_details.text = str(assets_visible.size()) + " resources in current filter.\n" + (
            "Source: original IBD header records; no asset data extracted." if not asset_catalog.is_empty() else
            "No asset catalog for this GLB. Import a GMP with its IBD bundles."
        )


func _asset_selected(index: int) -> void:
    if index < 0 or index >= assets_visible.size():
        return
    selected_asset = assets_visible[index]
    var name := str(selected_asset.get("name", ""))
    var placed := _placed_instances_for_asset(name) if str(selected_asset.get("kind", "")) == "staticmesh" else []
    asset_details.text = (
        "Name: " + name +
        "\nKind: " + str(selected_asset.get("kind", "")) +
        "\nSource: " + str(selected_asset.get("bundle", "")) +
        "\nResource index: " + str(selected_asset.get("resource_index", "?")) +
        "\nBytes: " + str(selected_asset.get("bytes", "?")) +
        "\nPlaced actors: " + str(placed.size()) +
        "\nPlace preview creates editor-only geometry, not a native game actor."
    )


func _placed_instances_for_asset(resource_name: String) -> Array:
    var matches := []
    for actor in actors:
        if typeof(actor) != TYPE_DICTIONARY:
            continue
        var mesh: Variant = actor.get("mesh", null)
        var name := str(mesh.get("name", "")) if typeof(mesh) == TYPE_DICTIONARY else str(mesh)
        if name.to_lower() == resource_name.to_lower():
            matches.append(actor)
    return matches


## Catalog meshes are visual previews only. No fake DX2 actor fields.
func _asset_source_key(name: String) -> String:
    return "AssetMesh::" + name


func _asset_record(name: String) -> Dictionary:
    var resources: Variant = asset_catalog.get("assets", [])
    if typeof(resources) != TYPE_ARRAY:
        return {}
    for item in resources:
        if typeof(item) == TYPE_DICTIONARY and str(item.get("kind", "")) == "staticmesh" and str(item.get("name", "")) == name:
            return item
    return {}


func _draft_source_is_valid(source: String) -> bool:
    if actors_by_name.has(source) and meshes_by_actor.has(source):
        return true
    if source.begins_with("AssetMesh::"):
        return not _asset_record(source.trim_prefix("AssetMesh::")).is_empty()
    if source.begins_with("Brush::"):
        return BrushGeometry.TYPES.has(source.trim_prefix("Brush::"))
    return false


func _asset_preview_path(name: String) -> String:
    return current_folder.path_join("asset_previews").path_join("mesh_" + name.sha256_text().substr(0, 20) + ".glb")


func _first_preview_mesh(root: Node) -> MeshInstance3D:
    if root is MeshInstance3D and (root as MeshInstance3D).mesh != null:
        return root as MeshInstance3D
    for child in root.get_children():
        var found := _first_preview_mesh(child)
        if is_instance_valid(found):
            return found
    return null


func _load_asset_mesh(name: String) -> bool:
    if asset_mesh_resources.has(name):
        return true
    if _asset_record(name).is_empty():
        return false
    var path := _asset_preview_path(name)
    if not FileAccess.file_exists(path):
        return false
    var gltf := GLTFDocument.new()
    var state := GLTFState.new()
    if gltf.append_from_file(path, state) != OK:
        return false
    var root := gltf.generate_scene(state)
    if root == null:
        return false
    var found := _first_preview_mesh(root)
    if is_instance_valid(found) and found.mesh != null:
        asset_mesh_resources[name] = found.mesh
    root.free()
    return asset_mesh_resources.has(name)


func _place_selected_asset() -> void:
    var name := str(selected_asset.get("name", ""))
    if str(selected_asset.get("kind", "")) != "staticmesh" or _asset_record(name).is_empty() or scene_root == null:
        status_label.text = "Load a map and select a cataloged static mesh first."
        return
    if asset_thread != null:
        status_label.text = "An asset preview is being generated."
        return
    if _load_asset_mesh(name):
        _place_loaded_asset(name)
        return
    var script := ProjectSettings.globalize_path("res://backend/dx2_asset_preview.py")
    var catalog := current_folder.path_join("assets.json")
    if not FileAccess.file_exists(script) or not FileAccess.file_exists(catalog):
        status_label.text = "Original IBD catalog or asset preview backend missing."
        return
    asset_pending_name = name
    asset_pending_folder = current_folder
    asset_thread = Thread.new()
    var err := asset_thread.start(_run_asset_preview.bind(script, catalog, name))
    if err != OK:
        asset_thread = null
        asset_pending_name = ""
        status_label.text = "Unable to start mesh preview worker."
    else:
        status_label.text = "Decoding IBD resource " + name + " into private textured GLB..."


func _run_asset_preview(script: String, catalog: String, name: String) -> void:
    var args := PackedStringArray([script, "--catalog", catalog, "--name", name])
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        var launcher := PackedStringArray(["-3"])
        launcher.append_array(args)
        output.clear()
        code = OS.execute("py", launcher, output, true)
    call_deferred("_asset_preview_finished", code, "\n".join(output))


func _asset_preview_finished(code: int, output: String) -> void:
    if asset_thread != null:
        asset_thread.wait_to_finish()
        asset_thread = null
    var name := asset_pending_name
    var folder := asset_pending_folder
    asset_pending_name = ""
    asset_pending_folder = ""
    if name.is_empty() or folder != current_folder or scene_root == null or _asset_record(name).is_empty():
        return
    if code == 0 and _load_asset_mesh(name):
        _place_loaded_asset(name)
        return
    var reason := "Python, bundle, or mesh decoder failure."
    for line in output.strip_edges().split("\n"):
        var item: Variant = JSON.parse_string(line.strip_edges())
        if typeof(item) == TYPE_DICTIONARY and item.get("status") == "error":
            reason = str(item.get("message", reason))
    status_label.text = "Cannot preview " + name + ": " + reason


func _place_loaded_asset(name: String) -> void:
    if scene_root == null or not asset_mesh_resources.has(name) or _asset_record(name).is_empty():
        return
    var before := _capture_edit_state()
    var copy_name := "DraftProp_" + str(next_prop_copy_id)
    next_prop_copy_id += 1
    var draft := _new_draft_copy(_asset_source_key(name), copy_name, Transform3D(Basis.IDENTITY, camera_target))
    if not is_instance_valid(draft):
        status_label.text = "Preview placement failed for " + name
        return
    _clear_selection()
    _add_selection_mesh(draft)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    _record_edit("Place IBD asset " + name, before)
    status_label.text = "Placed preview mesh " + name + ". Save draft; GMP remains untouched."


func _focus_asset_instance() -> void:
    if selected_asset.is_empty():
        return
    var matches := _placed_instances_for_asset(str(selected_asset.get("name", "")))
    if matches.is_empty():
        status_label.text = "This resource is not placed in the loaded mission."
        return
    select_actor(matches[0])
    focus_selected()
    status_label.text = "Located first placed instance of " + str(selected_asset.get("name", ""))


func _copy_asset_name() -> void:
    if selected_asset.is_empty():
        return
    DisplayServer.clipboard_set(str(selected_asset.get("name", "")))
    status_label.text = "Copied IBD resource name."


func _refresh_hierarchy() -> void:
    if hierarchy_tree == null:
        return
    hierarchy_syncing = true
    hierarchy_tree.clear()
    hierarchy_items.clear()
    var scene_item := hierarchy_tree.create_item()
    scene_item.set_text(0, "DX2 Scene  (" + str(actors.size()) + " actors)")
    scene_item.set_selectable(0, false)
    var categories: Dictionary = {}
    # These are editor folders by decoded class, NOT invented Unreal ownership.
    for actor in visible_actors:
        if typeof(actor) != TYPE_DICTIONARY:
            continue
        var group := _actor_category(actor)
        if not categories.has(group):
            var folder := hierarchy_tree.create_item(scene_item)
            folder.set_text(0, group)
            folder.set_selectable(0, false)
            folder.collapsed = group == "Brush" or group == "Gameplay / other"
            categories[group] = folder
        var name := str(actor.get("name", ""))
        var leaf := hierarchy_tree.create_item(categories[group])
        var evidence: Variant = actor.get("placement_diagnostic", {})
        var needs_review := typeof(evidence) == TYPE_DICTIONARY and bool(evidence.get("needs_review", false))
        leaf.set_text(0, name + ("  [bounds?]" if needs_review else ""))
        leaf.set_tooltip_text(0, str(actor.get("class", "?")) +
            (" | Source mesh bounds/pivot require review" if needs_review else ""))
        leaf.set_metadata(0, name)
        hierarchy_items[name] = leaf

    var query := search_box.text.strip_edges().to_lower()
    if category_filter.selected <= 1:
        var authored_brushes := hierarchy_tree.create_item(scene_item)
        authored_brushes.set_text(0, "Brushes (" + str(draft_brush_specs.size()) + ")")
        authored_brushes.set_selectable(0, false)
        var drafts := hierarchy_tree.create_item(scene_item)
        drafts.set_text(0, "Draft props (" + str(draft_prop_copies.size() - draft_brush_specs.size()) + ")")
        drafts.set_selectable(0, false)
        for name in draft_prop_copies:
            var source_name := str(draft_prop_sources.get(name, ""))
            var is_brush := draft_brush_specs.has(name)
            if query != "" and query not in str(name).to_lower() and query not in source_name.to_lower():
                continue
            var parent_item: TreeItem = authored_brushes if is_brush else drafts
            var leaf := hierarchy_tree.create_item(parent_item)
            leaf.set_text(0, str(name) + ("  [" + str(draft_brush_specs[name]["kind"]) + "]" if is_brush else "  [draft]"))
            leaf.set_tooltip_text(0, "Preview geometry " + source_name + " (not a compiled DX2 actor or BSP)")
            leaf.set_metadata(0, str(name))
            hierarchy_items[str(name)] = leaf

    if category_filter.selected == 0:
        var unlinked := hierarchy_tree.create_item(scene_item)
        unlinked.set_text(0, "Unlinked geometry (BSP / render nodes)")
        unlinked.set_selectable(0, false)
        unlinked.collapsed = true
        for node in all_mesh_instances:
            if not is_instance_valid(node):
                continue
            var name := str(node.name)
            if actors_by_name.has(name) or draft_prop_copies.has(name):
                continue
            if query != "" and query not in name.to_lower():
                continue
            var leaf := hierarchy_tree.create_item(unlinked)
            leaf.set_text(0, name)
            leaf.set_metadata(0, name)
            hierarchy_items[name] = leaf

    _sync_hierarchy_selection()
    hierarchy_syncing = false


func _sync_hierarchy_selection() -> void:
    if hierarchy_tree == null or hierarchy_syncing:
        return
    hierarchy_syncing = true
    hierarchy_tree.deselect_all()
    for name in selected_meshes:
        if hierarchy_items.has(name):
            var item: TreeItem = hierarchy_items[name]
            item.get_parent().collapsed = false
            item.select(0)
    if selected_meshes.is_empty() and not selected_actor.is_empty():
        var name := str(selected_actor.get("name", ""))
        if hierarchy_items.has(name):
            var item: TreeItem = hierarchy_items[name]
            item.get_parent().collapsed = false
            item.select(0)
    hierarchy_syncing = false


func _hierarchy_multi_selected(_item: TreeItem, _column: int, _selected: bool) -> void:
    if not hierarchy_syncing:
        call_deferred("_apply_hierarchy_selection")


func _apply_hierarchy_selection() -> void:
    if hierarchy_tree == null or hierarchy_syncing:
        return
    var chosen_names: Array[String] = []
    var cursor: TreeItem = hierarchy_tree.get_next_selected(null)
    while cursor != null:
        var meta: Variant = cursor.get_metadata(0)
        if typeof(meta) == TYPE_STRING and not str(meta).is_empty():
            chosen_names.append(str(meta))
        cursor = hierarchy_tree.get_next_selected(cursor)
    if chosen_names.is_empty():
        return
    _clear_selection()
    var logical_actor: Dictionary = {}
    for name in chosen_names:
        var node: MeshInstance3D = null
        if draft_prop_copies.has(name):
            node = draft_prop_copies[name]
        elif meshes_by_actor.has(name):
            node = meshes_by_actor[name]
        else:
            for mesh_node in all_mesh_instances:
                if is_instance_valid(mesh_node) and str(mesh_node.name) == name:
                    node = mesh_node
                    break
        if is_instance_valid(node):
            _add_selection_mesh(node)
        elif actors_by_name.has(name):
            logical_actor = actors_by_name[name]
    if selected_meshes.is_empty() and not logical_actor.is_empty():
        selected_actor = logical_actor
        selected_diagnostic = _format_actor_diagnostic(logical_actor)
        inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(logical_actor, "  ")
        status_label.text = "Selected logical actor: " + str(logical_actor.get("name", ""))
        _refresh_inspector_panel()
    else:
        _refresh_selection_inspector()
    _sync_actor_list_selection()


func _actor_list_selected(index: int) -> void:
    # Backward compatibility with the single-selection signal.
    if index >= 0 and index < visible_actors.size():
        select_actor(visible_actors[index])


func _actor_list_multi_selected(_index: int, _is_selected: bool) -> void:
    # The list emits an event per changed row (including Shift range selection).
    # Defer rebuilding until the control finishes applying the complete gesture.
    call_deferred("_apply_list_multi_selection")


func _apply_list_multi_selection() -> void:
    var rows := actor_list.get_selected_items()
    if rows.is_empty():
        _clear_selection()
        inspector.text = "No actors selected."
        return
    var choices: Array[MeshInstance3D] = []
    var last_actor: Dictionary = {}
    for row in rows:
        if row < 0 or row >= visible_actors.size():
            continue
        var actor: Dictionary = visible_actors[row]
        last_actor = actor
        var name := str(actor.get("name", ""))
        if meshes_by_actor.has(name):
            var node: MeshInstance3D = meshes_by_actor[name]
            if is_instance_valid(node) and not choices.has(node):
                choices.append(node)
    _clear_selection()
    for node in choices:
        _add_selection_mesh(node)
    if choices.is_empty() and not last_actor.is_empty():
        # Logical-only actors remain inspectable, but not transformable.
        selected_actor = last_actor
        selected_diagnostic = _format_actor_diagnostic(last_actor)
        inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(last_actor, "  ")
        status_label.text = "Selected logical actor: " + str(last_actor.get("name", "?"))
        _refresh_inspector_panel()
    else:
        _refresh_selection_inspector()


func _sync_actor_list_selection() -> void:
    if actor_list == null:
        return
    actor_list.deselect_all()
    for index in range(visible_actors.size()):
        if selected_meshes.has(str(visible_actors[index].get("name", ""))):
            actor_list.select(index, false)
    _sync_hierarchy_selection()



func _format_actor_diagnostic(actor: Dictionary) -> String:
    var name := str(actor.get("name", "Unknown"))
    # Actor Explorer emits a string mesh name plus separate mesh_bounds, whereas
    # the authored demo fixture uses {"name": ..., "bounds": ...}.
    # Support both without losing the original retail actor metadata.
    var mesh_data: Variant = actor.get("mesh", null)
    var mesh_name := "(no static mesh)"
    var bounds: Variant = actor.get("mesh_bounds", null)
    if typeof(mesh_data) == TYPE_DICTIONARY:
        mesh_name = str(mesh_data.get("name", "(unknown)"))
        if mesh_data.has("bounds"):
            bounds = mesh_data["bounds"]
    elif typeof(mesh_data) == TYPE_STRING and not str(mesh_data).is_empty():
        mesh_name = str(mesh_data)
    var bounds_text := str(bounds) if bounds != null else "(unavailable)"

    # Both the retail actor explorer and demo fixture use location: [x,y,z].
    # Keep a compatibility fallback for older exports containing x/y/z keys.
    var source_location: Variant = actor.get("location", null)
    if typeof(source_location) != TYPE_ARRAY or source_location.size() < 3:
        source_location = [actor.get("x", null), actor.get("y", null), actor.get("z", null)]

    var rotation: Variant = actor.get("rotation", [0, 0, 0])
    var degrees_text := "(unavailable)"
    if typeof(rotation) == TYPE_ARRAY and rotation.size() >= 3:
        degrees_text = "[%0.3f, %0.3f, %0.3f]" % [float(rotation[0]) * 360.0 / 65536.0, float(rotation[1]) * 360.0 / 65536.0, float(rotation[2]) * 360.0 / 65536.0]
    var lines := [
        "DX2Ed map geometry diagnostic (read-only)",
        "Actor: " + name,
        "Source map: " + (current_source_map_name if not current_source_map_name.is_empty() else "(not recorded)"),
        "Class: " + str(actor.get("class", "Unknown")),
        "Editor category (class hint): " + _actor_category(actor),
        "Physics / inventory semantics: not validated by this classification",
        "GMP export index: " + str(actor.get("export", "?")),
        "Mesh resource: " + mesh_name,
        "GMP position (UE units): " + str(source_location),
        "GMP rotation [Pitch, Yaw, Roll] (UE rotator units): " + str(rotation),
        "Rotation degrees [Pitch, Yaw, Roll]: " + degrees_text,
        "Mesh local bounds (UE units): " + bounds_text,
    ]
    var render_skin: Variant = actor.get("render_skin", null)
    if typeof(render_skin) == TYPE_DICTIONARY:
        lines.append("Requested skin: " + str(render_skin.get("requested", "(none)")))
        lines.append("Exported skin: " + str(render_skin.get("selected", "(none)")))
        lines.append("Skin resolution: " + str(render_skin.get("status", "unknown")))
        var material_rows: Variant = render_skin.get("materials", [])
        if typeof(material_rows) == TYPE_ARRAY:
            for material_row in material_rows:
                if typeof(material_row) == TYPE_DICTIONARY:
                    lines.append("Skin material: " + str(material_row.get("name", "?")) + " | " + str(material_row.get("resolution", "unknown")))
    else:
        for prop in actor.get("game_properties", []):
            if typeof(prop) == TYPE_DICTIONARY and int(prop.get("id", -1)) == 56:
                var details: Variant = prop.get("value", null)
                if typeof(details) == TYPE_DICTIONARY and details.has("Skin"):
                    lines.append("Requested skin: " + str(details["Skin"]) + " (export selection not recorded)")
                    break
    if meshes_by_actor.has(name) and is_instance_valid(meshes_by_actor[name]):
        var instance: MeshInstance3D = meshes_by_actor[name]
        var box := _mesh_world_aabb(instance)
        lines.append("Godot mesh node: " + str(instance.name))
        lines.append("Godot global transform: " + str(instance.global_transform))
        lines.append("Godot world AABB: " + str(box.position) + " size " + str(box.size))
    else:
        lines.append("Matching rendered mesh node: not found (may be logical-only or have an unresolved resource)")
    return "\n".join(lines)

func _format_mesh_diagnostic(mesh_instance: MeshInstance3D) -> String:
    var box := _mesh_world_aabb(mesh_instance)
    return "\n".join([
        "DX2Ed map geometry diagnostic (read-only)",
        "Rendered mesh node: " + str(mesh_instance.name),
        "Editor category: " + ("BSP render geometry" if str(mesh_instance.name).begins_with("BSP_") else "Unlinked rendered geometry"),
        "Original DX2 actor metadata: not matched; may be BSP or imported geometry",
        "Godot global transform: " + str(mesh_instance.global_transform),
        "Godot world AABB: " + str(box.position) + " size " + str(box.size),
    ])

func _copy_selection_details() -> void:
    if selected_diagnostic.is_empty():
        status_label.text = "Select an actor or click a rendered mesh first."
        return
    DisplayServer.clipboard_set(selected_diagnostic)
    status_label.text = "Copied selection diagnostic to clipboard. Paste it into your bug report."

func _selection_nodes() -> Array[MeshInstance3D]:
    var nodes: Array[MeshInstance3D] = []
    for node in selected_meshes.values():
        if is_instance_valid(node):
            nodes.append(node)
    return nodes


func _selection_pivot() -> Vector3:
    var nodes := _selection_nodes()
    if nodes.is_empty():
        return Vector3.ZERO
    var pivot := Vector3.ZERO
    for node in nodes:
        pivot += node.global_position
    return pivot / float(nodes.size())


## Geometry debugging never writes an editor draft or a native map.
## This is intentionally separate from the experimental actor writers.
func _refresh_geometry_debug_buttons() -> void:
    var available := _selection_nodes().size() == 1
    if geometry_isolation_button != null:
        geometry_isolation_button.disabled = not available and geometry_isolation_visibility.is_empty()
        geometry_isolation_button.text = (
            "Restore visibility" if not geometry_isolation_visibility.is_empty()
            else "Isolate selected"
        )
    if geometry_all_faces_button != null:
        geometry_all_faces_button.disabled = not available and not is_instance_valid(geometry_all_faces_target)
        geometry_all_faces_button.text = (
            "Restore materials" if is_instance_valid(geometry_all_faces_target)
            else "Inspect both faces"
        )


func _restore_geometry_isolation() -> void:
    for target in geometry_isolation_visibility:
        if is_instance_valid(target):
            target.visible = bool(geometry_isolation_visibility[target])
    geometry_isolation_visibility.clear()
    geometry_isolation_target = null
    _refresh_geometry_debug_buttons()


func _toggle_geometry_isolation() -> void:
    if not geometry_isolation_visibility.is_empty():
        _restore_geometry_isolation()
        status_label.text = "Geometry diagnostic ended. All original scene visibility restored."
        return
    var nodes := _selection_nodes()
    if nodes.size() != 1 or not is_instance_valid(nodes[0]):
        status_label.text = "Select exactly one original rendered mesh to isolate."
        return
    var source: MeshInstance3D = nodes[0]
    for node in all_mesh_instances:
        if is_instance_valid(node):
            geometry_isolation_visibility[node] = node.visible
            node.visible = node == source
    geometry_isolation_target = source
    status_label.text = (
        "Geometry diagnostic: isolated " + str(source.name)
        + ". Other meshes and glass are temporarily hidden, not changed."
    )
    _refresh_geometry_debug_buttons()


func _restore_geometry_all_faces() -> void:
    if is_instance_valid(geometry_all_faces_target):
        geometry_all_faces_target.material_override = geometry_all_faces_previous_override
    geometry_all_faces_target = null
    geometry_all_faces_previous_override = null
    _refresh_geometry_debug_buttons()


func _toggle_geometry_all_faces() -> void:
    if is_instance_valid(geometry_all_faces_target):
        _restore_geometry_all_faces()
        status_label.text = "Geometry diagnostic ended. Source preview material restored."
        return
    var nodes := _selection_nodes()
    if nodes.size() != 1 or not is_instance_valid(nodes[0]):
        status_label.text = "Select exactly one mesh to inspect backfaces."
        return
    var source: MeshInstance3D = nodes[0]
    if source.mesh == null:
        status_label.text = "The selected actor has no rendered triangles."
        return
    geometry_all_faces_target = source
    geometry_all_faces_previous_override = source.material_override
    var debug_material := StandardMaterial3D.new()
    debug_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    debug_material.cull_mode = BaseMaterial3D.CULL_DISABLED
    debug_material.albedo_color = Color(0.25, 0.9, 0.95, 1.0)
    source.material_override = debug_material
    var count := 0
    for surface in range(source.mesh.get_surface_count()):
        count += source.mesh.surface_get_array_index_len(surface) / 3
    status_label.text = (
        "Geometry diagnostic: " + str(source.name) + " approx " + str(count)
        + " triangles, both faces visible in cyan. This is a read-only preview."
    )
    _refresh_geometry_debug_buttons()


func _add_selection_mesh(mesh_instance: MeshInstance3D) -> void:
    if not is_instance_valid(mesh_instance):
        return
    var name := str(mesh_instance.name)
    if selected_meshes.has(name):
        selected_mesh = mesh_instance
        return
    selected_meshes[name] = mesh_instance
    selection_original_overlays[name] = mesh_instance.material_overlay
    mesh_instance.material_overlay = overlay_material
    selected_mesh = mesh_instance
    selected_actor = actors_by_name.get(name, {})


func _remove_selection_mesh(mesh_instance: MeshInstance3D) -> void:
    if not is_instance_valid(mesh_instance):
        return
    var name := str(mesh_instance.name)
    if not selected_meshes.has(name):
        return
    mesh_instance.material_overlay = selection_original_overlays.get(name, null)
    selected_meshes.erase(name)
    selection_original_overlays.erase(name)
    var survivors := _selection_nodes()
    selected_mesh = survivors.back() if not survivors.is_empty() else null
    selected_actor = actors_by_name.get(str(selected_mesh.name), {}) if is_instance_valid(selected_mesh) else {}


func _refresh_selection_inspector() -> void:
    var nodes := _selection_nodes()
    if nodes.is_empty():
        selected_diagnostic = ""
        inspector.text = "No rendered objects selected."
        status_label.text = "No objects selected."
        _refresh_inspector_panel()
        return
    if nodes.size() == 1:
        var node := nodes[0]
        var name := str(node.name)
        if actors_by_name.has(name):
            selected_actor = actors_by_name[name]
            selected_diagnostic = _format_actor_diagnostic(selected_actor)
            inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(selected_actor, "  ")
        else:
            selected_actor = {}
            selected_diagnostic = _format_mesh_diagnostic(node)
            inspector.text = selected_diagnostic
        status_label.text = "Selected " + name
        _refresh_inspector_panel()
        return
    var lines := ["DX2Ed multi-selection (preview only)",
        "Selected objects: " + str(nodes.size()),
        "Group pivot (Godot world): " + str(_selection_pivot()),
        "Move, Rotate and Scale use the group pivot.",
        "Original GMP/IBD files remain unchanged.", ""]
    for node in nodes:
        lines.append(str(node.name) + " | " + str(node.global_position))
    selected_diagnostic = "\n".join(lines)
    inspector.text = selected_diagnostic
    status_label.text = str(nodes.size()) + " objects selected. Group gizmo active."
    _refresh_inspector_panel()


## These are *hypotheses* for render orientation, not engine transform fixes.
## The authoritative source rotator and position are never modified.
func _source_ue_rotator(name: String) -> Array:
    if not actors_by_name.has(name):
        return []
    var values: Variant = actors_by_name[name].get("rotation", [])
    if typeof(values) != TYPE_ARRAY or values.size() < 3:
        return []
    for value in values:
        if typeof(value) not in [TYPE_FLOAT, TYPE_INT]:
            return []
    return values


func _ue_rotator_basis(values: Array) -> Basis:
    # glTF/Godot basis conversion of Unreal Rz(Yaw)*Ry(-Pitch)*Rx(Roll).
    # Swapping UE Y and Z reverses handedness, hence negative yaw/roll.
    var pitch: float = float(values[0]) * TAU / 65536.0
    var yaw: float = float(values[1]) * TAU / 65536.0
    var roll: float = float(values[2]) * TAU / 65536.0
    return Basis(Vector3.UP, -yaw) * Basis(Vector3.BACK, pitch) * Basis(Vector3.RIGHT, -roll)


func _rotation_hypothesis_pose(name: String, mode: int) -> Transform3D:
    var original: Transform3D = original_mesh_transforms.get(name, Transform3D.IDENTITY)
    if mode == 0 or mode < 0 or mode > 5:
        return original
    var pose := original
    if mode <= 3:
        var angle: float = float([-90.0, 90.0, 180.0][mode - 1])
        pose.basis = Basis(Vector3.UP, deg_to_rad(angle)) * original.basis
    else:
        var values := _source_ue_rotator(name)
        if values.is_empty():
            return original
        var corrected := values.duplicate()
        if mode == 4:
            corrected[0] = -float(corrected[0])
        if mode == 5:
            corrected[2] = -float(corrected[2])
        var matrix := _ue_rotator_basis(corrected)
        var scale := original.basis.get_scale()
        pose.basis = Basis(matrix.x * scale.x, matrix.y * scale.y, matrix.z * scale.z)
    return pose


func _aabb_for_pose(mesh: MeshInstance3D, pose: Transform3D) -> AABB:
    var local_box := mesh.get_aabb()
    var world_box := AABB(pose * local_box.get_endpoint(0), Vector3.ZERO)
    for i in range(1, 8):
        world_box = world_box.expand(pose * local_box.get_endpoint(i))
    return world_box


func _bbox_gap(a: AABB, b: AABB) -> float:
    var delta := Vector3.ZERO
    for i in range(3):
        delta[i] = maxf(0.0, maxf(b.position[i] - a.end[i], a.position[i] - b.end[i]))
    return delta.length()


func _rotation_spatial_evidence(mesh: MeshInstance3D, pose: Transform3D) -> Dictionary:
    var box := _aabb_for_pose(mesh, pose)
    var nearest := INF
    var overlap_count := 0
    var closest := ""
    for node in all_mesh_instances:
        if not is_instance_valid(node) or node.mesh == null:
            continue
        if not str(node.name).begins_with("BSP_"):
            continue
        var distance: float = _bbox_gap(box, _mesh_world_aabb(node))
        if distance < nearest:
            nearest = distance
            closest = str(node.name)
        if distance < 0.00001:
            overlap_count += 1
    return {
        "bounds": box,
        "nearest_bsp": closest if nearest < INF else "(BSP geometry unavailable)",
        "gap_m": nearest if nearest < INF else null,
        "bsp_aabb_overlaps": overlap_count
    }


func _rotation_evidence_text() -> String:
    if not _draft_selected_is_prop() or _selection_nodes().size() != 1:
        return "Choose one placed static mesh actor."
    var node: MeshInstance3D = _selection_nodes()[0]
    var name := str(node.name)
    if not actors_by_name.has(name) or not original_mesh_transforms.has(name):
        return "Original actor rotations are unavailable for draft copies."
    var actor: Dictionary = actors_by_name[name]
    var original: Transform3D = original_mesh_transforms[name]
    var raw := _source_ue_rotator(name)
    var lines := [
        "DX2Ed Rotation Lab (unverified orientation hypotheses)",
        "Actor: " + name + " | export: " + str(actor.get("export", "?")),
        "Map: " + current_source_map_name,
        "Mesh: " + str(actor.get("mesh", "")),
        "GMP rotator [Pitch, Yaw, Roll]: " + str(raw),
        "UE degrees [Pitch, Yaw, Roll]: " + str([
            float(raw[0])*360.0/65536.0,
            float(raw[1])*360.0/65536.0,
            float(raw[2])*360.0/65536.0
        ]) if raw.size() == 3 else "GMP rotator unavailable",
        "Original Godot basis: " + str(original.basis),
        "Current preview basis: " + str(node.global_transform.basis),
        "These tests keep the original position and source mesh unchanged.",
        "AABB proximity is NOT proof of correct orientation or collision.",
        ""
    ]
    for mode in range(rotation_lab_modes.item_count):
        var pose := _rotation_hypothesis_pose(name, mode)
        var info := _rotation_spatial_evidence(node, pose)
        var gap: Variant = info["gap_m"]
        lines.append(rotation_lab_modes.get_item_text(mode) +
            " | bounds: " + str(info["bounds"]) +
            " | nearby BSP: " + str(info["nearest_bsp"]) +
            " | AABB gap (m): " + (str(snappedf(float(gap), 0.001)) if gap != null else "unknown") +
            " | AABB overlaps: " + str(info["bsp_aabb_overlaps"]))
    lines.append("")
    lines.append("Original map transforms alone cannot establish correct in-game placement.")
    lines.append("Compare with retail game / original authoring data before applying changes globally.")
    return "\n".join(lines)


func _update_rotation_lab_hint() -> void:
    if rotation_lab_hint == null or rotation_lab_panel == null:
        return
    var nodes := _selection_nodes()
    var eligible := nodes.size() == 1 and actors_by_name.has(str(nodes[0].name)) and original_mesh_transforms.has(str(nodes[0].name)) if nodes.size() == 1 else false
    rotation_lab_panel.visible = eligible
    if not eligible:
        return
    var node: MeshInstance3D = nodes[0]
    var pose := _rotation_hypothesis_pose(str(node.name), rotation_lab_modes.selected)
    var info := _rotation_spatial_evidence(node, pose)
    var gap: Variant = info["gap_m"]
    rotation_lab_hint.text = (
        "Original UE rotator: " + str(_source_ue_rotator(str(node.name))) +
        "\nCandidate BSP-box gap: " + (str(snappedf(float(gap), 0.001)) + " m" if gap != null else "unknown") +
        " | overlaps: " + str(info["bsp_aabb_overlaps"]) +
        "\nAABB proximity is suggestive, never proof. Preview is undoable."
    )


func _preview_rotation_hypothesis() -> void:
    if rotation_lab_panel == null or not rotation_lab_panel.visible:
        return
    var nodes := _selection_nodes()
    if nodes.size() != 1:
        return
    var node: MeshInstance3D = nodes[0]
    var name := str(node.name)
    var before := _capture_edit_state()
    node.global_transform = _rotation_hypothesis_pose(name, rotation_lab_modes.selected)
    _refresh_prop_inspection()
    _record_edit("Rotation Lab: " + rotation_lab_modes.get_item_text(rotation_lab_modes.selected), before)
    status_label.text = "Rotation Lab: reversible preview orientation applied, retail GMP unchanged."


func _copy_rotation_research() -> void:
    var report := _rotation_evidence_text()
    DisplayServer.clipboard_set(report)
    status_label.text = "Copied rotation hypotheses and BSP bounding-box evidence to clipboard."


func _copy_placement_evidence() -> void:
    var actor: Dictionary = {}
    var nodes := _selection_nodes()
    if nodes.size() == 1 and actors_by_name.has(str(nodes[0].name)):
        actor = actors_by_name[str(nodes[0].name)]
    elif nodes.is_empty() and not selected_actor.is_empty():
        actor = selected_actor
    if actor.is_empty():
        status_label.text = "Select one original actor to copy placement evidence."
        return
    var data: Variant = actor.get("placement_diagnostic", null)
    var report := _format_actor_diagnostic(actor)
    if typeof(data) == TYPE_DICTIONARY:
        report += "\n\n--- SOURCE MESH PIVOT / BOUNDS AUDIT ---\n" + JSON.stringify(data, "  ")
    else:
        report += "\n\nSource mesh audit unavailable for this actor."
    DisplayServer.clipboard_set(report)
    status_label.text = "Copied original mesh bounds, pivot, rotation and source evidence."


func _refresh_placement_panel() -> void:
    if placement_inspector == null:
        return
    var actor: Dictionary = {}
    var nodes := _selection_nodes()
    if nodes.size() == 1 and actors_by_name.has(str(nodes[0].name)):
        actor = actors_by_name[str(nodes[0].name)]
    elif nodes.is_empty() and not selected_actor.is_empty():
        actor = selected_actor
    var evidence: Variant = actor.get("placement_diagnostic", null)
    placement_inspector.visible = typeof(evidence) == TYPE_DICTIONARY
    if not placement_inspector.visible:
        return
    var data: Dictionary = evidence
    var flags: Variant = data.get("warnings", [])
    var world_evidence := ""
    if data.has("preview_major_axis_endpoints_godot_m"):
        var pts: Variant = data["preview_major_axis_endpoints_godot_m"]
        world_evidence = (
            "\nWorld mesh endpoints: " + str(pts) +
            "\nWorld AABB min/max: " +
                str(data.get("preview_world_aabb_min_m", "?")) + " to " +
                str(data.get("preview_world_aabb_max_m", "?"))
        )
    if bool(data.get("roll_direction_aabb_ambiguous", false)):
        world_evidence += (
            "\nRoll warning: nearly square cross-section. " +
            "AABB cannot distinguish positive/negative roll; compare textured faces in game."
        )
    placement_inspector.text = (
        "Mesh origin ↔ center: " + str(data.get("mesh_pivot_to_center_m", "?")) + " m" +
        "\nIBD ↔ vertices max difference: " + str(data.get("ibd_vertex_bounds_max_delta_ue", "?")) + " UE" +
        "\nGMP ↔ vertices max difference: " + str(data.get("gmp_vertex_bounds_max_delta_ue", "?")) + " UE" +
        "\nSource checks: " + (", ".join(flags) if not flags.is_empty() else "No local bounds disagreements detected") +
        "\nThese comparisons do not determine the correct world rotation." +
        world_evidence
    )


func _mesh_geometry_material_summary(actor: Dictionary, node: MeshInstance3D = null) -> String:
    # Keep basic source type and material info immediately visible even when
    # the long original actor properties and mesh metadata require scrolling.
    var lines: Array[String] = []
    if not actor.is_empty():
        lines.append("Actor: " + str(actor.get("class", "Unknown")) +
            "  |  " + _actor_category(actor))
        if typeof(actor.get("auto_roll_preview", null)) == TYPE_DICTIONARY:
            lines.append("Auto Roll: inverted source roll (preview hypothesis, not game-verified)")
        var resource: Variant = actor.get("mesh", null)
        var mesh_name := ""
        if typeof(resource) == TYPE_STRING:
            mesh_name = str(resource)
        elif typeof(resource) == TYPE_DICTIONARY:
            mesh_name = str(resource.get("name", ""))
        if not mesh_name.is_empty():
            lines.append("Geometry: static mesh | " + mesh_name)
        else:
            lines.append("Geometry: logical actor (no linked mesh)")
        var skin: Variant = actor.get("render_skin", null)
        if typeof(skin) == TYPE_DICTIONARY:
            lines.append("Skin: " + str(skin.get("selected", "(unavailable)")) +
                " [" + str(skin.get("status", "unknown")) + "]")
            var material_rows: Variant = skin.get("materials", [])
            if typeof(material_rows) == TYPE_ARRAY:
                var names: Array[String] = []
                for item in material_rows:
                    if typeof(item) == TYPE_DICTIONARY:
                        var name := str(item.get("name", ""))
                        var resolution := str(item.get("resolution", "unknown"))
                        var detail := name + " [" + resolution + "]"
                        if not name.is_empty() and not names.has(detail):
                            names.append(detail)
                if not names.is_empty():
                    lines.append("Source materials: " + ", ".join(names.slice(0, 5)) +
                        (" (more)" if names.size() > 5 else ""))
    if is_instance_valid(node) and node.mesh != null:
        if actor.is_empty():
            var kind := "BSP render geometry" if str(node.name).begins_with("BSP_") else "Unlinked mesh geometry"
            if str(node.name).begins_with("DraftProp_"):
                kind = "Editor-only draft geometry"
            lines.append("Geometry: " + kind + " | " + str(node.name))
        var surface_count := node.mesh.get_surface_count()
        lines.append("Surfaces: " + str(surface_count))
        var material_names: Array[String] = []
        for index in range(mini(surface_count, 8)):
            var material: Material = node.get_active_material(index)
            if material != null:
                var label := material.resource_name
                if label.is_empty():
                    label = material.get_class()
                if not material_names.has(label):
                    material_names.append(label)
        if not material_names.is_empty():
            lines.append("Preview materials: " + ", ".join(material_names.slice(0, 4)) +
                (" (more)" if material_names.size() > 4 else ""))
    if lines.is_empty():
        return "Geometry: none selected\nMaterial: select an actor or rendered mesh"
    return "\n".join(lines)


func _refresh_inspector_panel() -> void:
    if inspector_title == null or inspector_transform_section == null:
        return
    _refresh_geometry_debug_buttons()
    _refresh_brush_inspector()
    _refresh_placement_panel()
    var nodes := _selection_nodes()
    var current_actor: Dictionary = {}
    var current_mesh: MeshInstance3D = null
    if nodes.size() == 1:
        current_mesh = nodes[0]
        if actors_by_name.has(str(nodes[0].name)):
            current_actor = actors_by_name[str(nodes[0].name)]
    elif nodes.is_empty() and not selected_actor.is_empty():
        current_actor = selected_actor
    inspector_summary.text = _mesh_geometry_material_summary(current_actor, current_mesh)
    var eligible := _draft_selected_is_prop()
    inspector_transform_section.visible = eligible
    _refresh_actor_property_editor()
    _refresh_source_gamesys_inspector()
    if nodes.is_empty():
        if selected_actor.is_empty():
            inspector_title.text = "Nothing selected"
            inspector_details.text = "Choose an actor from the Hierarchy or click a scene object."
        else:
            inspector_title.text = str(selected_actor.get("name", "Actor"))
            inspector_details.text = str(selected_actor.get("class", "Unknown")) + " | " + _actor_category(selected_actor) + "\nNo editable rendered mesh."
        return
    var name := str(nodes[0].name)
    inspector_title.text = name if nodes.size() == 1 else str(nodes.size()) + " selected objects"
    if nodes.size() > 1:
        inspector_details.text = "Group selection | Position = shared pivot\nTransforms are drafts; source map unchanged."
    elif draft_prop_copies.has(name):
        var template: Dictionary = draft_template_provenance.get(name, {})
        inspector_details.text = (
            "Preview-only mesh: " + str(draft_prop_sources.get(name, "?")) +
            ("\nBrush: " + str(draft_brush_specs[name].get("kind", "")) if draft_brush_specs.has(name) else "") +
            ("\nTemplate class: " + str(template.get("qualified", "")) if not template.is_empty() else "") +
            "\nNo native DX2 actor, physics or scripts")
    elif actors_by_name.has(name):
        var actor: Dictionary = actors_by_name[name]
        inspector_details.text = str(actor.get("class", "?")) + " | " + _actor_category(actor) + "\nExport " + str(actor.get("export", "?"))
    else:
        inspector_details.text = "Unlinked geometry\nRead-only"
    if not eligible:
        _update_rotation_lab_hint()
        return
    _update_rotation_lab_hint()
    var position := _selection_pivot() if nodes.size() > 1 else nodes[0].global_position
    var rotation := nodes[0].global_rotation_degrees
    var scale := nodes[0].scale
    var values := {"Position": position, "Rotation": rotation, "Scale": scale}
    inspector_syncing = true
    for mode in ["Position", "Rotation", "Scale"]:
        var vector: Vector3 = values[mode]
        for axis in range(3):
            var spin: SpinBox = inspector_spins[mode + str(axis)]
            spin.editable = nodes.size() == 1 or mode == "Position"
            spin.set_value_no_signal(vector[axis])
    inspector_syncing = false


## Only unambiguous decoded scalar values may enter the draft editor.
## Never edit native actor records or unresolved references/scripts.
func _find_editable_property(actor: Dictionary, id: int) -> Dictionary:
    if id < 0 or id == 43 or id == 92:
        return {}
    var matches := []
    for entry in actor.get("game_properties", []):
        if typeof(entry) != TYPE_DICTIONARY:
            continue
        if int(entry.get("id", -1)) == id:
            matches.append(entry)
    if matches.size() != 1:
        return {}
    var item: Dictionary = matches[0]
    var kind := str(item.get("type", "")).to_lower()
    var value: Variant = item.get("value", null)
    if kind == "bool" and typeof(value) == TYPE_BOOL:
        return item
    if kind in ["byte", "int"] and typeof(value) in [TYPE_INT, TYPE_FLOAT]:
        var number: float = float(value)
        if not is_nan(number) and not is_inf(number) and floorf(number) == number:
            if kind == "byte" and number >= 0 and number <= 255:
                return item
            if kind == "int" and absf(number) <= 1000000.0:
                return item
    if kind == "float" and typeof(value) in [TYPE_INT, TYPE_FLOAT]:
        if not is_nan(float(value)) and not is_inf(float(value)) and absf(float(value)) <= 1000000.0:
            return item
    if kind == "string" and typeof(value) == TYPE_STRING and str(value).length() <= 512:
        return item
    return {}


func _validated_scalar(kind: String, value: Variant) -> Variant:
    if kind == "bool":
        return value if typeof(value) == TYPE_BOOL else null
    if kind in ["byte", "int"]:
        if typeof(value) not in [TYPE_INT, TYPE_FLOAT]:
            return null
        var numeric := float(value)
        if is_nan(numeric) or is_inf(numeric) or floorf(numeric) != numeric:
            return null
        if kind == "byte" and (numeric < 0 or numeric > 255):
            return null
        if kind == "int" and absf(numeric) > 1000000.0:
            return null
        return int(numeric)
    if kind == "float":
        if typeof(value) not in [TYPE_INT, TYPE_FLOAT] or (is_nan(float(value)) or is_inf(float(value))):
            return null
        return float(value) if absf(float(value)) <= 1000000.0 else null
    if kind == "string":
        return value if typeof(value) == TYPE_STRING and value.length() <= 512 else null
    return null


func _refresh_actor_property_editor() -> void:
    if property_editor_panel == null or property_editor_rows == null:
        return
    var actor: Dictionary = {}
    var nodes := _selection_nodes()
    if nodes.size() == 1 and actors_by_name.has(str(nodes[0].name)):
        actor = actors_by_name[str(nodes[0].name)]
    elif nodes.is_empty() and not selected_actor.is_empty():
        actor = selected_actor
    var name := str(actor.get("name", ""))
    property_editor_panel.visible = not name.is_empty()
    var query := property_filter.text.strip_edges().to_lower() if property_filter != null else ""
    var key := name + "|" + query + "|" + JSON.stringify(property_overrides.get(name, {}))
    if not property_editor_panel.visible:
        property_editor_last_key = ""
        return
    if key == property_editor_last_key:
        return
    property_editor_last_key = key
    property_editor_syncing = true
    for node in property_editor_rows.get_children():
        property_editor_rows.remove_child(node)
        node.queue_free()

    var supported := 0
    var shown := 0
    var locked := 0
    for item in actor.get("game_properties", []):
        if typeof(item) != TYPE_DICTIONARY:
            continue
        var id := int(item.get("id", -1))
        var safe: Dictionary = _find_editable_property(actor, id)
        if safe.is_empty():
            locked += 1
            continue
        supported += 1
        var kind := str(safe.get("type", "")).to_lower()
        var prop_label := str(safe.get("name", "Property_" + str(id)))
        if query != "" and query not in (prop_label + " " + str(id) + " " + kind).to_lower():
            continue
        shown += 1
        if shown > 48:
            continue
        var current: Variant = property_overrides.get(name, {}).get(str(id), safe.get("value"))
        var row := HBoxContainer.new()
        property_editor_rows.add_child(row)
        var label := Label.new()
        label.text = prop_label + (" *" if property_overrides.get(name, {}).has(str(id)) else "")
        label.tooltip_text = "DX2 property ID " + str(id) + " | " + kind + " | original: " + str(safe.get("value"))
        label.custom_minimum_size.x = 125
        row.add_child(label)
        if kind == "bool":
            var check := CheckBox.new()
            check.button_pressed = bool(current)
            check.toggled.connect(_actor_property_changed.bind(name, id))
            row.add_child(check)
        elif kind in ["byte", "int", "float"]:
            var spin := SpinBox.new()
            spin.min_value = 0.0 if kind == "byte" else -1000000.0
            spin.max_value = 255.0 if kind == "byte" else 1000000.0
            spin.step = 0.01 if kind == "float" else 1.0
            spin.custom_minimum_size.x = 125
            spin.set_value_no_signal(float(current))
            spin.value_changed.connect(_actor_property_changed.bind(name, id))
            row.add_child(spin)
        elif kind == "string":
            var input := LineEdit.new()
            input.text = str(current)
            input.max_length = 512
            input.custom_minimum_size.x = 125
            input.text_submitted.connect(_actor_property_changed.bind(name, id))
            row.add_child(input)
    property_editor_note.text = (str(supported) + " decoded scalar properties; " + str(locked) +
        " complex/unknown properties locked. " +
        str(property_overrides.get(name, {}).size()) + " draft overrides (marked *). " +
        ("Only first 48 matching properties shown. " if shown > 48 else "") +
        "Values are draft metadata, not live gameplay or GMP writes.")
    property_editor_syncing = false


func _actor_property_changed(value: Variant, name: String, id: int) -> void:
    if property_editor_syncing or not actors_by_name.has(name):
        return
    var actor: Dictionary = actors_by_name[name]
    var source := _find_editable_property(actor, id)
    if source.is_empty():
        return
    var kind := str(source.get("type", "")).to_lower()
    var clean: Variant = _validated_scalar(kind, value)
    if clean == null:
        status_label.text = "Invalid actor property value; original and draft unchanged."
        return
    var before := _capture_edit_state()
    var overrides: Dictionary = property_overrides.get(name, {}).duplicate(true)
    if clean == source.get("value"):
        overrides.erase(str(id))
    else:
        overrides[str(id)] = clean
    if overrides.is_empty():
        property_overrides.erase(name)
    else:
        property_overrides[name] = overrides
    property_editor_last_key = ""
    _refresh_actor_property_editor()
    _record_edit("Property " + str(id) + " on " + name, before)
    status_label.text = "Saved actor property " + str(id) + " as preview metadata. Ctrl+Z to undo."


func _reset_actor_property_edits() -> void:
    var name := ""
    var nodes := _selection_nodes()
    if nodes.size() == 1 and actors_by_name.has(str(nodes[0].name)):
        name = str(nodes[0].name)
    elif nodes.is_empty() and not selected_actor.is_empty():
        name = str(selected_actor.get("name", ""))
    if name.is_empty() or not property_overrides.has(name):
        status_label.text = "This actor has no edited scalar property values."
        return
    var before := _capture_edit_state()
    property_overrides.erase(name)
    property_editor_last_key = ""
    _refresh_actor_property_editor()
    _record_edit("Reset actor properties " + name, before)
    status_label.text = "Restored this actor's original property values; Ctrl+Z to undo."


func _serialize_property_edits() -> Array:
    var rows := []
    for name in property_overrides:
        if not actors_by_name.has(name):
            continue
        var actor: Dictionary = actors_by_name[name]
        for key in property_overrides[name]:
            var id := int(key)
            var source: Dictionary = _find_editable_property(actor, id)
            if source.is_empty():
                continue
            var value: Variant = _validated_scalar(str(source.get("type", "")).to_lower(), property_overrides[name][key])
            if value != null and value != source.get("value"):
                rows.append({"actor": name, "export": int(actor.get("export", -1)), "id": id,
                    "type": str(source.get("type")), "value": value})
    return rows


func _validate_property_edits(rows: Variant) -> Variant:
    if typeof(rows) != TYPE_ARRAY or rows.size() > 10000:
        return null
    var result := {}
    var seen := {}
    for row in rows:
        if typeof(row) != TYPE_DICTIONARY:
            return null
        var name := str(row.get("actor", ""))
        if not actors_by_name.has(name):
            return null
        var actor: Dictionary = actors_by_name[name]
        if int(row.get("export", -1)) != int(actor.get("export", -2)):
            return null
        var id := int(row.get("id", -1))
        var key := name + "#" + str(id)
        if seen.has(key):
            return null
        seen[key] = true
        var source := _find_editable_property(actor, id)
        if source.is_empty() or str(row.get("type", "")) != str(source.get("type", "")):
            return null
        var value: Variant = _validated_scalar(str(source["type"]).to_lower(), row.get("value", null))
        if value == null:
            return null
        if value != source.get("value"):
            if not result.has(name):
                result[name] = {}
            result[name][str(id)] = value
    return result


func _inspector_transform_changed(value: float, mode: String, axis: int) -> void:
    if inspector_syncing or not _draft_selected_is_prop():
        return
    var nodes := _selection_nodes()
    if nodes.size() > 1 and mode != "Position":
        return
    var before := _capture_edit_state()
    if mode == "Position":
        var pivot := _selection_pivot()
        var offset := Vector3.ZERO
        offset[axis] = value - pivot[axis]
        for node in nodes:
            node.global_position += offset
    elif mode == "Rotation":
        var angles := nodes[0].global_rotation_degrees
        angles[axis] = value
        nodes[0].global_rotation_degrees = angles
    elif mode == "Scale":
        var new_scale := nodes[0].scale
        new_scale[axis] = maxf(0.001, value)
        nodes[0].scale = new_scale
    _refresh_prop_inspection()
    _record_edit("Inspector " + mode + " " + ["X", "Y", "Z"][axis], before)


func _select_mesh_only(mesh_instance: MeshInstance3D) -> void:
    _clear_selection()
    _add_selection_mesh(mesh_instance)
    _refresh_selection_inspector()
    _sync_actor_list_selection()


func _toggle_selection_mesh(mesh_instance: MeshInstance3D) -> void:
    var name := str(mesh_instance.name)
    # Only editable placed meshes and draft clones can join a group selection.
    if not (actors_by_name.has(name) and meshes_by_actor.has(name)) and not draft_prop_copies.has(name):
        status_label.text = "Ctrl-click supports static mesh actors and draft copies, not BSP geometry."
        return
    if selected_meshes.has(name):
        _remove_selection_mesh(mesh_instance)
    else:
        _add_selection_mesh(mesh_instance)
    _refresh_selection_inspector()
    _sync_actor_list_selection()


func select_actor(actor: Dictionary) -> void:
    _clear_selection()
    selected_actor = actor
    var name := str(actor.get("name", ""))
    if meshes_by_actor.has(name):
        _add_selection_mesh(meshes_by_actor[name])
        _refresh_selection_inspector()
    else:
        selected_diagnostic = _format_actor_diagnostic(actor)
        inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(actor, "  ")
        status_label.text = "Selected " + name + " | " + str(actor.get("class", "Unknown"))
        _refresh_inspector_panel()
    _sync_actor_list_selection()


func _clear_selection() -> void:
    for name in selected_meshes:
        var node: MeshInstance3D = selected_meshes[name]
        if is_instance_valid(node):
            node.material_overlay = selection_original_overlays.get(name, null)
    selected_meshes.clear()
    selection_original_overlays.clear()
    selected_mesh = null
    selected_overlay_original = null
    selected_diagnostic = ""
    selected_actor = {}



## Editable *preview* operations. Native GMP/IBD save remains intentionally disabled.
## Drafts live in user:// and are never written next to retail files.

func _draft_selected_is_prop() -> bool:
    var nodes := _selection_nodes()
    if nodes.is_empty():
        return false
    for node in nodes:
        var name := str(node.name)
        if not draft_prop_copies.has(name) and not (meshes_by_actor.has(name) and actors_by_name.has(name)):
            return false
    return true


## History snapshots contain only preview edits and selected names.
## Native DX2 objects remain represented by the original imported GLB.
func _capture_edit_state() -> Dictionary:
    var moved: Dictionary = {}
    for name in original_mesh_transforms:
        if not meshes_by_actor.has(name) or not actors_by_name.has(name):
            continue
        var node: MeshInstance3D = meshes_by_actor[name]
        if is_instance_valid(node) and node.global_transform != original_mesh_transforms[name]:
            moved[name] = node.global_transform
    var copies: Dictionary = {}
    for name in draft_prop_copies:
        var copy: MeshInstance3D = draft_prop_copies[name]
        if is_instance_valid(copy):
            copies[name] = {
                "source": str(draft_prop_sources.get(name, "")),
                "transform": copy.global_transform,
                "class_template": draft_template_provenance.get(name, {}).duplicate(true),
                "brush": draft_brush_specs.get(name, {}).duplicate(true)
            }
    return {
        "moved": moved,
        "copies": copies,
        "property_edits": property_overrides.duplicate(true),
        "selected": selected_meshes.keys().duplicate(),
        "selected_logical_actor": str(selected_actor.get("name", "")) if selected_meshes.is_empty() else "",
        "next_id": next_prop_copy_id
    }


func _apply_edit_state(state: Dictionary) -> void:
    _clear_selection()
    # Restore baseline first. A reverted move must not linger if absent
    # from the snapshot.
    for name in original_mesh_transforms:
        if meshes_by_actor.has(name):
            var node: MeshInstance3D = meshes_by_actor[name]
            if is_instance_valid(node):
                node.global_transform = original_mesh_transforms[name]
    # Free synchronously so undoing and immediately redoing a duplicate never
    # hits Godot's auto-renamed Node3D names from queued deletions.
    for copy in draft_prop_copies.values():
        if is_instance_valid(copy):
            all_mesh_instances.erase(copy)
            copy.free()
    draft_prop_copies.clear()
    draft_prop_sources.clear()
    draft_template_provenance.clear()
    draft_brush_specs.clear()
    next_prop_copy_id = 1
    var moved: Dictionary = state.get("moved", {})
    for name in moved:
        if meshes_by_actor.has(name) and actors_by_name.has(name):
            var node: MeshInstance3D = meshes_by_actor[name]
            if is_instance_valid(node):
                node.global_transform = moved[name]
    var copies: Dictionary = state.get("copies", {})
    for name in copies:
        var info: Dictionary = copies[name]
        if not str(name).begins_with("DraftProp_"):
            continue
        var source := str(info.get("source", ""))
        if _draft_source_is_valid(source):
            var rebuilt := _new_draft_copy(source, str(name), info["transform"])
            if is_instance_valid(rebuilt):
                var brush: Variant = info.get("brush", {})
                if typeof(brush) == TYPE_DICTIONARY and not brush.is_empty():
                    _set_brush_spec(str(name), brush)
                var prov: Variant = info.get("class_template", {})
                if typeof(prov) == TYPE_DICTIONARY and _valid_template_provenance(prov, source):
                    if not prov.is_empty():
                        draft_template_provenance[str(name)] = prov.duplicate(true)
    next_prop_copy_id = max(1, int(state.get("next_id", 1)))
    property_overrides = state.get("property_edits", {}).duplicate(true)
    for name in state.get("selected", []):
        var node: MeshInstance3D = null
        if draft_prop_copies.has(name):
            node = draft_prop_copies[name]
        elif meshes_by_actor.has(name) and actors_by_name.has(name):
            node = meshes_by_actor[name]
        if is_instance_valid(node):
            _add_selection_mesh(node)
    if _selection_nodes().is_empty() and actors_by_name.has(str(state.get("selected_logical_actor", ""))):
        selected_actor = actors_by_name[str(state["selected_logical_actor"])]
        selected_diagnostic = _format_actor_diagnostic(selected_actor)
        inspector.text = selected_diagnostic + "\n\n--- ORIGINAL ACTOR PROPERTIES ---\n" + JSON.stringify(selected_actor, "  ")
        _refresh_inspector_panel()
    else:
        _refresh_selection_inspector()
    _sync_actor_list_selection()
    _refresh_hierarchy()
    _update_gizmo_pose()


func _refresh_history_buttons() -> void:
    if undo_button != null:
        undo_button.disabled = undo_stack.is_empty()
        undo_button.tooltip_text = "Ctrl+Z" if undo_stack.is_empty() else "Ctrl+Z: " + str(undo_stack.back()["label"])
    if redo_button != null:
        redo_button.disabled = redo_stack.is_empty()
        redo_button.tooltip_text = "Ctrl+Y / Ctrl+Shift+Z" if redo_stack.is_empty() else "Ctrl+Y: " + str(redo_stack.back()["label"])


func _record_edit(label: String, before: Dictionary) -> void:
    var after := _capture_edit_state()
    # Selection changes alone do not count as edits.
    if before.get("moved") == after.get("moved") and before.get("copies") == after.get("copies") and before.get("property_edits", {}) == after.get("property_edits", {}):
        return
    undo_stack.append({"label": label, "before": before, "after": after})
    if undo_stack.size() > HISTORY_LIMIT:
        undo_stack.pop_front()
    redo_stack.clear()
    _refresh_history_buttons()
    if before.get("copies") != after.get("copies"):
        _refresh_hierarchy()


func _undo_edit() -> void:
    if gizmo_drag_active:
        _finish_gizmo_drag()
    if undo_stack.is_empty():
        return
    var item: Dictionary = undo_stack.pop_back()
    _apply_edit_state(item["before"])
    redo_stack.append(item)
    _refresh_history_buttons()
    status_label.text = "Undo: " + str(item["label"]) + " (preview draft only)."


func _redo_edit() -> void:
    if gizmo_drag_active:
        _finish_gizmo_drag()
    if redo_stack.is_empty():
        return
    var item: Dictionary = redo_stack.pop_back()
    _apply_edit_state(item["after"])
    undo_stack.append(item)
    _refresh_history_buttons()
    status_label.text = "Redo: " + str(item["label"]) + " (preview draft only)."


func _restore_all_edits() -> void:
    if scene_root == null:
        status_label.text = "Load a map before restoring edits."
        return
    var before := _capture_edit_state()
    _apply_edit_state({"moved": {}, "copies": {}, "property_edits": {}, "selected": [], "next_id": 1})
    _record_edit("Restore All", before)
    # Overwrite the sidecar with an empty draft. Undo restores the session's
    # preview state, but the user must Save draft to persist the undo.
    _save_prop_draft()
    status_label.text = "All prop edits restored to the imported map. Saved draft cleared. Ctrl+Z can undo this session."


func _finish_gizmo_drag() -> void:
    if not gizmo_drag_active:
        return
    gizmo_drag_active = false
    _record_edit("Drag " + editor_tool, gizmo_undo_before)
    gizmo_undo_before.clear()


func _update_brush_form(index: int) -> void:
    if brush_kind_control == null:
        return
    var index_safe := clampi(index, 0, BrushGeometry.TYPES.size() - 1)
    var spec: Dictionary = BrushGeometry.default_spec(BrushGeometry.TYPES[index_safe])
    for axis in range(3):
        brush_size_controls[axis].set_value_no_signal(float(spec["size"][axis]))
    brush_steps_control.set_value_no_signal(float(spec["steps"]))
    brush_steps_control.editable = spec["kind"] == "Stairs"


func _place_preview_brush() -> void:
    if scene_root == null:
        status_label.text = "Load a map before constructing a preview brush."
        return
    var kind: String = str(BrushGeometry.TYPES[brush_kind_control.selected])
    var size := []
    for field in brush_size_controls:
        size.append(float(field.value))
    var spec: Dictionary = BrushGeometry.validate({
        "kind": kind, "size": size, "steps": int(brush_steps_control.value)
    })
    if spec.is_empty():
        status_label.text = "Invalid brush dimensions or step count."
        return
    var before := _capture_edit_state()
    var name := "DraftProp_" + str(next_prop_copy_id)
    next_prop_copy_id += 1
    var draft := _new_draft_copy("Brush::" + kind, name,
                               Transform3D(Basis.IDENTITY, camera_target))
    if not is_instance_valid(draft):
        return
    _set_brush_spec(name, spec)
    _clear_selection()
    _add_selection_mesh(draft)
    _refresh_selection_inspector()
    _record_edit("Create " + kind + " preview brush", before)
    status_label.text = "Created " + kind + " preview brush. No DX2 BSP/collision was written."


func _set_brush_spec(name: String, raw: Variant) -> bool:
    if not draft_prop_copies.has(name):
        return false
    var spec: Dictionary = BrushGeometry.validate(raw)
    if spec.is_empty() or str(draft_prop_sources.get(name, "")) != "Brush::" + str(spec["kind"]):
        return false
    var mesh: Mesh = BrushGeometry.build_mesh(spec)
    if mesh == null:
        return false
    var node: MeshInstance3D = draft_prop_copies[name]
    node.mesh = mesh
    var surface_material := StandardMaterial3D.new()
    surface_material.albedo_color = Color(0.36, 0.72, 0.82, 0.75)
    surface_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    surface_material.cull_mode = BaseMaterial3D.CULL_DISABLED
    node.material_override = surface_material
    draft_brush_specs[name] = spec
    pick_faces_by_mesh.clear()
    return true


func _refresh_brush_inspector() -> void:
    if brush_inspector_panel == null:
        return
    var nodes := _selection_nodes()
    var show := nodes.size() == 1 and draft_brush_specs.has(str(nodes[0].name)) if nodes.size() == 1 else false
    brush_inspector_panel.visible = show
    if not show:
        return
    var spec: Dictionary = draft_brush_specs[str(nodes[0].name)]
    brush_inspector_syncing = true
    for axis in range(3):
        brush_inspector_sizes[axis].set_value_no_signal(float(spec["size"][axis]))
    brush_inspector_steps.set_value_no_signal(float(spec["steps"]))
    brush_inspector_steps.editable = spec["kind"] == "Stairs"
    brush_inspector_syncing = false


func _change_brush_dimension(value: float, axis: int) -> void:
    if brush_inspector_syncing:
        return
    var nodes := _selection_nodes()
    if nodes.size() != 1:
        return
    var name := str(nodes[0].name)
    if not draft_brush_specs.has(name):
        return
    var spec: Dictionary = draft_brush_specs[name].duplicate(true)
    spec["size"][axis] = value
    var before := _capture_edit_state()
    if _set_brush_spec(name, spec):
        _refresh_prop_inspection()
        _record_edit("Resize brush " + name, before)


func _change_brush_steps(value: float) -> void:
    if brush_inspector_syncing:
        return
    var nodes := _selection_nodes()
    if nodes.size() != 1:
        return
    var name := str(nodes[0].name)
    if not draft_brush_specs.has(name):
        return
    var spec: Dictionary = draft_brush_specs[name].duplicate(true)
    spec["steps"] = int(value)
    var before := _capture_edit_state()
    if _set_brush_spec(name, spec):
        _refresh_prop_inspection()
        _record_edit("Edit stair count " + name, before)


func _draft_source_name(instance: MeshInstance3D) -> String:
    var name := str(instance.name)
    if draft_prop_sources.has(name):
        return str(draft_prop_sources[name])
    if meshes_by_actor.has(name) and actors_by_name.has(name):
        return name
    return ""

func _new_draft_copy(source_name: String, copy_name: String, world_transform: Transform3D) -> MeshInstance3D:
    if draft_prop_copies.has(copy_name) or not _draft_source_is_valid(source_name):
        return null
    var mesh: Mesh = null
    var source: MeshInstance3D = null
    if source_name.begins_with("Brush::"):
        var kind := source_name.trim_prefix("Brush::")
        mesh = BrushGeometry.build_mesh(BrushGeometry.default_spec(kind))
    elif source_name.begins_with("AssetMesh::"):
        var resource_name := source_name.trim_prefix("AssetMesh::")
        if not _load_asset_mesh(resource_name):
            return null
        mesh = asset_mesh_resources[resource_name]
    else:
        source = meshes_by_actor[source_name]
        if not is_instance_valid(source):
            return null
        mesh = source.mesh
    if mesh == null:
        return null
    var duplicate := MeshInstance3D.new()
    duplicate.name = copy_name
    duplicate.mesh = mesh
    if is_instance_valid(source):
        duplicate.material_override = source.material_override
        duplicate.cast_shadow = source.cast_shadow
    world_root.add_child(duplicate)
    duplicate.global_transform = world_transform
    draft_prop_copies[copy_name] = duplicate
    draft_prop_sources[copy_name] = source_name
    if source_name.begins_with("Brush::"):
        _set_brush_spec(copy_name, BrushGeometry.default_spec(source_name.trim_prefix("Brush::")))
    all_mesh_instances.append(duplicate)
    return duplicate

func _duplicate_selected_prop() -> void:
    if not _draft_selected_is_prop():
        status_label.text = "Select a rendered static mesh actor first (BSP cannot be duplicated)."
        return
    var history_before := _capture_edit_state()
    var originals := _selection_nodes()
    var copies: Array[MeshInstance3D] = []
    for node in originals:
        var source := _draft_source_name(node)
        if source.is_empty():
            continue
        var name := "DraftProp_" + str(next_prop_copy_id)
        next_prop_copy_id += 1
        var new_copy := _new_draft_copy(source, name, node.global_transform)
        if is_instance_valid(new_copy):
            if draft_brush_specs.has(str(node.name)):
                _set_brush_spec(name, draft_brush_specs[str(node.name)])
            if draft_template_provenance.has(str(node.name)):
                draft_template_provenance[name] = draft_template_provenance[str(node.name)].duplicate(true)
            copies.append(new_copy)
    if copies.is_empty():
        return
    _clear_selection()
    for node in copies:
        _add_selection_mesh(node)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    _record_edit("Duplicate " + str(copies.size()) + " prop(s)", history_before)
    status_label.text = "Duplicated " + str(copies.size()) + " prop(s). Move the copies, then Save draft."


func _refresh_prop_inspection() -> void:
    _refresh_selection_inspector()
    if not _selection_nodes().is_empty():
        inspector.text += "\n\n--- PREVIEW EDIT ---\nGroup pivot: " + str(_selection_pivot())
        status_label.text = "Preview modified " + str(_selection_nodes().size()) + " prop(s). Save draft to keep changes."


func _move_selected_prop(axis: Vector3) -> void:
    if not _draft_selected_is_prop():
        status_label.text = "Select one or more rendered props (not BSP)."
        return
    var history_before := _capture_edit_state()
    var delta := axis * float(prop_edit_step.value)
    for node in _selection_nodes():
        node.global_position += delta
    _refresh_prop_inspection()
    _record_edit("Move " + str(_selection_nodes().size()) + " prop(s)", history_before)


func _rotate_selected_prop(angle: float) -> void:
    if not _draft_selected_is_prop():
        status_label.text = "Select one or more rendered props to rotate."
        return
    var history_before := _capture_edit_state()
    var pivot := _selection_pivot()
    var turn := Basis(Vector3.UP, deg_to_rad(angle))
    for node in _selection_nodes():
        var pose := node.global_transform
        pose.origin = pivot + turn * (pose.origin - pivot)
        pose.basis = turn * pose.basis
        node.global_transform = pose
    _refresh_prop_inspection()
    _record_edit("Rotate " + str(_selection_nodes().size()) + " prop(s)", history_before)


func _reset_selected_prop() -> void:
    if not _draft_selected_is_prop():
        return
    var history_before := _capture_edit_state()
    var nodes := _selection_nodes()
    _clear_selection()
    var restored: Array[MeshInstance3D] = []
    var removed := 0
    for node in nodes:
        var name := str(node.name)
        if draft_prop_copies.has(name):
            draft_prop_copies.erase(name)
            draft_prop_sources.erase(name)
            draft_template_provenance.erase(name)
            draft_brush_specs.erase(name)
            all_mesh_instances.erase(node)
            node.free()
            removed += 1
        elif original_mesh_transforms.has(name):
            node.global_transform = original_mesh_transforms[name]
            restored.append(node)
    for node in restored:
        _add_selection_mesh(node)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    _record_edit("Reset " + str(restored.size()) + " / delete " + str(removed), history_before)
    status_label.text = "Restored " + str(restored.size()) + " original(s), deleted " + str(removed) + " copy/copies. Save draft to persist."



func _draft_file_path() -> String:
    if current_folder.is_empty():
        return ""
    var folder := ProjectSettings.globalize_path("user://prop_drafts")
    var result := DirAccess.make_dir_recursive_absolute(folder)
    if result != OK:
        return ""
    return folder.path_join(current_folder.sha256_text() + ".json")

func _transform_to_array(xform: Transform3D) -> Array:
    return [
        xform.basis.x.x, xform.basis.x.y, xform.basis.x.z,
        xform.basis.y.x, xform.basis.y.y, xform.basis.y.z,
        xform.basis.z.x, xform.basis.z.y, xform.basis.z.z,
        xform.origin.x, xform.origin.y, xform.origin.z
    ]

func _array_to_transform(values: Variant) -> Variant:
    if typeof(values) != TYPE_ARRAY or values.size() != 12:
        return null
    var safe: Array = []
    for value in values:
        if typeof(value) not in [TYPE_FLOAT, TYPE_INT]:
            return null
        var number := float(value)
        if not is_finite(number) or abs(number) > 1000000.0:
            return null
        safe.append(number)
    return Transform3D(
        Vector3(safe[0], safe[1], safe[2]),
        Vector3(safe[3], safe[4], safe[5]),
        Vector3(safe[6], safe[7], safe[8]),
        Vector3(safe[9], safe[10], safe[11])
    )

func _open_native_verify_dialog() -> void:
    if (last_gmp_path.is_empty() or not FileAccess.file_exists(last_gmp_path)
        or current_source_map_name.to_lower() != last_gmp_path.get_file().to_lower()):
        status_label.text = "Open the original GMP map before verifying an exported copy."
        return
    if native_export_thread != null or build_thread != null:
        status_label.text = "Another native map operation is still active."
        return
    gmp_verify_dialog.popup_centered_ratio(0.75)


func _verify_native_gmp_file(output_path: String) -> void:
    if native_export_thread != null:
        return
    var backend := ProjectSettings.globalize_path("res://backend/dx2_native_save_as.py")
    if not FileAccess.file_exists(backend) or not FileAccess.file_exists(output_path):
        status_label.text = "Cannot verify: GMP copy or writer backend not found."
        return
    native_export_thread = Thread.new()
    var err := native_export_thread.start(
        _run_native_verify.bind(backend, last_gmp_path, output_path))
    if err != OK:
        native_export_thread = null
        status_label.text = "Failed to start native GMP verification."
        return
    status_label.text = "Verifying exported GMP byte-for-byte against its source and manifest..."


func _run_native_verify(script: String, source: String, output_path: String) -> void:
    var args := PackedStringArray([
        script, "--source", source, "--output", output_path, "--verify"
    ])
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        var launcher := PackedStringArray(["-3"])
        launcher.append_array(args)
        output.clear()
        code = OS.execute("py", launcher, output, true)
    call_deferred("_native_verify_finished", code, "\n".join(output))


func _native_verify_finished(code: int, output: String) -> void:
    if native_export_thread != null:
        native_export_thread.wait_to_finish()
        native_export_thread = null
    var result: Variant = JSON.parse_string(output.strip_edges())
    if code == 0 and typeof(result) == TYPE_DICTIONARY and result.get("schema") == "DX2Ed-native-verify-report-v1":
        var count := int(result.get("translated_existing_actors", 0))
        var changed := int(result.get("changed_bytes", 0))
        status_label.text = "GMP binary verification PASSED: " + str(count) + " moved actors, " + str(changed) + " changed bytes. Game load NOT tested."
        if native_audit_dialog != null:
            native_audit_dialog.dialog_text = (
                "GMP binary verification PASSED" +
                "\nEdited actors: " + str(count) +
                "\nChanged bytes: " + str(changed) +
                "\nOutput: " + str(result.get("output", "")) +
                "\n\nThe GMP is structurally consistent with the original." +
                "\nActual retail game loading and collision are NOT verified."
            )
            native_audit_dialog.popup_centered(Vector2i(680, 360))
        return
    var message := str(result.get("message", "Unrecognized manifest or GMP binary mismatch.")) if typeof(result) == TYPE_DICTIONARY else output.strip_edges().substr(0, 240)
    status_label.text = "GMP binary verification FAILED: " + message


func _audit_current_native_map() -> void:
    if native_export_thread != null or build_thread != null:
        status_label.text = "A map operation is already active."
        return
    var script := ProjectSettings.globalize_path("res://backend/dx2_native_save_as.py")
    var actors_path := current_folder.path_join("actors.json")
    if (last_gmp_path.is_empty() or not FileAccess.file_exists(last_gmp_path)
        or current_source_map_name.to_lower() != last_gmp_path.get_file().to_lower()
        or not FileAccess.file_exists(actors_path) or not FileAccess.file_exists(script)):
        status_label.text = "Audit requires the original GMP and its matching imported actors.json."
        return
    native_export_thread = Thread.new()
    var err := native_export_thread.start(_run_native_audit.bind(script, last_gmp_path, actors_path))
    if err != OK:
        native_export_thread = null
        status_label.text = "Could not start native map audit."
        return
    status_label.text = "Inspecting DX2 GMP actor Location encodings (read-only)..."


func _run_native_audit(script: String, source: String, actors_path: String) -> void:
    var args := PackedStringArray([script, "--source", source, "--actors", actors_path, "--audit"])
    var output: Array = []
    var code := OS.execute("python", args, output, true)
    if code == -1:
        var py_args := PackedStringArray(["-3"])
        py_args.append_array(args)
        output.clear()
        code = OS.execute("py", py_args, output, true)
    call_deferred("_native_audit_finished", code, "\n".join(output))


func _native_audit_finished(code: int, output: String) -> void:
    if native_export_thread != null:
        native_export_thread.wait_to_finish()
        native_export_thread = null
    var result: Variant = JSON.parse_string(output.strip_edges())
    if code == 0 and typeof(result) == TYPE_DICTIONARY and result.get("schema") == "DX2Ed-native-location-audit-v1":
        var eligible := int(result.get("native_location_candidates", 0))
        var candidates := int(result.get("rendered_static_mesh_candidates", 0))
        status_label.text = "Native Location audit: " + str(eligible) + " / " + str(candidates) + " static-mesh actors have writable Location tags. Game load unverified."
        var audit_text := (
            "Map: " + str(result.get("source", "")) +
            "\nLocation candidates: " + str(eligible) + " / " + str(candidates) +
            "\nUnsupported: " + str(result.get("unsupported_candidates", 0)) +
            "\nReasons: " + JSON.stringify(result.get("reasons", {})) +
            "\n\nThis checks existing serialized source fields only." +
            "\nNative gameplay loading and collision are NOT verified."
        )
        if native_audit_dialog != null:
            native_audit_dialog.dialog_text = audit_text
            native_audit_dialog.popup_centered(Vector2i(680, 350))
        return
    var message := str(result.get("message", "Check original GMP and matching actor metadata.")) if typeof(result) == TYPE_DICTIONARY else output.strip_edges().substr(0, 240)
    status_label.text = "Native location audit failed: " + message



## Only one existing StaticMeshActor may be cloned natively at a time.
## Normal Duplicate continues producing preview drafts until this explicit Save As.
## A pure translation of its unmodified imported pose is the only supported edit.
const NATIVE_CLONE_UNREAL_METRES := 0.01905

func _native_clone_draft_plan() -> Dictionary:
    if (scene_root == null or draft_prop_copies.size() != 1
        or not property_overrides.is_empty() or not draft_brush_specs.is_empty()
        or not draft_template_provenance.is_empty()):
        return {}
    # Native clone is not a combined edit mode. Other original transforms
    # must stay at the exact imported poses; they are not silently discarded.
    for name in original_mesh_transforms:
        if not meshes_by_actor.has(name):
            continue
        var original_node: MeshInstance3D = meshes_by_actor[name]
        if (is_instance_valid(original_node)
            and not original_node.global_transform.is_equal_approx(original_mesh_transforms[name])):
            return {}
    var draft_name := str(draft_prop_copies.keys()[0])
    var copy: MeshInstance3D = draft_prop_copies[draft_name]
    var original_name := str(draft_prop_sources.get(draft_name, ""))
    if (not is_instance_valid(copy) or not actors_by_name.has(original_name)
        or not meshes_by_actor.has(original_name)
        or not original_mesh_transforms.has(original_name)):
        return {}
    var original_actor: Dictionary = actors_by_name[original_name]
    if (str(original_actor.get("class", "")) != "StaticMeshActor"
        or int(original_actor.get("export", -1)) < 1):
        return {}
    var base_pose: Transform3D = original_mesh_transforms[original_name]
    if not copy.global_transform.basis.is_equal_approx(base_pose.basis):
        return {}  # Rotation/scale/preview auto-roll changes cannot be serialized.
    var delta_world := copy.global_position - base_pose.origin
    if not delta_world.is_finite() or delta_world.length_squared() <= 0.00000001:
        return {}
    # GLB basis: X=UE X; Y=UE Z; Z=UE Y. Never infer from mesh bounds.
    var delta_unreal := Vector3(
        delta_world.x / NATIVE_CLONE_UNREAL_METRES,
        delta_world.z / NATIVE_CLONE_UNREAL_METRES,
        delta_world.y / NATIVE_CLONE_UNREAL_METRES
    )
    if (not delta_unreal.is_finite()
        or abs(delta_unreal.x) > 4096.0
        or abs(delta_unreal.y) > 4096.0
        or abs(delta_unreal.z) > 4096.0):
        return {}
    return {
        "actor": original_name, "export": int(original_actor["export"]),
        "draft_name": draft_name, "delta": [delta_unreal.x, delta_unreal.y, delta_unreal.z]
    }


func _native_clone_source_ready() -> bool:
    return (build_thread == null and native_export_thread == null
        and not last_gmp_path.is_empty()
        and FileAccess.file_exists(last_gmp_path)
        and last_gmp_path.get_file().to_lower() == current_source_map_name.to_lower()
        and source_gamesys_sha256.length() == 64
        and FileAccess.get_sha256(last_gmp_path) == source_gamesys_sha256)


func _native_clone_error_reason(response: String) -> String:
    var parsed: Variant = JSON.parse_string(response.strip_edges())
    if typeof(parsed) == TYPE_DICTIONARY:
        return str(parsed.get("reason", parsed.get("message", "Unknown clone writer refusal."))).substr(0, 480)
    # A script/import crash might still be a traditional Python traceback.
    # Show the FINAL exception line, not the useless first traceback line.
    var lines := response.strip_edges().split("\n")
    return lines[lines.size() - 1].strip_edges().substr(0, 480) if lines.size() > 0 else "Python clone writer unavailable."


func _native_clone_check_actor(script: String, plan: Dictionary) -> Dictionary:
    # Read-only source-verified eligibility check BEFORE showing Save As.
    # The writer independently repeats all checks when exporting.
    var args := PackedStringArray([
        script, last_gmp_path,
        "--source-sha256", source_gamesys_sha256,
        "--check-actor",
        "--actor-export", str(plan["export"]),
        "--actor-name", str(plan["actor"])
    ])
    var stdout: Array = []
    var code := OS.execute("python", args, stdout, true)
    if code == -1:
        var pyargs := PackedStringArray(["-3"])
        pyargs.append_array(args)
        stdout.clear()
        code = OS.execute("py", pyargs, stdout, true)
    var response := "\n".join(stdout).strip_edges()
    var parsed: Variant = JSON.parse_string(response)
    if (code == 0 and typeof(parsed) == TYPE_DICTIONARY
        and parsed.get("schema") == "DX2Ed-experimental-native-prop-duplicate-v1"
        and parsed.get("status") == "clone-source-eligible"
        and str(parsed.get("actor", "")) == str(plan["actor"])
        and int(parsed.get("export", -1)) == int(plan["export"])
        and str(parsed.get("source_sha256", "")) == source_gamesys_sha256):
        return {"eligible": true,
            "source_latent_action": int(parsed.get("source_latent_action", 0)),
            "state_normalized": parsed.get("new_actor_state_will_be_normalized", false)}
    return {"eligible": false, "reason": _native_clone_error_reason(response)}


func _open_native_clone_dialog() -> void:
    _finish_gizmo_drag()
    native_clone_pending.clear()
    if not _native_clone_source_ready():
        status_label.text = "Clone Save As refused: original source GMP/hash unavailable or another operation is active."
        return
    var plan := _native_clone_draft_plan()
    if plan.is_empty():
        status_label.text = "Clone Save As supports exactly one moved StaticMeshActor preview copy, with no rotation, scaling, other moves, brushes or property edits."
        return
    var backend := ProjectSettings.globalize_path("res://../package_writer/dx2_actor_clone_probe.py")
    if not FileAccess.file_exists(backend):
        status_label.text = "Experimental native clone writer is unavailable."
        return
    var preflight := _native_clone_check_actor(backend, plan)
    if preflight.get("eligible", false) != true:
        var reason := str(preflight.get("reason", "Actor cannot be cloned safely."))
        status_label.text = "This prop cannot be cloned natively: " + reason
        if native_audit_dialog != null:
            native_audit_dialog.title = "Original actor is not eligible for native duplication"
            native_audit_dialog.dialog_text = (
                "Actor: " + str(plan["actor"]) + " (export " + str(plan["export"]) + ")"
                + "\n\n" + reason
                + "\n\nNothing was saved or modified."
                + "\nFor the first test, choose StaticMeshActor__611, the previously proven table."
            )
            native_audit_dialog.popup_centered(Vector2i(720, 310))
        return
    status_label.text = (
        "Source actor verified. A new static prop will be created with neutralized "
        + "native state; source actor and original GMP unchanged."
    )
    native_clone_dialog.current_file = last_gmp_path.get_file()
    native_clone_dialog.popup_centered_ratio(0.75)


func _stage_native_clone_export(destination: String) -> void:
    native_clone_pending.clear()
    if not _native_clone_source_ready():
        status_label.text = "Clone Save As refused: source GMP or import hash changed."
        return
    var plan := _native_clone_draft_plan()
    if plan.is_empty() or destination.get_file().to_lower() != current_source_map_name.to_lower():
        status_label.text = "Clone Save As refused: invalid draft or target map filename."
        return
    plan["source_sha256"] = source_gamesys_sha256
    plan["source"] = last_gmp_path
    plan["destination"] = destination
    native_clone_pending = plan
    native_clone_confirmation.dialog_text = (
        "EXPERIMENTAL one-actor GMP copy ONLY. Never install automatically."
        + "\nOriginal actor: " + str(plan["actor"])
        + "\nOriginal export: " + str(plan["export"])
        + "\nUnreal translation: " + str(plan["delta"])
        + "\n\nNew export: latent/script action DWORD reset to zero."
        + "\nOriginal actor and its bytes will not be changed."
        + "\nOutput: " + destination
        + "\n\nThe Python writer refuses game Maps folders, overwrites, and"
        + " non-byte-exact original source hashes."
        + "\nOriginal retail map stays unchanged. Runtime still requires testing."
    )
    native_clone_confirmation.popup_centered(Vector2i(720, 370))


func _execute_native_clone_export() -> void:
    if native_clone_pending.is_empty() or not _native_clone_source_ready():
        native_clone_pending.clear()
        status_label.text = "Clone Save As refused: source or operation changed before confirmation."
        return
    var current_plan := _native_clone_draft_plan()
    var frozen := native_clone_pending.duplicate(true)
    native_clone_pending.clear()
    if (current_plan.is_empty()
        or current_plan != {
            "actor": frozen["actor"], "export": frozen["export"],
            "draft_name": frozen["draft_name"], "delta": frozen["delta"]
        }
        or str(frozen["source"]) != last_gmp_path
        or str(frozen["source_sha256"]) != source_gamesys_sha256):
        status_label.text = "Clone Save As refused: preview clone or original source changed."
        return
    var script := ProjectSettings.globalize_path("res://../package_writer/dx2_actor_clone_probe.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Clone Save As refused: Python clone script missing."
        return
    native_export_thread = Thread.new()
    var error := native_export_thread.start(_run_native_clone_export.bind(script, frozen))
    if error != OK:
        native_export_thread = null
        status_label.text = "Unable to start native prop clone worker."
        return
    status_label.text = "Verifying one native StaticMeshActor clone and writing isolated GMP..."


func _run_native_clone_export(script: String, frozen: Dictionary) -> void:
    var delta: Array = frozen["delta"]
    var args := PackedStringArray([
        script, str(frozen["source"]),
        "--source-sha256", str(frozen["source_sha256"]),
        "--actor-export", str(frozen["export"]),
        "--actor-name", str(frozen["actor"]),
        "--dx", str(delta[0]), "--dy", str(delta[1]), "--dz", str(delta[2]),
        "--output", str(frozen["destination"])
    ])
    var stdout: Array = []
    var code := OS.execute("python", args, stdout, true)
    if code == -1:
        var pyargs := PackedStringArray(["-3"])
        pyargs.append_array(args)
        stdout.clear()
        code = OS.execute("py", pyargs, stdout, true)
    call_deferred("_native_clone_export_finished", code, "\n".join(stdout))


func _native_clone_export_finished(code: int, response: String) -> void:
    if native_export_thread != null:
        native_export_thread.wait_to_finish()
        native_export_thread = null
    var result: Variant = JSON.parse_string(response.strip_edges())
    if (code == 0 and typeof(result) == TYPE_DICTIONARY
        and result.get("schema") == "DX2Ed-experimental-native-prop-duplicate-v1"
        and result.get("status") == "isolated-GMP-created-runtime-unverified"
        and int(result.get("new_export_count", -1)) == int(result.get("original_export_count", 0)) + 1
        and int(result.get("level_actor_count_after", -1)) == int(result.get("level_actor_count_before", 0)) + 1
        and result.get("clone_frame_normalized") == true
        and result.get("clone_payload_provenance_verified") == true
        and int(result.get("clone_latent_action", -1)) == 0
        and result.get("original_bytes_unchanged") == true):
        status_label.text = (
            "Experimental native clone GMP saved: " + str(result.get("output_file", ""))
            + " | New actor: " + str(result.get("new_actor_name", ""))
            + " | Verify in a backed-up retail test and restore original."
        )
        return
    status_label.text = "Native clone Save As refused: " + _native_clone_error_reason(response)


## Experimental multiple static props: source-bound, translation-only.
## Kept separate from existing-actor Save As and one-prop path.
func _native_multi_clone_draft_plan() -> Array:
    var rows := []
    if (scene_root == null or draft_prop_copies.size() < 2
        or draft_prop_copies.size() > 8 or not property_overrides.is_empty()
        or not draft_brush_specs.is_empty()
        or not draft_template_provenance.is_empty()):
        return rows
    for name in original_mesh_transforms:
        if meshes_by_actor.has(name):
            var original_node: MeshInstance3D = meshes_by_actor[name]
            if (is_instance_valid(original_node)
                and not original_node.global_transform.is_equal_approx(original_mesh_transforms[name])):
                return []
    var keys := draft_prop_copies.keys()
    keys.sort()
    for name in keys:
        var node: MeshInstance3D = draft_prop_copies[name]
        var original_name := str(draft_prop_sources.get(name, ""))
        if (not is_instance_valid(node) or not actors_by_name.has(original_name)
            or not meshes_by_actor.has(original_name)
            or not original_mesh_transforms.has(original_name)):
            return []
        var actor: Dictionary = actors_by_name[original_name]
        if (str(actor.get("class", "")) != "StaticMeshActor"
            or int(actor.get("export", -1)) < 1):
            return []
        var base_pose: Transform3D = original_mesh_transforms[original_name]
        if not node.global_transform.basis.is_equal_approx(base_pose.basis):
            return []
        var shift := node.global_position - base_pose.origin
        if not shift.is_finite() or shift.length_squared() <= 0.00000001:
            return []
        var unreal := [
            shift.x / NATIVE_CLONE_UNREAL_METRES,
            shift.z / NATIVE_CLONE_UNREAL_METRES,
            shift.y / NATIVE_CLONE_UNREAL_METRES
        ]
        for component in unreal:
            if not is_finite(float(component)) or abs(float(component)) > 4096.0:
                return []
        rows.append({"actor": original_name, "export": int(actor["export"]), "delta": unreal})
    return rows


func _open_native_multi_dialog() -> void:
    _finish_gizmo_drag()
    native_multi_pending.clear()
    if not _native_clone_source_ready():
        status_label.text = "Multi Duplicate refused: original map/hash unavailable or writer busy."
        return
    var plan := _native_multi_clone_draft_plan()
    if plan.size() < 2:
        status_label.text = "Multi Duplicate needs 2..8 moved original StaticMeshActor copies; no rotation, scaling, original moves or other edits."
        return
    var script := ProjectSettings.globalize_path("res://../package_writer/dx2_actor_multi_clone_probe.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Multi Duplicate Python writer is missing."
        return
    # Verify every source independently before requesting a filename.
    var checker := ProjectSettings.globalize_path("res://../package_writer/dx2_actor_clone_probe.py")
    if not FileAccess.file_exists(checker):
        status_label.text = "Native actor eligibility preflight is missing."
        return
    for row in plan:
        var verdict := _native_clone_check_actor(checker, row)
        if not verdict.get("eligible", false):
            status_label.text = "Multi Duplicate blocked " + str(row["actor"]) + ": " + str(verdict.get("reason", "Unverified source actor"))
            return
    native_multi_dialog.current_file = last_gmp_path.get_file()
    native_multi_dialog.popup_centered_ratio(0.75)


func _stage_native_multi_export(destination: String) -> void:
    native_multi_pending.clear()
    if not _native_clone_source_ready():
        status_label.text = "Multi Duplicate refused: original map changed."
        return
    var rows := _native_multi_clone_draft_plan()
    if (rows.size() < 2
        or destination.get_file().to_lower() != last_gmp_path.get_file().to_lower()):
        status_label.text = "Multi Duplicate refused: invalid preview copies or output filename."
        return
    native_multi_pending = {
        "copies": rows.duplicate(true), "source": last_gmp_path,
        "source_sha256": source_gamesys_sha256, "destination": destination
    }
    native_multi_confirmation.dialog_text = (
        "Create " + str(rows.size()) + " new StaticMeshActor exports in ONE GMP?"
        + "\n\nOnly new actors receive normalized latent state and translated Location."
        + "\nNo rotation/scaling/original actor changes."
        + "\n\nIsolated output: " + destination
        + "\n\nNo game installation is modified automatically."
        + "\nThe original map remains unchanged and each clone is independently verified."
    )
    native_multi_confirmation.popup_centered(Vector2i(730, 340))


func _execute_native_multi_export() -> void:
    if native_multi_pending.is_empty() or not _native_clone_source_ready():
        native_multi_pending.clear()
        status_label.text = "Multi Duplicate refused: source or writer state changed."
        return
    var frozen := native_multi_pending.duplicate(true)
    native_multi_pending.clear()
    if (str(frozen["source"]) != last_gmp_path
        or str(frozen["source_sha256"]) != source_gamesys_sha256
        or _native_multi_clone_draft_plan() != frozen["copies"]):
        status_label.text = "Multi Duplicate refused: map or preview copies changed during confirmation."
        return
    var script := ProjectSettings.globalize_path("res://../package_writer/dx2_actor_multi_clone_probe.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Multi Duplicate script unavailable."
        return
    var plan_path := OS.get_user_data_dir().path_join("native_multi_clone_plan.json")
    var plan_file := FileAccess.open(plan_path, FileAccess.WRITE)
    if plan_file == null:
        status_label.text = "Multi Duplicate could not write private temporary plan."
        return
    plan_file.store_string(JSON.stringify({
        "schema": "DX2Ed-experimental-multi-prop-duplicate-v1",
        "copies": frozen["copies"]
    }))
    plan_file.close()
    frozen["plan_path"] = plan_path
    native_export_thread = Thread.new()
    var started := native_export_thread.start(_run_native_multi_export.bind(script, frozen))
    if started != OK:
        native_export_thread = null
        status_label.text = "Multi Duplicate could not start Python worker."
        return
    status_label.text = "Verifying and writing " + str(frozen["copies"].size()) + " new static props into one isolated GMP..."


func _run_native_multi_export(script: String, frozen: Dictionary) -> void:
    var args := PackedStringArray([
        script, str(frozen["source"]), "--source-sha256", str(frozen["source_sha256"]),
        "--copies-json", str(frozen["plan_path"]), "--output", str(frozen["destination"])
    ])
    var output: Array = []
    var status := OS.execute("python", args, output, true)
    if status == -1:
        var pyargs := PackedStringArray(["-3"])
        pyargs.append_array(args)
        output.clear()
        status = OS.execute("py", pyargs, output, true)
    call_deferred("_native_multi_export_finished", status, "\n".join(output), str(frozen["plan_path"]))


func _native_multi_export_finished(code: int, response: String, plan_path: String) -> void:
    if native_export_thread != null:
        native_export_thread.wait_to_finish()
        native_export_thread = null
    if FileAccess.file_exists(plan_path):
        DirAccess.remove_absolute(plan_path)
    var result: Variant = JSON.parse_string(response.strip_edges())
    if (code == 0 and typeof(result) == TYPE_DICTIONARY
        and result.get("schema") == "DX2Ed-experimental-multi-prop-duplicate-v1"
        and result.get("status") == "isolated-GMP-created-runtime-unverified"
        and typeof(result.get("copies", null)) == TYPE_ARRAY
        and result["copies"].size() >= 2 and result["copies"].size() <= 8
        and result.get("original_bytes_unchanged") == true
        and int(result.get("new_export_count", -1)) - int(result.get("original_export_count", 0)) == result["copies"].size()
        and int(result.get("level_actor_count_after", -1)) - int(result.get("level_actor_count_before", 0)) == result["copies"].size()):
        status_label.text = "Multi Duplicate GMP saved: " + str(result.get("output_file", "")) + " | New static props: " + str(result["copies"].size()) + " | Runtime unverified."
        return
    status_label.text = "Multi Duplicate refused: " + _native_clone_error_reason(response)


func _open_native_save_as_dialog() -> void:
    if scene_root == null or current_folder.is_empty():
        status_label.text = "Import a native GMP first."
        return
    if last_gmp_path.is_empty() or not FileAccess.file_exists(last_gmp_path):
        status_label.text = "Cannot export: no original GMP source selected."
        return
    if current_source_map_name.to_lower() != last_gmp_path.get_file().to_lower():
        status_label.text = "Current scene does not match the previously imported GMP."
        return
    if native_export_thread != null:
        status_label.text = "A GMP export is already running."
        return
    gmp_save_as_dialog.current_file = last_gmp_path.get_file()
    gmp_save_as_dialog.popup_centered_ratio(0.75)


func _export_native_gmp_copy(destination: String) -> void:
    if native_export_thread != null or scene_root == null:
        return
    if current_source_map_name.to_lower() != last_gmp_path.get_file().to_lower():
        status_label.text = "Native save cancelled: source map changed."
        return
    var script := ProjectSettings.globalize_path("res://backend/dx2_native_save_as.py")
    var actors_path := current_folder.path_join("actors.json")
    if not FileAccess.file_exists(script) or not FileAccess.file_exists(actors_path):
        status_label.text = "Native GMP writer or original actor metadata is unavailable."
        return
    _finish_gizmo_drag()
    _save_prop_draft()
    var draft_path := _draft_file_path()
    if draft_path.is_empty() or not FileAccess.file_exists(draft_path):
        status_label.text = "Cannot export: draft could not be saved."
        return
    native_export_target = destination
    native_export_thread = Thread.new()
    var started := native_export_thread.start(_run_native_export.bind(
        script, last_gmp_path, actors_path, draft_path, destination
    ))
    if started != OK:
        native_export_thread = null
        native_export_target = ""
        status_label.text = "Could not start GMP Save As worker."
        return
    status_label.text = "Validating edited actor locations and writing an isolated GMP copy..."


func _run_native_export(script: String, source: String, actors_path: String, draft: String, output: String) -> void:
    var args := PackedStringArray([
        script, "--source", source, "--actors", actors_path,
        "--draft", draft, "--output", output
    ])
    var stdout: Array = []
    var status := OS.execute("python", args, stdout, true)
    if status == -1:
        var launcher := PackedStringArray(["-3"])
        launcher.append_array(args)
        stdout.clear()
        status = OS.execute("py", launcher, stdout, true)
    call_deferred("_native_export_finished", status, "\n".join(stdout))


func _native_export_finished(code: int, output: String) -> void:
    if native_export_thread != null:
        native_export_thread.wait_to_finish()
        native_export_thread = null
    native_export_target = ""
    var result: Variant = JSON.parse_string(output.strip_edges())
    if code == 0 and typeof(result) == TYPE_DICTIONARY and result.get("status") == "written-unverified":
        status_label.text = "EXPERIMENTAL GMP copy saved: " + str(result.get("output", "")) + " | Existing actor translation ONLY. Not verified in game."
        return
    var reason := str(result.get("message", "Check Python, map file and editor draft.")) if typeof(result) == TYPE_DICTIONARY else output.strip_edges().substr(0, 250)
    status_label.text = "Native GMP Save As refused: " + reason


func _save_prop_draft() -> void:
    var path := _draft_file_path()
    if path.is_empty() or scene_root == null:
        status_label.text = "Load a GLB map before saving a prop draft."
        return
    var moved := []
    for name in original_mesh_transforms:
        if not meshes_by_actor.has(name) or not actors_by_name.has(name):
            continue
        var mesh: MeshInstance3D = meshes_by_actor[name]
        if is_instance_valid(mesh) and mesh.global_transform != original_mesh_transforms[name]:
            moved.append({"actor": name, "transform": _transform_to_array(mesh.global_transform)})
    var copies := []
    for name in draft_prop_copies:
        var duplicate: MeshInstance3D = draft_prop_copies[name]
        if is_instance_valid(duplicate):
            copies.append({"name": name, "from_actor": draft_prop_sources[name],
                           "transform": _transform_to_array(duplicate.global_transform),
                           "class_template": draft_template_provenance.get(name, {}).duplicate(true),
                           "brush": draft_brush_specs.get(name, {}).duplicate(true)})
    var document := {
        "schema": "DX2Ed-prop-draft-v1",
        "map_cache": current_folder,
        "coordinate_space": "Godot world metres (X=UE X, Y=UE Z, Z=UE Y)",
        "read_only_source": true,
        "moved": moved,
        "copies": copies,
        "property_edits": _serialize_property_edits()
    }
    var output := FileAccess.open(path, FileAccess.WRITE)
    if output == null:
        status_label.text = "Unable to write private draft: " + path
        return
    output.store_string(JSON.stringify(document, "  "))
    output.close()
    status_label.text = "Saved " + str(moved.size()) + " moved props, " + str(copies.size()) + " copies and " + str(document["property_edits"].size()) + " actor property overrides (not GMP)."

func _load_prop_draft(silent_if_absent: bool = false) -> void:
    var path := _draft_file_path()
    if path.is_empty() or not FileAccess.file_exists(path):
        if not silent_if_absent:
            status_label.text = "No saved prop draft for this map cache."
        return
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        status_label.text = "Unable to read prop draft."
        return
    var doc: Variant = JSON.parse_string(file.get_as_text())
    if typeof(doc) != TYPE_DICTIONARY or doc.get("schema") != "DX2Ed-prop-draft-v1" or doc.get("map_cache") != current_folder:
        status_label.text = "Prop draft did not match the current map."
        return
    var moved: Variant = doc.get("moved", [])
    var copies: Variant = doc.get("copies", [])
    var property_rows: Variant = doc.get("property_edits", [])
    if typeof(moved) != TYPE_ARRAY or typeof(copies) != TYPE_ARRAY or moved.size() > 10000 or copies.size() > 10000:
        status_label.text = "Prop draft contains invalid record arrays."
        return
    # Validate every transform before applying any of the saved changes.
    for entry in moved + copies:
        if typeof(entry) != TYPE_DICTIONARY or _array_to_transform(entry.get("transform")) == null:
            status_label.text = "Prop draft contains an invalid transform."
            return
    # Validate all brush dimensions and provenance before changing anything.
    for entry in copies:
        var source := str(entry.get("from_actor", ""))
        var brush: Variant = entry.get("brush", {})
        if typeof(brush) != TYPE_DICTIONARY:
            status_label.text = "Invalid brush metadata. Nothing loaded."
            return
        if source.begins_with("Brush::"):
            var checked: Dictionary = BrushGeometry.validate(brush)
            if checked.is_empty() or source != "Brush::" + str(checked["kind"]):
                status_label.text = "Untrusted brush source or dimensions. Nothing loaded."
                return
        elif not brush.is_empty():
            status_label.text = "Brush metadata cannot be attached to a non-brush."
            return
        var prov: Variant = entry.get("class_template", {})
        if typeof(prov) != TYPE_DICTIONARY or not _valid_template_provenance(prov, str(entry.get("from_actor", ""))):
            status_label.text = "Draft has an untrusted class template attribution; nothing loaded."
            return
    var loaded_properties: Variant = _validate_property_edits(property_rows)
    if loaded_properties == null:
        status_label.text = "Prop draft has invalid or unmatched actor properties; nothing loaded."
        return
    var history_before := _capture_edit_state()
    _clear_selection()
    property_overrides = loaded_properties
    for name in original_mesh_transforms:
        if meshes_by_actor.has(name) and is_instance_valid(meshes_by_actor[name]):
            meshes_by_actor[name].global_transform = original_mesh_transforms[name]
    for node in draft_prop_copies.values():
        if is_instance_valid(node):
            all_mesh_instances.erase(node)
            node.free()
    draft_prop_copies.clear()
    draft_prop_sources.clear()
    draft_template_provenance.clear()
    draft_brush_specs.clear()
    next_prop_copy_id = 1
    for entry in moved:
        var name := str(entry.get("actor", ""))
        if meshes_by_actor.has(name) and actors_by_name.has(name):
            meshes_by_actor[name].global_transform = _array_to_transform(entry["transform"])
    for entry in copies:
        var from_actor := str(entry.get("from_actor", ""))
        var name := str(entry.get("name", ""))
        if not name.begins_with("DraftProp_") or not _draft_source_is_valid(from_actor):
            continue
        var instance := _new_draft_copy(from_actor, name, _array_to_transform(entry["transform"]))
        if is_instance_valid(instance):
            var brush: Dictionary = entry.get("brush", {})
            if not brush.is_empty():
                _set_brush_spec(name, brush)
            var prov: Dictionary = entry.get("class_template", {})
            if not prov.is_empty():
                draft_template_provenance[name] = prov.duplicate(true)
            var suffix := name.trim_prefix("DraftProp_")
            if suffix.is_valid_int():
                next_prop_copy_id = max(next_prop_copy_id, int(suffix) + 1)
    if not silent_if_absent:
        _record_edit("Load draft", history_before)
    _refresh_hierarchy()
    _refresh_inspector_panel()
    status_label.text = "Loaded private prop/property draft. Original GMP unchanged."

func focus_selected() -> void:
    if is_instance_valid(selected_mesh):
        var aabb := _mesh_world_aabb(selected_mesh)
        camera_target = aabb.get_center()
        orbit_distance = max(1.0, aabb.size.length() * 2.4)
        _update_camera()
        return
    # Most original AI/NPC candidates have no GLB mesh. Make them locatable
    # without fabricating any native NPC geometry or gameplay behavior.
    if not selected_actor.is_empty() and _actor_on_original_ai_layer(selected_actor):
        var coords: Variant = selected_actor.get("location", [])
        if typeof(coords) != TYPE_ARRAY or coords.size() != 3:
            return
        for value in coords:
            if typeof(value) != TYPE_FLOAT and typeof(value) != TYPE_INT:
                return
        var source_point := Vector3(float(coords[0]), float(coords[2]), float(coords[1]))
        if not source_point.is_finite():
            return
        camera_target = source_point * NATIVE_CLONE_UNREAL_METRES
        orbit_distance = 6.0
        _update_camera()
        status_label.text = (
            "Focused original AI-layer actor " + str(selected_actor.get("name", ""))
            + " at source Location. This is not a spawned NPC."
        )

func frame_whole_scene() -> void:
    if scene_bounds_valid:
        camera_target = scene_bounds.get_center()
        orbit_distance = max(5.0, scene_bounds.size.length() * 1.2)
        _update_camera()

func _update_camera() -> void:
    orbit_pitch = clamp(orbit_pitch, -1.50, 1.50)
    orbit_distance = clamp(orbit_distance, 0.15, 200000.0)
    var offset := Vector3(sin(orbit_yaw) * cos(orbit_pitch), sin(orbit_pitch), cos(orbit_yaw) * cos(orbit_pitch)) * orbit_distance
    camera.global_position = camera_target + offset
    camera.look_at(camera_target, Vector3.UP)

## The gizmo lives outside the imported GLB and is never included in
## actor selection, scene exports, or the original game data.
func _gizmo_color(axis: Vector3) -> Color:
    if axis.x > 0.5: return Color(0.98, 0.26, 0.24)
    if axis.y > 0.5: return Color(0.29, 0.94, 0.32)
    return Color(0.28, 0.52, 1.0)


func _create_transform_gizmo() -> void:
    _refresh_gizmo_shape()


func _refresh_gizmo_shape() -> void:
    if gizmo_root == null:
        return
    for old_handle in gizmo_handles:
        if is_instance_valid(old_handle):
            old_handle.queue_free()
    gizmo_handles.clear()
    var axes := [Vector3.RIGHT, Vector3.UP, Vector3.BACK]
    for axis in axes:
        var handle := MeshInstance3D.new()
        handle.name = editor_tool + "_axis_" + str(gizmo_handles.size())
        handle.set_meta("axis", axis)
        var tint := StandardMaterial3D.new()
        tint.albedo_color = _gizmo_color(axis)
        tint.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
        tint.cull_mode = BaseMaterial3D.CULL_DISABLED
        tint.no_depth_test = true
        handle.material_override = tint
        handle.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        if editor_tool == "rotate":
            var torus := TorusMesh.new()
            torus.inner_radius = 0.80
            torus.outer_radius = 0.90
            handle.mesh = torus
            handle.quaternion = Quaternion(Vector3.UP, axis)
        elif editor_tool == "scale":
            var cube := BoxMesh.new()
            cube.size = Vector3(0.23, 0.23, 0.23)
            handle.mesh = cube
            handle.position = axis * 0.92
        else:
            var shaft := CylinderMesh.new()
            shaft.top_radius = 0.025
            shaft.bottom_radius = 0.095
            shaft.height = 1.18
            handle.mesh = shaft
            handle.position = axis * 0.68
            handle.quaternion = Quaternion(Vector3.UP, axis)
        gizmo_root.add_child(handle)
        gizmo_handles.append(handle)
    _update_gizmo_pose()


func _update_gizmo_pose() -> void:
    if gizmo_root == null:
        return
    var show := _draft_selected_is_prop()
    gizmo_root.visible = show
    if not show:
        return
    gizmo_root.global_position = _selection_pivot()
    # Keep the handles about the same apparent size while zooming.
    var distance := camera.global_position.distance_to(gizmo_root.global_position)
    # Unity-sized move handle: 75% larger on screen than the old preview.
    var size_ratio := 0.19 if editor_tool == "move" else 0.13
    var scale_size: float = clampf(distance * size_ratio, 0.22, 15.0)
    gizmo_root.scale = Vector3.ONE * scale_size


func _gizmo_axis_scalar(mouse_position: Vector2, pivot: Vector3, axis: Vector3) -> Variant:
    var ray := _mouse_ray(mouse_position)
    if ray.is_empty():
        return null
    var look := camera.global_position - pivot
    var normal := look - axis * look.dot(axis)
    if normal.length_squared() < 0.0001:
        var fallback := Vector3.UP if abs(axis.dot(Vector3.UP)) < 0.9 else Vector3.RIGHT
        normal = fallback - axis * fallback.dot(axis)
    normal = normal.normalized()
    var plane := Plane(normal, normal.dot(pivot))
    var point: Variant = plane.intersects_ray(ray["origin"], ray["direction"])
    if point == null:
        return null
    return (point - pivot).dot(axis)


func _begin_gizmo_drag() -> bool:
    if not _draft_selected_is_prop():
        return false
    _update_gizmo_pose()
    var ray := _mouse_ray(view_container.get_local_mouse_position())
    if ray.is_empty():
        return false
    var best_distance := INF
    var best_axis := Vector3.ZERO
    for handle in gizmo_handles:
        if not is_instance_valid(handle):
            continue
        var hit := _ray_mesh_triangles(handle, ray["origin"], ray["direction"])
        if not hit.is_empty() and float(hit["distance"]) < best_distance:
            best_distance = float(hit["distance"])
            best_axis = handle.get_meta("axis")
    if best_axis == Vector3.ZERO:
        return false
    gizmo_drag_axis = best_axis
    gizmo_drag_pivot = _selection_pivot()
    gizmo_start_transforms.clear()
    for node in _selection_nodes():
        gizmo_start_transforms[str(node.name)] = node.global_transform
    gizmo_start_transform = selected_mesh.global_transform
    gizmo_drag_start_screen = view_container.get_local_mouse_position()
    var scalar: Variant = _gizmo_axis_scalar(gizmo_drag_start_screen, gizmo_drag_pivot, best_axis)
    gizmo_drag_start_scalar = float(scalar) if scalar != null else 0.0
    gizmo_undo_before = _capture_edit_state()
    gizmo_drag_active = true
    return true


func _apply_gizmo_drag() -> void:
    if not gizmo_drag_active or not _draft_selected_is_prop():
        return
    var distance := camera.global_position.distance_to(gizmo_drag_pivot)
    var mouse := view_container.get_local_mouse_position()
    var rotate := Basis.IDENTITY
    var scale_factor := 1.0
    var movement := Vector3.ZERO
    if editor_tool == "rotate":
        var angle := (mouse.x - gizmo_drag_start_screen.x) * 0.012
        if Input.is_key_pressed(KEY_CTRL):
            angle = snapped(angle, deg_to_rad(15.0))
        rotate = Basis(gizmo_drag_axis, angle)
    else:
        var scalar: Variant = _gizmo_axis_scalar(mouse, gizmo_drag_pivot, gizmo_drag_axis)
        if scalar == null:
            return
        var change := float(scalar) - gizmo_drag_start_scalar
        if editor_tool == "move":
            if Input.is_key_pressed(KEY_CTRL):
                change = snapped(change, float(prop_edit_step.value))
            movement = gizmo_drag_axis * change
        elif editor_tool == "scale":
            scale_factor = clampf(1.0 + change / maxf(0.5, distance * 0.18), 0.05, 100.0)
            if Input.is_key_pressed(KEY_CTRL):
                scale_factor = maxf(0.05, snapped(scale_factor, 0.1))
    for node in _selection_nodes():
        var name := str(node.name)
        if not gizmo_start_transforms.has(name):
            continue
        var pose: Transform3D = gizmo_start_transforms[name]
        if editor_tool == "move":
            pose.origin += movement
        elif editor_tool == "rotate":
            pose.origin = gizmo_drag_pivot + rotate * (pose.origin - gizmo_drag_pivot)
            pose.basis = rotate * pose.basis
        elif editor_tool == "scale":
            var offset := pose.origin - gizmo_drag_pivot
            pose.origin = gizmo_drag_pivot + offset + gizmo_drag_axis * offset.dot(gizmo_drag_axis) * (scale_factor - 1.0)
            # Apply scale along the *world* gizmo axis to all three basis columns.
            for axis_index in range(3):
                var vector: Vector3 = pose.basis[axis_index]
                pose.basis[axis_index] = vector + gizmo_drag_axis * vector.dot(gizmo_drag_axis) * (scale_factor - 1.0)
        node.global_transform = pose
    _update_gizmo_pose()
    _refresh_prop_inspection()


func _camera_offset() -> Vector3:
    return Vector3(
        sin(orbit_yaw) * cos(orbit_pitch), sin(orbit_pitch),
        cos(orbit_yaw) * cos(orbit_pitch)) * orbit_distance


func _process(delta: float) -> void:
    if fly_looking and is_instance_valid(camera):
        var local := Vector3.ZERO
        if Input.is_key_pressed(KEY_W): local.z -= 1.0
        if Input.is_key_pressed(KEY_S): local.z += 1.0
        if Input.is_key_pressed(KEY_A): local.x -= 1.0
        if Input.is_key_pressed(KEY_D): local.x += 1.0
        if Input.is_key_pressed(KEY_Q): local.y -= 1.0
        if Input.is_key_pressed(KEY_E): local.y += 1.0
        if local != Vector3.ZERO:
            var multiplier := 4.0 if Input.is_key_pressed(KEY_SHIFT) else 1.0
            var step := camera.global_basis * local.normalized() * fly_speed * multiplier * delta
            camera_target += step
            _update_camera()
    _update_gizmo_pose()


func _mouse_ray(view_mouse_position: Vector2) -> Dictionary:
    if view_container.size.x <= 0 or view_container.size.y <= 0:
        return {}
    var screen := view_mouse_position * Vector2(world_view.size) / view_container.size
    return {"origin": camera.project_ray_origin(screen),
            "direction": camera.project_ray_normal(screen).normalized()}


func _set_editor_tool(tool: String) -> void:
    if tool not in ["move", "rotate", "scale"]:
        return
    _finish_gizmo_drag()
    editor_tool = tool
    _refresh_gizmo_shape()
    status_label.text = "Transform tool: " + tool.capitalize() + " (W/E/R). Preview edits only."


func _set_fly_mode(enabled: bool) -> void:
    fly_looking = enabled
    if enabled:
        # Preserve camera position while turning the view.
        drag_mode = "fly"
    else:
        drag_mode = ""


func _text_input_focused() -> bool:
    # Do not steal Ctrl+Z from a focused search/filter or numeric spinbox.
    var focused := get_viewport().gui_get_focus_owner()
    while focused != null:
        if focused is LineEdit or focused is TextEdit or focused is SpinBox:
            return true
        focused = focused.get_parent() as Control
    return false


func _input(event: InputEvent) -> void:
    if event is InputEventKey:
        var shortcut := event as InputEventKey
        if shortcut.pressed and not shortcut.echo and (shortcut.ctrl_pressed or shortcut.meta_pressed) and not shortcut.alt_pressed and not _text_input_focused():
            if shortcut.keycode == KEY_Z:
                if shortcut.shift_pressed:
                    _redo_edit()
                else:
                    _undo_edit()
                get_viewport().set_input_as_handled()
                return
            elif shortcut.keycode == KEY_Y:
                _redo_edit()
                get_viewport().set_input_as_handled()
                return
    if view_container == null or not view_container.visible:
        return
    var mouse_inside := view_container.get_global_rect().has_point(get_global_mouse_position())
    if event is InputEventKey:
        var ke := event as InputEventKey
        if ke.pressed and not ke.echo and not fly_looking and mouse_inside:
            if ke.keycode == KEY_W: _set_editor_tool("move")
            elif ke.keycode == KEY_E: _set_editor_tool("rotate")
            elif ke.keycode == KEY_R: _set_editor_tool("scale")
            elif ke.keycode == KEY_F: focus_selected()
            else: return
            get_viewport().set_input_as_handled()
        return
    if event is InputEventMouseButton:
        var button := event as InputEventMouseButton
        # Always handle release, including outside the embedded viewport.
        if button.pressed and not mouse_inside:
            return
        if button.button_index == MOUSE_BUTTON_RIGHT:
            _set_fly_mode(button.pressed)
            get_viewport().set_input_as_handled()
            return
        if button.button_index == MOUSE_BUTTON_WHEEL_UP and button.pressed:
            if fly_looking:
                fly_speed = min(250.0, fly_speed * 1.2)
            else:
                orbit_distance *= 0.88
                _update_camera()
            get_viewport().set_input_as_handled()
        elif button.button_index == MOUSE_BUTTON_WHEEL_DOWN and button.pressed:
            if fly_looking:
                fly_speed = max(0.1, fly_speed / 1.2)
            else:
                orbit_distance *= 1.13
                _update_camera()
            get_viewport().set_input_as_handled()
        elif button.button_index == MOUSE_BUTTON_MIDDLE:
            dragging = button.pressed
            drag_mode = "pan" if button.pressed else ""
        elif button.button_index == MOUSE_BUTTON_LEFT:
            if button.pressed:
                drag_distance = 0.0
                if button.alt_pressed:
                    dragging = true
                    drag_mode = "orbit"
                elif _begin_gizmo_drag():
                    dragging = true
                    drag_mode = "gizmo"
                else:
                    dragging = true
                    drag_mode = "select"
            else:
                if drag_mode == "select" and mouse_inside and drag_distance < 3.0:
                    _pick_actor(button.ctrl_pressed or button.shift_pressed)
                if drag_mode == "gizmo":
                    _finish_gizmo_drag()
                dragging = false
                drag_mode = ""
        return
    if event is InputEventMouseMotion:
        var motion := event as InputEventMouseMotion
        if fly_looking:
            var previous := camera.global_position
            orbit_yaw -= motion.relative.x * 0.006
            orbit_pitch += motion.relative.y * 0.006
            orbit_pitch = clamp(orbit_pitch, -1.50, 1.50)
            camera_target = previous - _camera_offset()
            _update_camera()
            get_viewport().set_input_as_handled()
        elif dragging:
            drag_distance += motion.relative.length()
            if drag_mode == "orbit":
                orbit_yaw -= motion.relative.x * 0.006
                orbit_pitch += motion.relative.y * 0.006
                _update_camera()
            elif drag_mode == "pan":
                var pan := (camera.global_basis.x * -motion.relative.x + camera.global_basis.y * motion.relative.y) * (orbit_distance * 0.0015)
                camera_target += pan
                _update_camera()
            elif drag_mode == "gizmo":
                _apply_gizmo_drag()
            get_viewport().set_input_as_handled()


func _pick_actor(additive: bool = false) -> void:
    # AABB is a broad-phase filter only. Actual visible triangles decide the pick:
    # a huge BSP box must not swallow a smaller prop, nor select an empty area.
    if all_mesh_instances.is_empty() or view_container.size.x <= 0.0 or view_container.size.y <= 0.0:
        return
    var local := view_container.get_local_mouse_position()
    var screen := local * Vector2(world_view.size) / view_container.size
    var origin := camera.project_ray_origin(screen)
    var direction := camera.project_ray_normal(screen).normalized()
    var candidates: Array = []
    for instance in all_mesh_instances:
        if not is_instance_valid(instance) or instance.mesh == null or not instance.is_visible_in_tree():
            continue
        var entry := _ray_aabb(origin, direction, _mesh_world_aabb(instance))
        if entry >= 0.0:
            candidates.append({"entry": entry, "instance": instance})
    candidates.sort_custom(func(a, b): return a["entry"] < b["entry"])

    var closest_mesh: MeshInstance3D = null
    var closest_distance := INF
    var closest_position := Vector3.ZERO
    for candidate in candidates:
        # If the closest face is in front of the box, no farther box can win.
        if float(candidate["entry"]) > closest_distance:
            break
        var instance: MeshInstance3D = candidate["instance"]
        var hit := _ray_mesh_triangles(instance, origin, direction)
        if hit.is_empty():
            continue
        var distance := float(hit["distance"])
        var this_is_actor := actors_by_name.has(str(instance.name))
        var previous_is_actor := is_instance_valid(closest_mesh) and actors_by_name.has(str(closest_mesh.name))
        if distance < closest_distance - 0.00001 or (abs(distance - closest_distance) <= 0.00001 and this_is_actor and not previous_is_actor):
            closest_distance = distance
            closest_position = hit["point"]
            closest_mesh = instance

    if not is_instance_valid(closest_mesh):
        status_label.text = "No rendered triangle under cursor (bounding boxes alone are not selectable)."
        return
    var chosen_name := str(closest_mesh.name)
    if additive:
        _toggle_selection_mesh(closest_mesh)
    elif actors_by_name.has(chosen_name):
        select_actor(actors_by_name[chosen_name])
    else:
        # Imported BSP geometry remains inspectable but cannot join prop groups.
        _select_mesh_only(closest_mesh)
    if selected_meshes.has(chosen_name) and not selected_diagnostic.is_empty():
        var hit_note := "Pick method: rendered triangle (not AABB)\nGodot hit (world): " + str(closest_position) + "\nRay distance (Godot units): " + str(closest_distance)
        selected_diagnostic += "\n" + hit_note
        inspector.text += "\n\n--- PICK DETAILS ---\n" + hit_note


func _ray_mesh_triangles(instance: MeshInstance3D, origin: Vector3, direction: Vector3) -> Dictionary:
    # Transform the ray into mesh space, avoiding recalculating vertices for
    # every rotated/scaled actor instance. World distance remains comparable.
    var mesh: Mesh = instance.mesh
    if mesh == null or abs(instance.global_transform.basis.determinant()) < 0.00000001:
        return {}
    var mesh_id := mesh.get_instance_id()
    var faces: PackedVector3Array
    if pick_faces_by_mesh.has(mesh_id):
        faces = pick_faces_by_mesh[mesh_id]
    else:
        faces = mesh.get_faces()
        pick_faces_by_mesh[mesh_id] = faces
    if faces.is_empty():
        return {}
    var inverse := instance.global_transform.affine_inverse()
    var local_origin := inverse * origin
    var local_direction := inverse.basis * direction
    if local_direction.length_squared() < 0.000000000001:
        return {}

    var closest := INF
    var best_point := Vector3.ZERO
    for i in range(0, faces.size() - 2, 3):
        var hit: Variant = Geometry3D.ray_intersects_triangle(
            local_origin, local_direction, faces[i], faces[i + 1], faces[i + 2])
        # The original exporter uses double-sided materials. Pick backfaces too.
        if hit == null:
            hit = Geometry3D.ray_intersects_triangle(
                local_origin, local_direction, faces[i + 2], faces[i + 1], faces[i])
        if hit is Vector3:
            var world_hit: Vector3 = instance.global_transform * hit
            var distance := (world_hit - origin).dot(direction)
            if distance >= 0.0 and distance < closest:
                closest = distance
                best_point = world_hit
    if closest == INF:
        return {}
    return {"distance": closest, "point": best_point}


func _ray_aabb(origin: Vector3, direction: Vector3, box: AABB) -> float:
    var entry := -INF
    var exit := INF
    var start := box.position
    var finish := box.end
    for axis in range(3):
        var d := direction[axis]
        var o := origin[axis]
        if abs(d) < 0.000001:
            if o < start[axis] or o > finish[axis]:
                return -1.0
            continue
        var t1 := (start[axis] - o) / d
        var t2 := (finish[axis] - o) / d
        entry = max(entry, min(t1, t2))
        exit = min(exit, max(t1, t2))
        if entry > exit:
            return -1.0
    if exit < 0.0:
        return -1.0
    return max(entry, 0.0)
