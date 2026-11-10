extends SceneTree
## DX2Ed v0.63 source-only UI smoke. No game GMP, ZIP or IBD is opened.
const Editor = preload("res://main.gd")

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed v0.63 cross-source UI smoke: " + message)
    quit(1)

func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    var button: Button = editor.gameplay_crosssource_button
    var dialog: AcceptDialog = editor.gameplay_crosssource_dialog
    if not is_instance_valid(button) or not is_instance_valid(dialog):
        _fail("Scripts tab did not initialize cross-source review controls")
        return
    if button.text != "Review selected prop: GMP links + original IBD scripts...":
        _fail("Cross-source reference review button missing")
        return
    if not button.disabled or not editor.gameplay_crosssource_ibd_path.is_empty():
        _fail("Cross-source review was enabled without any source-verified original IBD")
        return
    if not button.pressed.is_connected(
            Callable(editor, "_review_selected_original_prop_dependencies")):
        _fail("Cross-source review button is not wired to read-only source gate")
        return
    editor._review_selected_original_prop_dependencies()
    if (editor.gameplay_crosssource_thread != null
        or dialog.visible
        or not editor.status_label.text.contains("Review refused")):
        _fail("Cross-source review ran or opened without original source GMP/IBD")
        return
    editor.queue_free()
    print("DX2Ed v0.63 read-only GMP plus IBD/TSD cross-source review gate PASS")
    quit(0)
