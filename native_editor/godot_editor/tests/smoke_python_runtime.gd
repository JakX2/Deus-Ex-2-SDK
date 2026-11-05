extends SceneTree
## Prove the packaged preflight-selected interpreter really launches the
## Python worker from Godot. No original GMP or proprietary resources used.
const Runtime = preload("res://python_runtime.gd")
const StartupRoute = preload("res://startup_route.gd")

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed Windows verified Python worker smoke: " + message)
    quit(1)

func _run() -> void:
    var saved := OS.get_environment(Runtime.ENV)
    var expected := Runtime.executable()
    if not saved.is_empty() and saved.is_absolute_path():
        if expected != saved:
            _fail("Packaged launcher interpreter was not selected")
            return
    elif expected != "python":
        _fail("Unconfigured Godot session should retain Python fallback")
        return

    var output: Array = []
    var exit_code := OS.execute(expected, PackedStringArray([
        "-c", "import sys;print('DX2ED_VERIFIED_PYTHON_READY')"
    ]), output, true)
    if exit_code != 0 or not "\n".join(output).contains(
            "DX2ED_VERIFIED_PYTHON_READY"):
        _fail("Selected interpreter did not execute an asset-free worker")
        return

    var fake_path := ProjectSettings.globalize_path("user://python.exe")
    var fake := FileAccess.open(fake_path, FileAccess.WRITE)
    if fake == null:
        _fail("Unable to create local synthetic interpreter name fixture")
        return
    fake.store_string("NOT A REAL PYTHON BINARY")
    fake.close()
    OS.set_environment(Runtime.ENV, fake_path)
    if Runtime.executable() != fake_path:
        _fail("Valid absolute Python executable choice was not forwarded")
        return
    OS.set_environment(Runtime.ENV, fake_path + ".missing")
    if Runtime.executable() != "python":
        _fail("Missing configured Python must fall back to default")
        return
    OS.set_environment(Runtime.ENV, ProjectSettings.globalize_path("res://main.gd"))
    if Runtime.executable() != "python":
        _fail("Non-executable configured path must be refused")
        return
    OS.set_environment(Runtime.ENV, "python.exe")
    if Runtime.executable() != "python":
        _fail("Relative/PATH-only interpreter override must be refused")
        return

    if saved.is_empty():
        OS.unset_environment(Runtime.ENV)
    else:
        OS.set_environment(Runtime.ENV, saved)
    DirAccess.remove_absolute(fake_path)

    var main_source := FileAccess.get_file_as_string("res://main.gd")
    var panel_source := FileAccess.get_file_as_string(
        "res://capsule_sweep_panel.gd")
    if (not main_source.contains("OS.execute(PythonRuntime.executable(),")
        or not panel_source.contains("OS.execute(PythonRuntime.executable(),")):
        _fail("Packaged editor workers do not use shared verified interpreter")
        return

    if load("res://main.gd") == null:
        _fail("Editor main script does not load with verified Python helper")
        return
    # A Windows drag/drop GMP path is routed to the existing authenticated
    # direct importer, not treated as the old exported-GLB folder argument.
    var synthetic := ProjectSettings.globalize_path("user://DX2Ed_fake_startup.gmp")
    var owned := FileAccess.open(synthetic, FileAccess.WRITE)
    if owned == null:
        _fail("Could not create original-asset-free GMP argument fixture")
        return
    owned.store_string("SYNTHETIC PATH ROUTE ONLY, NOT A DEUS EX MAP")
    owned.close()
    var requested: Dictionary = StartupRoute.resolve(PackedStringArray([
        "--gmp", synthetic]))
    if (requested.get("kind") != "gmp"
        or requested.get("path") != synthetic):
        _fail("Dropped GMP startup path did not reach source map importer")
        return
    var old_args: Dictionary = StartupRoute.resolve(PackedStringArray([
        "C:/Synthetic/ExportFolder"]))
    if (old_args.get("kind") != "export_folder"
        or StartupRoute.resolve(PackedStringArray(["--gmp", synthetic + ".missing"]))
            .get("kind") != "invalid_gmp"
        or StartupRoute.resolve(PackedStringArray(["--unknown"]))
            .get("kind") != "invalid_args"
        or StartupRoute.resolve(PackedStringArray())
            .get("kind") != "idle"):
        _fail("Startup argument parser broke legacy mode or invalid path refusal")
        return
    DirAccess.remove_absolute(synthetic)

    print("DX2Ed verified packaged Python worker and GMP startup route: PASS")
    quit(0)
