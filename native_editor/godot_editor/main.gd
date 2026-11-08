extends Control
const BrushGeometry = preload("res://brush_geometry.gd")
const OrthoGuides = preload("res://orthographic_authoring_guides.gd")
const PythonRuntime = preload("res://python_runtime.gd")
const LightColorPanel = preload("res://light_color_panel.gd")
const MultiLightColorPanel = preload("res://multi_light_color_panel.gd")
const NativeScalarPanel = preload("res://native_scalar_panel.gd")
const MultiNativeScalarPanel = preload("res://multi_native_scalar_panel.gd")
const SceneActorWorkbenchBridge = preload("res://scene_actor_workbench_bridge.gd")
const StartupRoute = preload("res://startup_route.gd")
const MissionLogicDraft = preload("res://mission_logic_draft.gd")
const DialogueDesignDraft = preload("res://dialogue_design_draft.gd")
const ScriptIndexAuditView = preload("res://script_index_audit_view.gd")
const MissionKernelScriptView = preload("res://mission_kernel_script_view.gd")
const SourceCollisionPicker = preload("res://collision_source_picker.gd")
const CapsuleContactPreview = preload("res://capsule_contact_preview.gd")
const CapsuleSweepPanel = preload("res://capsule_sweep_panel.gd")
const SourceSurfacePanel = preload("res://source_surface_panel.gd")
const SourceEdgeTransitionPanel = preload("res://source_edge_transition_panel.gd")
## DX2Ed native viewer: a READ-ONLY Godot 4 GLB + GMP actor inspector.
## Can open an original DX2 .gmp using the bundled read-only Python backend.
## No runtime game assets bundled. Exports are cached outside the game folder.

var world_view: SubViewport
var view_container: SubViewportContainer
var world_root: Node3D
var scene_root: Node3D
var camera: Camera3D
var editor_view_mode := OrthoGuides.PERSPECTIVE
var editor_view_mode_select: OptionButton
var ortho_grid_node: MeshInstance3D
var ortho_grid_toggle: CheckBox
var ortho_grid_spacing_control: SpinBox
var ortho_grid_enabled := true
var ortho_grid_step := 0.25
var ortho_grid_last_mode := ""
var ortho_grid_last_center := Vector3(INF, INF, INF)
var ortho_grid_last_step := -1.0
var actor_list: ItemList
var search_box: LineEdit
var category_filter: OptionButton
var hierarchy_tree: Tree
var asset_filter: LineEdit
var asset_kind_filter: OptionButton
var asset_list: ItemList
var asset_details: Label
var skeletal_zip_dialog: FileDialog
var skeletal_inventory: Dictionary = {} # source-only .ski metadata, never native NPC body
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
# Opt-in original MOPP-linked collision triangle selection. Never an actor,
# an edit target, a physics material, or a native GMP Save As input.
var source_collision_picker = SourceCollisionPicker.new()
var source_collision_button: Button
var source_collision_details: Label
var source_collision_thread: Thread = null
var source_collision_pending_folder := ""
var source_collision_pending_map := ""
var source_collision_pending_sha := ""
var source_collision_marker: MeshInstance3D
var source_collision_section_marker: MeshInstance3D
var source_collision_section_actions: HFlowContainer
var source_collision_section_toggle: CheckBox
var source_collision_previous_button: Button
var source_collision_next_button: Button
var source_collision_copy_button: Button
var source_collision_last_hit: Dictionary = {}
var source_collision_mode := false
# Deliberately separate from actors, draft tools, Save As and actual game collision.
var capsule_contact_preview = CapsuleContactPreview.new()
var capsule_preview_button: Button
var capsule_preview_dialog: FileDialog
var capsule_preview_marker: MeshInstance3D
var capsule_preview_details: Label
var interactive_capsule_panel: VBoxContainer
var source_surface_panel: VBoxContainer
var source_edge_transition_panel: VBoxContainer
var source_gamesys_panel: VBoxContainer
var light_color_panel: VBoxContainer
var multi_light_color_panel: VBoxContainer
var native_scalar_panel: VBoxContainer
var multi_native_scalar_panel: VBoxContainer
var workbench_tabs: TabContainer
var workbench_handoff_button: Button
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
var native_asset_place_button: Button
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
# Original IBD script resource evidence: exact TSD payload comparison, not
# a connection from GameSys actor numeric indices to executable scripts.
var gameplay_script_zip_path := ""
var gameplay_ibd_dialog: FileDialog
var gameplay_ibd_thread: Thread = null
var gameplay_ibd_button: Button
var gameplay_ibd_status: Label
var gameplay_index_audit_button: Button
var gameplay_copy_index_audit_button: Button
var gameplay_ibd_evidence: Dictionary = {}
var gameplay_ibd_by_id: Dictionary = {}
# Separate original mission IBD / shared Kernel_TSDALL bytes. Metadata only,
# never used by game writers, and never sent out of Godot's private cache.
var gameplay_verified_mission_ibd_path := ""
var gameplay_kernel_dialog: FileDialog
var gameplay_kernel_thread: Thread = null
var gameplay_kernel_compare_button: Button
var gameplay_kernel_script_button: Button
var gameplay_kernel_copy_button: Button
var gameplay_kernel_comparison: Dictionary = {}
# Verified independent GameSys property 92 re-decoding, plus *coincidental*
# package-name-table slot lookups. NEVER a proven FName/actor script binding.
var gameplay_actor_name_slots_by_export: Dictionary = {}
# Editable private mission-logic DESIGN ONLY. Never consumed by native GMP
# Save As; original actor TriggerScript binary indices remain unresolved.
var mission_logic_draft = MissionLogicDraft.new()
var mission_plan_list: ItemList
var mission_plan_note: LineEdit
var mission_plan_add_button: Button
var mission_plan_remove_button: Button
var mission_plan_note_button: Button
var mission_plan_save_button: Button
var mission_plan_load_button: Button
# Editor-owned conversation graph design. Does NOT change original dialogue,
# localized text resources, mission logic, speech, or any DX2 game file.
var dialogue_design = DialogueDesignDraft.new()
var dialogue_list: ItemList
var dialogue_speaker_label: Label
var dialogue_text: TextEdit
var dialogue_choices_list: ItemList
var dialogue_choice_caption: LineEdit
var dialogue_choice_target: SpinBox
var dialogue_add_button: Button
var dialogue_update_button: Button
var dialogue_delete_button: Button
var dialogue_choice_add_button: Button
var dialogue_choice_remove_button: Button
var dialogue_save_button: Button
var dialogue_load_button: Button
# v12: source AI-layer locations, deliberately NOT reconstructed NPCs.
# These editor-only capsules never enter the imported GLB or GMP state.
var ai_proxies_root: Node3D
var ai_proxies: Dictionary = {} # source actor name -> MeshInstance3D
var ai_proxies_toggle: CheckBox
var ai_proxies_count: Label
# Original per-map light actors, ambient sound zones and particle emitters.
# This tab never creates lights, changes sound schemas or writes game files.
var environment_filter: LineEdit
var environment_list: ItemList
var environment_details: TextEdit
var environment_visible: Array = []
# Explicitly opt-in isolated native editing for existing ZoneProperties
# schema strings. Never a new point sound actor or a direct game-folder write.
var environment_sound_field: OptionButton
var environment_sound_schema: OptionButton
var environment_sound_button: Button
var environment_sound_dialog: FileDialog
var environment_sound_confirmation: ConfirmationDialog
var environment_sound_pending: Dictionary = {}
var environment_light_audit_button: Button
var environment_light_preview_button: Button
var environment_light_clear_button: Button
var environment_light_audit_thread: Thread = null
var environment_light_previews: Array[OmniLight3D] = []
# Unity-style source Light selection is editor-only. Never a native
# actor transform, prop draft, or input to any GMP writer.
var environment_light_markers_root: Node3D
var environment_light_markers: Dictionary = {} # source actor name -> MeshInstance3D
var environment_light_positions: Dictionary = {} # changed visual-only positions
var environment_light_radius: MeshInstance3D
var environment_light_show_markers: CheckBox
var environment_light_reset_button: Button
var environment_light_gizmo_drag := false
# v10 light inspector is an isolated visual sandbox. These controls and
# settings must NEVER be routed into native GMP writers or draft state.
var environment_light_color_control: ColorPickerButton
var environment_light_radius_control: SpinBox
var environment_light_energy_control: SpinBox
var environment_light_live_toggle: CheckBox
var environment_light_visual_reset_button: Button
var environment_light_visual_settings: Dictionary = {} # source name -> preview-only color/range/energy
var environment_light_live_node: OmniLight3D
var environment_light_controls_syncing := false
# v11 scene-wide source Light approximations in a bounded, read-only render mode.
# No baked DX2 lighting, shadow maps or native Light writers are implied.
const SEMI_LIT_DEFAULT_LIGHT_LIMIT := 32
const SEMI_LIT_SAFE_HARD_CAP := 256
const SEMI_LIT_DEFAULT_AMBIENT := 0.38
const SEMI_LIT_DEFAULT_KEY_LIGHT := 0.18
var semi_lit_enabled := false
# v13. All values stay editor-only and NEVER feed GameSys/GMP draft writers.
# Limit 0 = every valid source light, up to the renderer safety cap.
var semi_lit_light_limit := SEMI_LIT_DEFAULT_LIGHT_LIMIT
var semi_lit_ambient := SEMI_LIT_DEFAULT_AMBIENT
var semi_lit_radius_multiplier := 1.0
var semi_lit_energy_multiplier := 1.0
var lighting_dialog: AcceptDialog
var lighting_preset_select: OptionButton
var lighting_limit_select: OptionButton
var lighting_ambient_control: SpinBox
var lighting_radius_control: SpinBox
var lighting_energy_control: SpinBox
var lighting_diagnostics: Label
var lighting_source_list: ItemList
var lighting_source_names: Array[String] = []
var lighting_controls_syncing := false
var semi_lit_last_source_stats: Dictionary = {}
var semi_lit_toggle: CheckBox
var semi_lit_label: Label
var semi_lit_key_light: DirectionalLight3D
var semi_lit_world_environment: Environment
var semi_lit_root: Node3D
var semi_lit_nodes: Dictionary = {} # source Light name -> OmniLight3D
var semi_lit_last_camera_position := Vector3(INF, INF, INF)
var semi_lit_update_elapsed := 0.0
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
var brush_face_controls: HBoxContainer
var brush_face_selector: OptionButton
var brush_face_inward_button: Button
var brush_face_outward_button: Button
var brush_face_hint: Label
var brush_face_outline: MeshInstance3D
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
# User-controlled visibility exclusion for suspect native BSP preview blocks.
# Never touches GLB, GMP, actor drafts, game source or native save plans.
var bsp_hidden_preview: Dictionary = {} # MeshInstance3D -> original visibility
var bsp_hide_preview_button: Button
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
    if gameplay_ibd_thread != null:
        gameplay_ibd_thread.wait_to_finish()
        gameplay_ibd_thread = null
    if gameplay_kernel_thread != null:
        gameplay_kernel_thread.wait_to_finish()
        gameplay_kernel_thread = null
    if environment_light_audit_thread != null:
        environment_light_audit_thread.wait_to_finish()
        environment_light_audit_thread = null
    if source_collision_thread != null:
        source_collision_thread.wait_to_finish()
        source_collision_thread = null
    if interactive_capsule_panel != null:
        interactive_capsule_panel.finish()


