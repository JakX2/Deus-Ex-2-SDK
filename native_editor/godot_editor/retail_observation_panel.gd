extends AcceptDialog
## DX2Ed v0.67: owner-only retail A/B observation entry panel.
## No game process is launched and no original, candidate, test-map or backup
## file is written. Only v0.66's private observation JSON is ever updated.
const PythonRuntime = preload("res://python_runtime.gd")
const WORKER_SCHEMA := "DX2Ed-retail-human-observation-recorder-v1"
const ACK := "OWNER_REPORTED_NOT_GAME_VERIFIED"

var source_map := ""
var source_sha256 := ""
var worker: Thread = null
var worker_script := ""
var inspected := false
var pending: Dictionary = {}
var paths: Dictionary = {}
var check_choice: OptionButton
var result_choice: OptionButton
var note_input: LineEdit
var evidence_input: LineEdit
var status: Label
var confirmation: ConfirmationDialog
var choose_file: FileDialog
var browse_kind := ""
var inspect_button: Button
var record_button: Button


func _ready() -> void:
    title = "Retail Test Observations (owner-reported)"
    get_ok_button().text = "Close"
    min_size = Vector2i(830, 530)
    var layout := VBoxContainer.new()
    layout.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    add_child(layout)
    var notice := Label.new()
    notice.text = ("This records what YOU observed in a disposable DX2 installation. "
        + "It does not execute or verify the game. An unchanged original GMP, "
        + "source-replayed candidate, matching trial dossier and v0.65 test journal are required.")
    notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    layout.add_child(notice)
    for kind in ["candidate", "dossier", "observations", "root"]:
        var row := HBoxContainer.new()
        layout.add_child(row)
        var label := Label.new()
        label.text = {
            "candidate": "Candidate GMP",
            "dossier": "Trial dossier",
            "observations": "Owner observations",
            "root": "Disposable game root"
        }[kind]
        label.custom_minimum_size.x = 150
        row.add_child(label)
        var entry := LineEdit.new()
        entry.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        entry.text_changed.connect(_path_changed)
        row.add_child(entry)
        paths[kind] = entry
        var browse := Button.new()
        browse.text = "Browse..."
        browse.pressed.connect(_browse.bind(kind))
        row.add_child(browse)
    var choices := HBoxContainer.new()
    layout.add_child(choices)
    var check_label := Label.new()
    check_label.text = "Check ID (from inspected trial):"
    choices.add_child(check_label)
    check_choice = OptionButton.new()
    check_choice.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    choices.add_child(check_choice)
    var result_label := Label.new()
    result_label.text = "Owner result"
    choices.add_child(result_label)
    result_choice = OptionButton.new()
    for value in ["pass", "fail", "inconclusive", "not-tested"]:
        result_choice.add_item(value)
    choices.add_child(result_choice)
    var note_row := HBoxContainer.new()
    layout.add_child(note_row)
    var note_label := Label.new()
    note_label.text = "Human observation"
    note_label.custom_minimum_size.x = 150
    note_row.add_child(note_label)
    note_input = LineEdit.new()
    note_input.max_length = 1000
    note_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    note_input.placeholder_text = "Describe what you actually tested and observed"
    note_row.add_child(note_input)
    var evidence_row := HBoxContainer.new()
    layout.add_child(evidence_row)
    var evidence_label := Label.new()
    evidence_label.text = "Evidence (optional)"
    evidence_label.custom_minimum_size.x = 150
    evidence_row.add_child(evidence_label)
    evidence_input = LineEdit.new()
    evidence_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    evidence_input.placeholder_text = "Local screenshot/video (SHA-256 only, not copied)"
    evidence_row.add_child(evidence_input)
    var browse_evidence := Button.new()
    browse_evidence.text = "Browse..."
    browse_evidence.pressed.connect(_browse.bind("evidence"))
    evidence_row.add_child(browse_evidence)
    status = Label.new()
    status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    status.text = "Open an original GMP, then select a matching private trial."
    layout.add_child(status)
    inspect_button = add_button("Inspect trial state", false, "inspect")
    record_button = add_button("Record owner result...", false, "record")
    record_button.disabled = true
    custom_action.connect(_custom_action)
    choose_file = FileDialog.new()
    choose_file.access = FileDialog.ACCESS_FILESYSTEM
    choose_file.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    choose_file.file_selected.connect(_selected_file)
    choose_file.dir_selected.connect(_selected_directory)
    add_child(choose_file)
    confirmation = ConfirmationDialog.new()
    confirmation.title = "Confirm OWNER-REPORTED observation"
    confirmation.confirmed.connect(_confirmed_record)
    add_child(confirmation)


func _exit_tree() -> void:
    if worker != null:
        worker.wait_to_finish()
        worker = null


