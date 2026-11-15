extends SceneTree
## P108 compact toolbar, synthetic-editor only.
## Menu items must route to the ORIGINAL guarded callbacks; no native save
## capability is created. All game resources remain outside this fixture.
const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed P108 compact toolbar: " + message)
    quit(1)


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    if (editor.compact_toolbar_root == null or editor.compact_quickbar == null
        or editor.compact_legacy_bars.size() != 3
        or editor.compact_menus.size() != 6
        or editor.compact_advanced_toggle == null):
        _fail("Compact toolbar or menu categories were not initialized")
        return
    for bar in editor.compact_legacy_bars:
        if bar.visible:
            _fail("Uncluttered editor opened with legacy rows visible")
            return
    for name in ["Open DX2 map (.gmp)", "Save draft", "Load draft",
                 "Save / Export map...", "Undo", "Redo", "Move W", "Rotate E", "Scale R"]:
        if not editor.compact_action_buttons.has(name):
            _fail("Missing quick action: " + name)
            return
        var button: Button = editor.compact_action_buttons[name]
        if button.get_parent() != editor.compact_quickbar or not button.visible:
            _fail("Quick action not visible: " + name)
            return
    if (editor.editor_view_mode_select.get_parent() != editor.compact_quickbar
        or editor.view_layout_select.get_parent() != editor.compact_quickbar
        or editor.ortho_grid_toggle.get_parent() != editor.compact_quickbar
        or editor.ortho_grid_spacing_control.get_parent() != editor.compact_quickbar):
        _fail("Essential viewport and grid controls were hidden")
        return

    var file_menu: MenuButton = editor.compact_menus["File"]
    var popup := file_menu.get_popup()
    var demo_index := -1
    var save_index := -1
    for index in range(popup.get_item_count()):
        match popup.get_item_text(index):
            "Load demo cubes":
                demo_index = popup.get_item_id(index)
            "Save draft":
                save_index = popup.get_item_id(index)
    if demo_index < 0 or save_index < 0:
        _fail("File menu lost demo or save action")
        return
    # Real menu signal, same action as existing Load demo cubes button.
    popup.id_pressed.emit(demo_index)
    if editor.scene_root == null or editor.current_folder.is_empty():
        _fail("File menu did not route to the original demo loader")
        return
    popup.id_pressed.emit(save_index)
    var draft_path: String = editor._draft_file_path()
    if (not FileAccess.file_exists(draft_path)
        or editor.status_label.text.find("Saved") == -1):
        _fail("File menu did not preserve private Save draft behavior")
        return

    # The user's top-level Save / Export button saves a private draft
    # and reports exactly ZERO game-native changes for the synthetic demo.
    editor.compact_action_buttons["Save / Export map..."].pressed.emit()
    if (editor.save_export_overview == null
        or editor.save_export_native_button == null
        or not editor.save_export_native_button.disabled
        or editor.save_export_overview.dialog_text.find("No source-backed native edits were found") < 0
        or not editor.status_label.text.begins_with("Save / Export: editor draft saved.")):
        _fail("Save / Export did not save draft and explicitly refuse unsupported native output")
        return
    editor.save_export_overview.hide()
    var native_menu: MenuButton = editor.compact_menus["Native GMP (test)"]
    if native_menu.get_popup().get_item_count() < 10:
        _fail("Research native Save As actions were lost")
        return
    var geometry_menu: MenuButton = editor.compact_menus["Geometry"]
    var geometry_popup := geometry_menu.get_popup()
    geometry_popup.about_to_popup.emit()
    var refresh_index := -1
    for i in range(geometry_popup.get_item_count()):
        if geometry_popup.get_item_text(i) == "Refresh CSG":
            refresh_index = i
    if (refresh_index < 0 or not geometry_popup.is_item_disabled(refresh_index)):
        _fail("Disabled CSG action became enabled in menu")
        return

    editor.compact_advanced_toggle.toggled.emit(true)
    for bar in editor.compact_legacy_bars:
        if not bar.visible:
            _fail("Advanced controls could not restore legacy rows")
            return
    editor.compact_advanced_toggle.toggled.emit(false)
    for bar in editor.compact_legacy_bars:
        if bar.visible:
            _fail("Advanced controls could not collapse legacy rows")
            return
    editor.queue_free()
    print("DX2Ed P108 compact toolbar and Save draft menu routing PASS")
    quit(0)