func _ready() -> void:
    _make_ui()
    _make_world()
    if source_surface_panel != null:
        source_surface_panel.initialize(world_root)
    if source_edge_transition_panel != null:
        source_edge_transition_panel.initialize(self, world_root)
    _make_material()
    _update_camera()
    status_label.text = "Ready. Open an original DX2 .gmp map (Python 3 required) or an existing GLB."
    var requested: Dictionary = StartupRoute.resolve(OS.get_cmdline_user_args())
    match str(requested.get("kind", "invalid_args")):
        "gmp":
            # A dropped owner GMP uses the identical guarded UI import path.
            call_deferred("open_gmp", str(requested["path"]))
        "export_folder":
            # Backward-compatible existing manually exported GLB scene folder.
            call_deferred("open_export_folder", str(requested["path"]))
        "invalid_gmp":
            status_label.text = "Startup GMP refused: select an existing original .gmp file."
        "invalid_args":
            status_label.text = "Startup arguments refused. Use --gmp <original.gmp>."
        _:
            pass

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
    source_collision_button = Button.new()
    source_collision_button.text = "Inspect source collision"
    source_collision_button.toggle_mode = true
    source_collision_button.disabled = true
    source_collision_button.tooltip_text = (
        "Opt-in, original MOPP-linked triangle picking. Cache is source SHA-bound. "
        + "Click a surface for its original Level ID and render-section provenance. "
        + "Not a Havok runtime query, physics material, or editable collision."
    )
    source_collision_button.pressed.connect(_toggle_source_collision_inspection)
    toolbar.add_child(source_collision_button)
    capsule_preview_button = Button.new()
    capsule_preview_button.text = "Load capsule research preview..."
    capsule_preview_button.disabled = true
    capsule_preview_button.tooltip_text = (
        "Load a private, original-GMP-hash-bound PR #46 capsule first-contact JSON. "
        + "Editor wireframe only. NOT Havok, gameplay collision or Save As.")
    capsule_preview_button.pressed.connect(func():
        if source_collision_mode and source_collision_picker.ready:
            capsule_preview_dialog.popup_centered_ratio(0.72))
    toolbar.add_child(capsule_preview_button)
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
    # T3Ed-style planar authoring views; editor preview ONLY.
    editor_view_mode_select = OptionButton.new()
    editor_view_mode_select.tooltip_text = (
        "Perspective / top XZ / front XY / side ZY (keys 1-4 over viewport). "
        + "Views never change original camera or DX2 geometry.")
    for mode in OrthoGuides.MODES:
        editor_view_mode_select.add_item(str(mode))
    editor_view_mode_select.item_selected.connect(_view_mode_item_selected)
    toolbar.add_child(editor_view_mode_select)
    ortho_grid_toggle = CheckBox.new()
    ortho_grid_toggle.text = "Ortho grid"
    ortho_grid_toggle.button_pressed = true
    ortho_grid_toggle.tooltip_text = "Editor-only grid; not DX2 BSP/zone or collision geometry"
    ortho_grid_toggle.toggled.connect(_toggle_ortho_grid)
    toolbar.add_child(ortho_grid_toggle)
    ortho_grid_spacing_control = SpinBox.new()
    ortho_grid_spacing_control.prefix = "Grid m"
    ortho_grid_spacing_control.min_value = 0.25
    ortho_grid_spacing_control.max_value = 64.0
    ortho_grid_spacing_control.step = 0.25
    ortho_grid_spacing_control.value = 0.25
    ortho_grid_spacing_control.custom_minimum_size.x = 103
    ortho_grid_spacing_control.tooltip_text = (
        "Preview grid spacing in Godot metres. Matches Ctrl-snapping of "
        + "draft prop transforms and preview nudge distance.")
    ortho_grid_spacing_control.value_changed.connect(_grid_spacing_changed)
    toolbar.add_child(ortho_grid_spacing_control)
    var snap_selection_btn := Button.new()
    snap_selection_btn.text = "Snap selected"
    snap_selection_btn.tooltip_text = (
        "Align selected original prop PREVIEW or draft copies to the Godot grid; "
        + "undoable. Native GMP, BSP and source actor locations are never saved.")
    snap_selection_btn.pressed.connect(_snap_selected_preview_to_grid)
    toolbar.add_child(snap_selection_btn)
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
    semi_lit_toggle = CheckBox.new()
    semi_lit_toggle.text = "Semi-lit (map lights)"
    semi_lit_toggle.button_pressed = false
    semi_lit_toggle.disabled = true
    semi_lit_toggle.tooltip_text = (
        "Approximate Godot lighting from original DX2 Light actors. "
        + "Default 32 nearby, configurable up to all source lights (safe cap 256). "
        + "No DX2 lightmaps or baked lighting."
    )
    semi_lit_toggle.toggled.connect(_set_semi_lit_enabled)
    zip_bar.add_child(semi_lit_toggle)
    semi_lit_label = Label.new()
    semi_lit_label.text = ""
    zip_bar.add_child(semi_lit_label)
    var lighting_button := Button.new()
    lighting_button.text = "Lighting..."
    lighting_button.tooltip_text = (
        "Preview light count, ambient light, range and brightness; "
        + "see why some source Lights are skipped. No native map edits."
    )
    lighting_button.pressed.connect(func(): lighting_dialog.popup_centered())
    zip_bar.add_child(lighting_button)
    ai_proxies_toggle = CheckBox.new()
    ai_proxies_toggle.text = "AI origins (capsule proxies)"
    ai_proxies_toggle.tooltip_text = (
        "Show source-verified property-82 AI-layer origins as translucent capsule guides. "
        + "NOT NPC bodies, skeletons, AI simulation or native gameplay objects."
    )
    ai_proxies_toggle.button_pressed = false
    ai_proxies_toggle.disabled = true
    ai_proxies_toggle.toggled.connect(_set_ai_proxies_visible)
    zip_bar.add_child(ai_proxies_toggle)
    ai_proxies_count = Label.new()
    ai_proxies_count.text = ""
    zip_bar.add_child(ai_proxies_count)
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
    prop_edit_step.max_value = 64.0
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
    workbench_tabs = left_tabs
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
    for kind in ["All resources", "Static meshes", "Textures", "Materials", "Physics hulls", "TriggerScript", "Other", "Skeletal meshes", "Skeletal animations"]:
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
    var skeletal_source_button := Button.new()
    skeletal_source_button.text = "Open original SkeletalMeshes.zip (read-only)"
    skeletal_source_button.tooltip_text = (
        "Browse original .ski animation-set metadata for skeletal IBD assets. "
        + "Does not render bodies, assign NPCs or write game files."
    )
    skeletal_source_button.pressed.connect(
        func(): skeletal_zip_dialog.popup_centered_ratio(0.72))
    assets_tab.add_child(skeletal_source_button)
    var place_resource := Button.new()
    place_resource.text = "Place preview mesh"
    place_resource.tooltip_text = "Place a cataloged static mesh as an editable draft; does not create native DX2 actors"
    place_resource.pressed.connect(_place_selected_asset)
    assets_tab.add_child(place_resource)
    native_asset_place_button = Button.new()
    native_asset_place_button.text = "Place native copy (placed mesh)"
    native_asset_place_button.tooltip_text = (
        "Creates a saveable static prop draft using an original actor of the selected IBD mesh. "
        + "Only for resources already placed as valid StaticMeshActor in THIS map; source preflight required."
    )
    native_asset_place_button.disabled = true
    native_asset_place_button.pressed.connect(_place_asset_as_native_copy)
    assets_tab.add_child(native_asset_place_button)
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

    # v0.12: standalone original-GMP LightColor byte controls. The SDK
    # worker independently checks source, actor, serializer parity and
    # isolated output; this panel never feeds regular actor Save As.
    light_color_panel = LightColorPanel.new()
    left_tabs.add_child(light_color_panel)
    # v0.13: a separate isolated 2–8 original actor batch workflow, never
    # mixed into the single-actor Save As or regular transform writer.
    multi_light_color_panel = MultiLightColorPanel.new()
    left_tabs.add_child(multi_light_color_panel)
    # Original top-level int32/float32 actor properties are independent
    # of ordinary draft property editing and GameSys light authoring.
    native_scalar_panel = NativeScalarPanel.new()
    left_tabs.add_child(native_scalar_panel)
    # v0.15: the same original source/cache-verified numeric tag authoring
    # with a staged 2–8 field batch and a single independent GMP Save As.
    multi_native_scalar_panel = MultiNativeScalarPanel.new()
    left_tabs.add_child(multi_native_scalar_panel)

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
    gameplay_ibd_button = Button.new()
    gameplay_ibd_button.text = "Verify script resources in original IBD..."
    gameplay_ibd_button.disabled = true
    gameplay_ibd_button.tooltip_text = (
        "Compare original standalone TSD payload bytes against kind-21 IBD resources. "
        + "This does NOT resolve actor-to-script runtime bindings.")
    gameplay_ibd_button.pressed.connect(
        func(): gameplay_ibd_dialog.popup_centered_ratio(0.75))
    gameplay_tab.add_child(gameplay_ibd_button)
    gameplay_ibd_status = Label.new()
    gameplay_ibd_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    gameplay_ibd_status.text = "Select your own original TriggerScript ZIP before checking IBD resources."
    gameplay_tab.add_child(gameplay_ibd_status)
    gameplay_kernel_compare_button = Button.new()
    gameplay_kernel_compare_button.text = "Compare mission IBD against Kernel_TSDALL..."
    gameplay_kernel_compare_button.tooltip_text = (
        "Compare your own original mission resources to Kernel_TSDALL.ibd "
        + "and standalone TSDs. No game files are modified.")
    gameplay_kernel_compare_button.disabled = true
    gameplay_kernel_compare_button.pressed.connect(
        func(): gameplay_kernel_dialog.popup_centered_ratio(0.75))
    gameplay_tab.add_child(gameplay_kernel_compare_button)
    gameplay_kernel_script_button = Button.new()
    gameplay_kernel_script_button.text = "Inspect selected script's mission / Kernel differences"
    gameplay_kernel_script_button.disabled = true
    gameplay_kernel_script_button.pressed.connect(_show_selected_mission_kernel_script_diff)
    gameplay_tab.add_child(gameplay_kernel_script_button)
    gameplay_kernel_copy_button = Button.new()
    gameplay_kernel_copy_button.text = "Copy sanitized mission / Kernel summary"
    gameplay_kernel_copy_button.disabled = true
    gameplay_kernel_copy_button.tooltip_text = (
        "Only aggregate counts and difference offsets. "
        + "No private game paths, script names, hashes or original bytes.")
    gameplay_kernel_copy_button.pressed.connect(_copy_mission_kernel_script_diff)
    gameplay_tab.add_child(gameplay_kernel_copy_button)
    gameplay_index_audit_button = Button.new()
    gameplay_index_audit_button.text = "Show map-wide script index audit"
    gameplay_index_audit_button.disabled = true
    gameplay_index_audit_button.tooltip_text = (
        "Compare all verified original GameSys 92 numeric arrays against "
        + "five GMP name-table offsets. No offset proves a runtime binding.")
    gameplay_index_audit_button.pressed.connect(_show_original_map_script_index_audit)
    gameplay_tab.add_child(gameplay_index_audit_button)
    gameplay_copy_index_audit_button = Button.new()
    gameplay_copy_index_audit_button.text = "Copy sanitized index audit summary"
    gameplay_copy_index_audit_button.disabled = true
    gameplay_copy_index_audit_button.tooltip_text = (
        "Copies aggregate counts and source-evidence warnings ONLY. "
        + "No actor names, private map paths or original game bytes.")
    gameplay_copy_index_audit_button.pressed.connect(
        _copy_original_map_script_index_audit)
    gameplay_tab.add_child(gameplay_copy_index_audit_button)
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

    var plan_heading := Label.new()
    plan_heading.text = "TRIGGERSCRIPT DESIGN PLAN | private, not executable"
    gameplay_tab.add_child(plan_heading)
    var plan_row := HFlowContainer.new()
    gameplay_tab.add_child(plan_row)
    mission_plan_add_button = Button.new()
    mission_plan_add_button.text = "Plan script on selected actor"
    mission_plan_add_button.tooltip_text = "Record a hypothetical original script/actor association in a private draft. NOT a native TriggerScript assignment."
    mission_plan_add_button.pressed.connect(_mission_plan_add)
    plan_row.add_child(mission_plan_add_button)
    mission_plan_remove_button = Button.new()
    mission_plan_remove_button.text = "Remove plan"
    mission_plan_remove_button.pressed.connect(_mission_plan_remove)
    plan_row.add_child(mission_plan_remove_button)
    mission_plan_save_button = Button.new()
    mission_plan_save_button.text = "Save design"
    mission_plan_save_button.pressed.connect(_mission_plan_save)
    plan_row.add_child(mission_plan_save_button)
    mission_plan_load_button = Button.new()
    mission_plan_load_button.text = "Load design"
    mission_plan_load_button.pressed.connect(_mission_plan_load)
    plan_row.add_child(mission_plan_load_button)
    mission_plan_list = ItemList.new()
    mission_plan_list.custom_minimum_size.y = 85
    mission_plan_list.item_selected.connect(_mission_plan_selected)
    gameplay_tab.add_child(mission_plan_list)
    var note_row := HFlowContainer.new()
    gameplay_tab.add_child(note_row)
    mission_plan_note = LineEdit.new()
    mission_plan_note.placeholder_text = "Design note for planned actor/script link (max 400 chars)"
    mission_plan_note.max_length = 400
    mission_plan_note.custom_minimum_size.x = 260
    mission_plan_note.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    note_row.add_child(mission_plan_note)
    mission_plan_note_button = Button.new()
    mission_plan_note_button.text = "Update note"
    mission_plan_note_button.pressed.connect(_mission_plan_set_note)
    note_row.add_child(mission_plan_note_button)
    _mission_plan_refresh()

    gameplay_details = TextEdit.new()
    gameplay_details.editable = false
    gameplay_details.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
    gameplay_details.custom_minimum_size.y = 180
    gameplay_details.text = "Open a GMP and its original TriggerScript.zip. No native script binding or NPC spawning yet."
    gameplay_tab.add_child(gameplay_details)

    # A separate authored conversation graph. No attempt to decode retail
    # dialogue resources or treat drafts as a game's spoken conversations.
    var dialogue_tab := VBoxContainer.new()
    dialogue_tab.name = "Dialogue"
    left_tabs.add_child(dialogue_tab)
    var dialogue_header := Label.new()
    dialogue_header.text = "DIALOGUE TREE DESIGN | LOCAL ONLY | NOT IN-GAME"
    dialogue_tab.add_child(dialogue_header)
    var dialogue_note := Label.new()
    dialogue_note.text = "Select an ORIGINAL actor in Hierarchy to add a draft line. Branch by line number. Save locally."
    dialogue_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    dialogue_tab.add_child(dialogue_note)
    dialogue_list = ItemList.new()
    dialogue_list.custom_minimum_size.y = 140
    dialogue_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    dialogue_list.item_selected.connect(_dialogue_line_selected)
    dialogue_tab.add_child(dialogue_list)
    dialogue_speaker_label = Label.new()
    dialogue_speaker_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    dialogue_speaker_label.text = "No source map actor loaded."
    dialogue_tab.add_child(dialogue_speaker_label)
    dialogue_text = TextEdit.new()
    dialogue_text.custom_minimum_size.y = 90
    dialogue_text.placeholder_text = "Write a draft conversation line. Original DX2 speech/localization is untouched."
    dialogue_tab.add_child(dialogue_text)
    var dialogue_tools := HFlowContainer.new()
    dialogue_tab.add_child(dialogue_tools)
    dialogue_add_button = Button.new()
    dialogue_add_button.text = "Add line for selected actor"
    dialogue_add_button.pressed.connect(_dialogue_add_line)
    dialogue_tools.add_child(dialogue_add_button)
    dialogue_update_button = Button.new()
    dialogue_update_button.text = "Update line text"
    dialogue_update_button.pressed.connect(_dialogue_update_line)
    dialogue_tools.add_child(dialogue_update_button)
    dialogue_delete_button = Button.new()
    dialogue_delete_button.text = "Delete line"
    dialogue_delete_button.pressed.connect(_dialogue_delete_line)
    dialogue_tools.add_child(dialogue_delete_button)
    var branch_header := Label.new()
    branch_header.text = "Branches from selected line (authoring only):"
    dialogue_tab.add_child(branch_header)
    dialogue_choices_list = ItemList.new()
    dialogue_choices_list.custom_minimum_size.y = 85
    dialogue_tab.add_child(dialogue_choices_list)
    var branch_row := HFlowContainer.new()
    dialogue_tab.add_child(branch_row)
    dialogue_choice_caption = LineEdit.new()
    dialogue_choice_caption.placeholder_text = "Choice text, e.g. Ask about WTO"
    dialogue_choice_caption.max_length = 160
    dialogue_choice_caption.custom_minimum_size.x = 160
    dialogue_choice_caption.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    branch_row.add_child(dialogue_choice_caption)
    dialogue_choice_target = SpinBox.new()
    dialogue_choice_target.prefix = "Target #"
    dialogue_choice_target.min_value = 1
    dialogue_choice_target.max_value = 100000
    dialogue_choice_target.step = 1
    dialogue_choice_target.rounded = true
    branch_row.add_child(dialogue_choice_target)
    var branch_buttons := HFlowContainer.new()
    dialogue_tab.add_child(branch_buttons)
    dialogue_choice_add_button = Button.new()
    dialogue_choice_add_button.text = "Connect choice"
    dialogue_choice_add_button.pressed.connect(_dialogue_add_choice)
    branch_buttons.add_child(dialogue_choice_add_button)
    dialogue_choice_remove_button = Button.new()
    dialogue_choice_remove_button.text = "Remove choice"
    dialogue_choice_remove_button.pressed.connect(_dialogue_remove_choice)
    branch_buttons.add_child(dialogue_choice_remove_button)
    dialogue_save_button = Button.new()
    dialogue_save_button.text = "Save dialogue design"
    dialogue_save_button.pressed.connect(_dialogue_save)
    branch_buttons.add_child(dialogue_save_button)
    dialogue_load_button = Button.new()
    dialogue_load_button.text = "Load dialogue design"
    dialogue_load_button.pressed.connect(_dialogue_load)
    branch_buttons.add_child(dialogue_load_button)
    _dialogue_refresh()

    # The v10 visual properties extend the Environment inspector. Keep all
    # previous source controls reachable on smaller Windows screens.
    var environment_scroll := ScrollContainer.new()
    environment_scroll.name = "Environment"
    environment_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
    left_tabs.add_child(environment_scroll)
    var environment_tab := VBoxContainer.new()
    environment_tab.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    environment_scroll.add_child(environment_tab)
    var environment_heading := Label.new()
    environment_heading.text = "Original light / ambient zone / particle entities | Read-only"
    environment_heading.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    environment_tab.add_child(environment_heading)
    environment_filter = LineEdit.new()
    environment_filter.placeholder_text = "Search lights, zone schemas and particles..."
    environment_filter.text_changed.connect(func(_filter): _refresh_environment_entities())
    environment_tab.add_child(environment_filter)
    environment_list = ItemList.new()
    environment_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    environment_list.custom_minimum_size.y = 150
    environment_list.item_selected.connect(_environment_entity_selected)
    environment_tab.add_child(environment_list)
    var environment_locate := Button.new()
    environment_locate.text = "Locate selected source entity (F)"
    environment_locate.tooltip_text = "Focus original actor Location. No runtime entity is spawned."
    environment_locate.pressed.connect(func(): focus_selected())
    environment_tab.add_child(environment_locate)
    environment_details = TextEdit.new()
    environment_details.editable = false
    environment_details.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
    environment_details.custom_minimum_size.y = 200
    environment_details.text = "Import an original DX2 map to browse its native lights and audio zones. Read-only."
    environment_tab.add_child(environment_details)
    environment_light_show_markers = CheckBox.new()
    environment_light_show_markers.text = "Show clickable Light markers in Scene"
    environment_light_show_markers.button_pressed = true
    environment_light_show_markers.tooltip_text = "Original Light locations. Click a marker to select; W to move its preview-only gizmo."
    environment_light_show_markers.toggled.connect(_set_environment_light_markers_visible)
    environment_tab.add_child(environment_light_show_markers)
    environment_light_reset_button = Button.new()
    environment_light_reset_button.text = "Reset selected Light gizmo preview"
    environment_light_reset_button.disabled = true
    environment_light_reset_button.pressed.connect(_reset_selected_environment_light_position)
    environment_tab.add_child(environment_light_reset_button)
    var light_visual_heading := Label.new()
    light_visual_heading.text = "Selected Light appearance | GODOT PREVIEW ONLY"
    light_visual_heading.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    environment_tab.add_child(light_visual_heading)
    environment_light_color_control = ColorPickerButton.new()
    environment_light_color_control.text = "Preview color"
    environment_light_color_control.disabled = true
    environment_light_color_control.edit_alpha = false
    environment_light_color_control.color_changed.connect(
        func(value): _set_environment_light_visual_setting("color", value))
    environment_tab.add_child(environment_light_color_control)
    var light_radius_row := HBoxContainer.new()
    var light_radius_label := Label.new()
    light_radius_label.text = "Radius (preview m)"
    light_radius_row.add_child(light_radius_label)
    environment_light_radius_control = SpinBox.new()
    environment_light_radius_control.min_value = 0.5
    environment_light_radius_control.max_value = 16.0
    environment_light_radius_control.step = 0.1
    environment_light_radius_control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    environment_light_radius_control.editable = false
    environment_light_radius_control.value_changed.connect(
        func(value): _set_environment_light_visual_setting("range", value))
    light_radius_row.add_child(environment_light_radius_control)
    environment_tab.add_child(light_radius_row)
    var light_energy_row := HBoxContainer.new()
    var light_energy_label := Label.new()
    light_energy_label.text = "Brightness (preview)"
    light_energy_row.add_child(light_energy_label)
    environment_light_energy_control = SpinBox.new()
    environment_light_energy_control.min_value = 0.05
    environment_light_energy_control.max_value = 2.5
    environment_light_energy_control.step = 0.05
    environment_light_energy_control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    environment_light_energy_control.editable = false
    environment_light_energy_control.value_changed.connect(
        func(value): _set_environment_light_visual_setting("energy", value))
    light_energy_row.add_child(environment_light_energy_control)
    environment_tab.add_child(light_energy_row)
    environment_light_live_toggle = CheckBox.new()
    environment_light_live_toggle.text = "Live lighting at selected source marker"
    environment_light_live_toggle.tooltip_text = (
        "Godot OmniLight3D at visual marker position, approximate lighting. "
        + "Does NOT bake illumination, edit LightColor, or save to GMP."
    )
    environment_light_live_toggle.disabled = true
    environment_light_live_toggle.toggled.connect(
        func(_enabled): _sync_environment_light_live_node())
    environment_tab.add_child(environment_light_live_toggle)
    environment_light_visual_reset_button = Button.new()
    environment_light_visual_reset_button.text = "Reset selected Light preview appearance"
    environment_light_visual_reset_button.disabled = true
    environment_light_visual_reset_button.pressed.connect(
        _reset_selected_environment_light_visual_settings)
    environment_tab.add_child(environment_light_visual_reset_button)
    var light_visual_note := Label.new()
    light_visual_note.text = (
        "Visual units are approximate, not DX2 engine units. "
        + "No original GameSys values, GMP bytes or native light states are changed."
    )
    light_visual_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    environment_tab.add_child(light_visual_note)
    environment_light_audit_button = Button.new()
    environment_light_audit_button.text = "Audit original Light dependencies"
    environment_light_audit_button.disabled = true
    environment_light_audit_button.tooltip_text = (
        "Read-only source GMP verification of Region.iLeaf, ZoneNumberLow, PhysicsVolume, "
        + "Level and native state. Does not spawn a light."
    )
    environment_light_audit_button.pressed.connect(_start_environment_light_dependency_audit)
    environment_tab.add_child(environment_light_audit_button)
    environment_light_preview_button = Button.new()
    environment_light_preview_button.text = "Preview selected Light at camera target"
    environment_light_preview_button.disabled = true
    environment_light_preview_button.tooltip_text = (
        "Godot-only approximate light. Never serialized into DX2 GMP; source "
        + "hue/brightness/radius are not calibrated to DX2 renderer units."
    )
    environment_light_preview_button.pressed.connect(_preview_selected_light_at_target)
    environment_tab.add_child(environment_light_preview_button)
    environment_light_clear_button = Button.new()
    environment_light_clear_button.text = "Clear temporary Light previews"
    environment_light_clear_button.disabled = true
    environment_light_clear_button.pressed.connect(_clear_environment_light_previews)
    environment_tab.add_child(environment_light_clear_button)
    var env_schema_note := Label.new()
    env_schema_note.text = "Experimental existing-zone sound edit (isolated GMP only)"
    env_schema_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    environment_tab.add_child(env_schema_note)
    environment_sound_field = OptionButton.new()
    environment_sound_field.disabled = true
    environment_sound_field.item_selected.connect(func(_index): _refresh_environment_sound_replacements())
    environment_tab.add_child(environment_sound_field)
    environment_sound_schema = OptionButton.new()
    environment_sound_schema.disabled = true
    environment_sound_schema.tooltip_text = "Only names already authored for this exact field in the original map can be selected."
    environment_tab.add_child(environment_sound_schema)
    environment_sound_button = Button.new()
    environment_sound_button.text = "Experimental Zone Sound Save As..."
    environment_sound_button.disabled = true
    environment_sound_button.tooltip_text = (
        "Replaces one existing ZoneProperties sound string with another source-observed schema. "
        + "No new emitter; original GMP remains untouched."
    )
    environment_sound_button.pressed.connect(_open_environment_sound_dialog)
    environment_tab.add_child(environment_sound_button)

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
    workbench_handoff_button = Button.new()
    workbench_handoff_button.text = "Inspect original actor in Workbench"
    workbench_handoff_button.tooltip_text = (
        "Navigate only one source-verified original StaticMeshActor from"
        + " the 3D selection. Draft clones, BSP, proxies and groups are refused."
        + " Does not modify the original GMP or stage a numeric edit.")
    workbench_handoff_button.disabled = true
    workbench_handoff_button.pressed.connect(_open_selected_source_in_workbench)
    inspector_pane.add_child(workbench_handoff_button)
    source_collision_details = Label.new()
    source_collision_details.visible = false
    source_collision_details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    inspector_pane.add_child(source_collision_details)
    capsule_preview_details = Label.new()
    capsule_preview_details.visible = false
    capsule_preview_details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    inspector_pane.add_child(capsule_preview_details)
    source_surface_panel = SourceSurfacePanel.new()
    inspector_pane.add_child(source_surface_panel)
    source_edge_transition_panel = SourceEdgeTransitionPanel.new()
    inspector_pane.add_child(source_edge_transition_panel)
    interactive_capsule_panel = CapsuleSweepPanel.new()
    inspector_pane.add_child(interactive_capsule_panel)
    interactive_capsule_panel.initialize(self)
    # These are source-only inspection tools, never inputs to Save As or drafts.
    source_collision_section_actions = HFlowContainer.new()
    source_collision_section_actions.visible = false
    inspector_pane.add_child(source_collision_section_actions)
    source_collision_previous_button = Button.new()
    source_collision_previous_button.text = "Previous in section"
    source_collision_previous_button.tooltip_text = "Browse original Level triangle IDs within this Flesh render section."
    source_collision_previous_button.pressed.connect(_step_source_collision_triangle.bind(-1))
    source_collision_section_actions.add_child(source_collision_previous_button)
    source_collision_next_button = Button.new()
    source_collision_next_button.text = "Next in section"
    source_collision_next_button.pressed.connect(_step_source_collision_triangle.bind(1))
    source_collision_section_actions.add_child(source_collision_next_button)
    source_collision_section_toggle = CheckBox.new()
    source_collision_section_toggle.text = "Outline section"
    source_collision_section_toggle.tooltip_text = (
        "Preview all original MOPP triangles in this render section, capped at 1024 faces. "
        + "Render materials are not Havok physical materials."
    )
    source_collision_section_toggle.toggled.connect(_toggle_source_collision_section_outline)
    source_collision_section_actions.add_child(source_collision_section_toggle)
    source_collision_copy_button = Button.new()
    source_collision_copy_button.text = "Copy triangle evidence"
    source_collision_copy_button.pressed.connect(_copy_source_collision_evidence)
    source_collision_section_actions.add_child(source_collision_copy_button)
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
    bsp_hide_preview_button = Button.new()
    bsp_hide_preview_button.text = "Hide selected BSP (preview)"
    bsp_hide_preview_button.tooltip_text = (
        "Temporarily hide a selected original BSP render block to inspect geometry behind it. "
        + "Restore here; original GMP/GLB and game geometry are unchanged."
    )
    bsp_hide_preview_button.pressed.connect(_toggle_bsp_preview_visibility)
    geometry_debug_row.add_child(bsp_hide_preview_button)
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
    # Original T3Ed ModeFaceDrag-inspired workflow: adjust a single face of
    # an editor-only box/wall/floor while its opposite face stays anchored.
    # Never edits native BSP faces, imported map meshes or GMP data.
    brush_face_controls = HBoxContainer.new()
    brush_face_controls.visible = false
    brush_inspector_panel.add_child(brush_face_controls)
    var face_title := Label.new()
    face_title.text = "Face"
    brush_face_controls.add_child(face_title)
    brush_face_selector = OptionButton.new()
    brush_face_selector.tooltip_text = "Choose local draft brush face, not original DX2 BSP geometry."
    for face_label in BrushGeometry.FACE_LABELS:
        brush_face_selector.add_item(face_label)
    brush_face_selector.custom_minimum_size.x = 65
    brush_face_selector.item_selected.connect(_brush_face_selected)
    brush_face_controls.add_child(brush_face_selector)
    brush_face_inward_button = Button.new()
    brush_face_inward_button.text = "In"
    brush_face_inward_button.tooltip_text = "Move this draft face inward by Grid m; preserve opposite face. Ctrl+Z to undo."
    brush_face_inward_button.pressed.connect(_change_brush_face.bind(-1.0))
    brush_face_controls.add_child(brush_face_inward_button)
    brush_face_outward_button = Button.new()
    brush_face_outward_button.text = "Out"
    brush_face_outward_button.tooltip_text = "Move this draft face outward by Grid m; preserve opposite face. Ctrl+Z to undo."
    brush_face_outward_button.pressed.connect(_change_brush_face.bind(1.0))
    brush_face_controls.add_child(brush_face_outward_button)
    brush_face_hint = Label.new()
    brush_face_hint.text = "Alt+Shift+click visible draft face to select it"
    brush_face_hint.tooltip_text = (
        "Only selects a face on the already-selected editor-only Box/Wall/Floor. "
        + "Then use In/Out; does not alter source actor or DX2 BSP.")
    brush_face_hint.visible = false
    brush_inspector_panel.add_child(brush_face_hint)
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
    capsule_preview_dialog = FileDialog.new()
    capsule_preview_dialog.access = FileDialog.ACCESS_FILESYSTEM
    capsule_preview_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    capsule_preview_dialog.filters = PackedStringArray(["*.json ; DX2Ed read-only capsule contact research preview"])
    capsule_preview_dialog.file_selected.connect(_load_capsule_research_preview)
    add_child(capsule_preview_dialog)
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
    environment_sound_dialog = FileDialog.new()
    environment_sound_dialog.access = FileDialog.ACCESS_FILESYSTEM
    environment_sound_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
    environment_sound_dialog.filters = PackedStringArray(["*.gmp ; Experimental original ZoneProperties sound edit"])
    environment_sound_dialog.file_selected.connect(_stage_environment_sound_export)
    add_child(environment_sound_dialog)
    environment_sound_confirmation = ConfirmationDialog.new()
    environment_sound_confirmation.title = "Confirm isolated existing sound-zone schema edit"
    environment_sound_confirmation.confirmed.connect(_execute_environment_sound_export)
    add_child(environment_sound_confirmation)
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
    gameplay_ibd_dialog = FileDialog.new()
    gameplay_ibd_dialog.access = FileDialog.ACCESS_FILESYSTEM
    gameplay_ibd_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    gameplay_ibd_dialog.filters = PackedStringArray([
        "*.ibd ; Original Deus Ex Invisible War mission/Kernel resource IBD"])
    gameplay_ibd_dialog.file_selected.connect(_open_original_script_ibd)
    add_child(gameplay_ibd_dialog)
    gameplay_kernel_dialog = FileDialog.new()
    gameplay_kernel_dialog.access = FileDialog.ACCESS_FILESYSTEM
    gameplay_kernel_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    gameplay_kernel_dialog.filters = PackedStringArray([
        "*.ibd ; Original Kernel_TSDALL.ibd shared script bundle"])
    gameplay_kernel_dialog.file_selected.connect(_open_mission_kernel_script_comparison)
    add_child(gameplay_kernel_dialog)
    _make_lighting_dialog()
    skeletal_zip_dialog = FileDialog.new()
    skeletal_zip_dialog.access = FileDialog.ACCESS_FILESYSTEM
    skeletal_zip_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    skeletal_zip_dialog.filters = PackedStringArray(["*.zip ; Original DX2 SkeletalMeshes ZIP"])
    skeletal_zip_dialog.file_selected.connect(_open_original_skeletal_zip)
    add_child(skeletal_zip_dialog)

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
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
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
    if source_collision_thread != null:
        status_label.text = "Source collision cache is building; finish it before changing maps."
        return
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
    if light_color_panel != null:
        light_color_panel.reset_context()
    if multi_light_color_panel != null:
        multi_light_color_panel.reset_context()
    if native_scalar_panel != null:
        native_scalar_panel.reset_context()
    if multi_native_scalar_panel != null:
        multi_native_scalar_panel.reset_context()
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
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
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

## Popup is intentionally separate from the already crowded source toolbar.
## OptionButton IDs are the exact bounded preview light-node budgets.
func _make_lighting_dialog() -> void:
    lighting_dialog = AcceptDialog.new()
    lighting_dialog.title = "DX2Ed Lighting | PREVIEW ONLY"
    lighting_dialog.min_size = Vector2i(500, 545)
    add_child(lighting_dialog)
    var panel := VBoxContainer.new()
    panel.custom_minimum_size = Vector2(455, 485)
    lighting_dialog.add_child(panel)
    var heading := Label.new()
    heading.text = (
        "Godot approximation, NOT original DX2 lightmaps / shadows / PVS.\n"
        + "These controls do not edit Light actors or native GMP files."
    )
    heading.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    panel.add_child(heading)
    var preset_row := HBoxContainer.new()
    var preset_label := Label.new()
    preset_label.text = "Preset"
    preset_label.custom_minimum_size.x = 150.0
    preset_row.add_child(preset_label)
    lighting_preset_select = OptionButton.new()
    lighting_preset_select.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    for preset in ["Editor (fully lit)", "Semi-lit (v11)", "Brighter", "Dark", "Custom"]:
        lighting_preset_select.add_item(preset)
    lighting_preset_select.select(0)
    lighting_preset_select.item_selected.connect(_select_lighting_preset)
    preset_row.add_child(lighting_preset_select)
    panel.add_child(preset_row)
    var limit_row := HBoxContainer.new()
    var limit_label := Label.new()
    limit_label.text = "Source light nodes"
    limit_label.custom_minimum_size.x = 150.0
    limit_row.add_child(limit_label)
    lighting_limit_select = OptionButton.new()
    lighting_limit_select.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    for budget in [8, 16, 32, 64]:
        lighting_limit_select.add_item(str(budget), budget)
    lighting_limit_select.add_item("All (safety max 256)", 0)
    lighting_limit_select.select(2)
    lighting_limit_select.item_selected.connect(func(_index): _lighting_manual_change())
    limit_row.add_child(lighting_limit_select)
    panel.add_child(limit_row)
    for spec in [
        ["Ambient energy", "ambient", 0.0, 2.0, 0.01, SEMI_LIT_DEFAULT_AMBIENT],
        ["Source radius multiplier", "radius", 0.25, 4.0, 0.05, 1.0],
        ["Source brightness multiplier", "energy", 0.1, 4.0, 0.05, 1.0]
    ]:
        var line := HBoxContainer.new()
        var name := Label.new()
        name.text = str(spec[0])
        name.custom_minimum_size.x = 215
        line.add_child(name)
        var spin := SpinBox.new()
        spin.min_value = float(spec[2])
        spin.max_value = float(spec[3])
        spin.step = float(spec[4])
        spin.value = float(spec[5])
        spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        spin.value_changed.connect(func(_value): _lighting_manual_change())
        line.add_child(spin)
        panel.add_child(line)
        match str(spec[1]):
            "ambient": lighting_ambient_control = spin
            "radius": lighting_radius_control = spin
            "energy": lighting_energy_control = spin
    lighting_diagnostics = Label.new()
    lighting_diagnostics.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    lighting_diagnostics.text = "Open an original map with source Light actors to view diagnostics."
    panel.add_child(lighting_diagnostics)
    var list_hint := Label.new()
    list_hint.text = "Original sources | double-click an ID to focus"
    panel.add_child(list_hint)
    lighting_source_list = ItemList.new()
    lighting_source_list.custom_minimum_size.y = 120
    lighting_source_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    lighting_source_list.item_activated.connect(_focus_lighting_source)
    panel.add_child(lighting_source_list)


func _focus_lighting_source(index: int) -> void:
    if index < 0 or index >= lighting_source_names.size():
        return
    var name := lighting_source_names[index]
    if not actors_by_name.has(name):
        return
    var actor: Dictionary = actors_by_name[name]
    if actor.get("class", "") != "Light":
        return
    select_actor(actor)
    focus_selected()