func configure(original: String, original_sha: String) -> void:
    if original != source_map or original_sha != source_sha256:
        for key in paths:
            (paths[key] as LineEdit).clear()
        evidence_input.clear()
        note_input.clear()
    source_map = original
    source_sha256 = original_sha
    _invalidate()
    if not source_map.is_empty():
        status.text = "Source pinned to " + source_map.get_file() + ". Inspect the disposable trial."


func _invalidate(_new_text: String = "") -> void:
    inspected = false
    pending.clear()
    check_choice.clear()
    record_button.disabled = true


func _path_changed(_new_text: String) -> void:
    _invalidate()


func _browse(kind: String) -> void:
    if worker != null:
        return
    browse_kind = kind
    choose_file.clear_filters()
    if kind == "root":
        choose_file.file_mode = FileDialog.FILE_MODE_OPEN_DIR
    else:
        choose_file.file_mode = FileDialog.FILE_MODE_OPEN_FILE
        if kind == "candidate":
            choose_file.add_filter("*.gmp", "Isolated GMP")
        elif kind == "dossier":
            choose_file.add_filter("*.dx2trial.json", "Private retail trial dossier")
        elif kind == "observations":
            choose_file.add_filter("*.dx2observations.json", "Private owner observations")
    choose_file.popup_centered_ratio(0.78)


func _selected_file(path: String) -> void:
    if browse_kind == "evidence":
        evidence_input.text = path
        return
    if paths.has(browse_kind):
        (paths[browse_kind] as LineEdit).text = path
        if browse_kind == "dossier" and path.ends_with(".dx2trial.json"):
            (paths["observations"] as LineEdit).text = (
                path.trim_suffix(".dx2trial.json") + ".dx2observations.json")
        _invalidate()


func _selected_directory(path: String) -> void:
    if browse_kind == "root":
        (paths["root"] as LineEdit).text = path
        _invalidate()


func _base_args() -> PackedStringArray:
    return PackedStringArray([
        worker_script,
        "--source", source_map, "--candidate", (paths["candidate"] as LineEdit).text,
        "--source-sha256", source_sha256,
        "--dossier", (paths["dossier"] as LineEdit).text,
        "--observations", (paths["observations"] as LineEdit).text,
        "--test-root", (paths["root"] as LineEdit).text,
    ])


func _local_preflight() -> bool:
    if worker != null:
        status.text = "Previous trial verification still running."
        return false
    worker_script = ProjectSettings.globalize_path(
        "res://../package_writer/dx2_retail_observation_recorder.py")
    if not FileAccess.file_exists(worker_script):
        status.text = "Owner-only observation recorder is missing from the local SDK."
        return false
    if (source_map.is_empty() or source_sha256.length() != 64
        or not FileAccess.file_exists(source_map)
        or FileAccess.get_sha256(source_map) != source_sha256):
        status.text = "Original GMP missing or changed since editor import."
        return false
    var candidate := (paths["candidate"] as LineEdit).text
    if (not FileAccess.file_exists(candidate)
        or candidate == source_map or candidate.get_file().to_lower() != source_map.get_file().to_lower()):
        status.text = "Select a separate isolated candidate with the original GMP basename."
        return false
    for kind in ["dossier", "observations"]:
        if not FileAccess.file_exists((paths[kind] as LineEdit).text):
            status.text = "Missing matching private " + kind + " JSON."
            return false
    var root := (paths["root"] as LineEdit).text
    if not DirAccess.dir_exists_absolute(root) or root.get_file() != "DX2Ed_Disposable_Test":
        status.text = "Only a separately created DX2Ed_Disposable_Test folder is allowed."
        return false
    return true


func _custom_action(action: StringName) -> void:
    if action == &"inspect":
        _inspect()
    elif action == &"record":
        _request_record()


func _inspect() -> void:
    _invalidate()
    if not _local_preflight():
        return
    pending = {
        "kind": "inspect",
        "source_sha": source_sha256,
        "candidate_sha": FileAccess.get_sha256((paths["candidate"] as LineEdit).text)
    }
    var args := _base_args()
    args.append("--inspect")
    _start_worker(args)


