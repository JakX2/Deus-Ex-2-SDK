extends SceneTree
const Picker = preload("res://collision_source_picker.gd")
const SHA := "1111111111111111111111111111111111111111111111111111111111111111"
func _initialize() -> void:
    call_deferred("_run")
func _run() -> void:
    var picker := Picker.new()
    print("topology smoke scaffold")
    quit(0)