func _sync_lighting_panel_controls() -> void:
    if lighting_preset_select == null:
        return
    lighting_controls_syncing = true
    var wanted_id := semi_lit_light_limit
    for i in range(lighting_limit_select.item_count):
        if lighting_limit_select.get_item_id(i) == wanted_id:
            lighting_limit_select.select(i)
            break
    lighting_ambient_control.set_value_no_signal(semi_lit_ambient)
    lighting_radius_control.set_value_no_signal(semi_lit_radius_multiplier)
    lighting_energy_control.set_value_no_signal(semi_lit_energy_multiplier)
    lighting_controls_syncing = false


func _select_lighting_preset(index: int) -> void:
    if lighting_controls_syncing:
        return
    match index:
        0:
            _set_semi_lit_enabled(false)
            if semi_lit_toggle != null:
                semi_lit_toggle.set_pressed_no_signal(false)
            _update_environment_light_selection()
            return
        1:
            semi_lit_light_limit = SEMI_LIT_DEFAULT_LIGHT_LIMIT
            semi_lit_ambient = SEMI_LIT_DEFAULT_AMBIENT
            semi_lit_radius_multiplier = 1.0
            semi_lit_energy_multiplier = 1.0
        2:
            semi_lit_light_limit = 0
            semi_lit_ambient = 0.60
            semi_lit_radius_multiplier = 1.50
            semi_lit_energy_multiplier = 1.20
        3:
            semi_lit_light_limit = 32
            semi_lit_ambient = 0.15
            semi_lit_radius_multiplier = 0.85
            semi_lit_energy_multiplier = 0.85
        4:
            pass
        _:
            return
    _sync_lighting_panel_controls()
    _set_semi_lit_enabled(true)
    if semi_lit_toggle != null:
        semi_lit_toggle.set_pressed_no_signal(semi_lit_enabled)
    _update_environment_light_selection()


func _lighting_manual_change() -> void:
    if lighting_controls_syncing or lighting_limit_select == null:
        return
    semi_lit_light_limit = lighting_limit_select.get_selected_id()
    semi_lit_ambient = clampf(float(lighting_ambient_control.value), 0.0, 2.0)
    semi_lit_radius_multiplier = clampf(float(lighting_radius_control.value), 0.25, 4.0)
    semi_lit_energy_multiplier = clampf(float(lighting_energy_control.value), 0.1, 4.0)
    lighting_controls_syncing = true
    lighting_preset_select.select(4) # Custom, without initiating preset reset
    lighting_controls_syncing = false
    _set_semi_lit_enabled(true)
    if semi_lit_toggle != null:
        semi_lit_toggle.set_pressed_no_signal(semi_lit_enabled)
    _update_environment_light_selection()


func _semi_lit_active_budget() -> int:
    return SEMI_LIT_SAFE_HARD_CAP if semi_lit_light_limit == 0 else (
        mini(semi_lit_light_limit, SEMI_LIT_SAFE_HARD_CAP))


func _apply_semi_lit_global_tone() -> void:
    if is_instance_valid(semi_lit_key_light):
        semi_lit_key_light.light_energy = (
            SEMI_LIT_DEFAULT_KEY_LIGHT if semi_lit_enabled else 1.6)
    if semi_lit_world_environment != null:
        semi_lit_world_environment.ambient_light_energy = (
            semi_lit_ambient if semi_lit_enabled else 1.1)


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
    # Grid is a separate editor-only mesh, never a selectable original actor.
    ortho_grid_node = MeshInstance3D.new()
    ortho_grid_node.name = "DX2Ed_Planar_Authoring_Grid_EDITOR_ONLY"
    ortho_grid_node.set_meta("editor_only", true)
    ortho_grid_node.visible = false
    ortho_grid_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    var ortho_grid_material := StandardMaterial3D.new()
    ortho_grid_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    ortho_grid_material.vertex_color_use_as_albedo = true
    ortho_grid_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    ortho_grid_material.cull_mode = BaseMaterial3D.CULL_DISABLED
    ortho_grid_node.material_override = ortho_grid_material
    world_root.add_child(ortho_grid_node)
    gizmo_root = Node3D.new()
    gizmo_root.name = "EditorGizmo"
    world_root.add_child(gizmo_root)
    _create_transform_gizmo()
    environment_light_markers_root = Node3D.new()
    environment_light_markers_root.name = "DX2Ed_Original_Light_Markers_EDITOR_ONLY"
    environment_light_markers_root.set_meta("editor_only", true)
    world_root.add_child(environment_light_markers_root)
    environment_light_radius = MeshInstance3D.new()
    environment_light_radius.name = "DX2Ed_Selected_Light_Radius_EDITOR_ONLY"
    environment_light_radius.set_meta("editor_only", true)
    var radius_material := StandardMaterial3D.new()
    radius_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    radius_material.albedo_color = Color(1.0, 0.85, 0.25, 0.78)
    radius_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    radius_material.no_depth_test = true
    radius_material.cull_mode = BaseMaterial3D.CULL_DISABLED
    environment_light_radius.material_override = radius_material
    environment_light_radius.visible = false
    environment_light_markers_root.add_child(environment_light_radius)
    semi_lit_root = Node3D.new()
    semi_lit_root.name = "DX2Ed_SemiLit_Source_Approximation_EDITOR_ONLY"
    semi_lit_root.set_meta("editor_only", true)
    world_root.add_child(semi_lit_root)
    ai_proxies_root = Node3D.new()
    ai_proxies_root.name = "DX2Ed_AI_Origins_EDITOR_ONLY"
    ai_proxies_root.set_meta("editor_only", true)
    ai_proxies_root.visible = false
    world_root.add_child(ai_proxies_root)
    semi_lit_key_light = DirectionalLight3D.new()
    semi_lit_key_light.rotation_degrees = Vector3(-45, 25, 0)
    semi_lit_key_light.light_energy = 1.6
    world_root.add_child(semi_lit_key_light)
    var env := WorldEnvironment.new()
    semi_lit_world_environment = Environment.new()
    semi_lit_world_environment.background_mode = Environment.BG_COLOR
    semi_lit_world_environment.background_color = Color(0.12, 0.16, 0.2)
    semi_lit_world_environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    semi_lit_world_environment.ambient_light_color = Color(0.75, 0.8, 0.9)
    semi_lit_world_environment.ambient_light_energy = 1.1
    env.environment = semi_lit_world_environment
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
    if source_collision_button != null:
        source_collision_button.disabled = (
            last_gmp_path.is_empty() or not FileAccess.file_exists(last_gmp_path)
            or current_source_map_name != last_gmp_path.get_file()
            or source_gamesys_sha256.length() != 64
        )
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
    _refresh_environment_entities()
    _rebuild_environment_light_markers()
    _rebuild_ai_proxies()
    if semi_lit_toggle != null:
        semi_lit_toggle.disabled = not _semi_lit_has_valid_source_lights()
    _refresh_semi_lit_scene()
    _load_source_gamesys_catalog(path.get_base_dir().path_join("gamesys_inspector.json"))
    if light_color_panel != null:
        var lightcolor_worker := ProjectSettings.globalize_path(
            "res://backend/dx2_sdk_lightcolor_worker.py")
        if (last_gmp_path.get_file().to_lower() == current_source_map_name.to_lower()
            and not source_gamesys_sha256.is_empty()):
            light_color_panel.configure_original(
                last_gmp_path, source_gamesys_sha256, lightcolor_worker)
        else:
            light_color_panel.reset_context()
    if multi_light_color_panel != null:
        var multi_lightcolor_worker := ProjectSettings.globalize_path(
            "res://backend/dx2_sdk_multi_lightcolor_worker.py")
        if (last_gmp_path.get_file().to_lower() == current_source_map_name.to_lower()
            and not source_gamesys_sha256.is_empty()):
            multi_light_color_panel.configure_original(
                last_gmp_path, source_gamesys_sha256, multi_lightcolor_worker)
        else:
            multi_light_color_panel.reset_context()
    if native_scalar_panel != null:
        var scalar_worker := ProjectSettings.globalize_path(
            "res://backend/dx2_sdk_scalar_worker.py")
        if (last_gmp_path.get_file().to_lower() == current_source_map_name.to_lower()
            and not source_gamesys_sha256.is_empty()):
            native_scalar_panel.configure_original(
                last_gmp_path, path, source_gamesys_sha256, scalar_worker)
        else:
            native_scalar_panel.reset_context()
    if multi_native_scalar_panel != null:
        var multi_scalar_worker := ProjectSettings.globalize_path(
            "res://backend/dx2_sdk_multi_scalar_worker.py")
        if (last_gmp_path.get_file().to_lower() == current_source_map_name.to_lower()
            and not source_gamesys_sha256.is_empty()):
            multi_native_scalar_panel.configure_original(
                last_gmp_path, path, source_gamesys_sha256, multi_scalar_worker)
        else:
            multi_native_scalar_panel.reset_context()
    _dialogue_initialize_from_current_map()
    status_label.text = "Loaded %d actors, %d meshes. Click a mesh or select an actor." % [actors.size(), mesh_count]

func _clear_current_scene() -> void:
    if light_color_panel != null:
        light_color_panel.reset_context()
    if multi_light_color_panel != null:
        multi_light_color_panel.reset_context()
    if native_scalar_panel != null:
        native_scalar_panel.reset_context()
    if multi_native_scalar_panel != null:
        multi_native_scalar_panel.reset_context()
    _reset_source_collision_inspection()
    if source_collision_button != null:
        source_collision_button.disabled = true
    _clear_ai_proxies()
    if ai_proxies_toggle != null:
        ai_proxies_toggle.set_pressed_no_signal(false)
        ai_proxies_toggle.disabled = true
    _set_semi_lit_enabled(false)
    if semi_lit_toggle != null:
        semi_lit_toggle.set_pressed_no_signal(false)
        semi_lit_toggle.disabled = true
    _clear_environment_light_markers()
    _clear_environment_light_previews()
    if environment_light_audit_button != null:
        environment_light_audit_button.disabled = true
    if environment_light_preview_button != null:
        environment_light_preview_button.disabled = true
    if environment_light_reset_button != null:
        environment_light_reset_button.disabled = true
    _restore_geometry_all_faces()
    _restore_geometry_isolation()
    _restore_bsp_preview_visibility()
    _clear_selection()
    asset_catalog.clear()
    selected_asset.clear()
    if native_asset_place_button != null:
        native_asset_place_button.disabled = true
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
    environment_visible.clear()
    environment_sound_pending.clear()
    if environment_sound_field != null:
        environment_sound_field.clear()
        environment_sound_field.disabled = true
    if environment_sound_schema != null:
        environment_sound_schema.clear()
        environment_sound_schema.disabled = true
    if environment_sound_button != null:
        environment_sound_button.disabled = true
    if environment_list != null:
        environment_list.clear()
    if environment_details != null:
        environment_details.text = "Import a source map to inspect light and sound entities."
    loaded_actors_json_path = ""
    gameplay_catalog.clear()
    gameplay_visible.clear()
    gameplay_script_zip_path = ""
    gameplay_ibd_evidence.clear()
    gameplay_ibd_by_id.clear()
    gameplay_actor_name_slots_by_export.clear()
    gameplay_verified_mission_ibd_path = ""
    gameplay_kernel_comparison.clear()
    if gameplay_kernel_compare_button != null:
        gameplay_kernel_compare_button.disabled = true
    if gameplay_kernel_script_button != null:
        gameplay_kernel_script_button.disabled = true
    if gameplay_kernel_copy_button != null:
        gameplay_kernel_copy_button.disabled = true
    if gameplay_ibd_button != null:
        gameplay_ibd_button.disabled = true
    if gameplay_index_audit_button != null:
        gameplay_index_audit_button.disabled = true
    if gameplay_copy_index_audit_button != null:
        gameplay_copy_index_audit_button.disabled = true
    if gameplay_ibd_status != null:
        gameplay_ibd_status.text = "Import your original GMP and TriggerScript ZIP to compare IBD script resources."
    mission_logic_draft.clear()
    _mission_plan_refresh()
    dialogue_design.clear()
    _dialogue_refresh()
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

## Only source-verified AI-layer candidates receive editable-scene
## ORIGIN GUIDES. An AI category is not evidence of a humanoid class,
## skeletal asset, complete NPC or safe actor-spawning semantics.
func _source_ai_position(actor: Dictionary) -> Variant:
    if not _actor_on_original_ai_layer(actor):
        return null
    var position: Variant = actor.get("location", null)
    if typeof(position) != TYPE_ARRAY or position.size() != 3:
        return null
    for component in position:
        if (typeof(component) != TYPE_FLOAT and typeof(component) != TYPE_INT
            or not is_finite(float(component))):
            return null
    return Vector3(float(position[0]),float(position[2]),float(position[1])) * NATIVE_CLONE_UNREAL_METRES


func _clear_ai_proxies() -> void:
    for marker in ai_proxies.values():
        if is_instance_valid(marker):
            marker.free()
    ai_proxies.clear()
    if ai_proxies_count != null:
        ai_proxies_count.text = ""
    if ai_proxies_root != null:
        ai_proxies_root.visible = false


func _rebuild_ai_proxies() -> void:
    _clear_ai_proxies()
    if not is_instance_valid(ai_proxies_root):
        return
    var capsule := CapsuleMesh.new()
    capsule.radius = 0.28
    capsule.height = 1.65
    var material := StandardMaterial3D.new()
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.albedo_color = Color(0.22, 0.94, 0.97, 0.27)
    material.no_depth_test = true
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    for actor in actors:
        if typeof(actor) != TYPE_DICTIONARY:
            continue
        var position: Variant = _source_ai_position(actor)
        if typeof(position) != TYPE_VECTOR3 or not position.is_finite():
            continue
        var name := str(actor.get("name", ""))
        if name.is_empty() or ai_proxies.has(name):
            continue
        var marker := MeshInstance3D.new()
        marker.name = "AI_SourceOrigin_" + name
        marker.mesh = capsule
        marker.material_override = material
        marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        marker.set_meta("editor_only", true)
        marker.set_meta("source_actor", name)
        marker.set_meta("npc_body_decoded", false)
        ai_proxies_root.add_child(marker)
        marker.global_position = position
        ai_proxies[name] = marker
    if ai_proxies_toggle != null:
        ai_proxies_toggle.disabled = ai_proxies.is_empty()
    _set_ai_proxies_visible(
        ai_proxies_toggle != null and ai_proxies_toggle.button_pressed)


func _set_ai_proxies_visible(enabled: bool) -> void:
    if ai_proxies_root != null:
        ai_proxies_root.visible = enabled and not ai_proxies.is_empty()
    if ai_proxies_count != null:
        ai_proxies_count.text = (
            " %d original AI origins (NOT bodies)" % ai_proxies.size()
            if enabled and not ai_proxies.is_empty() else ""
        )


