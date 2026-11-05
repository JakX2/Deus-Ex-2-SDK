extends SceneTree
## Synthetic source-pinned dialogue-tree authoring contract. No proprietary
## conversation/voice data and no native Unreal script or GMP modifications.
const Dialogue = preload("res://dialogue_design_draft.gd")
const SHA := "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"

func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("DX2Ed source-only dialogue tree design: " + message)
    quit(1)

func _actors() -> Array:
    # Exactly the same JSON number typing as the real imported actors.json.
    var original := [
        {"name": "SyntheticNPC__1", "class": "ScriptedPawn", "export": 7},
        {"name": "SyntheticPlayerStart__2", "class": "PlayerStart", "export": 23},
    ]
    var parsed: Variant = JSON.parse_string(JSON.stringify(original))
    return parsed

func _run() -> void:
    var model = Dialogue.new()
    if not model.initialize("SyntheticMap.gmp", SHA, _actors()):
        _fail("Source actor catalog was refused: " + model.last_error)
        return
    var alice: Dictionary = _actors()[0]
    var player: Dictionary = _actors()[1]
    var first: int = model.add_line(alice, "Can I help you?")
    var second: int = model.add_line(player, "Tell me about the facility.")
    var third: int = model.add_line(alice, "This section is restricted.")
    if first != 1 or second != 2 or third != 3:
        _fail("Node IDs are not stable and monotonic")
        return
    if not model.add_choice(first, second, "Ask a question"):
        _fail("First conversation choice rejected: " + model.last_error)
        return
    if not model.add_choice(second, third, "Continue"):
        _fail("Linear conversation choice rejected")
        return
    if not model.add_choice(first, third, "Leave") or model.nodes[0]["choices"].size() != 2:
        _fail("Multi-branch dialogue cannot be authored")
        return
    if model.add_choice(first, 999, "Unknown line"):
        _fail("Dangling conversation branch accepted")
        return
    if model.add_choice(first, third, "Leave"):
        _fail("Duplicate conversation choice accepted")
        return
    if model.add_choice(first, second, ""):
        _fail("Empty branch label accepted")
        return
    if not model.update_line(first, "I need a security clearance."):
        _fail("Editing text in selected source-bounded node failed")
        return
    if model.update_line(first, "X".repeat(Dialogue.MAX_TEXT + 1)):
        _fail("Oversize conversation text accepted")
        return
    var unknown: Dictionary = alice.duplicate()
    unknown["export"] = 99
    if model.add_line(unknown, "Forged") >= 0:
        _fail("Foreign actor placed into original-only dialogue")
        return
    unknown = alice.duplicate()
    unknown["name"] = "FakeNPC"
    if model.add_line(unknown, "Forged") >= 0:
        _fail("Altered original actor identity accepted")
        return
    var original := model.make_document()
    if (original.get("schema") != Dialogue.SCHEMA
        or original.get("authoring_only") != true
        or original.get("original_dialogue_format_decoded") != false
        or original.get("native_export_enabled") != false
        or original.get("gameplay_runtime_verified") != false
        or original.get("original_game_assets_modified") != false):
        _fail("Dialogue plan falsely claimed engine-compatible compiled dialogue")
        return

    var invalid: Dictionary = original.duplicate(true)
    invalid["source_map_sha256"] = "0".repeat(64)
    if model.load_document(invalid) or model.nodes.size() != 3:
        _fail("Stale original GMP identity changed dialogue model")
        return
    invalid = original.duplicate(true)
    invalid["nodes"][0]["speaker_export"] = 7.5
    if model.load_document(invalid) or model.nodes.size() != 3:
        _fail("Fractional native export accepted")
        return
    invalid = original.duplicate(true)
    invalid["nodes"][0]["speaker_name"] = "Unknown"
    if model.load_document(invalid) or model.nodes.size() != 3:
        _fail("Forged speaker name accepted")
        return
    invalid = original.duplicate(true)
    invalid["nodes"][0]["choices"][0]["target"] = 200
    if model.load_document(invalid) or model.nodes.size() != 3:
        _fail("Invalid forward dialogue edge accepted")
        return
    invalid = original.duplicate(true)
    invalid["nodes"][1]["id"] = 1
    if model.load_document(invalid) or model.nodes.size() != 3:
        _fail("Duplicate authored node ID accepted")
        return
    invalid = original.duplicate(true)
    invalid["next_node_id"] = 3
    if model.load_document(invalid) or model.nodes.size() != 3:
        _fail("Reused node allocator ID accepted")
        return
    invalid = original.duplicate(true)
    invalid["native_export_enabled"] = true
    if model.load_document(invalid):
        _fail("Forged native conversation write claim accepted")
        return

    # Verify private JSON roundtrip, including whole-number float conversion,
    # before pruning reference edges on deleted target nodes.
    var path: String = model.private_path()
    if not path.begins_with(OS.get_user_data_dir()):
        _fail("Private dialogue document is outside Godot user data")
        return
    if not model.save_private() or not FileAccess.file_exists(path):
        _fail("Private dialogue save failed: " + model.last_error)
        return
    if not model.remove_line(2) or model.nodes.size() != 2:
        _fail("Dialogue line removal failed")
        return
    if model.nodes[0]["choices"].size() != 1:
        _fail("Removed node left dangling branches in source design")
        return
    if not model.load_private() or model.nodes.size() != 3:
        _fail("Original map dialogue design did not reload from disk: " + model.last_error)
        return
    if model.make_document() != original:
        _fail("Loaded original source dialogue tree is not the saved authoring state")
        return
    var on_disk: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
    if typeof(on_disk) != TYPE_DICTIONARY or not model.load_document(on_disk):
        _fail("Original source JSON not independently validated on disk")
        return
    if DirAccess.remove_absolute(path) != OK:
        _fail("Synthetic private user data test was not cleaned")
        return
    var stale = Dialogue.new()
    if not stale.initialize("Other.gmp", "b".repeat(64), _actors()):
        _fail("Second synthetic source cannot be initialized")
        return
    if stale.load_document(original):
        _fail("Dialogue project loaded across unrelated GMP identity")
        return
    if load("res://main.gd") == null:
        _fail("DX2Ed main script cannot load with source dialogue UI")
        return
    print("DX2Ed original-GMP-bound dialogue tree design and branches: PASS")
    quit(0)
