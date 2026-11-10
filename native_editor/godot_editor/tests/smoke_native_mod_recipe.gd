extends SceneTree
## Asset-free DX2Ed v0.61 mod recipe export UI smoke.
## No external GMP, IBD, owned map, or retail game directory is accessed.

const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.61 recipe UI: " + message)
    quit(1)


func _find_button(start: Node, title: String) -> Button:
    if start is Button and (start as Button).text == title:
        return start as Button
    for node in start.get_children():
        var found := _find_button(node, title)
        if found != null:
            return found
    return null


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    if (not is_instance_valid(editor.native_recipe_dialog)
        or not is_instance_valid(editor.native_recipe_confirmation)):
        _fail("New file chooser or confirmation dialog missing")
        return
    if editor.native_recipe_dialog.file_mode != FileDialog.FILE_MODE_SAVE_FILE:
        _fail("Recipe action must choose a NEW file")
        return
    if editor.native_recipe_dialog.access != FileDialog.ACCESS_FILESYSTEM:
        _fail("Recipe destination chooser cannot reach owner's normal files")
        return
    var filters := editor.native_recipe_dialog.filters
    if filters.size() != 1 or not filters[0].begins_with("*.dx2edmod.json"):
        _fail("Recipe chooser permits a non-JSON output")
        return
    if (not editor.native_recipe_dialog.file_selected.is_connected(
            Callable(editor, "_stage_native_recipe_export"))
        or not editor.native_recipe_confirmation.confirmed.is_connected(
            Callable(editor, "_execute_native_recipe_export"))):
        _fail("Native recipe export confirmation was not wired")
        return
    var button := _find_button(editor, "Export Mod Recipe...")
    if button == null or not button.pressed.is_connected(
            Callable(editor, "_open_native_recipe_dialog")):
        _fail("Godot toolbar has no wired recipe button")
        return
    if not editor.native_recipe_pending.is_empty():
        _fail("Recipe operation must not be pending on startup")
        return
    editor._open_native_recipe_dialog()
    if (not editor.native_recipe_pending.is_empty()
        or editor.native_export_thread != null
        or editor.native_recipe_dialog.visible):
        _fail("Recipe action attempted an export without a source GMP")
        return
    editor.queue_free()
    print("DX2Ed v0.61 content-free mod recipe chooser and source refusal smoke PASS")
    quit(0)
