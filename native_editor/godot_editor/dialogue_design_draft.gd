extends RefCounted
## DX2Ed original-map-bound conversation TREE DESIGN only. These text lines
## and branches are never a decoded DX2 conversation, localization writer,
## audio scheduler, or native GMP/IBD/script package modification.
const SCHEMA := "DX2Ed-private-dialogue-tree-design-v1"
const MAX_NODES := 256
const MAX_CHOICES := 8
const MAX_TEXT := 1200
const MAX_CHOICE_TEXT := 160
const MAX_ID := 100000
const MAX_DOC_BYTES := 2 * 1024 * 1024

var ready := false
var last_error := ""
var source_map := ""
var source_sha256 := ""
var actors_by_export: Dictionary = {}
var nodes: Array[Dictionary] = []
var next_node_id := 1

func clear() -> void:
    ready = false
    last_error = ""
    source_map = ""
    source_sha256 = ""
    actors_by_export.clear()
    nodes.clear()
    next_node_id = 1

func _fail(reason: String) -> bool:
    last_error = reason
    return false

func _whole(value: Variant, low: int, high: int) -> bool:
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value))
        and float(value) >= float(low) and float(value) <= float(high)
        and float(int(value)) == float(value))

func initialize(map_name: String, sha: String, original_actors: Array) -> bool:
    clear()
    if (map_name.is_empty() or map_name.get_file() != map_name
        or not map_name.to_lower().ends_with(".gmp")
        or sha.length() != 64 or not sha.is_valid_hex_number()
        or original_actors.is_empty() or original_actors.size() > 30000):
        return _fail("No SHA-verified original GMP actor cache available")
    var indexed: Dictionary = {}
    for actor in original_actors:
        if (typeof(actor) != TYPE_DICTIONARY
            or not _whole(actor.get("export"), 1, 2147483647)
            or typeof(actor.get("name")) != TYPE_STRING
            or str(actor["name"]).is_empty()
            or typeof(actor.get("class")) != TYPE_STRING
            or str(actor["class"]).is_empty()):
            return _fail("Invalid source actor identity in map cache")
        var number := int(actor["export"])
        if indexed.has(number):
            return _fail("Duplicate native source actor export")
        indexed[number] = {
            "name": str(actor["name"]),
            "class": str(actor["class"]),
        }
    source_map = map_name
    source_sha256 = sha
    actors_by_export = indexed
    ready = true
    return true

func _text_safe(value: Variant, max_len: int, must_contain_text: bool) -> bool:
    if typeof(value) != TYPE_STRING:
        return false
    var text_value := str(value)
    return (text_value.length() <= max_len
        and (not must_contain_text or not text_value.strip_edges().is_empty())
        and not text_value.contains("\u0000"))

func _speaker(source_actor: Dictionary) -> Dictionary:
    if not _whole(source_actor.get("export"), 1, 2147483647):
        return {}
    var export_number := int(source_actor["export"])
    if (not actors_by_export.has(export_number)
        or source_actor.get("name") != actors_by_export[export_number]["name"]
        or source_actor.get("class") != actors_by_export[export_number]["class"]):
        return {}
    return {
        "speaker_export": export_number,
        "speaker_name": source_actor["name"],
        "speaker_class": source_actor["class"],
    }

func add_line(source_actor: Dictionary, text_value: String) -> int:
    last_error = ""
    if not ready or nodes.size() >= MAX_NODES or next_node_id > MAX_ID:
        _fail("Dialogue plan not ready or maximum line count reached")
        return -1
    if not _text_safe(text_value, MAX_TEXT, true):
        _fail("Dialogue line must contain text, maximum 1200 characters")
        return -1
    var speaker := _speaker(source_actor)
    if speaker.is_empty():
        _fail("Choose a verified original map actor as draft speaker")
        return -1
    var id := next_node_id
    next_node_id += 1
    nodes.append({
        "id": id,
        "speaker_export": speaker["speaker_export"],
        "speaker_name": speaker["speaker_name"],
        "speaker_class": speaker["speaker_class"],
        "text": text_value,
        "choices": [],
    })
    return id

func _index_by_id(node_id: int) -> int:
    for index in nodes.size():
        if int(nodes[index]["id"]) == node_id:
            return index
    return -1

func update_line(node_id: int, new_text: String) -> bool:
    var index := _index_by_id(node_id)
    if index < 0 or not _text_safe(new_text, MAX_TEXT, true):
        return _fail("Selected dialogue line or text is invalid")
    nodes[index]["text"] = new_text
    last_error = ""
    return true

func add_choice(node_id: int, target_id: int, caption: String) -> bool:
    var index := _index_by_id(node_id)
    if (not ready or index < 0 or _index_by_id(target_id) < 0
        or not _text_safe(caption, MAX_CHOICE_TEXT, true)
        or nodes[index]["choices"].size() >= MAX_CHOICES):
        return _fail("Choose existing source/target lines and a choice caption")
    for choice in nodes[index]["choices"]:
        if choice["target"] == target_id and choice["caption"] == caption:
            return _fail("Duplicate conversation branch")
    nodes[index]["choices"].append({"caption": caption, "target": target_id})
    last_error = ""
    return true

func remove_choice(node_id: int, choice_index: int) -> bool:
    var index := _index_by_id(node_id)
    if (index < 0 or choice_index < 0
        or choice_index >= nodes[index]["choices"].size()):
        return _fail("No conversation branch selected")
    nodes[index]["choices"].remove_at(choice_index)
    last_error = ""
    return true

