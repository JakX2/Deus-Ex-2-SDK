extends SceneTree
## DX2Ed v0.65: source/asset-free disposable game copy guard smoke.

const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.65 disposable trial: " + message)
    quit(1)


func _find_button(node: Node, text: String) -> Button:
    if node is Button and (node as Button).text == text:
        return node as Button
    for child in node.get_children():
        var found := _find_button(child, text)
        if found != null:
            return found
    return null


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    var button := _find_button(editor, "Disposable Game Trial...")
    if button == null or not button.pressed.is_connected(
            Callable(editor, "_open_native_sandbox_trial")):
        _fail("Disposable test-copy action missing or not wired")
        return
    if (not is_instance_valid(editor.native_sandbox_action)
        or editor.native_sandbox_action.get_item_count() != 4
        or editor.native_sandbox_action.get_item_text(0) != "Prepare backup"
        or editor.native_sandbox_action.get_item_text(1) != "Stage test GMP"
        or editor.native_sandbox_action.get_item_text(2) != "Restore original"
        or editor.native_sandbox_action.get_item_text(3) != "Inspect test copy"):
        _fail("Prepare/stage/restore/status actions are not all accessible")
        return
    if (not is_instance_valid(editor.native_sandbox_candidate_dialog)
        or not is_instance_valid(editor.native_sandbox_root_dialog)
        or not is_instance_valid(editor.native_sandbox_confirmation)):
        _fail("Candidate GMP, disposable game directory or explicit confirmation missing")
        return
    if (editor.native_sandbox_candidate_dialog.file_mode != FileDialog.FILE_MODE_OPEN_FILE
        or editor.native_sandbox_root_dialog.file_mode != FileDialog.FILE_MODE_OPEN_DIR
        or editor.native_sandbox_candidate_dialog.filters.size() != 1
        or not editor.native_sandbox_candidate_dialog.filters[0].begins_with("*.gmp")):
        _fail("Native candidate must already exist, target must be a directory")
        return
    if (not editor.native_sandbox_candidate_dialog.file_selected.is_connected(
            Callable(editor, "_stage_sandbox_candidate"))
        or not editor.native_sandbox_root_dialog.dir_selected.is_connected(
            Callable(editor, "_stage_sandbox_root"))
        or not editor.native_sandbox_confirmation.confirmed.is_connected(
            Callable(editor, "_execute_sandbox_trial"))):
        _fail("Disposable trial must have explicit selected GMP/root and confirmation")
        return
    if not editor.native_sandbox_pending.is_empty():
        _fail("No disposable trial must be armed at editor startup")
        return
    editor._open_native_sandbox_trial()
    if (not editor.native_sandbox_pending.is_empty()
        or editor.native_export_thread != null
        or editor.native_sandbox_candidate_dialog.visible
        or not editor.status_label.text.contains("exact unchanged original GMP")):
        _fail("Disposable trial failed to refuse without original source GMP")
        return
    editor.queue_free()
    print("DX2Ed v0.65 test-copy stage/restore chooser and source guard smoke PASS")
    quit(0)