func _request_record() -> void:
    if not inspected or not _local_preflight() or check_choice.item_count == 0:
        status.text = "First inspect the matching trial; the map state may have changed."
        return
    var chosen := check_choice.get_selected_id()
    if chosen < 0 or chosen >= check_choice.item_count:
        status.text = "Select a check from the inspected trial."
        return
    var result_name := result_choice.get_item_text(result_choice.get_selected_id())
    var note := note_input.text
    if result_name == "not-tested":
        if not note.is_empty() or not evidence_input.text.is_empty():
            status.text = "To clear a result, empty the note and evidence fields."
            return
    elif note.strip_edges().is_empty():
        status.text = "A human-observation note is required for any reported result."
        return
    pending = {
        "kind": "record", "source_sha": source_sha256,
        "candidate_sha": FileAccess.get_sha256((paths["candidate"] as LineEdit).text),
        "check_id": check_choice.get_item_text(chosen),
        "result": result_name, "note": note,
        "evidence": evidence_input.text,
        "paths": _base_args()
    }
    confirmation.dialog_text = (
        "Record a HUMAN-REPORTED " + result_name + " for " + str(pending["check_id"])
        + "?\n\n" + note
        + "\n\nOnly the private owner observations JSON is updated."
        + "\nThis does NOT prove that Invisible War was run, or that the change works."
        + "\nThe Python worker will revalidate source, GMP and trial journal.")
    confirmation.popup_centered(Vector2i(730, 360))


func _confirmed_record() -> void:
    if pending.get("kind", "") != "record" or not inspected or not _local_preflight():
        pending.clear()
        status.text = "Observation recording cancelled: session changed or trial unavailable."
        return
    if (str(pending.get("source_sha", "")) != source_sha256
        or str(pending.get("candidate_sha", "")) != FileAccess.get_sha256(
            (paths["candidate"] as LineEdit).text)
        or pending.get("paths") != _base_args()
        or str(pending.get("note", "")) != note_input.text
        or str(pending.get("evidence", "")) != evidence_input.text):
        _invalidate()
        status.text = "Observation recording cancelled: source or requested fields changed."
        return
    var args := _base_args()
    args.append_array(PackedStringArray([
        "--record", "--check-id", str(pending["check_id"]),
        "--result", str(pending["result"]), "--note", str(pending["note"]),
        "--acknowledge", ACK
    ]))
    if not str(pending["evidence"]).is_empty():
        args.append_array(PackedStringArray(["--evidence", str(pending["evidence"])]))
    _start_worker(args)


func _start_worker(args: PackedStringArray) -> void:
    if worker != null:
        return
    worker = Thread.new()
    var error := worker.start(_run_worker.bind(args, pending.duplicate(true)))
    if error != OK:
        worker = null
        status.text = "Could not start original-derived owner observation worker."
        return
    inspect_button.disabled = true
    record_button.disabled = true
    status.text = "Checking source-GMP replay and disposable test journal..."


func _run_worker(args: PackedStringArray, context: Dictionary) -> void:
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        var fallback := PackedStringArray(["-3"])
        fallback.append_array(args)
        output.clear()
        code = OS.execute("py", fallback, output, true)
    call_deferred("_worker_done", code, "\n".join(output), context)


func _worker_done(code: int, response: String, context: Dictionary) -> void:
    if worker != null:
        worker.wait_to_finish()
        worker = null
    inspect_button.disabled = false
    var doc: Variant = JSON.parse_string(response.strip_edges())
    if (code != 0 or typeof(doc) != TYPE_DICTIONARY
        or doc.get("schema") != WORKER_SCHEMA
        or doc.get("gameplay_runtime_verified") != false):
        _invalidate()
        status.text = "Trial inspection/observation refused: " + response.substr(0, 400)
        return
    if context.get("kind") == "inspect":
        if (doc.get("game_installation_modified") != false
            or doc.get("observations_independently_verified") != false
            or doc.get("source_sha256") != source_sha256
            or doc.get("candidate_sha256") != context.get("candidate_sha")
            or typeof(doc.get("recordable_check_ids_at_current_phase")) != TYPE_ARRAY):
            _invalidate()
            status.text = "Trial inspector returned unexpected source, state or safety flags."
            return
        check_choice.clear()
        var offered: Dictionary = {}
        for key in doc["recordable_check_ids_at_current_phase"]:
            if typeof(key) != TYPE_STRING or key.is_empty() or offered.has(key):
                _invalidate()
                status.text = "Invalid or duplicated owner check identifier."
                return
            offered[key] = true
            check_choice.add_item(key)
        inspected = check_choice.item_count > 0
        record_button.disabled = not inspected
        status.text = (
            "Disposable phase: " + str(doc.get("trial_phase", "?"))
            + " | Map: " + str(doc.get("test_map_content", "?"))
            + " | Eligible owner checks: " + str(check_choice.item_count)
            + " | No game execution/verification claimed.")
    else:
        if (doc.get("status") != "owner-observation-recorded-not-independently-verified"
            or doc.get("observations_independently_verified") != false
            or doc.get("game_installation_modified") != false
            or doc.get("check_id") != context.get("check_id")
            or doc.get("owner_result") != context.get("result")):
            _invalidate()
            status.text = "Observation worker returned unexpected result."
            return
        _invalidate()
        status.text = ("Owner observation stored for " + str(doc["check_id"])
            + ". Inspect again to refresh counts and eligible checks. Gameplay remains unverified.")
    pending.clear()