func _pick_ai_proxy_marker(screen: Vector2) -> String:
    if (not is_instance_valid(ai_proxies_root) or not ai_proxies_root.visible
        or not is_instance_valid(camera)):
        return ""
    var nearest := ""
    var nearest_pixels := 19.0
    for name in ai_proxies:
        var marker: MeshInstance3D = ai_proxies[name]
        if (not is_instance_valid(marker) or not marker.is_visible_in_tree()
            or camera.is_position_behind(marker.global_position)):
            continue
        var projected: Vector2 = camera.unproject_position(marker.global_position)
        var pixels := projected.distance_to(screen)
        if pixels < nearest_pixels:
            nearest_pixels = pixels
            nearest = str(name)
    return nearest


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
    if (gameplay_thread != null or gameplay_ibd_thread != null
        or build_thread != null or last_gmp_path.is_empty() or loaded_actors_json_path.is_empty()
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
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        var pyargs := PackedStringArray(["-3"])
        pyargs.append_array(args)
        output.clear()
        code = OS.execute("py", pyargs, output, true)
    call_deferred("_original_gameplay_scripts_finished", code, "\n".join(output), archive)


func _original_gameplay_scripts_finished(code: int, response: String,
        archive: String) -> void:
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
    # No shortcut from raw GMP TriggerScript integer indices to TS_ names:
    # the draft records author intent only and cannot enter native Save As.
    if not mission_logic_draft.initialize(doc, actors):
        status_label.text = (
            "Original gameplay browser rejected unverifiable actor/script identities: "
            + mission_logic_draft.last_error)
        return
    gameplay_catalog = doc
    gameplay_script_zip_path = archive
    gameplay_ibd_evidence.clear()
    gameplay_ibd_by_id.clear()
    gameplay_actor_name_slots_by_export.clear()
    gameplay_verified_mission_ibd_path = ""
    gameplay_kernel_comparison.clear()
    if gameplay_kernel_compare_button != null:
        gameplay_kernel_compare_button.disabled = true
    if gameplay_kernel_script_button != null:
        gameplay_kernel_script_button.disabled = true
    if gameplay_kernel_copy_button != null:
        gameplay_kernel_copy_button.disabled = true
    if gameplay_ibd_button != null:
        gameplay_ibd_button.disabled = false
    if gameplay_index_audit_button != null:
        gameplay_index_audit_button.disabled = true
    if gameplay_copy_index_audit_button != null:
        gameplay_copy_index_audit_button.disabled = true
    if gameplay_ibd_status != null:
        gameplay_ibd_status.text = (
            "Source catalog loaded. Select your original mission/Kernel .ibd to "
            + "verify stored TriggerScript payload bytes; actor bindings remain unresolved.")
    _refresh_gameplay_script_list()
    _mission_plan_refresh()
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
        var display := str(script.get("id", "?")) + " | " + str(script.get("title", ""))
        var evidence: Dictionary = gameplay_ibd_by_id.get(
            str(script.get("id", "")).to_lower(), {})
        match str(evidence.get("status", "")):
            "exact_payload":
                display = "[IBD exact] " + display
            "different_payload":
                display = "[IBD differs] " + display
        gameplay_list.add_item(display)
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
    var proof: Dictionary = gameplay_ibd_by_id.get(
        str(script.get("id", "")).to_lower(), {})
    if not proof.is_empty():
        lines.append("ORIGINAL IBD RESOURCE EVIDENCE:")
        lines.append("Source: " + str(gameplay_ibd_evidence.get("ibd_name", "")))
        lines.append("Resource index: " + str(proof.get("ibd_resource_index", -1)))
        lines.append("Payload result: " + str(proof.get("status", "unknown")))
        lines.append(
            "Exact source TSD payload equality does NOT prove actor/runtime bindings.")
        lines.append("")
    elif not gameplay_ibd_evidence.is_empty():
        lines.append("No matching script ID found in selected original IBD.")
        lines.append("")
    lines.append("Not bound to a specific map actor. No executable edits.")
    gameplay_details.text = "\n".join(lines)


## Verifies a standalone original TriggerScript's exact payload against
## an original IBD kind-21 resource. This does NOT resolve mission-logic
## integer indices, allow bindings, or write editable scripts to retail.
func _open_original_script_ibd(ibd_path: String) -> void:
    if (gameplay_ibd_thread != null or gameplay_thread != null
        or build_thread != null or gameplay_catalog.is_empty()
        or gameplay_script_zip_path.is_empty()
        or not FileAccess.file_exists(gameplay_script_zip_path)
        or last_gmp_path.is_empty() or loaded_actors_json_path.is_empty()
        or not FileAccess.file_exists(last_gmp_path)
        or not FileAccess.file_exists(loaded_actors_json_path)
        or FileAccess.get_sha256(last_gmp_path) != source_gamesys_sha256
        or FileAccess.get_sha256(gameplay_script_zip_path)
            != str(gameplay_catalog.get("script_archive_sha256", ""))):
        status_label.text = "IBD resource check refused: GMP or source ZIP changed."
        return
    var script := ProjectSettings.globalize_path(
        "res://backend/dx2_script_ibd_provenance.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Original IBD resource verifier is missing from this build."
        return
    var target := OS.get_user_data_dir().path_join(
        "original_ibd_script_evidence_%d.json" % Time.get_ticks_usec())
    var source := last_gmp_path
    var sha := source_gamesys_sha256
    gameplay_ibd_thread = Thread.new()
    var err := gameplay_ibd_thread.start(_script_ibd_worker.bind(
        script, source, loaded_actors_json_path,
        gameplay_script_zip_path, ibd_path, target, sha))
    if err != OK:
        gameplay_ibd_thread = null
        status_label.text = "Unable to launch original IBD resource verifier."
        return
    status_label.text = "Comparing original TSD and IBD resource bytes (read-only)..."

func _script_ibd_worker(script: String, source: String, actor_path: String,
        archive: String, ibd: String, target: String, sha: String) -> void:
    var args := PackedStringArray([
        script, "--map", source, "--actors", actor_path,
        "--scripts", archive, "--ibd", ibd, "--output", target])
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        var launcher := PackedStringArray(["-3"])
        launcher.append_array(args)
        output.clear()
        code = OS.execute("py", launcher, output, true)
    call_deferred("_script_ibd_finished", code, "\n".join(output),
        source, sha, archive, ibd, target)

func _script_ibd_finished(code: int, response: String, source: String,
        sha: String, archive: String, ibd: String, target: String) -> void:
    if gameplay_ibd_thread != null:
        gameplay_ibd_thread.wait_to_finish()
        gameplay_ibd_thread = null
    if (source != last_gmp_path or sha != source_gamesys_sha256
        or archive != gameplay_script_zip_path
        or FileAccess.get_sha256(source) != sha
        or FileAccess.get_sha256(archive)
            != str(gameplay_catalog.get("script_archive_sha256", ""))):
        status_label.text = "Stale IBD resource evidence discarded after source change."
        return
    var result: Variant = null
    if response.strip_edges().begins_with("{"):
        result = JSON.parse_string(response.strip_edges())
    if (code != 0 or typeof(result) != TYPE_DICTIONARY
        or result.get("status") != "ok"
        or result.get("schema") !=
            "DX2Ed-original-IBD-TriggerScript-resource-evidence-v1"
        or not FileAccess.file_exists(target)):
        status_label.text = "IBD resource verification refused: source or resource mismatch."
        return
    var doc: Variant = JSON.parse_string(FileAccess.get_file_as_string(target))
    if (typeof(doc) != TYPE_DICTIONARY
        or doc.get("schema") !=
            "DX2Ed-original-IBD-TriggerScript-resource-evidence-v1"
        or doc.get("read_only") != true
        or doc.get("source_map") != current_source_map_name
        or doc.get("source_map_sha256") != sha
        or doc.get("script_archive_sha256") !=
            gameplay_catalog.get("script_archive_sha256")
        or doc.get("ibd_sha256") != FileAccess.get_sha256(ibd)
        or doc.get("actor_to_script_binding_verified") != false
        or doc.get("native_actor_script_indices_resolved") != false
        or doc.get("native_script_writer_enabled") != false
        or doc.get("original_game_assets_modified") != false
        or doc.get("gameplay_runtime_verified") != false
        or typeof(doc.get("entries")) != TYPE_ARRAY
        or doc["entries"].size() > 6000):
        status_label.text = "Original IBD evidence rejected: source identity/flags mismatch."
        return
    var exact: Dictionary = {}
    for item in doc["entries"]:
        if (typeof(item) != TYPE_DICTIONARY
            or typeof(item.get("script_id")) != TYPE_STRING
            or typeof(item.get("status")) != TYPE_STRING
            or item["status"] not in [
                "exact_payload", "different_payload", "not_in_original_zip"]):
            status_label.text = "Original IBD evidence contains malformed resource rows."
            return
        var key := str(item["script_id"]).to_lower()
        if exact.has(key):
            status_label.text = "Original IBD resource IDs are ambiguous."
            return
        if (item["status"] == "exact_payload"
            and item.get("source_payload_sha256") !=
                item.get("ibd_payload_sha256")):
            status_label.text = "Original IBD evidence contains false byte-match claim."
            return
        exact[key] = item
    # Optional actor raw-array probe must satisfy its own fail-closed
    # schema and match the current native-cache actors exactly. It is only
    # provenance: even an exact name-table + ZIP + IBD triple remains an
    # unverified possible runtime association, never a script assignment.
    var validated_name_slots: Dictionary = {}
    var slot_probe: Variant = doc.get("original_actor_name_slot_probe", {})
    if typeof(slot_probe) == TYPE_DICTIONARY and not slot_probe.is_empty():
        if (slot_probe.get("read_only") != true
            or slot_probe.get("actor_to_script_binding_verified") != false
            or slot_probe.get("name_table_indices_semantics_verified") != false
            or slot_probe.get("native_script_writer_enabled") != false
            or slot_probe.get("status") not in [
                "source_package_unavailable",
                "original_package_name_slots_inspected"]
            or typeof(slot_probe.get("actors")) != TYPE_ARRAY
            or slot_probe["actors"].size() > 30000):
            status_label.text = "Unverifiable original actor script name-slot probe."
            return
        var source_exports: Dictionary = {}
        for original_actor in actors:
            if (typeof(original_actor) == TYPE_DICTIONARY
                and typeof(original_actor.get("export")) in [TYPE_INT, TYPE_FLOAT]):
                source_exports[int(original_actor["export"])] = original_actor
        for entry in slot_probe["actors"]:
            if (typeof(entry) != TYPE_DICTIONARY
                or typeof(entry.get("export")) not in [TYPE_INT, TYPE_FLOAT]
                or not is_finite(float(entry["export"]))
                or float(entry["export"]) < 1.0
                or float(entry["export"]) > 2147483647.0
                or float(int(entry["export"])) != float(entry["export"])
                or typeof(entry.get("candidates")) != TYPE_ARRAY
                or entry["candidates"].size() > 256
                or entry.get("numeric_slots_are_name_references_verified") != false):
                status_label.text = "Malformed actor script name-slot evidence."
                return
            var number := int(entry["export"])
            var source_actor: Dictionary = source_exports.get(number, {})
            if (source_actor.is_empty()
                or entry.get("actor") != source_actor.get("name")
                or entry.get("class") != source_actor.get("class")
                or validated_name_slots.has(number)):
                status_label.text = "Actor script name-slot source identity mismatch."
                return
            if entry.get("native_game_property_92_verified") == true:
                var src: Variant = source_actor.get("trigger_script_serialized")
                if typeof(src) != TYPE_DICTIONARY:
                    status_label.text = "No source raw script property for validated actor."
                    return
                var elements: Variant = src.get("items", [])
                if entry["status"] == "numeric_array_redecoded":
                    if (typeof(elements) != TYPE_ARRAY
                        or elements.size() != entry["candidates"].size()):
                        status_label.text = "Original script array candidate length changed."
                        return
                    for item_index in entry["candidates"].size():
                        if entry["candidates"][item_index].get(
                            "raw_compact_integer") != elements[item_index]:
                            status_label.text = "Original script array integer changed."
                            return
            for candidate in entry["candidates"]:
                if (typeof(candidate) != TYPE_DICTIONARY
                    or candidate.get("actor_runtime_link_verified") != false
                    or typeof(candidate.get("slot_in_package_name_table")) != TYPE_BOOL
                    or typeof(candidate.get("same_name_in_original_tsd_archive")) != TYPE_BOOL
                    or candidate.get("ibd_resource_payload_status") not in [
                        "not_found", "exact_payload", "different_payload",
                        "not_in_original_zip"]):
                    status_label.text = "Malformed original name-slot candidate."
                    return
            validated_name_slots[number] = entry
    gameplay_ibd_evidence = doc
    gameplay_ibd_by_id = exact
    gameplay_actor_name_slots_by_export = validated_name_slots
    gameplay_verified_mission_ibd_path = ""
    gameplay_kernel_comparison.clear()
    if gameplay_kernel_script_button != null:
        gameplay_kernel_script_button.disabled = true
    if gameplay_kernel_copy_button != null:
        gameplay_kernel_copy_button.disabled = true
    if ibd.get_file().to_lower() != "kernel_tsdall.ibd":
        gameplay_verified_mission_ibd_path = ibd
    if gameplay_kernel_compare_button != null:
        gameplay_kernel_compare_button.disabled = gameplay_verified_mission_ibd_path.is_empty()
    var actor_probe: Variant = doc.get("original_actor_name_slot_probe", {})
    var index_audit: Variant = {}
    if typeof(actor_probe) == TYPE_DICTIONARY:
        index_audit = actor_probe.get("map_wide_index_audit", {})
    var audit_text := ScriptIndexAuditView.format_audit(index_audit)
    if gameplay_index_audit_button != null:
        gameplay_index_audit_button.disabled = audit_text.is_empty()
    if gameplay_copy_index_audit_button != null:
        gameplay_copy_index_audit_button.disabled = audit_text.is_empty()
    var counts: Dictionary = doc.get("counts", {})
    var summary := (
        "IBD source resource evidence: %d exact payloads, %d different payloads, "
        + "%d names absent in source ZIP. Actor script indices STILL unresolved."
    ) % [
        int(counts.get("exact_payload", 0)),
        int(counts.get("different_payload", 0)),
        int(counts.get("not_in_original_zip", 0))]
    if gameplay_ibd_status != null:
        gameplay_ibd_status.text = summary
    _refresh_gameplay_script_list()
    status_label.text = "Original script resource comparison complete. No game files written."


## Compare two original owner files after the one-IBD source cache
## verifies the mission IBD. Script refs remain unexecutable hypotheses.
func _open_mission_kernel_script_comparison(kernel_ibd: String) -> void:
    var mission := gameplay_verified_mission_ibd_path
    if (gameplay_kernel_thread != null or gameplay_ibd_thread != null
        or gameplay_thread != null or build_thread != null
        or mission.is_empty() or gameplay_catalog.is_empty()
        or kernel_ibd.get_file().to_lower() != "kernel_tsdall.ibd"
        or kernel_ibd == mission
        or last_gmp_path.is_empty() or loaded_actors_json_path.is_empty()
        or not FileAccess.file_exists(last_gmp_path)
        or not FileAccess.file_exists(loaded_actors_json_path)
        or not FileAccess.file_exists(gameplay_script_zip_path)
        or not FileAccess.file_exists(mission)
        or FileAccess.get_sha256(last_gmp_path) != source_gamesys_sha256
        or FileAccess.get_sha256(gameplay_script_zip_path) !=
            str(gameplay_catalog.get("script_archive_sha256", ""))
        or FileAccess.get_sha256(mission) !=
            str(gameplay_ibd_evidence.get("ibd_sha256", ""))):
        if status_label != null:
            status_label.text = "Mission/Kernel comparison refused: source identity mismatch."
        return
    var script := ProjectSettings.globalize_path(
        "res://backend/dx2_mission_kernel_script_diff.py")
    if not FileAccess.file_exists(script):
        if status_label != null:
            status_label.text = "Mission/Kernel comparison backend missing."
        return
    var output := OS.get_user_data_dir().path_join(
        "original_mission_kernel_script_diff_%d.json" % Time.get_ticks_usec())
    var source := last_gmp_path
    var archive := gameplay_script_zip_path
    var sha := source_gamesys_sha256
    gameplay_kernel_thread = Thread.new()
    var err := gameplay_kernel_thread.start(_mission_kernel_script_worker.bind(
        script, source, loaded_actors_json_path, archive, mission,
        kernel_ibd, output, sha))
    if err != OK:
        gameplay_kernel_thread = null
        if status_label != null:
            status_label.text = "Unable to start original mission/Kernel comparison."
        return
    if status_label != null:
        status_label.text = "Comparing original Club/mission TSD resources with Kernel... read-only."

func _mission_kernel_script_worker(script: String, source: String,
        actor_path: String, archive: String, mission: String, kernel: String,
        target: String, sha: String) -> void:
    var args := PackedStringArray([
        script, "--map", source, "--actors", actor_path,
        "--scripts", archive, "--mission-ibd", mission,
        "--kernel-ibd", kernel, "--output", target])
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        var fallback := PackedStringArray(["-3"])
        fallback.append_array(args)
        output.clear()
        code = OS.execute("py", fallback, output, true)
    call_deferred("_mission_kernel_script_finished", code, "\n".join(output),
        source, archive, mission, kernel, target, sha)

func _mission_kernel_script_finished(code: int, response: String,
        source: String, archive: String, mission: String,
        kernel: String, target: String, sha: String) -> void:
    if gameplay_kernel_thread != null:
        gameplay_kernel_thread.wait_to_finish()
        gameplay_kernel_thread = null
    if (source != last_gmp_path or archive != gameplay_script_zip_path
        or mission != gameplay_verified_mission_ibd_path
        or sha != source_gamesys_sha256
        or not FileAccess.file_exists(source)
        or not FileAccess.file_exists(archive)
        or not FileAccess.file_exists(mission)
        or not FileAccess.file_exists(kernel)
        or FileAccess.get_sha256(source) != sha
        or FileAccess.get_sha256(archive) !=
            str(gameplay_catalog.get("script_archive_sha256", ""))
        or FileAccess.get_sha256(mission) !=
            str(gameplay_ibd_evidence.get("ibd_sha256", ""))):
        if status_label != null:
            status_label.text = "Source changed. Discarded stale mission/Kernel evidence."
        return
    var answer: Variant = JSON.parse_string(response.strip_edges())
    if (code != 0 or typeof(answer) != TYPE_DICTIONARY
        or answer.get("status") != "ok"
        or answer.get("schema") != MissionKernelScriptView.SCHEMA
        or not FileAccess.file_exists(target)):
        if status_label != null:
            status_label.text = "Original mission/Kernel source comparison was refused."
        return
    var doc: Variant = JSON.parse_string(FileAccess.get_file_as_string(target))
    if (not MissionKernelScriptView.valid(doc)
        or doc.get("source_map") != current_source_map_name
        or doc.get("source_map_sha256") != sha
        or doc.get("script_archive_sha256") !=
            gameplay_catalog.get("script_archive_sha256")
        or doc.get("mission_ibd_name") != mission.get_file()
        or doc.get("mission_ibd_sha256") != FileAccess.get_sha256(mission)
        or doc.get("kernel_ibd_sha256") != FileAccess.get_sha256(kernel)
        or doc.get("kernel_ibd_name") != kernel.get_file()):
        if status_label != null:
            status_label.text = "Mission/Kernel report source hashes or fields invalid."
        return
    var summary := MissionKernelScriptView.summary(doc)
    if summary.is_empty():
        if status_label != null:
            status_label.text = "Original source comparison could not be rendered safely."
        return
    gameplay_kernel_comparison = doc
    if gameplay_kernel_script_button != null:
        gameplay_kernel_script_button.disabled = false
    if gameplay_kernel_copy_button != null:
        gameplay_kernel_copy_button.disabled = false
    if gameplay_details != null:
        gameplay_details.text = summary
    if gameplay_ibd_status != null:
        gameplay_ibd_status.text = (
            "Mission / Kernel original-resource comparison ready. "
            + "Select a script for per-payload diff or copy aggregate summary.")
    if status_label != null:
        status_label.text = "Mission/Kernel original IBD comparison completed. No game writes."

func _show_selected_mission_kernel_script_diff() -> void:
    if gameplay_details == null:
        return
    if gameplay_list == null or gameplay_list.get_selected_items().is_empty():
        gameplay_details.text = "Select a script ID from the original Scripts list first."
        return
    var n := int(gameplay_list.get_selected_items()[0])
    if n < 0 or n >= gameplay_visible.size():
        gameplay_details.text = "No valid source script selected."
        return
    var script_id := str(gameplay_visible[n].get("id", ""))
    var output := MissionKernelScriptView.script_details(
        gameplay_kernel_comparison, script_id)
    gameplay_details.text = output if not output.is_empty() else (
        "No verified mission/Kernel script comparison for selection.")

func _copy_mission_kernel_script_diff() -> void:
    var summary := MissionKernelScriptView.summary(gameplay_kernel_comparison)
    if summary.is_empty():
        if status_label != null:
            status_label.text = "No source-verified mission/Kernel summary to copy."
        return
    # Only aggregate numbers and offset clusters, NO source names or bytes.
    DisplayServer.clipboard_set(summary)
    if status_label != null:
        status_label.text = "Copied sanitized mission/Kernel counts and offset clusters."


## Map-wide source-based index controls never imply a native FName
## interpretation, gameplay binding or executable script installation.
func _show_original_map_script_index_audit() -> void:
    if gameplay_details == null:
        return
    var probe: Variant = gameplay_ibd_evidence.get(
        "original_actor_name_slot_probe", {})
    var report: Variant = {}
    if typeof(probe) == TYPE_DICTIONARY:
        report = probe.get("map_wide_index_audit", {})
    var summary := ScriptIndexAuditView.format_audit(report)
    if summary.is_empty():
        gameplay_details.text = (
            "No source-validated map-wide TriggerScripts array audit available. "
            + "No runtime actor-to-script links are claimed.")
        return
    gameplay_details.text = summary


func _copy_original_map_script_index_audit() -> void:
    var probe: Variant = gameplay_ibd_evidence.get(
        "original_actor_name_slot_probe", {})
    var report: Variant = {}
    if typeof(probe) == TYPE_DICTIONARY:
        report = probe.get("map_wide_index_audit", {})
    var summary := ScriptIndexAuditView.format_audit(report)
    if summary.is_empty():
        if status_label != null:
            status_label.text = "No verified source-only index audit is available to copy."
        return
    # This formatter emits aggregate COUNTS and caveats only; no filenames,
    # original actor/script IDs, original paths, game bytes or source hashes.
    DisplayServer.clipboard_set(summary)
    if status_label != null:
        status_label.text = (
            "Copied map-wide index audit aggregate only. "
            + "Original GMP/IBD/ZIP and actor names are excluded.")


## Source-verified authoring notes ONLY. Native binary writer and
## gameplay engine never consume these private project-design rows.
func _mission_plan_refresh() -> void:
    if mission_plan_list == null:
        return
    mission_plan_list.clear()
    for row in mission_logic_draft.rows:
        mission_plan_list.add_item(
            "Actor #%d %s : %s" % [
                int(row["actor_export"]), str(row["actor_name"]), str(row["script_id"])
            ])
    if mission_plan_add_button != null:
        mission_plan_add_button.disabled = not mission_logic_draft.ready
    if mission_plan_save_button != null:
        mission_plan_save_button.disabled = not mission_logic_draft.ready
    if mission_plan_load_button != null:
        mission_plan_load_button.disabled = not mission_logic_draft.ready
    if mission_plan_remove_button != null:
        mission_plan_remove_button.disabled = mission_logic_draft.rows.is_empty()
    if mission_plan_note_button != null:
        mission_plan_note_button.disabled = mission_logic_draft.rows.is_empty()

func _mission_plan_add() -> void:
    if not mission_logic_draft.ready or gameplay_list == null:
        status_label.text = "Load a source-matched original GMP and TriggerScript ZIP first."
        return
    var chosen := gameplay_list.get_selected_items()
    if chosen.is_empty() or int(chosen[0]) >= gameplay_visible.size():
        status_label.text = "Choose an original TriggerScript from the Scripts list."
        return
    var actor: Dictionary = selected_actor
    if is_instance_valid(selected_mesh) and actors_by_name.has(str(selected_mesh.name)):
        actor = actors_by_name[str(selected_mesh.name)]
    var original_script: Dictionary = gameplay_visible[int(chosen[0])]
    if not mission_logic_draft.plan_actor_script(
        str(original_script["id"]), actor, mission_plan_note.text):
        status_label.text = "Design plan refused: " + mission_logic_draft.last_error
        return
    _mission_plan_refresh()
    mission_plan_list.select(mission_logic_draft.rows.size() - 1)
    status_label.text = (
        "Added private script-binding DESIGN row. Original GMP/IBD unchanged; "
        + "no executable script assigned.")

func _mission_plan_selected(index: int) -> void:
    if index < 0 or index >= mission_logic_draft.rows.size():
        return
    var row: Dictionary = mission_logic_draft.rows[index]
    mission_plan_note.text = str(row["note"])
    gameplay_details.text = (
        "MISSION-LOGIC DESIGN ONLY | NOT A COMPILED TRIGGERSCRIPT BINDING"
        + "\nOriginal actor: " + str(row["actor_name"])
        + "\nOriginal class: " + str(row["actor_class"])
        + "\nNative export: " + str(row["actor_export"])
        + "\nSource script definition: " + str(row["script_id"])
        + "\nAuthor's note: " + str(row["note"])
        + "\n\nNot verified by an original mission-logic reference table."
        + "\nNo GMP, IBD, native actor property or TriggerScript file will be changed.")

func _mission_plan_set_note() -> void:
    if mission_plan_list == null:
        return
    var chosen := mission_plan_list.get_selected_items()
    if chosen.is_empty() or not mission_logic_draft.change_note(
        int(chosen[0]), mission_plan_note.text):
        status_label.text = "Design note update refused: " + mission_logic_draft.last_error
        return
    _mission_plan_selected(int(chosen[0]))
    status_label.text = "Private design note updated in memory. Save design to persist."

func _mission_plan_remove() -> void:
    if mission_plan_list == null:
        return
    var chosen := mission_plan_list.get_selected_items()
    if chosen.is_empty() or not mission_logic_draft.remove(int(chosen[0])):
        status_label.text = "No valid design plan row selected for removal."
        return
    _mission_plan_refresh()
    status_label.text = "Removed design-only script/actor plan. Source map unaffected."

func _mission_plan_save() -> void:
    if not mission_logic_draft.save_private():
        status_label.text = "Design save refused: " + mission_logic_draft.last_error
        return
    status_label.text = (
        "Saved %d design-only script/actor plans into DX2Ed private user data. "
        + "No native GMP, IBD or scripts modified.") % mission_logic_draft.rows.size()

func _mission_plan_load() -> void:
    if not mission_logic_draft.load_private():
        status_label.text = "Design load refused: " + mission_logic_draft.last_error
        return
    _mission_plan_refresh()
    status_label.text = (
        "Loaded %d source-matched private script-binding DESIGN rows. "
        + "No original runtime behavior changed.") % mission_logic_draft.rows.size()


## Dialogue authoring is a private document bound to an unchanged original
## GMP, NOT a decoded conversation format or any native game script editor.
func _dialogue_initialize_from_current_map() -> void:
    dialogue_design.clear()
    if (last_gmp_path.is_empty()
        or not FileAccess.file_exists(last_gmp_path)
        or current_source_map_name != last_gmp_path.get_file()
        or source_gamesys_sha256.length() != 64
        or not source_gamesys_sha256.is_valid_hex_number()
        or FileAccess.get_sha256(last_gmp_path) != source_gamesys_sha256):
        _dialogue_refresh()
        return
    dialogue_design.initialize(
        current_source_map_name, source_gamesys_sha256, actors)
    _dialogue_refresh()

func _dialogue_selected_id() -> int:
    if dialogue_list == null:
        return -1
    var selection := dialogue_list.get_selected_items()
    if selection.is_empty() or int(selection[0]) >= dialogue_design.nodes.size():
        return -1
    return int(dialogue_design.nodes[int(selection[0])]["id"])

func _dialogue_refresh(select_id: int = -1) -> void:
    if dialogue_list == null:
        return
    dialogue_list.clear()
    var selected_index := -1
    for i in dialogue_design.nodes.size():
        var line: Dictionary = dialogue_design.nodes[i]
        var preview := str(line["text"]).replace("\n", " ").substr(0, 52)
        dialogue_list.add_item("#%d | %s: %s" % [
            int(line["id"]), str(line["speaker_name"]), preview])
        if int(line["id"]) == select_id:
            selected_index = i
    if selected_index < 0 and not dialogue_design.nodes.is_empty():
        selected_index = 0
    if selected_index >= 0:
        dialogue_list.select(selected_index)
        _dialogue_line_selected(selected_index)
    else:
        if dialogue_choices_list != null:
            dialogue_choices_list.clear()
        if dialogue_speaker_label != null:
            dialogue_speaker_label.text = (
                "Select a source map actor in Hierarchy to start a dialogue design."
                if dialogue_design.ready else
                "Import an original GMP to enable source-pinned dialogue design.")
    if dialogue_add_button != null:
        dialogue_add_button.disabled = not dialogue_design.ready
    if dialogue_save_button != null:
        dialogue_save_button.disabled = not dialogue_design.ready
    if dialogue_load_button != null:
        dialogue_load_button.disabled = not dialogue_design.ready
    for b in [dialogue_update_button, dialogue_delete_button,
              dialogue_choice_add_button, dialogue_choice_remove_button]:
        if b != null:
            b.disabled = not dialogue_design.ready or dialogue_design.nodes.is_empty()

func _dialogue_line_selected(index: int) -> void:
    if index < 0 or index >= dialogue_design.nodes.size():
        return
    var line: Dictionary = dialogue_design.nodes[index]
    if dialogue_text != null:
        dialogue_text.text = str(line["text"])
    if dialogue_speaker_label != null:
        dialogue_speaker_label.text = (
            "Draft line #%d | Original %s (%s), export #%d" % [
                int(line["id"]), str(line["speaker_name"]),
                str(line["speaker_class"]), int(line["speaker_export"])])
    if dialogue_choices_list != null:
        dialogue_choices_list.clear()
        for choice in line["choices"]:
            dialogue_choices_list.add_item(
                "%s -> #%d" % [str(choice["caption"]), int(choice["target"])])

func _dialogue_add_line() -> void:
    if not dialogue_design.ready:
        status_label.text = "Import an unmodified original GMP with source actors first."
        return
    var actor: Dictionary = selected_actor
    if is_instance_valid(selected_mesh) and actors_by_name.has(str(selected_mesh.name)):
        actor = actors_by_name[str(selected_mesh.name)]
    var id := dialogue_design.add_line(actor, dialogue_text.text)
    if id < 0:
        status_label.text = "Dialogue design refused: " + dialogue_design.last_error
        return
    _dialogue_refresh(id)
    status_label.text = "Private dialogue line #%d added. Not a DX2 conversation binary." % id

func _dialogue_update_line() -> void:
    var id := _dialogue_selected_id()
    if not dialogue_design.update_line(id, dialogue_text.text):
        status_label.text = "Dialogue design refused: " + dialogue_design.last_error
        return
    _dialogue_refresh(id)
    status_label.text = "Dialogue design line text updated in memory. Save to persist."

func _dialogue_delete_line() -> void:
    var id := _dialogue_selected_id()
    if not dialogue_design.remove_line(id):
        status_label.text = "Dialogue line delete refused: " + dialogue_design.last_error
        return
    _dialogue_refresh()
    status_label.text = (
        "Removed dialogue design line and branches pointing to it. "
        + "Original game resources unchanged.")

func _dialogue_add_choice() -> void:
    var id := _dialogue_selected_id()
    if not dialogue_design.add_choice(
        id, int(dialogue_choice_target.value), dialogue_choice_caption.text):
        status_label.text = "Dialogue design branch refused: " + dialogue_design.last_error
        return
    _dialogue_refresh(id)
    status_label.text = "Conversation design branch added (not compiled)."

func _dialogue_remove_choice() -> void:
    var id := _dialogue_selected_id()
    var selection := dialogue_choices_list.get_selected_items()
    if selection.is_empty() or not dialogue_design.remove_choice(id, int(selection[0])):
        status_label.text = "Select an existing design branch first."
        return
    _dialogue_refresh(id)
    status_label.text = "Conversation design branch removed. Game assets unchanged."

func _dialogue_save() -> void:
    if not dialogue_design.save_private():
        status_label.text = "Dialogue save refused: " + dialogue_design.last_error
        return
    status_label.text = (
        "Saved %d original-map-bound dialogue design lines. "
        + "Native conversation and voice resources NOT modified.") % dialogue_design.nodes.size()

func _dialogue_load() -> void:
    if not dialogue_design.load_private():
        status_label.text = "Dialogue load refused: " + dialogue_design.last_error
        return
    _dialogue_refresh()
    status_label.text = (
        "Loaded %d source-pinned dialogue design lines. "
        + "No native conversation export.") % dialogue_design.nodes.size()


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
    var lines: PackedStringArray = [
        "Original actor: " + str(actor.get("name", "?")),
        "Class: " + str(actor.get("class", "?")),
        "Export: " + str(actor.get("export", "?")),
        "Original AI layer: " + str(_actor_on_original_ai_layer(actor)),
        "Serialized TriggerScript data: " + JSON.stringify(raw, "  "),
        "",
        "Raw integer indices are NOT verified TS_ IDs.",
    ]
    var export_value: Variant = actor.get("export", -1)
    if typeof(export_value) in [TYPE_INT, TYPE_FLOAT]:
        var row: Dictionary = gameplay_actor_name_slots_by_export.get(
            int(export_value), {})
        if (not row.is_empty() and row.get("actor") == actor.get("name")
            and row.get("class") == actor.get("class")):
            lines.append("")
            lines.append("ORIGINAL GMP GAMEPROPERTY 92 / NAME-SLOT RESEARCH:")
            lines.append("Native block re-decode: " +
                str(row.get("status", "unverified_native_actor")))
            for candidate in row.get("candidates", []):
                var slot := str(candidate.get("raw_compact_integer", "?"))
                var found := str(candidate.get(
                    "name_at_same_numeric_slot", "<no original name in that slot>"))
                var source_state := (
                    "ZIP name match" if candidate.get(
                        "same_name_in_original_tsd_archive") == true
                        else "no ZIP name match")
                lines.append(
                    "  Raw integer " + slot + " | package slot name: "
                    + found + " | " + source_state
                    + " | IBD: " + str(candidate.get(
                        "ibd_resource_payload_status", "not_found")))
            lines.append(
                "Names at equal numeric slots are CANDIDATES, not proved FName references.")
            lines.append(
                "Even a ZIP + IBD byte match does NOT verify an actor executes that script.")
    lines.append("No NPC spawning or script assignment is enabled.")
    gameplay_details.text = "\n".join(lines)



## These property IDs and names are verified against the original
## DX2 System/Engine.d2u and Gamesys declarations. A stream schema is
## a ZONE-level sound setting, not a positionable AmbientSound actor.
func _environment_entity_kind(actor: Dictionary) -> String:
    match str(actor.get("class", "")):
        "Light":
            return "Light"
        "ZoneProperties":
            return "Ambient sound zone"
        "Emitter":
            return "Particle emitter (NOT sound)"
    return ""


func _environment_game_value(actor: Dictionary, property_id: int) -> Variant:
    var props: Variant = actor.get("game_properties", [])
    if typeof(props) != TYPE_ARRAY:
        return null
    for prop in props:
        if typeof(prop) == TYPE_DICTIONARY and int(prop.get("id", -1)) == property_id:
            return prop.get("value")
    return null


func _refresh_environment_entities() -> void:
    if environment_list == null:
        return
    environment_list.clear()
    environment_visible.clear()
    var query := environment_filter.text.strip_edges().to_lower() if environment_filter != null else ""
    for actor in actors:
        if typeof(actor) != TYPE_DICTIONARY:
            continue
        var kind := _environment_entity_kind(actor)
        if kind.is_empty():
            continue
        var searchable := str(actor.get("name", "")) + " " + kind
        for property_id in [116, 118, 1586, 1467, 1286, 1287]:
            searchable += " " + str(_environment_game_value(actor, property_id))
        if not query.is_empty() and query not in searchable.to_lower():
            continue
        environment_visible.append(actor)
        environment_list.add_item(str(actor.get("name", "?")) + " [" + kind + "]")
    if environment_details != null:
        environment_details.text = (
            "Original environment actors: " + str(environment_visible.size())
            + " match the current filter.\nLights are native actors; sound schemas "
            + "are attached to ZoneProperties. Particle Emitters are NOT audio.\n"
            + "Select a source entity to view exact original parameters. "
            + "No sound playback, new lights or GMP writes."
        )


func _environment_entity_selected(index: int) -> void:
    if index < 0 or index >= environment_visible.size():
        return
    var actor: Dictionary = environment_visible[index]
    var kind := _environment_entity_kind(actor)
    select_actor(actor)
    if environment_light_audit_button != null:
        environment_light_audit_button.disabled = kind != "Light"
    if environment_light_preview_button != null:
        environment_light_preview_button.disabled = kind != "Light"
    if environment_light_reset_button != null:
        environment_light_reset_button.disabled = (kind != "Light"
            or not environment_light_positions.has(str(actor.get("name", ""))))
    if environment_details == null:
        return
    var rows: PackedStringArray = [
        "ORIGINAL DX2 " + kind.to_upper() + " | READ ONLY",
        "Actor: " + str(actor.get("name", "?")),
        "Native class: " + str(actor.get("class", "?")),
        "Source export: " + str(actor.get("export", "?")),
        "Source Unreal XYZ: " + str(actor.get("location", [])),
        ""
    ]
    if kind == "Light":
        rows.append("LightColor (GameSys 116): " + str(_environment_game_value(actor, 116)))
        rows.append("LightShape (GameSys 118): " + str(_environment_game_value(actor, 118)))
        rows.append("EmissiveScale (GameSys 1586): " + str(_environment_game_value(actor, 1586)))
        rows.append("bLightOn (GameSys 1487, explicit value only): " + str(_environment_game_value(actor, 1487)))
        var native: Variant = actor.get("tagged", {})
        if typeof(native) == TYPE_DICTIONARY:
            rows.append("")
            rows.append("Original PhysicsVolume: " + str(native.get("PhysicsVolume", "unknown")))
            rows.append("Original Region: " + str(native.get("Region", "unavailable")))
            rows.append("Original Level reference: " + str(native.get("Level", "unavailable")))
            rows.append("bDynamicLight: " + str(native.get("bDynamicLight", "unavailable")))
            rows.append("bSentSpawnNotification: " + str(native.get("bSentSpawnNotification", "unavailable")))
        var visual_position: Variant = _environment_light_preview_position(actor)
        if typeof(visual_position) == TYPE_VECTOR3:
            rows.append("Light marker (Godot metres): " + str(visual_position))
            rows.append("Move with W gizmo. Editor preview ONLY; Reset restores original coordinates.")
        rows.append("New light placement BLOCKED: BSP point-to-leaf and native state must be reconstructed.")
    elif kind == "Ambient sound zone":
        rows.append("StreamSchema1 (GameSys 1287): " + str(_environment_game_value(actor, 1287)))
        rows.append("StreamSchema2 (GameSys 1286): " + str(_environment_game_value(actor, 1286)))
        rows.append("NonStreamSchema1 (GameSys 1467): " + str(_environment_game_value(actor, 1467)))
        rows.append("These configure zone audio, not a standalone point sound emitter.")
    else:
        rows.append("Particle effects are unrelated to the sound emitter system.")
    rows.append("")
    rows.append("Original source unchanged; zone edits are opt-in, isolated and experimental.")
    environment_details.text = "\n".join(rows)
    _refresh_environment_sound_fields(actor)
    _update_environment_light_selection()




## Source-authentic Light markers with Unity-like click selection and a
## three-circle influence preview. No input to GMP writers or prop drafts.
func _environment_light_original_position(actor: Dictionary) -> Variant:
    if actor.get("class", "") != "Light":
        return null
    var original: Variant = actor.get("location", null)
    if typeof(original) != TYPE_ARRAY or original.size() != 3:
        return null
    for value in original:
        if (typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT
            or not is_finite(float(value))):
            return null
    return Vector3(float(original[0]), float(original[2]),
        float(original[1])) * NATIVE_CLONE_UNREAL_METRES


func _environment_light_preview_position(actor: Dictionary) -> Variant:
    var source_name := str(actor.get("name", ""))
    if environment_light_positions.has(source_name):
        var preview: Variant = environment_light_positions[source_name]
        if typeof(preview) == TYPE_VECTOR3 and preview.is_finite():
            return preview
    return _environment_light_original_position(actor)


func _environment_light_proxy_selected() -> bool:
    return (selected_actor.get("class", "") == "Light"
        and selected_meshes.is_empty()
        and environment_light_markers_root != null
        and environment_light_markers_root.visible
        and typeof(_environment_light_preview_position(selected_actor)) == TYPE_VECTOR3)


func _environment_light_preview_radius(actor: Dictionary) -> float:
    var shape: Variant = _environment_game_value(actor, 118)
    if typeof(shape) != TYPE_DICTIONARY:
        return 1.5
    var original: Variant = shape.get("LightRadius", null)
    if typeof(original) != TYPE_FLOAT and typeof(original) != TYPE_INT:
        return 1.5
    if not is_finite(float(original)):
        return 1.5
    # Explicitly an approximate Godot preview. UE native bounds are not
    # calibrated to the Godot/SubViewport renderer's light falloff.
    return clampf(float(original) * 0.12, 0.5, 16.0)


# Source byte fields are interpreted only as approximate Godot visuals.
# We deliberately keep source GameSys dictionaries immutable.
func _environment_light_visual_defaults(actor: Dictionary) -> Dictionary:
    if actor.get("class", "") != "Light":
        return {}
    var color_info: Variant = _environment_game_value(actor, 116)
    var shape: Variant = _environment_game_value(actor, 118)
    if typeof(color_info) != TYPE_DICTIONARY or typeof(shape) != TYPE_DICTIONARY:
        return {}
    var values := [
        color_info.get("LightHue", 0),
        color_info.get("LightSaturation", 0),
        color_info.get("LightBrightness", null),
        shape.get("LightRadius", null)
    ]
    for value in values:
        if typeof(value) != TYPE_FLOAT and typeof(value) != TYPE_INT:
            return {}
        if not is_finite(float(value)) or float(value) < 0.0 or float(value) > 255.0:
            return {}
    return {
        "color": Color.from_hsv(float(values[0]) / 255.0,
            float(values[1]) / 255.0, 1.0),
        "range": clampf(float(values[3]) * 0.12, 0.5, 16.0),
        "energy": clampf(float(values[2]) / 64.0, 0.05, 2.5)
    }


func _environment_light_visual_values(actor: Dictionary) -> Dictionary:
    var defaults := _environment_light_visual_defaults(actor)
    if defaults.is_empty():
        return {}
    var name := str(actor.get("name", ""))
    var overrides: Variant = environment_light_visual_settings.get(name, {})
    if typeof(overrides) != TYPE_DICTIONARY:
        return defaults
    for key in ["color", "range", "energy"]:
        if overrides.has(key):
            defaults[key] = overrides[key]
    return defaults


func _refresh_environment_light_visual_controls() -> void:
    if environment_light_color_control == null:
        return
    var enabled: bool = selected_actor.get("class", "") == "Light"
    var values := _environment_light_visual_values(selected_actor) if enabled else {}
    enabled = enabled and not values.is_empty()
    environment_light_controls_syncing = true
    environment_light_color_control.disabled = not enabled
    environment_light_radius_control.editable = enabled
    environment_light_energy_control.editable = enabled
    environment_light_live_toggle.disabled = not enabled
    environment_light_visual_reset_button.disabled = (not enabled
        or not environment_light_visual_settings.has(str(selected_actor.get("name", ""))))
    if enabled:
        environment_light_color_control.color = values["color"]
        environment_light_radius_control.value = float(values["range"])
        environment_light_energy_control.value = float(values["energy"])
    environment_light_controls_syncing = false


func _set_environment_light_visual_setting(key: String, value: Variant) -> void:
    if environment_light_controls_syncing or selected_actor.get("class", "") != "Light":
        return
    var defaults := _environment_light_visual_defaults(selected_actor)
    if defaults.is_empty() or not defaults.has(key):
        return
    if key == "color":
        if (typeof(value) != TYPE_COLOR or not is_finite(value.r)
            or not is_finite(value.g) or not is_finite(value.b)
            or not is_finite(value.a)):
            return
        value = Color(value.r, value.g, value.b, 1.0)
    else:
        if typeof(value) != TYPE_FLOAT and typeof(value) != TYPE_INT:
            return
        if not is_finite(float(value)):
            return
        if key == "range":
            value = clampf(float(value), 0.5, 16.0)
        elif key == "energy":
            value = clampf(float(value), 0.05, 2.5)
        else:
            return
    var name := str(selected_actor.get("name", ""))
    if not environment_light_markers.has(name):
        return
    var settings: Dictionary = environment_light_visual_settings.get(name, {})
    settings[key] = value
    environment_light_visual_settings[name] = settings
    _refresh_semi_lit_actor(selected_actor)
    _update_environment_light_selection()
    if status_label != null:
        status_label.text = ("Godot-only preview " + key + " for " + name
            + "; original LightColor/LightShape and GMP are unchanged.")


func _reset_selected_environment_light_visual_settings() -> void:
    if selected_actor.get("class", "") != "Light":
        return
    var name := str(selected_actor.get("name", ""))
    environment_light_visual_settings.erase(name)
    _refresh_semi_lit_actor(selected_actor)
    _update_environment_light_selection()
    if status_label != null:
        status_label.text = ("Reset " + name
            + " preview appearance to source-derived approximation. No GMP changes.")


## Semi-lit mode is a *visual approximation* using existing source actors.
## Reusing nearest source locations rather than creating uncapped lights keeps
## the Godot 4 compatibility renderer usable in dense DX2 maps.
func _semi_lit_has_valid_source_lights() -> bool:
    for actor in actors:
        if (typeof(actor) == TYPE_DICTIONARY
            and actor.get("class", "") == "Light"
            and _environment_light_visual_defaults(actor).size() == 3
            and typeof(_environment_light_original_position(actor)) == TYPE_VECTOR3):
            return true
    return false


func _set_semi_lit_enabled(enabled: bool) -> void:
    if enabled and not _semi_lit_has_valid_source_lights():
        semi_lit_enabled = false
        if semi_lit_toggle != null:
            semi_lit_toggle.set_pressed_no_signal(false)
        if status_label != null:
            status_label.text = "Semi-lit requires original positioned Lights with readable LightColor and LightShape."
    else:
        semi_lit_enabled = enabled
    _apply_semi_lit_global_tone()
    if lighting_preset_select != null and not lighting_controls_syncing:
        if not semi_lit_enabled:
            lighting_preset_select.select(0)
        elif lighting_preset_select.selected == 0:
            lighting_preset_select.select(1)
    semi_lit_last_camera_position = Vector3(INF, INF, INF)
    _refresh_semi_lit_scene()
    _sync_environment_light_live_node()
    if semi_lit_enabled and status_label != null:
        status_label.text = (
            "SEMI-LIT preview uses nearby original source Light actors, "
            + "approximated by Godot. Not native/baked DX2 lighting."
        )


func _clear_semi_lit_nodes() -> void:
    for light in semi_lit_nodes.values():
        if is_instance_valid(light):
            light.free()
    semi_lit_nodes.clear()
    semi_lit_last_source_stats.clear()
    lighting_source_names.clear()
    if lighting_source_list != null:
        lighting_source_list.clear()
    if semi_lit_label != null:
        semi_lit_label.text = ""
    if lighting_diagnostics != null:
        lighting_diagnostics.text = (
            "Semi-lit is OFF; ordinary Godot editor lighting is restored.\n"
            + "Enable Semi-lit to count eligible original map Light actors."
        )


func _refresh_semi_lit_scene() -> void:
    if not semi_lit_enabled or not is_instance_valid(semi_lit_root):
        _clear_semi_lit_nodes()
        return
    var ranked: Array[Dictionary] = []
    var source_light_total := 0
    var explicitly_off := 0
    var missing_source_data := 0
    var names_explicit_off: Array[String] = []
    var names_invalid: Array[String] = []
    var eye := camera.global_position if is_instance_valid(camera) else Vector3.ZERO
    for actor in actors:
        if typeof(actor) != TYPE_DICTIONARY or actor.get("class", "") != "Light":
            continue
        source_light_total += 1
        # Only an explicitly authored false bLightOn is known to be OFF.
        if _environment_game_value(actor, 1487) == false:
            explicitly_off += 1
            names_explicit_off.append(str(actor.get("name", "")))
            continue
        var position: Variant = _environment_light_preview_position(actor)
        var settings: Dictionary = _environment_light_visual_values(actor)
        var name := str(actor.get("name", ""))
        if (typeof(position) != TYPE_VECTOR3 or not position.is_finite()
            or settings.is_empty() or name.is_empty()
            or not environment_light_markers.has(name)):
            missing_source_data += 1
            names_invalid.append(name)
            continue
        ranked.append({
            "name": name, "position": position, "settings": settings,
            "distance2": eye.distance_squared_to(position)
        })
    ranked.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
        if abs(float(a["distance2"]) - float(b["distance2"])) <= 0.000001:
            return str(a["name"]) < str(b["name"])
        return float(a["distance2"]) < float(b["distance2"]))
    var wanted := {}
    var budget := _semi_lit_active_budget()
    var count := mini(ranked.size(), budget)
    for index in range(count):
        var info: Dictionary = ranked[index]
        var name: String = str(info["name"])
        wanted[name] = true
        var node: OmniLight3D = semi_lit_nodes.get(name, null)
        if not is_instance_valid(node):
            node = OmniLight3D.new()
            node.name = "DX2Ed_SemiLit_EDITOR_ONLY_" + name
            node.shadow_enabled = false
            node.set_meta("editor_only", true)
            node.set_meta("source_actor", name)
            semi_lit_root.add_child(node)
            semi_lit_nodes[name] = node
        node.global_position = info["position"]
        node.light_color = info["settings"]["color"]
        node.omni_range = clampf(
            float(info["settings"]["range"]) * semi_lit_radius_multiplier,
            0.125, 64.0)
        node.light_energy = clampf(
            float(info["settings"]["energy"]) * semi_lit_energy_multiplier,
            0.005, 10.0)
    for name in semi_lit_nodes.keys():
        if not wanted.has(name):
            var stale: OmniLight3D = semi_lit_nodes[name]
            if is_instance_valid(stale):
                stale.free()
            semi_lit_nodes.erase(name)
    semi_lit_last_camera_position = eye
    if lighting_source_list != null:
        lighting_source_list.clear()
        lighting_source_names.clear()
        for i in range(mini(ranked.size(), 500)):
            var name := str(ranked[i]["name"])
            lighting_source_list.add_item(
                ("ACTIVE   " if i < count else "LIMITED  ") + name)
            lighting_source_names.append(name)
        for name in names_explicit_off:
            lighting_source_list.add_item("OFF      " + name)
            lighting_source_names.append(name)
        for name in names_invalid:
            lighting_source_list.add_item("INVALID  " + name)
            lighting_source_names.append(name)
    var capped := maxi(0, ranked.size() - count)
    semi_lit_last_source_stats = {
        "total": source_light_total, "eligible": ranked.size(),
        "active": count, "capped": capped, "explicit_off": explicitly_off,
        "missing_data": missing_source_data
    }
    if semi_lit_label != null:
        semi_lit_label.text = (
            " %d/%d eligible source light nodes | %d limited"
            % [count, ranked.size(), capped]
        )
    if lighting_diagnostics != null:
        lighting_diagnostics.text = (
            "Original Light actors: %d\nEligible source lights: %d\n"
            + "Godot light nodes: %d\nExcluded by chosen limit: %d\n"
            + "Explicit bLightOn=false: %d\nMissing/invalid source data: %d\n"
            + ("Only first 500 eligible IDs listed below.\n" if ranked.size() > 500 else "")
            + "Godot Compatibility still limits lights affecting individual meshes; "
            + "these nodes do not recreate DX2 occlusion, shadows, or lightmaps."
        ) % [source_light_total, ranked.size(), count, capped,
            explicitly_off, missing_source_data]


func _refresh_semi_lit_actor(actor: Dictionary) -> void:
    if not semi_lit_enabled or actor.get("class", "") != "Light":
        return
    var name := str(actor.get("name", ""))
    if not semi_lit_nodes.has(name):
        return
    var node: OmniLight3D = semi_lit_nodes[name]
    if not is_instance_valid(node):
        return
    var pos: Variant = _environment_light_preview_position(actor)
    var values := _environment_light_visual_values(actor)
    if typeof(pos) != TYPE_VECTOR3 or values.is_empty():
        return
    node.global_position = pos
    node.light_color = values["color"]
    node.omni_range = clampf(float(values["range"]) * semi_lit_radius_multiplier,
        0.125, 64.0)
    node.light_energy = clampf(float(values["energy"]) * semi_lit_energy_multiplier,
        0.005, 10.0)


func _clear_environment_light_live_node() -> void:
    if is_instance_valid(environment_light_live_node):
        environment_light_live_node.free()
    environment_light_live_node = null


func _sync_environment_light_live_node() -> void:
    if (semi_lit_enabled
        or environment_light_live_toggle == null
        or not environment_light_live_toggle.button_pressed
        or not _environment_light_proxy_selected()
        or not is_instance_valid(world_root)):
        _clear_environment_light_live_node()
        return
    var values := _environment_light_visual_values(selected_actor)
    if values.is_empty():
        _clear_environment_light_live_node()
        return
    if not is_instance_valid(environment_light_live_node):
        environment_light_live_node = OmniLight3D.new()
        environment_light_live_node.name = "DX2Ed_Selected_Light_LIVE_PREVIEW_ONLY"
        environment_light_live_node.shadow_enabled = false
        environment_light_live_node.set_meta("editor_only", true)
        world_root.add_child(environment_light_live_node)
    environment_light_live_node.set_meta("source_actor", str(selected_actor.get("name", "")))
    environment_light_live_node.global_position = _environment_light_preview_position(selected_actor)
    environment_light_live_node.light_color = values["color"]
    environment_light_live_node.omni_range = float(values["range"])
    environment_light_live_node.light_energy = float(values["energy"])


func _light_sphere_wire_mesh(radius: float) -> ArrayMesh:
    var verts := PackedVector3Array()
    var steps := 64
    for plane in range(3):
        for segment in range(steps):
            var a := TAU * float(segment) / float(steps)
            var b := TAU * float(segment + 1) / float(steps)
            var ax := cos(a) * radius
            var ay := sin(a) * radius
            var bx := cos(b) * radius
            var by := sin(b) * radius
            match plane:
                0:
                    verts.append(Vector3(ax, ay, 0))
                    verts.append(Vector3(bx, by, 0))
                1:
                    verts.append(Vector3(0, ax, ay))
                    verts.append(Vector3(0, bx, by))
                _:
                    verts.append(Vector3(ax, 0, ay))
                    verts.append(Vector3(bx, 0, by))
    var arrays := []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = verts
    var mesh := ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_LINES, arrays)
    return mesh