func remove_line(node_id: int) -> bool:
    var index := _index_by_id(node_id)
    if index < 0:
        return _fail("No conversation line selected")
    nodes.remove_at(index)
    # Keep the draft graph referentially consistent on deletion.
    for line in nodes:
        var survivors: Array = []
        for choice in line["choices"]:
            if int(choice["target"]) != node_id:
                survivors.append(choice)
        line["choices"] = survivors
    last_error = ""
    return true

func make_document() -> Dictionary:
    if not ready:
        return {}
    return {
        "schema": SCHEMA,
        "source_map": source_map,
        "source_map_sha256": source_sha256,
        "authoring_only": true,
        "original_dialogue_format_decoded": false,
        "native_export_enabled": false,
        "gameplay_runtime_verified": false,
        "original_game_assets_modified": false,
        "next_node_id": next_node_id,
        "nodes": nodes.duplicate(true),
    }

func load_document(doc: Dictionary) -> bool:
    last_error = ""
    if (not ready or doc.get("schema") != SCHEMA
        or doc.get("source_map") != source_map
        or doc.get("source_map_sha256") != source_sha256
        or doc.get("authoring_only") != true
        or doc.get("original_dialogue_format_decoded") != false
        or doc.get("native_export_enabled") != false
        or doc.get("gameplay_runtime_verified") != false
        or doc.get("original_game_assets_modified") != false
        or typeof(doc.get("nodes")) != TYPE_ARRAY
        or doc["nodes"].size() > MAX_NODES
        or not _whole(doc.get("next_node_id"), 1, MAX_ID+1)):
        return _fail("Dialogue design is malformed or from a different original GMP")
    var validated: Array[Dictionary] = []
    var ids: Dictionary = {}
    var greatest := 0
    for line in doc["nodes"]:
        if (typeof(line) != TYPE_DICTIONARY
            or not _whole(line.get("id"), 1, MAX_ID)
            or not _whole(line.get("speaker_export"), 1, 2147483647)
            or not _text_safe(line.get("text"), MAX_TEXT, true)
            or typeof(line.get("choices")) != TYPE_ARRAY
            or line["choices"].size() > MAX_CHOICES):
            return _fail("Malformed dialogue line or oversized branch list")
        var id := int(line["id"])
        var export_number := int(line["speaker_export"])
        if (ids.has(id) or not actors_by_export.has(export_number)
            or line.get("speaker_name") != actors_by_export[export_number]["name"]
            or line.get("speaker_class") != actors_by_export[export_number]["class"]):
            return _fail("Dialogue speaker is not an original GMP actor")
        ids[id] = true
        greatest = maxi(greatest, id)
        var accepted_choices: Array = []
        var duplicates: Dictionary = {}
        for choice in line["choices"]:
            if (typeof(choice) != TYPE_DICTIONARY
                or not _text_safe(choice.get("caption"), MAX_CHOICE_TEXT, true)
                or not _whole(choice.get("target"), 1, MAX_ID)):
                return _fail("Malformed conversation branch")
            var target := int(choice["target"])
            var key := str(target) + ":" + str(choice["caption"])
            if duplicates.has(key):
                return _fail("Repeated conversation branch")
            duplicates[key] = true
            accepted_choices.append({"caption": choice["caption"], "target": target})
        validated.append({
            "id": id,
            "speaker_export": export_number,
            "speaker_name": line["speaker_name"],
            "speaker_class": line["speaker_class"],
            "text": line["text"],
            "choices": accepted_choices,
        })
    if greatest >= int(doc["next_node_id"]):
        return _fail("Dialogue node ID allocator is stale or corrupted")
    for line in validated:
        for choice in line["choices"]:
            if not ids.has(choice["target"]):
                return _fail("Dialogue branch points to a missing line")
    # Atomic. No partial mutation if an input node or link is invalid.
    nodes = validated
    next_node_id = int(doc["next_node_id"])
    return true

func private_path() -> String:
    if not ready:
        return ""
    return (ProjectSettings.globalize_path("user://dialogue_design")
        .path_join(source_sha256 + ".json"))

func save_private() -> bool:
    last_error = ""
    var path := private_path()
    if path.is_empty():
        return _fail("Import a real original GMP and its actor metadata first")
    if DirAccess.make_dir_recursive_absolute(path.get_base_dir()) != OK:
        return _fail("Cannot create private dialogue design directory")
    var target := FileAccess.open(path, FileAccess.WRITE)
    if target == null:
        return _fail("Cannot create private dialogue design JSON")
    target.store_string(JSON.stringify(make_document(), "  "))
    target.close()
    return true

func load_private() -> bool:
    last_error = ""
    var path := private_path()
    if path.is_empty() or not FileAccess.file_exists(path):
        return _fail("No dialogue design saved for this original source GMP")
    var stream := FileAccess.open(path, FileAccess.READ)
    if stream == null:
        return _fail("Cannot open private dialogue design JSON")
    var byte_count := stream.get_length()
    if byte_count <= 0 or byte_count > MAX_DOC_BYTES:
        stream.close()
        return _fail("Private dialogue draft is empty or too large")
    var text := stream.get_as_text()
    stream.close()
    if not text.strip_edges().begins_with("{"):
        return _fail("Private dialogue draft is not JSON")
    var doc: Variant = JSON.parse_string(text)
    if typeof(doc) != TYPE_DICTIONARY:
        return _fail("Private dialogue design JSON is malformed")
    return load_document(doc)
