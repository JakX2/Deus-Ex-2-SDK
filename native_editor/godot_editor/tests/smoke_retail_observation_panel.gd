extends SceneTree
## DX2Ed v0.67 fixture-free Godot owner observation UI and refusal smoke.
const Editor = preload("res://main.gd")
const ObservationPanel = preload("res://retail_observation_panel.gd")


func _initialize() -> void:
    call_deferred("_run")


func _fail(why: String) -> void:
    push_error("DX2Ed v0.67 owner observations: " + why)
    quit(1)


func _find_button(parent: Node, label: String) -> Button:
    if parent is Button and (parent as Button).text == label:
        return parent as Button
    for child in parent.get_children():
        var match := _find_button(child, label)
        if match != null:
            return match
    return null


func _run() -> void:
    var editor := Editor.new()
    get_root().add_child(editor)
    var open_button := _find_button(editor, "Record Retail Test...")
    if open_button == null or not open_button.pressed.is_connected(
            Callable(editor, "_open_retail_observation_panel")):
        _fail("Main editor is missing observation entry action")
        return
    var panel = editor.retail_observation_panel
    if panel == null or not panel is ObservationPanel:
        _fail("Owner observation dialog was not instantiated")
        return
    if (panel.paths.size() != 4 or panel.check_choice == null
        or panel.result_choice.item_count != 4
        or panel.confirmation == null
        or not panel.confirmation.confirmed.is_connected(
            Callable(panel, "_confirmed_record"))
        or panel.worker != null or not panel.record_button.disabled):
        _fail("Owner recording input and explicit confirmation guards are missing")
        return
    panel.configure("", "")
    if panel.inspected or panel.record_button.disabled == false:
        _fail("No initial, unverified observation recording is allowed")
        return
    editor._open_retail_observation_panel()
    if (panel.visible or panel.worker != null
        or not editor.status_label.text.contains("unchanged original GMP")):
        _fail("Without original GMP, editor incorrectly opens observation record")
        return
    panel.configure("/nonexistent/M1_Fake.gmp", "a".repeat(64))
    panel._inspect()
    if (panel.worker != null or panel.inspected
        or not panel.status.text.contains("Original GMP missing")):
        _fail("Panel allowed a worker or recording without real original GMP")
        return
    panel.configure("", "")
    editor.queue_free()
    print("DX2Ed v0.67 source-free owner observation UI/refusal smoke PASS")
    quit(0)