func _clear_environment_light_markers() -> void:
    _clear_semi_lit_nodes()
    environment_light_gizmo_drag = false
    _clear_environment_light_live_node()
    environment_light_visual_settings.clear()
    if environment_light_live_toggle != null:
        environment_light_live_toggle.set_pressed_no_signal(false)
    environment_light_positions.clear()
    for marker in environment_light_markers.values():
        if is_instance_valid(marker):
            marker.queue_free()
    environment_light_markers.clear()
    if is_instance_valid(environment_light_radius):
        environment_light_radius.mesh = null
        environment_light_radius.visible = false
    if environment_light_reset_button != null:
        environment_light_reset_button.disabled = true


func _rebuild_environment_light_markers() -> void:
    _clear_environment_light_markers()
    if not is_instance_valid(environment_light_markers_root):
        return
    var marker_mesh := SphereMesh.new()
    marker_mesh.radius = 0.15
    marker_mesh.height = 0.3
    var material := StandardMaterial3D.new()
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.albedo_color = Color(1.0, 0.77, 0.28, 1.0)
    material.no_depth_test = true
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    for actor in actors:
        if typeof(actor) != TYPE_DICTIONARY or actor.get("class", "") != "Light":
            continue
        var at: Variant = _environment_light_original_position(actor)
        if typeof(at) != TYPE_VECTOR3 or not at.is_finite():
            continue
        var name := str(actor.get("name", ""))
        if name.is_empty() or environment_light_markers.has(name):
            continue
        var marker := MeshInstance3D.new()
        marker.name = "SourceLightMarker_" + name
        marker.mesh = marker_mesh
        marker.material_override = material
        marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        marker.set_meta("editor_only", true)
        marker.set_meta("source_actor", name)
        environment_light_markers_root.add_child(marker)
        marker.global_position = at
        environment_light_markers[name] = marker
    _set_environment_light_markers_visible(
        environment_light_show_markers == null
        or environment_light_show_markers.button_pressed)


func _set_environment_light_markers_visible(enabled: bool) -> void:
    if is_instance_valid(environment_light_markers_root):
        environment_light_markers_root.visible = enabled
    _update_environment_light_selection()
    _update_gizmo_pose()
    if status_label != null:
        status_label.text = (
            "Original Light markers shown (editor-only). Click to select, W to move the visual proxy."
            if enabled else "Original Light markers hidden; native GMP remains unchanged."
        )


func _update_environment_light_selection() -> void:
    if not is_instance_valid(environment_light_radius):
        return
    _refresh_environment_light_visual_controls()
    _sync_environment_light_live_node()
    environment_light_radius.visible = false
    if environment_light_reset_button != null:
        environment_light_reset_button.disabled = not environment_light_positions.has(
            str(selected_actor.get("name", "")))
    if environment_light_audit_button != null:
        environment_light_audit_button.disabled = selected_actor.get("class", "") != "Light"
    if environment_light_preview_button != null:
        environment_light_preview_button.disabled = selected_actor.get("class", "") != "Light"
    if not _environment_light_proxy_selected():
        _update_gizmo_pose()
        return
    var position: Vector3 = _environment_light_preview_position(selected_actor)
    var appearance := _environment_light_visual_values(selected_actor)
    var radius := (float(appearance.get("range", 1.5))
        if not appearance.is_empty() else _environment_light_preview_radius(selected_actor))
    if semi_lit_enabled:
        radius = clampf(radius * semi_lit_radius_multiplier, 0.125, 64.0)
    environment_light_radius.mesh = _light_sphere_wire_mesh(radius)
    environment_light_radius.global_position = position
    environment_light_radius.visible = true
    _update_gizmo_pose()


func _set_environment_light_preview_position(actor: Dictionary, position: Vector3) -> void:
    if actor.get("class", "") != "Light" or not position.is_finite():
        return
    var name := str(actor.get("name", ""))
    if not environment_light_markers.has(name):
        return
    environment_light_positions[name] = position
    var marker: MeshInstance3D = environment_light_markers[name]
    if is_instance_valid(marker):
        marker.global_position = position
    _refresh_semi_lit_actor(actor)
    _update_environment_light_selection()
    _update_gizmo_pose()


