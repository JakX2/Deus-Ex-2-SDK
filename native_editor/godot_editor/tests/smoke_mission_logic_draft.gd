extends SceneTree
## Synthetic GMP/TriggerScript authoring-plan smoke. No original DX2 content,
## no native save, and no inference of executable actor->TS_ script binding.
const Draft = preload("res://mission_logic_draft.gd")
const MAP_SHA := "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
const ZIP_SHA := "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

func _initialize() -> void:
    call_deferred("_run")

func _fail(reason: String) -> void:
    push_error("DX2Ed design-only TriggerScript workflow: " + reason)
    quit(1)

func _catalog() -> Dictionary:
    return {
        "schema": Draft.CATALOG_SCHEMA,
        "read_only": true,
        "bindings_verified": false,
        "spawn_enabled": false,
        "map": "SyntheticFixture.gmp",
        "map_sha256": MAP_SHA,
        "script_archive_sha256": ZIP_SHA,
        "script_definitions": [
            {"id": "TS_100", "title": "Synthetic switch",
             "actions": ["kTAT_Test"], "conditions": ["kTCT_Test"]},
            {"id": "TS_101", "title": "Synthetic door",
             "actions": [], "conditions": []},
        ],
    }

func _actors() -> Array:
    # Read through the same Godot JSON parser as real actors.json. On Godot
    # 4.3, the native export fields become floating-point numeric values.
    var source: Array = [
        {"name": "SyntheticSwitch__4", "class": "Trigger", "export": 42},
        {"name": "SyntheticDoor__2", "class": "Mover", "export": 51},
    ]
    var decoded: Variant = JSON.parse_string(JSON.stringify(source))
    return decoded

func _run() -> void:
    var model = Draft.new()
    if not model.initialize(_catalog(), _actors()):
        _fail("Synthetic original actor/script source catalog not accepted")
        return
    var first := _actors()[0] as Dictionary
    if not model.plan_actor_script("TS_100", first, "Switch should announce a door"):
        _fail("Authoring plan on original source actor could not be added")
        return
    if model.plan_actor_script("TS_100", first, "Duplicate"):
        _fail("Duplicate original actor/script plan permitted")
        return
    if model.plan_actor_script("TS_999", first):
        _fail("Unknown original script accepted")
        return
    var forged: Dictionary = first.duplicate()
    forged["export"] = 9999
    if model.plan_actor_script("TS_101", forged):
        _fail("Non-source actor accepted")
        return
    forged = first.duplicate()
    forged["class"] = "Counterfeit"
    if model.plan_actor_script("TS_101", forged):
        _fail("Forged source actor class accepted")
        return
    if model.plan_actor_script("TS_101", first, "x".repeat(401)):
        _fail("Excessive draft note accepted")
        return
    var second := _actors()[1] as Dictionary
    if not model.plan_actor_script("TS_101", second, "Door after switch"):
        _fail("Second original actor/script pair rejected")
        return
    if not model.change_note(1, "Draft only, no real TriggerScript assignment"):
        _fail("Editable author note rejected")
        return
    var snapshot := model.make_document()
    if (snapshot.get("schema") != Draft.SCHEMA
        or snapshot.get("authoring_only") != true
        or snapshot.get("native_script_binding_written") != false
        or snapshot.get("gameplay_runtime_verified") != false
        or snapshot.get("original_game_assets_modified") != false
        or snapshot.get("rows", []).size() != 2):
        _fail("Design file falsely claims native actor/script binding")
        return

    var altered: Dictionary = snapshot.duplicate(true)
    altered["source_map_sha256"] = "f".repeat(64)
    if model.load_document(altered) or model.rows.size() != 2:
        _fail("Foreign GMP SHA replaced active design")
        return
    altered = snapshot.duplicate(true)
    altered["script_archive_sha256"] = "e".repeat(64)
    if model.load_document(altered) or model.rows.size() != 2:
        _fail("Foreign original TriggerScript ZIP accepted")
        return
    altered = snapshot.duplicate(true)
    altered["rows"][1]["actor_export"] = 999
    if model.load_document(altered) or model.rows.size() != 2:
        _fail("Unknown native actor export corrupted existing plan")
        return
    altered = snapshot.duplicate(true)
    altered["rows"][0]["actor_export"] = 42.5
    if model.load_document(altered) or model.rows.size() != 2:
        _fail("Fractional native actor export accepted after JSON load")
        return
    altered = snapshot.duplicate(true)
    altered["rows"][0]["actor_export"] = 42.0
    if not model.load_document(altered) or model.rows[0]["actor_export"] != 42:
        _fail("Whole JSON number not normalized to original export integer")
        return
    altered = snapshot.duplicate(true)
    altered["rows"][1] = altered["rows"][0].duplicate(true)
    if model.load_document(altered) or model.rows.size() != 2:
        _fail("Duplicate pair accepted or caused partial mutation")
        return
    altered = snapshot.duplicate(true)
    altered["native_script_binding_written"] = true
    if model.load_document(altered):
        _fail("Native script compilation falsely asserted")
        return
    if not model.remove(0) or model.rows.size() != 1:
        _fail("Removing a planned link did not update the private model")
        return
    if not model.load_document(snapshot) or model.rows.size() != 2:
        _fail("Valid original-authenticated design could not be reloaded")
        return

    # Test actual private write/read. Source paths are synthetic and never
    # touched by this class. Remove test output after checking persistence.
    var path: String = model.private_path()
    if (not path.begins_with(OS.get_user_data_dir())
        or path.get_extension() != "json"):
        _fail("Private output did not remain under Godot user data")
        return
    if not model.save_private() or not FileAccess.file_exists(path):
        _fail("Private authoring document save failed: " + model.last_error)
        return
    if not model.remove(1) or model.rows.size() != 1:
        _fail("Could not mutate unsaved design before reload")
        return
    if not model.load_private() or model.rows.size() != 2:
        _fail("Private source-authenticated draft did not survive disk roundtrip")
        return
    var old_text := FileAccess.get_file_as_string(path)
    var removed := DirAccess.remove_absolute(path)
    if removed != OK:
        _fail("Synthetic private test draft could not be cleaned up")
        return
    var check: Variant = JSON.parse_string(old_text)
    # Godot JSON materializes integer fields as floating-point numbers.
    # Compare the *source-validated, normalized* reloaded document instead
    # of byte-for-byte Variant types that JSON does not preserve.
    if typeof(check) != TYPE_DICTIONARY or not model.load_document(check):
        _fail("Private on-disk document failed source-identity validation")
        return
    if model.make_document() != snapshot:
        _fail("Private persisted document changed an authoring-only field")
        return
    var from_other_source = Draft.new()
    var foreign := _catalog()
    foreign["map_sha256"] = "0".repeat(64)
    if not from_other_source.initialize(foreign, _actors()):
        _fail("Alternate synthetic map identity should be loadable")
        return
    if from_other_source.load_document(snapshot):
        _fail("Different verified original map accepted a prior design")
        return
    if load("res://main.gd") == null:
        _fail("Main editor fails to parse with mission-logic Scripts tab")
        return
    print("DX2Ed private source-pinned TriggerScript authoring draft: PASS")
    quit(0)
