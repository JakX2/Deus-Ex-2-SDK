extends SceneTree
## DX2Ed v0.64 source-free Godot private human test dossier smoke.
## No original or modified GMP data, game installation or script files.

const Editor = preload("res://main.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(message: String) -> void:
    push_error("DX2Ed v0.64 trial dossier UI: " + message)
    quit(1)


func _find_button(root: Node, title: String) -> Button:
    if root is Button and (root as Button).text == title:
        return root as Button
    for child in root.get_children():
        var found := _find_button(child, title)
        if found != null:
            return found
    return null


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    var button := _find_button(editor, "Prepare Retail Test Dossier...")
    if button == null or not button.pressed.is_connected(
            Callable(editor, "_open_native_trial_candidate_dialog")):
        _fail("Original-source trial preparation button not wired")
        return
    if (not is_instance_valid(editor.native_trial_candidate_dialog)
        or not is_instance_valid(editor.native_trial_dossier_dialog)
        or not is_instance_valid(editor.native_trial_confirmation)):
        _fail("Trial source/candidate chooser and confirmation dialogs missing")
        return
    if (editor.native_trial_candidate_dialog.file_mode != FileDialog.FILE_MODE_OPEN_FILE
        or editor.native_trial_candidate_dialog.filters.size() != 1
        or not editor.native_trial_candidate_dialog.filters[0].begins_with("*.gmp")):
        _fail("Trial candidate must be a previously created GMP, never a new game asset")
        return
    if (editor.native_trial_dossier_dialog.file_mode != FileDialog.FILE_MODE_SAVE_FILE
        or editor.native_trial_dossier_dialog.filters.size() != 1
        or not editor.native_trial_dossier_dialog.filters[0].begins_with("*.dx2trial.json")):
        _fail("Trial dossier output must be private JSON")
        return
    if (not editor.native_trial_candidate_dialog.file_selected.is_connected(
            Callable(editor, "_stage_native_trial_candidate"))
        or not editor.native_trial_dossier_dialog.file_selected.is_connected(
            Callable(editor, "_stage_native_trial_dossier"))
        or not editor.native_trial_confirmation.confirmed.is_connected(
            Callable(editor, "_execute_native_trial_dossier"))):
        _fail("Trial preparation signals or manual confirmation missing")
        return
    if not editor.native_trial_pending.is_empty():
        _fail("Trial dossier must never be pending on startup")
        return
    editor._open_native_trial_candidate_dialog()
    if (not editor.native_trial_pending.is_empty()
        or editor.native_export_thread != null
        or editor.native_trial_candidate_dialog.visible
        or not editor.status_label.text.contains("requires an unchanged original GMP")):
        _fail("Trial action did not refuse without a source-pinned original GMP")
        return
    editor.queue_free()
    print("DX2Ed v0.64 source-free retail test dossier UI and refusal smoke PASS")
    quit(0)