func _reset_selected_environment_light_position() -> void:
    if selected_actor.get("class", "") != "Light":
        return
    var name := str(selected_actor.get("name", ""))
    environment_light_positions.erase(name)
    var source: Variant = _environment_light_original_position(selected_actor)
    if typeof(source) == TYPE_VECTOR3 and environment_light_markers.has(name):
        var marker: MeshInstance3D = environment_light_markers[name]
        if is_instance_valid(marker):
            marker.global_position = source
    _refresh_semi_lit_actor(selected_actor)
    _update_environment_light_selection()
    _update_gizmo_pose()
    status_label.text = (
        "Reset editor-only Light marker " + name
        + " to original source Location. No GMP changes exist."
    )


func _pick_environment_light_marker(screen: Vector2) -> String:
    if (not is_instance_valid(environment_light_markers_root)
        or not environment_light_markers_root.visible
        or not is_instance_valid(camera)):
        return ""
    var closest_pixels := 17.0
    var nearest := ""
    for name in environment_light_markers:
        var marker: MeshInstance3D = environment_light_markers[name]
        if (not is_instance_valid(marker) or not marker.is_visible_in_tree()
            or camera.is_position_behind(marker.global_position)):
            continue
        var pixels: Vector2 = camera.unproject_position(marker.global_position)
        var distance := pixels.distance_to(screen)
        if distance < closest_pixels:
            closest_pixels = distance
            nearest = str(name)
    return nearest


func _select_environment_light_from_viewport(name: String) -> void:
    if not actors_by_name.has(name):
        return
    var actor: Dictionary = actors_by_name[name]
    if actor.get("class", "") != "Light":
        return
    if environment_filter != null and not environment_filter.text.is_empty():
        environment_filter.clear()
        _refresh_environment_entities()
    for i in range(environment_visible.size()):
        if str(environment_visible[i].get("name", "")) == name:
            environment_list.select(i)
            _environment_entity_selected(i)
            status_label.text = (
                "Selected original " + name + " in Scene. Drag W arrows for "
                + "editor-only position preview; never a native GMP write."
            )
            return
    select_actor(actor)


## Visual-only source-light visualization. Never a DX2 actor. Never attached
## under imported scene_root or listed among native draft_prop_copies.
func _preview_selected_light_at_target() -> void:
    if selected_actor.get("class", "") != "Light" or world_root == null:
        status_label.text = "Select an original native Light actor first."
        return
    if environment_light_previews.size() >= 8:
        status_label.text = "Limit of 8 temporary editor-only Light previews reached. Clear previews."
        return
    var color_info: Variant = _environment_game_value(selected_actor, 116)
    var shape: Variant = _environment_game_value(selected_actor, 118)
    if typeof(color_info) != TYPE_DICTIONARY or typeof(shape) != TYPE_DICTIONARY:
        status_label.text = "Missing original LightColor/LightShape. Visual preview refused."
        return
    var values := [color_info.get("LightHue", 0), color_info.get("LightSaturation", 0),
        color_info.get("LightBrightness", 0), shape.get("LightRadius", 0)]
    for value in values:
        if typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT:
            status_label.text = "Original LightColor/LightShape contains unsupported values."
            return
        if not is_finite(float(value)) or float(value) < 0.0 or float(value) > 255.0:
            status_label.text = "Original light values exceed source byte ranges."
            return
    if not camera_target.is_finite():
        status_label.text = "Cannot place preview at invalid camera target."
        return
    var preview := OmniLight3D.new()
    preview.name = "DX2EdPreviewOnly_Light_" + str(environment_light_previews.size() + 1)
    preview.light_color = Color.from_hsv(
        float(values[0]) / 255.0,
        float(values[1]) / 255.0, 1.0)
    preview.light_energy = clampf(float(values[2]) / 64.0, 0.05, 2.5)
    # PREVIEW ONLY: No verified Unreal-unit to Godot intensity/range mapping.
    preview.omni_range = clampf(float(values[3]) * 0.12, 0.5, 16.0)
    preview.shadow_enabled = false
    preview.set_meta("editor_only", true)
    preview.set_meta("source_actor", str(selected_actor.get("name", "")))
    world_root.add_child(preview)
    preview.global_position = camera_target
    environment_light_previews.append(preview)
    if environment_light_clear_button != null:
        environment_light_clear_button.disabled = false
    status_label.text = (
        "Editor-only light approximation at camera target from "
        + str(selected_actor.get("name", ""))
        + ". NO GMP actor or native light was created."
    )


func _clear_environment_light_previews() -> void:
    for node in environment_light_previews:
        if is_instance_valid(node):
            node.queue_free()
    environment_light_previews.clear()
    if environment_light_clear_button != null:
        environment_light_clear_button.disabled = true


func _start_environment_light_dependency_audit() -> void:
    var actor: Dictionary = selected_actor
    if (actor.get("class", "") != "Light"
        or int(actor.get("export", -1)) < 1
        or environment_light_audit_thread != null
        or not _native_clone_source_ready()):
        status_label.text = "Light audit needs one original Light from an unchanged source-matched GMP."
        return
    var script := ProjectSettings.globalize_path("res://../package_writer/dx2_light_dependency_audit.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Native Light dependency audit backend not installed."
        return
    var source := last_gmp_path
    var digest := source_gamesys_sha256
    var expected_actor := str(actor.get("name", ""))
    var expected_export := int(actor.get("export", -1))
    environment_light_audit_thread = Thread.new()
    var started := environment_light_audit_thread.start(
        _run_environment_light_dependency_audit.bind(
            script, source, digest, expected_export, expected_actor))
    if started != OK:
        environment_light_audit_thread = null
        status_label.text = "Could not start read-only native Light dependency audit."
        return
    status_label.text = "Checking source Light, PhysicsVolume, Region and native state without writes..."


func _run_environment_light_dependency_audit(script: String, source: String,
        digest: String, actor_export: int, actor_name: String) -> void:
    var args := PackedStringArray([
        script, source, "--source-sha256", digest,
        "--actor-export", str(actor_export)
    ])
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        var pyargs := PackedStringArray(["-3"])
        pyargs.append_array(args)
        output.clear()
        code = OS.execute("py", pyargs, output, true)
    call_deferred("_environment_light_dependency_audit_finished",
        code, "\n".join(output), source, digest, actor_export, actor_name)


func _environment_light_dependency_audit_finished(code: int, raw: String,
        source: String, digest: String, actor_export: int, actor_name: String) -> void:
    if environment_light_audit_thread != null:
        environment_light_audit_thread.wait_to_finish()
        environment_light_audit_thread = null
    if (source != last_gmp_path or digest != source_gamesys_sha256
        or not _native_clone_source_ready()
        or int(selected_actor.get("export", -1)) != actor_export
        or str(selected_actor.get("name", "")) != actor_name):
        status_label.text = "Light audit discarded: source map or selected actor changed."
        return
    var doc: Variant = JSON.parse_string(raw.strip_edges())
    if (code != 0 or typeof(doc) != TYPE_DICTIONARY
        or doc.get("schema") != "DX2Ed-original-light-dependency-audit-v1"
        or doc.get("status") != "read-only-source-verified"
        or doc.get("source_sha256") != digest
        or doc.get("source_map", "").to_lower() != last_gmp_path.get_file().to_lower()
        or doc.get("source_modified") != false
        or doc.get("native_light_spawn_enabled") != false
        or typeof(doc.get("lights")) != TYPE_ARRAY
        or doc["lights"].size() != 1):
        status_label.text = "Light dependency audit refused: " + _native_clone_error_reason(raw)
        return
    var rec: Dictionary = doc["lights"][0]
    if (str(rec.get("actor", "")) != actor_name
        or int(rec.get("export", -1)) != actor_export
        or rec.get("tagged_object_references_checked") != true
        or rec.get("region_for_new_position_verified") != false):
        status_label.text = "Light audit report did not match selected original actor."
        return
    var state: Dictionary = rec.get("state_frame", {})
    var rows: PackedStringArray = [
        "ORIGINAL LIGHT DEPENDENCY AUDIT | SOURCE VERIFIED",
        "Light: " + actor_name + " (export " + str(actor_export) + ")",
        "Original PhysicsVolume: " + str(rec.get("physics_volume", {})),
        "Region.Zone: " + str(rec.get("region_zone", {})),
        "Region.iLeaf: " + str(rec.get("region_leaf", "?")),
        "Region.ZoneNumberLow: " + str(rec.get("region_zone_number_low", "?")),
        "Original LevelInfo reference: " + str(rec.get("level", {})),
        "Native frame: " + str(state),
        "Original map Light actor count: " + str(doc.get("source_light_count", "?")),
        "Distinct source zone numbers: " + str(doc.get("distinct_zone_numbers", [])),
        "",
        "Light creation remains BLOCKED. We do not know how to calculate",
        "BSP leaf + zone for a new position, or initialize native state.",
        "No original GMP or game asset was modified."
    ]
    if environment_details != null:
        environment_details.text = "\n".join(rows)
    status_label.text = "Original Light dependencies verified. New native Light creation correctly remains disabled."


func _environment_sound_values(property_id: int) -> Array[String]:
    # Strictly source-observed values for this exact property; never convert
    # unrelated zone label/actor name fields into fake sound schemas.
    var values: Array[String] = []
    for rec in actors:
        if typeof(rec) != TYPE_DICTIONARY or rec.get("class") != "ZoneProperties":
            continue
        var value: Variant = _environment_game_value(rec, property_id)
        if typeof(value) != TYPE_STRING:
            continue
        var name := str(value)
        if (not name.is_valid_identifier() or name.length() > 95
            or name.to_lower() in ["silence", "inaccessible", "outside_world", "elevator"]):
            continue
        if not values.has(name):
            values.append(name)
    values.sort()
    return values


func _refresh_environment_sound_fields(actor: Dictionary) -> void:
    if environment_sound_field == null:
        return
    environment_sound_field.clear()
    environment_sound_schema.clear()
    environment_sound_field.disabled = true
    environment_sound_schema.disabled = true
    environment_sound_button.disabled = true
    if actor.get("class", "") != "ZoneProperties":
        return
    for pid in [1287, 1286, 1467]:
        var original: Variant = _environment_game_value(actor, pid)
        if typeof(original) != TYPE_STRING:
            continue
        var choices := _environment_sound_values(pid)
        if choices.size() < 2 or not choices.has(str(original)):
            continue
        var label := ("StreamSchema1" if pid == 1287 else "StreamSchema2" if pid == 1286 else "NonStreamSchema1")
        environment_sound_field.add_item(label + ": " + str(original), pid)
    if environment_sound_field.item_count > 0:
        environment_sound_field.disabled = false
        environment_sound_field.select(0)
        _refresh_environment_sound_replacements()


func _refresh_environment_sound_replacements() -> void:
    if environment_sound_schema == null:
        return
    environment_sound_schema.clear()
    environment_sound_schema.disabled = true
    environment_sound_button.disabled = true
    if environment_sound_field == null or environment_sound_field.selected < 0:
        return
    var actor: Dictionary = selected_actor
    if actor.get("class", "") != "ZoneProperties":
        return
    var pid := environment_sound_field.get_selected_id()
    var original: Variant = _environment_game_value(actor, pid)
    if typeof(original) != TYPE_STRING:
        return
    for candidate in _environment_sound_values(pid):
        if candidate != str(original):
            environment_sound_schema.add_item(candidate)
    if environment_sound_schema.item_count > 0:
        environment_sound_schema.disabled = false
        environment_sound_schema.select(0)
        environment_sound_button.disabled = false


func _environment_sound_plan() -> Dictionary:
    if environment_sound_field == null or environment_sound_schema == null:
        return {}
    var actor: Dictionary = selected_actor
    if (actor.get("class", "") != "ZoneProperties"
        or environment_sound_field.selected < 0
        or environment_sound_schema.selected < 0):
        return {}
    var pid := environment_sound_field.get_selected_id()
    if pid not in [1287, 1286, 1467]:
        return {}
    var expected: Variant = _environment_game_value(actor, pid)
    var replacement := environment_sound_schema.get_item_text(environment_sound_schema.selected)
    if (typeof(expected) != TYPE_STRING
        or replacement == str(expected)
        or not _environment_sound_values(pid).has(replacement)
        or int(actor.get("export", -1)) < 1):
        return {}
    return {
        "actor": str(actor.get("name", "")),
        "export": int(actor.get("export", -1)),
        "property_id": pid, "expect": str(expected),
        "replace": replacement
    }


func _environment_sound_clean_draft() -> bool:
    if (not draft_prop_copies.is_empty()
        or not draft_brush_specs.is_empty()
        or not property_overrides.is_empty()
        or not draft_template_provenance.is_empty()):
        return false
    for name in original_mesh_transforms:
        if meshes_by_actor.has(name):
            var node: MeshInstance3D = meshes_by_actor[name]
            if (is_instance_valid(node)
                and not node.global_transform.is_equal_approx(original_mesh_transforms[name])):
                return false
    return true


func _open_environment_sound_dialog() -> void:
    _finish_gizmo_drag()
    environment_sound_pending.clear()
    if not _native_clone_source_ready() or not _environment_sound_clean_draft():
        status_label.text = "Sound zone Save As requires an unchanged original map and no unrelated draft edits."
        return
    if _environment_sound_plan().is_empty():
        status_label.text = "Select an original ZoneProperties source with a verified alternative sound schema."
        return
    var script := ProjectSettings.globalize_path("res://../package_writer/dx2_zone_sound_probe.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Experimental native ZoneProperties sound writer not installed."
        return
    environment_sound_dialog.current_file = last_gmp_path.get_file()
    environment_sound_dialog.popup_centered_ratio(0.75)


func _stage_environment_sound_export(destination: String) -> void:
    environment_sound_pending.clear()
    if not _native_clone_source_ready() or not _environment_sound_clean_draft():
        status_label.text = "Sound zone edit refused: source map or draft state changed."
        return
    var plan := _environment_sound_plan()
    if (plan.is_empty() or destination.get_file().to_lower() != last_gmp_path.get_file().to_lower()):
        status_label.text = "Sound zone edit refused: source selection or output map filename invalid."
        return
    environment_sound_pending = plan.duplicate(true)
    environment_sound_pending["source"] = last_gmp_path
    environment_sound_pending["source_sha256"] = source_gamesys_sha256
    environment_sound_pending["destination"] = destination
    environment_sound_confirmation.dialog_text = (
        "EXPERIMENTAL: replace ONE original sound schema field."
        + "\nActor: " + str(plan["actor"]) + " | export " + str(plan["export"])
        + "\nGameSys property " + str(plan["property_id"])
        + "\nFrom: " + str(plan["expect"]) + "\nTo: " + str(plan["replace"])
        + "\n\nNew GMP: " + destination
        + "\nOriginal map untouched. No game installation writes."
        + "\nSound effect has NOT been confirmed in retail gameplay."
    )
    environment_sound_confirmation.popup_centered(Vector2i(760, 350))


func _execute_environment_sound_export() -> void:
    if environment_sound_pending.is_empty() or not _native_clone_source_ready() or not _environment_sound_clean_draft():
        environment_sound_pending.clear()
        status_label.text = "Sound zone Save As refused: original source or editor state changed."
        return
    var frozen := environment_sound_pending.duplicate(true)
    environment_sound_pending.clear()
    if (str(frozen["source"]) != last_gmp_path
        or str(frozen["source_sha256"]) != source_gamesys_sha256
        or _environment_sound_plan() != {
            "actor": frozen["actor"], "export": frozen["export"],
            "property_id": frozen["property_id"],
            "expect": frozen["expect"], "replace": frozen["replace"]
        }):
        status_label.text = "Sound zone export cancelled: actor, field or source changed."
        return
    var script := ProjectSettings.globalize_path("res://../package_writer/dx2_zone_sound_probe.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Sound zone writer unavailable."
        return
    native_export_thread = Thread.new()
    var started := native_export_thread.start(_run_environment_sound_export.bind(script, frozen))
    if started != OK:
        native_export_thread = null
        status_label.text = "Could not start sound zone writer."
        return
    status_label.text = "Verifying original sound zone property and writing isolated GMP..."


func _run_environment_sound_export(script: String, frozen: Dictionary) -> void:
    var args := PackedStringArray([
        script, str(frozen["source"]), "--source-sha256",
        str(frozen["source_sha256"]), "--actor-export", str(frozen["export"]),
        "--actor-name", str(frozen["actor"]), "--property-id",
        str(frozen["property_id"]), "--expect", str(frozen["expect"]),
        "--replace", str(frozen["replace"]),
        "--output", str(frozen["destination"])
    ])
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        var pyargs := PackedStringArray(["-3"])
        pyargs.append_array(args)
        output.clear()
        code = OS.execute("py", pyargs, output, true)
    call_deferred("_environment_sound_export_finished", code, "\n".join(output))


func _environment_sound_export_finished(code: int, response: String) -> void:
    if native_export_thread != null:
        native_export_thread.wait_to_finish()
        native_export_thread = null
    var doc: Variant = JSON.parse_string(response.strip_edges())
    if (code == 0 and typeof(doc) == TYPE_DICTIONARY
        and doc.get("schema") == "DX2Ed-experimental-existing-zone-schema-v1"
        and doc.get("status") == "isolated-gmp-written-runtime-unverified"
        and doc.get("reverse_payload_parity") == true
        and doc.get("original_exports_preserved_except_target") == true
        and doc.get("source_modified") == false):
        status_label.text = (
            "Verified isolated sound-zone GMP: " + str(doc.get("output", ""))
            + " | One source schema changed. Retail sound effect unverified."
        )
        return
    status_label.text = "Experimental sound zone export refused: " + _native_clone_error_reason(response)


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
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
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


## Original .ski metadata helps future skeletal assembly but contains
## neither decoded vertices/bone weights nor verified actor-to-model links.
func _skeletal_source_description(name: String) -> String:
    var records: Variant = skeletal_inventory.get("records", [])
    if typeof(records) != TYPE_ARRAY:
        return "Open original SkeletalMeshes.zip to inspect .ski links."
    for record in records:
        if (typeof(record) == TYPE_DICTIONARY
            and str(record.get("name", "")).to_lower() == name.to_lower()):
            return (
                "Original SKI version: " + str(record.get("version", "unknown"))
                + "\nMatching .pro in ZIP: " + str(record.get("pro_present", false))
                + "\nDeclared animation sets: " + str(record.get("animation_sets", []))
                + "\nOriginal SKI offset: " + str(record.get("position", []))
                + "\nOriginal SKI scale: " + str(record.get("scale", []))
                + "\nActor-to-skeleton mapping NOT verified."
            )
    return "No matching .ski descriptor loaded (IBD asset may be bundled separately)."


func _open_original_skeletal_zip(path: String) -> void:
    if path.get_extension().to_lower() != "zip" or not FileAccess.file_exists(path):
        status_label.text = "Choose an existing original SkeletalMeshes.zip."
        return
    var script := ProjectSettings.globalize_path(
        "res://backend/dx2_skeletal_ski_inventory.py")
    if not FileAccess.file_exists(script):
        status_label.text = "Read-only SKI metadata parser unavailable."
        return
    var args := PackedStringArray([script, path])
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        output.clear()
        code = OS.execute("py", PackedStringArray(["-3", script, path]), output, true)
    var parsed: Variant = JSON.parse_string("\n".join(output))
    if (code != 0 or typeof(parsed) != TYPE_DICTIONARY
        or parsed.get("schema", "") != "DX2Ed-original-skeletal-ski-inventory-v1"
        or parsed.get("read_only") != true
        or parsed.get("npc_spawn_enabled") != false
        or parsed.get("geometry_decoded") != false
        or typeof(parsed.get("records", null)) != TYPE_ARRAY
        or parsed["records"].size() > 2000):
        skeletal_inventory.clear()
        status_label.text = "Source-only skeletal metadata rejected; check original ZIP and Python 3."
        return
    skeletal_inventory = parsed
    if not selected_asset.is_empty():
        for index in range(assets_visible.size()):
            if (str(assets_visible[index].get("name", "")) == str(selected_asset.get("name", ""))
                and str(assets_visible[index].get("kind", "")) == str(selected_asset.get("kind", ""))):
                _asset_selected(index)
                break
    status_label.text = ("Read %d original .ski descriptors (metadata only). "
        + "No NPC geometry, animation or gameplay was imported.") % int(parsed.get("record_count", 0))


func _load_asset_catalog(path: String) -> void:
    asset_catalog.clear()
    selected_asset.clear()
    if native_asset_place_button != null:
        native_asset_place_button.disabled = true
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
        7: return kind == "skeletalmesh"
        8: return kind == "skeletalanim"
        _: return kind not in ["staticmesh", "texture", "matlib", "physicshull", "triggerscriptdef", "skeletalmesh", "skeletalanim"]


func _refresh_asset_list() -> void:
    if asset_list == null:
        return
    asset_list.clear()
    assets_visible.clear()
    if native_asset_place_button != null:
        native_asset_place_button.disabled = true
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
    var native_candidate := _native_asset_source_for(name)
    if native_asset_place_button != null:
        native_asset_place_button.disabled = native_candidate.is_empty()
    var skeletal := str(selected_asset.get("kind", "")) in ["skeletalmesh", "skeletalanim"]
    asset_details.text = (
        "Name: " + name +
        "\nKind: " + str(selected_asset.get("kind", "")) +
        "\nSource: " + str(selected_asset.get("bundle", "")) +
        "\nResource index: " + str(selected_asset.get("resource_index", "?")) +
        "\nBytes: " + str(selected_asset.get("bytes", "?")) +
        "\nPlaced actors: " + str(placed.size()) +
        "\nNative reuse source: " + (
            str(native_candidate.get("name", "?")) + " (export " + str(native_candidate.get("export", "?")) + ")"
            if not native_candidate.is_empty() else "Unavailable; only preview placement possible"
        ) +
        ("\nSKELETAL RESOURCE (source metadata only). "
         + "Body bones, skin weights and animation are not decoded; "
         + "static-mesh preview and native spawn are NOT supported.\n"
         + _skeletal_source_description(name) if skeletal else
         "\nPlace preview = editor-only. Place native copy = uses verified original actor; isolated GMP export still required.")
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
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
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



## Use the Assets list for real native prop placement when a verified
## original StaticMeshActor already references this exact mesh resource.
## This never fabricates a new StaticMesh resource reference or collision.
func _native_asset_source_for(resource_name: String) -> Dictionary:
    var catalog_item := _asset_record(resource_name)
    if catalog_item.is_empty() or str(catalog_item.get("kind", "")) != "staticmesh":
        return {}
    var chosen: Dictionary = {}
    for source in _placed_instances_for_asset(resource_name):
        if typeof(source) != TYPE_DICTIONARY:
            continue
        var source_name := str(source.get("name", ""))
        if (str(source.get("class", "")) != "StaticMeshActor"
            or int(source.get("export", -1)) < 1
            or not meshes_by_actor.has(source_name)
            or not original_mesh_transforms.has(source_name)):
            continue
        var mesh_node: MeshInstance3D = meshes_by_actor[source_name]
        if not is_instance_valid(mesh_node) or mesh_node.mesh == null:
            continue
        if chosen.is_empty() or int(source["export"]) < int(chosen["export"]):
            chosen = source
    return chosen


func _native_asset_target_pose(source_name: String, target: Vector3) -> Transform3D:
    var original_pose: Transform3D = original_mesh_transforms[source_name]
    var difference := target - original_pose.origin
    var max_translation := 4095.0 * NATIVE_CLONE_UNREAL_METRES
    # The first position is the camera target when safely serializable.
    # Never silently extrapolate an impossibly distant placement. Start
    # a metre from the original if the camera is in a different region.
    if (not difference.is_finite()
        or difference.length_squared() < 0.0000001
        or abs(difference.x) >= max_translation
        or abs(difference.y) >= max_translation
        or abs(difference.z) >= max_translation):
        target = original_pose.origin + Vector3(1.0, 0.0, 0.0)
    return Transform3D(original_pose.basis, target)


func _place_asset_as_native_copy() -> void:
    var name := str(selected_asset.get("name", ""))
    if scene_root == null or not _native_clone_source_ready():
        status_label.text = "Native asset placement needs an unchanged original GMP and finished import."
        return
    var source_actor := _native_asset_source_for(name)
    if source_actor.is_empty():
        status_label.text = (
            "No original StaticMeshActor uses " + name
            + " in this map. Preview-only placement still works; new asset references aren't supported yet."
        )
        return
    if draft_prop_copies.size() >= 8:
        status_label.text = "Native Save As supports at most eight draft copies. Save a batch or Restore All."
        return
    var name_of_source := str(source_actor.get("name", ""))
    var checker := ProjectSettings.globalize_path("res://../package_writer/dx2_actor_clone_probe.py")
    if not FileAccess.file_exists(checker):
        status_label.text = "Native source verification backend is unavailable."
        return
    var checked := _native_clone_check_actor(checker, {
        "actor": name_of_source, "export": int(source_actor["export"])
    })
    if checked.get("eligible", false) != true:
        status_label.text = (
            "Native placement refused for " + name_of_source + ": "
            + str(checked.get("reason", "Original source is not eligible."))
        )
        return
    var history_before := _capture_edit_state()
    var draft_name := "DraftProp_" + str(next_prop_copy_id)
    var placement := _native_asset_target_pose(name_of_source, camera_target)
    var copy := _new_draft_copy(name_of_source, draft_name, placement)
    if not is_instance_valid(copy):
        status_label.text = "Could not create source-verified native preview from " + name_of_source
        return
    next_prop_copy_id += 1
    _clear_selection()
    _add_selection_mesh(copy)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    _record_edit("Place native asset " + name + " from " + name_of_source, history_before)
    status_label.text = (
        "Native draft " + draft_name + " uses original " + name_of_source
        + " (export " + str(source_actor["export"]) + "). Use ONE Duplicate Save As "
        + "(or MULTI for 2-8) to write an isolated GMP. Original game unchanged."
    )


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
    if bsp_hide_preview_button != null:
        var selected_bsp := (available and _selection_nodes()[0] is MeshInstance3D
            and str(_selection_nodes()[0].name).begins_with("BSP_"))
        bsp_hide_preview_button.disabled = (bsp_hidden_preview.is_empty() and not selected_bsp)
        bsp_hide_preview_button.text = (
            "Restore hidden BSP (" + str(bsp_hidden_preview.size()) + ")"
            if not bsp_hidden_preview.is_empty() else "Hide selected BSP (preview)"
        )


## Reversible scene-visibility operation only. Does NOT remove BSP from GLB,
## package files, actor metadata, or the native writer's source set.
func _restore_bsp_preview_visibility() -> void:
    for node in bsp_hidden_preview:
        if is_instance_valid(node):
            node.visible = bool(bsp_hidden_preview[node])
    bsp_hidden_preview.clear()
    _refresh_geometry_debug_buttons()


func _toggle_bsp_preview_visibility() -> void:
    if not bsp_hidden_preview.is_empty():
        _restore_bsp_preview_visibility()
        if status_label != null:
            status_label.text = "Original BSP viewport visibility restored. No game files edited."
        return
    if not geometry_isolation_visibility.is_empty():
        if status_label != null:
            status_label.text = "End geometry isolation before temporarily hiding BSP."
        return
    var nodes := _selection_nodes()
    if nodes.size() != 1 or not is_instance_valid(nodes[0]):
        return
    var target: MeshInstance3D = nodes[0]
    if not str(target.name).begins_with("BSP_") or not all_mesh_instances.has(target):
        return
    bsp_hidden_preview[target] = target.visible
    target.visible = false
    _clear_selection()
    _refresh_inspector_panel()
    if status_label != null:
        status_label.text = ("Temporarily hid " + str(target.name)
            + " in the Godot viewport only. Click Restore hidden BSP to bring it back.")


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
    if _actor_on_original_ai_layer(current_actor):
        var tag: Variant = _environment_game_value(current_actor, 41)
        var skin: Variant = _environment_game_value(current_actor, 1659)
        inspector_summary.text += (
            "\nOriginal SkeletalTag (41): "
            + (str(tag) if tag != null else "not serialized on this actor")
            + "\nOriginal MaterialSkin (1659): "
            + (str(skin) if skin != null else "not serialized on this actor")
            + "\nThese are per-actor observations only; inherited class defaults "
            + "and skeletal rendering are not reconstructed."
        )
    var eligible := _draft_selected_is_prop()
    inspector_transform_section.visible = eligible
    _refresh_actor_property_editor()
    _refresh_source_gamesys_inspector()
    _update_workbench_handoff_button()
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



func _source_scene_workbench_candidate() -> Dictionary:
    # Visual preview mesh identity is not enough: source-only native fields
    # require this exact imported actor, class and original GMP/actors cache.
    if (multi_native_scalar_panel == null
        or selected_meshes.size() != 1
        or not is_instance_valid(selected_mesh)
        or last_gmp_path.is_empty()
        or loaded_actors_json_path.is_empty()):
        return {}
    var actor_name := str(selected_mesh.name)
    if (not meshes_by_actor.has(actor_name)
        or meshes_by_actor[actor_name] != selected_mesh
        or not actors_by_name.has(actor_name)):
        return {}
    return SceneActorWorkbenchBridge.candidate(
        selected_actor, actors_by_name[actor_name],
        actor_name, selected_meshes.size(),
        current_source_map_name, last_gmp_path.get_file(),
        source_gamesys_sha256, str(multi_native_scalar_panel.source_sha256),
        loaded_actors_json_path, str(multi_native_scalar_panel.actors_file))


func _update_workbench_handoff_button() -> void:
    if workbench_handoff_button != null:
        workbench_handoff_button.disabled = _source_scene_workbench_candidate().is_empty()


func _open_selected_source_in_workbench() -> void:
    var source := _source_scene_workbench_candidate()
    if source.is_empty():
        status_label.text = (
            "Actor Workbench requires one original source StaticMeshActor mesh,"
            + " matching GMP and private actors.json. Draft/BSP/group selection refused.")
        return
    if not multi_native_scalar_panel.request_viewport_actor(source):
        status_label.text = "Actor Workbench refused: source GMP/cache changed or actor not verified."
        return
    if workbench_tabs != null:
        workbench_tabs.current_tab = workbench_tabs.get_tab_idx_from_control(
            multi_native_scalar_panel)
    status_label.text = ("Inspecting original source actor " + str(source["actor"])
        + " export #" + str(source["export"])
        + " in Actor Workbench (read-only source reload).")


func _sync_scene_to_workbench_when_open() -> void:
    if (multi_native_scalar_panel == null or workbench_tabs == null
        or workbench_tabs.current_tab !=
            workbench_tabs.get_tab_idx_from_control(multi_native_scalar_panel)):
        return
    var candidate := _source_scene_workbench_candidate()
    if not candidate.is_empty():
        multi_native_scalar_panel.request_viewport_actor(candidate)


func _select_mesh_only(mesh_instance: MeshInstance3D) -> void:
    _clear_selection()
    _add_selection_mesh(mesh_instance)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    _sync_scene_to_workbench_when_open()


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
    _sync_scene_to_workbench_when_open()


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
    _update_environment_light_selection()
    _sync_scene_to_workbench_when_open()


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
    _update_environment_light_selection()



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
    if environment_light_gizmo_drag:
        environment_light_gizmo_drag = false
        gizmo_undo_before.clear()
        status_label.text = (
            "Light gizmo preview positioned. Editor-only: no native DX2 Light moved or saved."
        )
        return
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
        _refresh_brush_face_outline()
        return
    var spec: Dictionary = draft_brush_specs[str(nodes[0].name)]
    brush_inspector_syncing = true
    for axis in range(3):
        brush_inspector_sizes[axis].set_value_no_signal(float(spec["size"][axis]))
    brush_inspector_steps.set_value_no_signal(float(spec["steps"]))
    brush_inspector_steps.editable = spec["kind"] == "Stairs"
    if brush_face_controls != null:
        var can_face_edit := BrushGeometry.FACE_EDIT_KINDS.has(str(spec["kind"]))
        brush_face_controls.visible = can_face_edit
        if brush_face_hint != null:
            brush_face_hint.visible = can_face_edit
    brush_inspector_syncing = false
    _refresh_brush_face_outline()


func _brush_face_selected(_index: int) -> void:
    _refresh_brush_face_outline()


## Highlight is a temporary 8-vertex line overlay parented only to the
## selected authored draft mesh. It is NOT added to imported geometry,
## actor lists, source preview caches or private draft Save/Load records.
func _refresh_brush_face_outline() -> void:
    var nodes := _selection_nodes()
    var target: MeshInstance3D = null
    if nodes.size() == 1 and brush_face_selector != null:
        var candidate: MeshInstance3D = nodes[0]
        if (is_instance_valid(candidate) and draft_brush_specs.has(str(candidate.name))
            and draft_prop_copies.has(str(candidate.name))):
            var spec: Dictionary = draft_brush_specs[str(candidate.name)]
            if (BrushGeometry.FACE_EDIT_KINDS.has(str(spec.get("kind", "")))
                and str(draft_prop_sources.get(str(candidate.name), "")) ==
                    "Brush::" + str(spec["kind"])):
                target = candidate
    if is_instance_valid(brush_face_outline) and (
            not is_instance_valid(target)
            or brush_face_outline.get_parent() != target):
        brush_face_outline.free()
        brush_face_outline = null
    if not is_instance_valid(target):
        return
    var face := brush_face_selector.selected
    var wire := BrushGeometry.face_outline_mesh(
        draft_brush_specs[str(target.name)], face)
    if wire.get_surface_count() != 1:
        return
    if not is_instance_valid(brush_face_outline):
        brush_face_outline = MeshInstance3D.new()
        brush_face_outline.name = "DX2Ed_DraftFaceOutline_EDITOR_ONLY"
        brush_face_outline.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        brush_face_outline.set_meta("editor_only", true)
        var ink := StandardMaterial3D.new()
        ink.albedo_color = Color(1.0, 0.74, 0.10, 1.0)
        ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
        ink.no_depth_test = true
        ink.cull_mode = BaseMaterial3D.CULL_DISABLED
        brush_face_outline.material_override = ink
        target.add_child(brush_face_outline)
    brush_face_outline.mesh = wire


## Face-pick gesture is explicit Alt+Shift+LEFT click on an already
## selected editor-created cuboid. This never changes the selected mesh and
## cannot target source BSP or original StaticMeshActor triangles.
func _can_pick_selected_draft_face() -> bool:
    var nodes := _selection_nodes()
    if nodes.size() != 1 or brush_face_selector == null:
        return false
    var name := str(nodes[0].name)
    if not draft_prop_copies.has(name) or not draft_brush_specs.has(name):
        return false
    var spec: Dictionary = draft_brush_specs[name]
    return (BrushGeometry.FACE_EDIT_KINDS.has(str(spec.get("kind", "")))
        and str(draft_prop_sources.get(name, "")) == "Brush::" + str(spec["kind"])
        and is_instance_valid(nodes[0]) and nodes[0].mesh != null
        and nodes[0].is_visible_in_tree())


func _pick_selected_draft_face_ray(origin: Vector3, direction: Vector3) -> bool:
    if not _can_pick_selected_draft_face():
        return false
    var node: MeshInstance3D = _selection_nodes()[0]
    var hit: Dictionary = BrushGeometry.pick_draft_face(
        draft_brush_specs[str(node.name)], node.global_transform,
        origin, direction)
    if hit.is_empty():
        return false
    brush_face_selector.select(int(hit["face_index"]))
    _refresh_brush_face_outline()
    status_label.text = (
        "Picked draft " + str(node.name) + " face " + str(hit["label"])
        + " at " + str(hit["world_point"])
        + ". Use Face In/Out to resize, Ctrl+Z to undo. Native BSP unchanged.")
    return true


func _pick_selected_draft_face_from_viewport() -> void:
    var ray: Dictionary = _mouse_ray(view_container.get_local_mouse_position())
    if ray.is_empty() or not _pick_selected_draft_face_ray(
            ray["origin"], ray["direction"]):
        status_label.text = (
            "No face on selected Box/Wall/Floor under cursor. "
            + "Select one draft brush, then Alt+Shift+click its face.")


func _change_brush_face(side: float) -> void:
    # Only a single editor-created box/wall/floor brush. Never pick a native
    # BSP triangle or move an imported original StaticMeshActor through here.
    var nodes := _selection_nodes()
    if nodes.size() != 1 or brush_face_selector == null:
        return
    var node: MeshInstance3D = nodes[0]
    var name := str(node.name)
    if (not draft_brush_specs.has(name)
        or not draft_prop_copies.has(name)
        or str(draft_prop_sources.get(name, "")) != "Brush::" + str(draft_brush_specs[name].get("kind", ""))):
        return
    var step := float(ortho_grid_step)
    if not is_finite(step) or step < 0.25 or step > 64.0:
        return
    if side != -1.0 and side != 1.0:
        return
    var face := brush_face_selector.selected
    var result: Dictionary = BrushGeometry.face_resize(
        draft_brush_specs[name], face, side * step)
    if result.is_empty():
        status_label.text = "Face resize refused: invalid dimension or preview-only brush type."
        return
    var before := _capture_edit_state()
    # Local face center offset follows the preview's existing basis, so even
    # rotated/scaled draft brushes keep the *opposite local face* in place.
    var world_offset: Vector3 = node.global_transform.basis * result["center_offset_local"]
    if not world_offset.is_finite():
        status_label.text = "Face resize refused: nonfinite preview transform."
        return
    if not _set_brush_spec(name, result["spec"]):
        status_label.text = "Face resize refused: invalid preview brush."
        return
    node.global_position += world_offset
    _refresh_prop_inspection()
    _record_edit("Face " + str(result["face"]) + " " + (
        "out" if side > 0.0 else "in") + " (draft only)", before)
    status_label.text = (
        "Resized draft face " + str(result["face"]) + " by "
        + str(side * step) + " m. Opposite face fixed; Undo available. "
        + "Original DX2 GMP/BSP unchanged.")


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
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
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
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
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
    var code := OS.execute(PythonRuntime.executable(), args, stdout, true)
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
    var code := OS.execute(PythonRuntime.executable(), args, stdout, true)
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
    var status := OS.execute(PythonRuntime.executable(), args, output, true)
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
    var status := OS.execute(PythonRuntime.executable(), args, stdout, true)
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


## Editor-only workspace settings are stored alongside private JSON drafts.
## Never interpreted as source map data or native export instructions.
func _validated_draft_workspace(value: Variant) -> Variant:
    if typeof(value) != TYPE_DICTIONARY:
        return null
    if value.size() != 3 or not value.has("view_mode") or not value.has("grid_step") or not value.has("grid_enabled"):
        return null
    if typeof(value["view_mode"]) != TYPE_STRING or not OrthoGuides.valid_mode(value["view_mode"]):
        return null
    if typeof(value["grid_step"]) != TYPE_FLOAT and typeof(value["grid_step"]) != TYPE_INT:
        return null
    var step := float(value["grid_step"])
    if not is_finite(step) or step < 0.25 or step > 64.0:
        return null
    if typeof(value["grid_enabled"]) != TYPE_BOOL:
        return null
    return {"view_mode": value["view_mode"], "grid_step": step, "grid_enabled": value["grid_enabled"]}


## Transactional private JSON save. Stage and close the entire new document before
## moving the previous copy aside. Never truncate an existing draft on a failed
## write. A successful replacement retains the previous version as .bak.
## Only called with a user:// private draft path, never a GMP/IBD path.
func _write_private_draft_transaction(path: String, payload: String) -> bool:
    if path.is_empty() or not path.begins_with(ProjectSettings.globalize_path("user://prop_drafts") + "/") or path.get_extension() != "json":
        return false
    var pending := path + ".pending"
    var backup := path + ".bak"
    # Do not silently destroy a pending document from a previous interrupted save.
    if FileAccess.file_exists(pending):
        return false
    var output := FileAccess.open(pending, FileAccess.WRITE)
    if output == null:
        return false
    output.store_string(payload)
    output.flush()
    output.close()
    var staged := FileAccess.open(pending, FileAccess.READ)
    if staged == null:
        DirAccess.remove_absolute(pending)
        return false
    var verified := staged.get_as_text() == payload
    staged.close()
    if not verified:
        DirAccess.remove_absolute(pending)
        return false
    var had_original := FileAccess.file_exists(path)
    if had_original:
        # Existing backup is superseded only after the new payload is staged.
        if FileAccess.file_exists(backup) and DirAccess.remove_absolute(backup) != OK:
            DirAccess.remove_absolute(pending)
            return false
        if DirAccess.rename_absolute(path, backup) != OK:
            DirAccess.remove_absolute(pending)
            return false
    if DirAccess.rename_absolute(pending, path) != OK:
        if had_original:
            DirAccess.rename_absolute(backup, path)
        return false
    return true


## Draft-only source-aware editable selection identities. Preflight every name
## before resetting the current scene so malformed saved selections are refused.
func _validated_draft_selection(value: Variant, copies: Array) -> Variant:
    if typeof(value) != TYPE_ARRAY or value.size() > 10000:
        return null
    var allowed := {}
    for name in meshes_by_actor:
        if actors_by_name.has(name) and is_instance_valid(meshes_by_actor[name]):
            allowed[str(name)] = true
    for entry in copies:
        if typeof(entry) != TYPE_DICTIONARY or typeof(entry.get("name", null)) != TYPE_STRING:
            return null
        allowed[entry["name"]] = true
    var seen := {}
    var result: Array[String] = []
    for name in value:
        if typeof(name) != TYPE_STRING or not allowed.has(name) or seen.has(name):
            return null
        seen[name] = true
        result.append(name)
    return result


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
        "property_edits": _serialize_property_edits(),
        "selection": selected_meshes.keys().map(func(name): return str(name)),
        "workspace": {"view_mode": editor_view_mode, "grid_step": ortho_grid_step,
                      "grid_enabled": ortho_grid_enabled}
    }
    if not _write_private_draft_transaction(path, JSON.stringify(document, "  ")):
        status_label.text = "Private draft save failed; existing draft preserved: " + path
        return
    status_label.text = "Saved " + str(moved.size()) + " moved props, " + str(copies.size()) + " copies and " + str(document["property_edits"].size()) + " actor property overrides (not GMP)."

## Reject missing, ambiguous and unbuildable private draft records BEFORE clearing
## current editor state. Source-only validation; never authorizes native GMP writes.
func _draft_record_preflight(moved: Array, copies: Array) -> String:
    var seen_moves := {}
    for entry in moved:
        if typeof(entry) != TYPE_DICTIONARY or typeof(entry.get("actor", null)) != TYPE_STRING:
            return "Invalid moved actor identity."
        var name: String = entry["actor"]
        if seen_moves.has(name) or not actors_by_name.has(name) or not meshes_by_actor.has(name):
            return "Duplicate or unmatched moved actor."
        var node: Variant = meshes_by_actor[name]
        if not is_instance_valid(node) or not (node is MeshInstance3D):
            return "Moved actor has no live preview mesh."
        seen_moves[name] = true
    var seen_copies := {}
    for entry in copies:
        if typeof(entry) != TYPE_DICTIONARY or typeof(entry.get("name", null)) != TYPE_STRING or typeof(entry.get("from_actor", null)) != TYPE_STRING:
            return "Invalid draft copy identity."
        var name: String = entry["name"]
        var source: String = entry["from_actor"]
        var suffix := name.trim_prefix("DraftProp_")
        if (not name.begins_with("DraftProp_") or not suffix.is_valid_int()
            or int(suffix) < 1 or seen_copies.has(name)):
            return "Duplicate or invalid draft copy name."
        if not _draft_source_is_valid(source):
            return "Draft copy source is unavailable."
        if source.begins_with("AssetMesh::"):
            # Existing catalog entry alone is insufficient to reconstruct a copy.
            # A local preview GLB must be available before mutating editor state.
            if not _load_asset_mesh(source.trim_prefix("AssetMesh::")):
                return "Draft asset preview mesh is unavailable."
        elif actors_by_name.has(source):
            var node: Variant = meshes_by_actor.get(source, null)
            if not is_instance_valid(node) or not (node is MeshInstance3D) or node.mesh == null:
                return "Draft original source mesh is unavailable."
        seen_copies[name] = true
    return ""


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
    var record_error := _draft_record_preflight(moved, copies)
    if not record_error.is_empty():
        status_label.text = "Prop draft refused: " + record_error + " Nothing loaded."
        return
    # Legacy drafts without workspace metadata remain readable.
    # Refuse malformed workspace records before clearing any editor edits.
    var workspace: Variant = {}
    if doc.has("workspace"):
        workspace = _validated_draft_workspace(doc["workspace"])
        if workspace == null:
            status_label.text = "Prop draft has invalid editor workspace settings; nothing loaded."
            return
    var saved_selection: Variant = []
    if doc.has("selection"):
        saved_selection = _validated_draft_selection(doc["selection"], copies)
        if saved_selection == null:
            status_label.text = "Prop draft has invalid or duplicate preview selection; nothing loaded."
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
    for selected_name in saved_selection:
        var selected_node: Variant = draft_prop_copies.get(
            selected_name, meshes_by_actor.get(selected_name, null))
        if is_instance_valid(selected_node) and selected_node is MeshInstance3D:
            _add_selection_mesh(selected_node)
    _refresh_selection_inspector()
    _sync_actor_list_selection()
    if not workspace.is_empty():
        ortho_grid_enabled = workspace["grid_enabled"]
        if ortho_grid_toggle != null:
            ortho_grid_toggle.set_pressed_no_signal(ortho_grid_enabled)
        _grid_spacing_changed(workspace["grid_step"])
        if ortho_grid_spacing_control != null:
            ortho_grid_spacing_control.set_value_no_signal(ortho_grid_step)
        _set_editor_view_mode(workspace["view_mode"])
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
    if (not selected_actor.is_empty() and
        (_actor_on_original_ai_layer(selected_actor)
         or not _environment_entity_kind(selected_actor).is_empty())):
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
            "Focused original source actor " + str(selected_actor.get("name", ""))
            + " at original Location. No new entity spawned."
        )

func frame_whole_scene() -> void:
    if scene_bounds_valid:
        camera_target = scene_bounds.get_center()
        orbit_distance = max(5.0, scene_bounds.size.length() * 1.2)
        _update_camera()

func _view_mode_item_selected(index: int) -> void:
    if index < 0 or index >= OrthoGuides.MODES.size():
        return
    _set_editor_view_mode(str(OrthoGuides.MODES[index]))


func _set_editor_view_mode(mode: String) -> void:
    if not OrthoGuides.valid_mode(mode):
        return
    if gizmo_drag_active:
        _finish_gizmo_drag()
    _set_fly_mode(false)
    editor_view_mode = mode
    if editor_view_mode_select != null:
        editor_view_mode_select.select(OrthoGuides.MODES.find(mode))
    ortho_grid_last_mode = ""
    _update_camera()
    if status_label != null:
        status_label.text = (
            "Editor-only " + mode + " view. Scroll to zoom, middle-drag to pan."
            + " Ctrl-snapping uses the grid step. No original BSP/actor changes.")


func _snap_selected_preview_to_grid() -> void:
    if not _draft_selected_is_prop():
        status_label.text = (
            "Snap selected: choose original rendered prop previews or draft copies, "
            + "not BSP/collision or native Light geometry.")
        return
    var selection := _selection_nodes()
    var before := _capture_edit_state()
    var count := 0
    for node in selection:
        if not node.global_position.is_finite():
            continue
        var snapped_position: Vector3 = OrthoGuides.snapped_preview_position(
            node.global_position, ortho_grid_step)
        if not snapped_position.is_equal_approx(node.global_position):
            node.global_position = snapped_position
            count += 1
    if count == 0:
        status_label.text = "Selected previews already aligned to the editor grid."
        return
    _refresh_prop_inspection()
    _record_edit("Snap " + str(count) + " preview prop(s) to grid", before)
    status_label.text = (
        "Snapped " + str(count) + " editor preview prop(s) to "
        + str(ortho_grid_step) + " m grid. Undo available. Original GMP unchanged.")


func _toggle_ortho_grid(enabled: bool) -> void:
    ortho_grid_enabled = enabled
    _refresh_ortho_grid()


func _grid_spacing_changed(step: float) -> void:
    if not is_finite(step) or step < 0.25 or step > 64.0:
        return
    ortho_grid_step = step
    if prop_edit_step != null:
        prop_edit_step.value = step
    ortho_grid_last_step = -1.0
    _refresh_ortho_grid()


func _refresh_ortho_grid() -> void:
    if ortho_grid_node == null:
        return
    var show_grid := ortho_grid_enabled and editor_view_mode != OrthoGuides.PERSPECTIVE
    ortho_grid_node.visible = show_grid
    if not show_grid:
        return
    var center: Vector3 = OrthoGuides.grid_center(
        editor_view_mode, camera_target, ortho_grid_step)
    if (ortho_grid_last_mode == editor_view_mode
        and ortho_grid_last_center == center
        and is_equal_approx(ortho_grid_last_step, ortho_grid_step)):
        return
    ortho_grid_node.mesh = OrthoGuides.grid_mesh(
        editor_view_mode, camera_target, ortho_grid_step, 24)
    ortho_grid_last_mode = editor_view_mode
    ortho_grid_last_center = center
    ortho_grid_last_step = ortho_grid_step


func _update_camera() -> void:
    if not is_instance_valid(camera):
        return
    orbit_pitch = clamp(orbit_pitch, -1.50, 1.50)
    orbit_distance = clamp(orbit_distance, 0.15, 200000.0)
    OrthoGuides.apply_camera(
        camera, editor_view_mode, camera_target,
        orbit_distance, orbit_yaw, orbit_pitch)
    _refresh_ortho_grid()

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
        if editor_tool == "move":
            # Unity-style arrow tip stays a child of its own pickable axis.
            var tip := MeshInstance3D.new()
            tip.name = "arrow_tip"
            var cone := CylinderMesh.new()
            cone.top_radius = 0.0
            cone.bottom_radius = 0.16
            cone.height = 0.28
            tip.mesh = cone
            tip.position = axis * 1.35
            tip.quaternion = Quaternion(Vector3.UP, axis)
            tip.material_override = tint
            tip.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
            handle.add_child(tip)
        gizmo_handles.append(handle)
    _update_gizmo_pose()


func _update_gizmo_pose() -> void:
    if gizmo_root == null:
        return
    var preview_light := _environment_light_proxy_selected() and editor_tool == "move"
    var show := _draft_selected_is_prop() or preview_light
    gizmo_root.visible = show
    if not show:
        return
    if preview_light:
        var position: Vector3 = _environment_light_preview_position(selected_actor)
        gizmo_root.global_position = position
    else:
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
    var is_light := _environment_light_proxy_selected() and editor_tool == "move"
    if not is_light and not _draft_selected_is_prop():
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
        var parts: Array[MeshInstance3D] = [handle]
        for child in handle.get_children():
            if child is MeshInstance3D:
                parts.append(child)
        for part in parts:
            var hit := _ray_mesh_triangles(part, ray["origin"], ray["direction"])
            if not hit.is_empty() and float(hit["distance"]) < best_distance:
                best_distance = float(hit["distance"])
                best_axis = handle.get_meta("axis")
    if best_axis == Vector3.ZERO:
        return false
    gizmo_drag_axis = best_axis
    environment_light_gizmo_drag = is_light
    if is_light:
        gizmo_drag_pivot = _environment_light_preview_position(selected_actor)
    else:
        gizmo_drag_pivot = _selection_pivot()
    gizmo_start_transforms.clear()
    if not is_light:
        for node in _selection_nodes():
            gizmo_start_transforms[str(node.name)] = node.global_transform
        gizmo_start_transform = selected_mesh.global_transform
    gizmo_drag_start_screen = view_container.get_local_mouse_position()
    var scalar: Variant = _gizmo_axis_scalar(gizmo_drag_start_screen, gizmo_drag_pivot, best_axis)
    gizmo_drag_start_scalar = float(scalar) if scalar != null else 0.0
    if is_light:
        gizmo_undo_before.clear() # This light proxy must NEVER enter prop undo/draft records.
    else:
        gizmo_undo_before = _capture_edit_state()
    gizmo_drag_active = true
    return true


func _apply_gizmo_drag() -> void:
    if not gizmo_drag_active:
        return
    if environment_light_gizmo_drag:
        if editor_tool != "move" or not _environment_light_proxy_selected():
            return
        var scalar: Variant = _gizmo_axis_scalar(
            view_container.get_local_mouse_position(), gizmo_drag_pivot, gizmo_drag_axis)
        if scalar == null:
            return
        var shift := float(scalar) - gizmo_drag_start_scalar
        if Input.is_key_pressed(KEY_CTRL):
            shift = snapped(shift, float(prop_edit_step.value))
        _set_environment_light_preview_position(
            selected_actor, gizmo_drag_pivot + gizmo_drag_axis * shift)
        status_label.text = (
            "Editor-only " + str(selected_actor.get("name", "")) +
            " light gizmo: " + str(_environment_light_preview_position(selected_actor))
            + " | original DX2 Light remains unchanged; use Reset to restore."
        )
        return
    if not _draft_selected_is_prop():
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
    if semi_lit_enabled and is_instance_valid(camera):
        semi_lit_update_elapsed += delta
        if semi_lit_update_elapsed >= 0.75:
            semi_lit_update_elapsed = 0.0
            if camera.global_position.distance_squared_to(semi_lit_last_camera_position) > 9.0:
                _refresh_semi_lit_scene()
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
    # Orthographic projection is fixed-axis: never allow FPS fly rotation.
    fly_looking = enabled and editor_view_mode == OrthoGuides.PERSPECTIVE
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
            elif ke.keycode in [KEY_1, KEY_2, KEY_3, KEY_4]:
                _set_editor_view_mode(
                    str(OrthoGuides.MODES[ke.keycode - KEY_1]))
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
                if button.alt_pressed and button.shift_pressed and _can_pick_selected_draft_face():
                    dragging = true
                    drag_mode = "draft_face_pick"
                elif button.alt_pressed:
                    dragging = true
                    drag_mode = ("orbit" if editor_view_mode == OrthoGuides.PERSPECTIVE
                                 else "pan")
                elif _begin_gizmo_drag():
                    dragging = true
                    drag_mode = "gizmo"
                else:
                    dragging = true
                    drag_mode = "select"
            else:
                if drag_mode == "select" and mouse_inside and drag_distance < 3.0:
                    if source_collision_mode:
                        _pick_source_collision_triangle()
                    else:
                        _pick_actor(button.ctrl_pressed or button.shift_pressed)
                if drag_mode == "draft_face_pick" and mouse_inside and drag_distance < 3.0:
                    _pick_selected_draft_face_from_viewport()
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



# Read-only capsule preview overlays are detached from source actor/draft lifecycle.
func _clear_capsule_research_preview() -> void:
    capsule_contact_preview.clear()
    if is_instance_valid(capsule_preview_marker):
        capsule_preview_marker.queue_free()
    capsule_preview_marker = null
    if capsule_preview_details != null:
        capsule_preview_details.text = ""
        capsule_preview_details.visible = false
    if capsule_preview_button != null:
        capsule_preview_button.disabled = true


func _load_capsule_research_preview(path: String) -> void:
    _clear_capsule_research_preview()
    if (not source_collision_mode or not source_collision_picker.ready
        or current_source_map_name != source_collision_picker.source_map
        or source_gamesys_sha256 != source_collision_picker.source_sha256):
        status_label.text = "Capsule research preview requires an authenticated open collision map."
        return
    capsule_preview_button.disabled = false
    if not capsule_contact_preview.load_file(path, source_gamesys_sha256,
        current_source_map_name, source_collision_picker.face_index_by_id):
        status_label.text = "Capsule preview rejected: " + capsule_contact_preview.last_error
        return
    var overlay: ImmediateMesh = capsule_contact_preview.make_mesh()
    if overlay == null or world_root == null:
        _clear_capsule_research_preview()
        status_label.text = "Capsule preview geometry unavailable."
        return
    capsule_preview_marker = MeshInstance3D.new()
    capsule_preview_marker.name = "ResearchOnly_CapsuleContactOverlay_NotGamePhysics"
    capsule_preview_marker.mesh = overlay
    var ink := StandardMaterial3D.new()
    ink.albedo_color = Color.WHITE
    ink.vertex_color_use_as_albedo = true
    ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    ink.no_depth_test = true
    ink.cull_mode = BaseMaterial3D.CULL_DISABLED
    capsule_preview_marker.material_override = ink
    capsule_preview_marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    world_root.add_child(capsule_preview_marker)
    capsule_preview_details.visible = true
    capsule_preview_details.text = capsule_contact_preview.description()
    if capsule_contact_preview.contact_triangle_id >= 0:
        var hit: Dictionary = source_collision_picker.triangle_details(
            capsule_contact_preview.contact_triangle_id)
        if hit.is_empty():
            _clear_capsule_research_preview()
            status_label.text = "Capsule preview source triangle not found in authenticated cache."
            return
        _show_source_collision_hit(hit)
    status_label.text = (
        "Capsule research-only overlay loaded. NOT Havok gameplay or writable map collision.")


# Source collision inspection has a separate read-only selection lifecycle.
# Existing actor selection, transform gizmos, draft edits and GMP writers
# never consume this triangle ID, marker or provenance label.
func _reset_source_collision_inspection() -> void:
    _clear_capsule_research_preview()
    if source_surface_panel != null:
        source_surface_panel.reset()
    if source_edge_transition_panel != null:
        source_edge_transition_panel.reset()
    if interactive_capsule_panel != null:
        interactive_capsule_panel.reset()
    source_collision_mode = false
    source_collision_picker.clear()
    if source_collision_button != null:
        source_collision_button.set_pressed_no_signal(false)
    if source_collision_details != null:
        source_collision_details.visible = false
        source_collision_details.text = ""
    _clear_source_collision_highlights()
    source_collision_last_hit.clear()
    if source_collision_section_actions != null:
        source_collision_section_actions.visible = false
    if source_collision_section_toggle != null:
        source_collision_section_toggle.set_pressed_no_signal(false)


func _clear_source_collision_highlights() -> void:
    if is_instance_valid(source_collision_marker):
        source_collision_marker.queue_free()
    source_collision_marker = null
    if is_instance_valid(source_collision_section_marker):
        source_collision_section_marker.queue_free()
    source_collision_section_marker = null


func _toggle_source_collision_inspection() -> void:
    if source_collision_button == null:
        return
    if not source_collision_button.button_pressed:
        _reset_source_collision_inspection()
        status_label.text = "Original collision inspection disabled. Actor selection restored."
        return
    if (source_collision_thread != null or last_gmp_path.is_empty()
        or not FileAccess.file_exists(last_gmp_path) or current_folder.is_empty()
        or current_source_map_name != last_gmp_path.get_file()
        or source_gamesys_sha256.length() != 64):
        _reset_source_collision_inspection()
        status_label.text = "Open an authenticated original DX2 GMP before collision inspection."
        return
    var cache := current_folder.path_join("source_collision_selection_v3.json")
    if FileAccess.file_exists(cache):
        _activate_source_collision_cache(cache)
        return
    var script := ProjectSettings.globalize_path("res://backend/dx2_collision_selection_cache.py")
    if not FileAccess.file_exists(script):
        _reset_source_collision_inspection()
        status_label.text = "Missing source collision backend: " + script
        return
    source_collision_pending_folder = current_folder
    source_collision_pending_map = last_gmp_path
    source_collision_pending_sha = source_gamesys_sha256
    source_collision_button.disabled = true
    source_collision_thread = Thread.new()
    var error := source_collision_thread.start(_build_source_collision_cache.bind(
        script, last_gmp_path, cache, source_gamesys_sha256))
    if error != OK:
        source_collision_thread = null
        source_collision_button.disabled = false
        _reset_source_collision_inspection()
        status_label.text = "Could not start collision cache worker: " + error_string(error)
        return
    status_label.text = "Validating original collision triangles in private editor cache..."


func _build_source_collision_cache(script: String, source: String, cache: String, sha: String) -> void:
    var args := PackedStringArray([
        script, "--map", source, "--output", cache, "--expected-sha256", sha])
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        var py_args := PackedStringArray(["-3"])
        py_args.append_array(args)
        output.clear()
        code = OS.execute("py", py_args, output, true)
    call_deferred("_source_collision_cache_finished", code, "\n".join(output), cache,
        source, sha)


func _source_collision_cache_finished(code: int, output: String, cache: String, source: String, sha: String) -> void:
    if source_collision_thread != null:
        source_collision_thread.wait_to_finish()
        source_collision_thread = null
    if source_collision_button != null:
        source_collision_button.disabled = false
    if (source_collision_pending_folder != current_folder
        or source_collision_pending_map != source
        or source_collision_pending_sha != sha
        or source != last_gmp_path or sha != source_gamesys_sha256):
        _reset_source_collision_inspection()
        status_label.text = "Collision cache result discarded after map/source change."
        return
    var result: Variant = null
    for line in output.strip_edges().split("\n"):
        var candidate: Variant = JSON.parse_string(line.strip_edges())
        if typeof(candidate) == TYPE_DICTIONARY and candidate.has("status"):
            result = candidate
    if code != 0 or typeof(result) != TYPE_DICTIONARY or result.get("status") != "ok":
        _reset_source_collision_inspection()
        status_label.text = "Source collision validation refused: " + str(
            result.get("reason", "check Python/retail GMP")) if typeof(result) == TYPE_DICTIONARY else (
            "Source collision validation failed. Check Python and map input."
        )
        return
    _activate_source_collision_cache(cache)


func _activate_source_collision_cache(cache: String) -> void:
    if not source_collision_picker.load_cache(cache, source_gamesys_sha256, current_source_map_name):
        var reason: String = source_collision_picker.last_error
        _reset_source_collision_inspection()
        status_label.text = "Source collision cache refused: " + reason
        return
    _clear_capsule_research_preview()
    source_collision_mode = true
    if source_surface_panel != null:
        source_surface_panel.activate(source_collision_picker)
    if source_edge_transition_panel != null:
        source_edge_transition_panel.activate(source_collision_picker)
    if interactive_capsule_panel != null:
        interactive_capsule_panel.activate()
    if capsule_preview_button != null:
        capsule_preview_button.disabled = false
    source_collision_button.set_pressed_no_signal(true)
    source_collision_details.visible = true
    var counts: Dictionary = source_collision_picker.source_topology_summary
    var topology_line := (
        "Unique source edges: %d | open: %d | render seams: %d | non-manifold: %d.\n"
        % [
            int(counts.get("unique_source_edges", 0)),
            int(counts.get("open_boundary_edges", 0)),
            int(counts.get("two_triangle_render_material_seams", 0)),
            int(counts.get("three_or_more_triangle_edges", 0))
        ]
    )
    source_collision_details.text = (
        "ORIGINAL COLLISION TRIANGLES | READ-ONLY\n"
        + "Click a source MOPP-linked triangle for original Level IDs and geometric edge diagnostics.\n"
        + "Edge legend: amber interior | cyan open | pink render seam | red non-manifold.\n"
        + topology_line
        + "Render materials are NOT verified Havok physical materials."
    )
    status_label.text = (
        ("Collision inspection enabled: %d source MOPP-linked triangles. "
        + "Click to inspect; toggle off to restore actor picking.") %
        source_collision_picker.faces.size()
    )


func _pick_source_collision_triangle() -> void:
    if not source_collision_mode or not source_collision_picker.ready:
        return
    var ray := _mouse_ray(view_container.get_local_mouse_position())
    if ray.is_empty():
        return
    var hit: Dictionary = source_collision_picker.ray_pick(ray["origin"], ray["direction"])
    if hit.is_empty():
        _clear_source_collision_highlights()
        source_collision_last_hit.clear()
        if source_surface_panel != null:
            source_surface_panel.observe_hit({})
        source_collision_section_actions.visible = false
        source_collision_details.text = "ORIGINAL COLLISION TRIANGLES | No MOPP-linked triangle under cursor."
        status_label.text = "No original MOPP-linked triangle under cursor."
        return
    hit["selection_is_ray_hit"] = true
    if interactive_capsule_panel != null and interactive_capsule_panel.capture_pending():
        if interactive_capsule_panel.accept_source_hit(hit):
            _show_source_collision_hit(hit)
        return
    _show_source_collision_hit(hit)


func _show_source_collision_hit(hit: Dictionary) -> void:
    if not source_collision_mode or not source_collision_picker.ready or hit.is_empty():
        return
    var tid := int(hit["original_level_triangle_id"])
    var section: Dictionary = source_collision_picker.section_details(tid)
    if section.is_empty():
        return
    source_collision_last_hit = hit.duplicate()
    if source_surface_panel != null:
        source_surface_panel.observe_hit(hit)
    if source_edge_transition_panel != null:
        source_edge_transition_panel.observe_hit(hit)
    source_collision_section_actions.visible = true
    _clear_source_collision_highlights()
    var ray_hit := bool(hit.get("selection_is_ray_hit", false))
    var point_name := "Ray hit position" if ray_hit else "Source triangle centroid"
    var distance_text := ("%.5f Godot units" % float(hit["distance_godot_units"])) if ray_hit else (
        "N/A (section navigation, not a ray)")
    var edge_codes: Array = hit.get("source_edge_kinds", [])
    if edge_codes.size() != 3:
        status_label.text = "Missing original source edge metadata; refusing partial geometry evidence."
        return
    var edge_names: Array = SourceCollisionPicker.EDGE_NAMES
    var edge_labels := []
    for code in edge_codes:
        if int(code) < 0 or int(code) >= edge_names.size():
            return
        edge_labels.append(str(edge_names[int(code)]))
    source_collision_details.text = (
        ("ORIGINAL DX2 COLLISION TRIANGLE (READ-ONLY)\n"
        + "Level triangle ID: %d\n"
        + "Flesh render block ordinal: %d\n"
        + "Original source block ID: %d\n"
        + "Render section: %d\n"
        + "Original render-material name: %s\n"
        + "Triangle in original section: %d of %d\n"
        + "Source edge AB / BC / CA: %s / %s / %s\n"
        + "%s (Godot): %s\n"
        + "Geometric normal (Godot): %s\n"
        + "Geometric distance: %s\n"
        + "NOT a Havok runtime contact or verified physics material.") % [
            tid, int(hit["render_block_ordinal"]), int(hit["source_block_id"]),
            int(hit["render_section_ordinal"]), str(hit["render_material_name"]),
            int(section["triangle_index_in_section"])+1, int(section["triangle_count"]),
            edge_labels[0], edge_labels[1], edge_labels[2],
            point_name, str(hit["point_godot"]), str(hit["normal_godot"]), distance_text,
        ]
    )
    status_label.text = (
        "Original MOPP triangle #%d | render material %s | source-only." %
        [tid, str(hit["render_material_name"])]
    )
    var points: Array = hit["vertices_godot"]
    if points.size() == 3 and world_root != null:
        var edges := ImmediateMesh.new()
        edges.surface_begin(Mesh.PRIMITIVE_LINES)
        var colors := [
            Color(1.0, 0.77, 0.08),  # two incident triangles, same render material
            Color(0.05, 0.9, 0.91),  # one incident original Level triangle
            Color(1.0, 0.24, 0.72),  # two incident triangles with different render names
            Color(1.0, 0.1, 0.1),   # three or more incident source triangles
        ]
        for i in 3:
            edges.surface_set_color(colors[int(edge_codes[i])])
            edges.surface_add_vertex(points[i])
            edges.surface_add_vertex(points[(i + 1) % 3])
        edges.surface_end()
        source_collision_marker = MeshInstance3D.new()
        source_collision_marker.name = "SourceCollision_EditorOnly_Selection"
        source_collision_marker.mesh = edges
        var highlight := StandardMaterial3D.new()
        highlight.albedo_color = Color.WHITE
        highlight.vertex_color_use_as_albedo = true
        highlight.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
        highlight.no_depth_test = true
        highlight.cull_mode = BaseMaterial3D.CULL_DISABLED
        source_collision_marker.material_override = highlight
        source_collision_marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        world_root.add_child(source_collision_marker)
    if source_collision_section_toggle.button_pressed:
        _draw_source_collision_section_outline(section)


func _draw_source_collision_section_outline(section: Dictionary) -> void:
    if is_instance_valid(source_collision_section_marker):
        source_collision_section_marker.queue_free()
    source_collision_section_marker = null
    if section.is_empty() or world_root == null:
        return
    if bool(section.get("preview_skipped_for_size", true)):
        source_collision_details.text += (
            "\nSection outline skipped: %d triangles exceeds %d-face preview safety cap." %
            [int(section["triangle_count"]), int(section["preview_triangle_cap"])]
        )
        return
    var points: PackedVector3Array = section["outline_vertices_godot"]
    if points.is_empty():
        return
    var outline := ImmediateMesh.new()
    outline.surface_begin(Mesh.PRIMITIVE_LINES)
    for point in points:
        outline.surface_add_vertex(point)
    outline.surface_end()
    source_collision_section_marker = MeshInstance3D.new()
    source_collision_section_marker.name = "SourceCollision_EditorOnly_SectionOutline"
    source_collision_section_marker.mesh = outline
    var ink := StandardMaterial3D.new()
    ink.albedo_color = Color(0.17, 0.83, 0.94)
    ink.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    ink.no_depth_test = true
    ink.cull_mode = BaseMaterial3D.CULL_DISABLED
    source_collision_section_marker.material_override = ink
    source_collision_section_marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    world_root.add_child(source_collision_section_marker)


func _toggle_source_collision_section_outline(enabled: bool) -> void:
    if is_instance_valid(source_collision_section_marker):
        source_collision_section_marker.queue_free()
    source_collision_section_marker = null
    if (not enabled or not source_collision_mode or source_collision_last_hit.is_empty()
        or not source_collision_picker.ready):
        return
    var tid := int(source_collision_last_hit["original_level_triangle_id"])
    _draw_source_collision_section_outline(source_collision_picker.section_details(tid))


func _step_source_collision_triangle(step: int) -> void:
    if (not source_collision_mode or not source_collision_picker.ready
        or source_collision_last_hit.is_empty() or step not in [-1, 1]):
        return
    var tid := int(source_collision_last_hit["original_level_triangle_id"])
    var section: Dictionary = source_collision_picker.section_details(tid)
    if section.is_empty():
        return
    var next_id := int(section["previous_triangle_id"]) if step == -1 else int(
        section["next_triangle_id"])
    var next_hit: Dictionary = source_collision_picker.triangle_details(next_id)
    if next_hit.is_empty():
        return
    _show_source_collision_hit(next_hit)


func _source_collision_evidence_json() -> String:
    if (not source_collision_mode or source_collision_last_hit.is_empty()
        or not source_collision_picker.ready):
        return ""
    var hit := source_collision_last_hit
    var id := int(hit["original_level_triangle_id"])
    var section: Dictionary = source_collision_picker.section_details(id)
    if section.is_empty():
        return ""
    var pos: Vector3 = hit["point_godot"]
    var normal: Vector3 = hit["normal_godot"]
    return JSON.stringify({
        "schema": "DX2Ed-read-only-source-collision-evidence-v1",
        "source_map": source_collision_picker.source_map,
        "source_sha256": source_collision_picker.source_sha256,
        "original_level_triangle_id": id,
        "source_block_id": int(hit["source_block_id"]),
        "render_block_ordinal": int(hit["render_block_ordinal"]),
        "render_section_ordinal": int(hit["render_section_ordinal"]),
        "render_material_name": str(hit["render_material_name"]),
        "source_edge_kinds_ab_bc_ca": hit.get("source_edge_kinds", []).duplicate(),
        "source_edge_names_ab_bc_ca": [
            SourceCollisionPicker.EDGE_NAMES[int(hit["source_edge_kinds"][0])],
            SourceCollisionPicker.EDGE_NAMES[int(hit["source_edge_kinds"][1])],
            SourceCollisionPicker.EDGE_NAMES[int(hit["source_edge_kinds"][2])]
        ],
        "source_exact_edge_topology": true,
        "source_section_triangle_count": int(section["triangle_count"]),
        "point_godot_xyz": [pos.x, pos.y, pos.z],
        "geometric_normal_godot_xyz": [normal.x, normal.y, normal.z],
        "selection_is_ray_hit": bool(hit.get("selection_is_ray_hit", false)),
        "render_material_is_physics_material": false,
        "havok_runtime_contact": false,
        "native_map_written": false,
    }, "  ")


func _copy_source_collision_evidence() -> void:
    var evidence := _source_collision_evidence_json()
    if evidence.is_empty():
        return
    DisplayServer.clipboard_set(evidence)
    status_label.text = "Copied original triangle provenance (read-only JSON, not a Havok contact)."


func _pick_actor(additive: bool = false) -> void:
    # On-screen original Light handles are editor overlays, not map meshes.
    # Give a clearly clickable marker priority over underlying BSP triangles.
    if view_container.size.x > 0.0 and view_container.size.y > 0.0:
        var screen := (view_container.get_local_mouse_position()
            * Vector2(world_view.size) / view_container.size)
        var light_name := _pick_environment_light_marker(screen)
        if not light_name.is_empty():
            _select_environment_light_from_viewport(light_name)
            return
        var ai_name := _pick_ai_proxy_marker(screen)
        if not ai_name.is_empty() and actors_by_name.has(ai_name):
            select_actor(actors_by_name[ai_name])
            status_label.text = (
                "Selected original AI-layer candidate " + ai_name
                + ". Source position only; no NPC body or native spawn."
            )
            return
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
