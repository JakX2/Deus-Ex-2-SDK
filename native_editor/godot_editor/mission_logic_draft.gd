extends RefCounted
## Owner-local, source-hash-bound TriggerScript DESIGN plan.
## This is intentionally a separate authoring document, NOT a GMP/IBD/TSD
## writer, executable script, decoded actor-script binding or native link.
const SCHEMA := "DX2Ed-mission-logic-design-draft-v1"
const CATALOG_SCHEMA := "DX2Ed-original-gameplay-catalog-v1"
const MAX_ROWS := 512
const MAX_NOTE := 400
const MAX_DOC_BYTES := 1024 * 1024

var ready := false
var last_error := ""
var source_map := ""
var map_sha256 := ""
var archive_sha256 := ""
var actors_by_export: Dictionary = {}
var definitions: Dictionary = {}
var rows: Array[Dictionary] = []

func clear() -> void:
    ready = false
    last_error = ""
    source_map = ""
    map_sha256 = ""
    archive_sha256 = ""
    actors_by_export.clear()
    definitions.clear()
    rows.clear()

func _fail(reason: String) -> bool:
    last_error = reason
    return false

func _source_sha(value: Variant) -> bool:
    return (typeof(value) == TYPE_STRING
        and str(value).length() == 64
        and str(value).is_valid_hex_number())

func initialize(catalog: Dictionary, original_actors: Array) -> bool:
    clear()
    if (catalog.get("schema") != CATALOG_SCHEMA
        or catalog.get("read_only") != true
        or catalog.get("bindings_verified") != false
        or catalog.get("spawn_enabled") != false
        or not _source_sha(catalog.get("map_sha256"))
        or not _source_sha(catalog.get("script_archive_sha256"))
        or typeof(catalog.get("map")) != TYPE_STRING
        or str(catalog["map"]).get_file() != str(catalog["map"])
        or not str(catalog["map"]).to_lower().ends_with(".gmp")
        or typeof(catalog.get("script_definitions")) != TYPE_ARRAY
        or catalog["script_definitions"].is_empty()
        or catalog["script_definitions"].size() > 5000
        or original_actors.is_empty() or original_actors.size() > 30000):
        return _fail("Original GMP or TriggerScript source identity is not verified")
    var validated_scripts: Dictionary = {}
    for script in catalog["script_definitions"]:
        if typeof(script) != TYPE_DICTIONARY or typeof(script.get("id")) != TYPE_STRING:
            return _fail("Original TriggerScript definition is malformed")
        var sid: String = script["id"]
        if sid.is_empty() or sid.length() > 128 or validated_scripts.has(sid):
            return _fail("Original TriggerScript IDs are missing or ambiguous")
        validated_scripts[sid] = true
    var validated_actors: Dictionary = {}
    for actor in original_actors:
        if (typeof(actor) != TYPE_DICTIONARY
            or not _valid_export(actor.get("export"))
            or typeof(actor.get("name")) != TYPE_STRING
            or str(actor["name"]).is_empty()
            or typeof(actor.get("class")) != TYPE_STRING
            or str(actor["class"]).is_empty()
            or validated_actors.has(int(actor["export"]))):
            return _fail("Original actor export identities are missing or ambiguous")
        validated_actors[int(actor["export"])] = {
            "name": str(actor["name"]),
            "class": str(actor["class"])
        }
    source_map = str(catalog["map"])
    map_sha256 = str(catalog["map_sha256"])
    archive_sha256 = str(catalog["script_archive_sha256"])
    definitions = validated_scripts
    actors_by_export = validated_actors
    ready = true
    return true

func _valid_export(value: Variant) -> bool:
    # Godot's JSON parser materializes serialized integer actor exports as
    # float64. Accept exactly representable whole numbers only; never round.
    return (typeof(value) in [TYPE_INT, TYPE_FLOAT]
        and is_finite(float(value))
        and float(value) >= 1. and float(value) <= 2147483647.
        and float(int(value)) == float(value))

func _valid_row(row: Variant) -> bool:
    if not ready or typeof(row) != TYPE_DICTIONARY:
        return false
    if not _valid_export(row.get("actor_export")):
        return false
    var actor_export := int(row["actor_export"])
    if (typeof(row.get("script_id")) != TYPE_STRING
        or not definitions.has(row["script_id"])
        or not actors_by_export.has(actor_export)
        or typeof(row.get("actor_name")) != TYPE_STRING
        or typeof(row.get("actor_class")) != TYPE_STRING
        or row["actor_name"] != actors_by_export[actor_export]["name"]
        or row["actor_class"] != actors_by_export[actor_export]["class"]
        or typeof(row.get("note")) != TYPE_STRING
        or str(row["note"]).length() > MAX_NOTE):
        return false
    return true

func plan_actor_script(script_id: String, actor: Dictionary, note: String = "") -> bool:
    last_error = ""
    if not ready:
        return _fail("Import the original map and TriggerScript catalog first")
    var row := {
        "script_id": script_id,
        "actor_export": actor.get("export", -1),
        "actor_name": actor.get("name", ""),
        "actor_class": actor.get("class", ""),
        "note": note,
    }
    if not _valid_row(row):
        return _fail("Select one original actor and a known source TriggerScript ID")
    if rows.size() >= MAX_ROWS:
        return _fail("Too many editor-only planned bindings")
    for existing in rows:
        if (existing["script_id"] == row["script_id"]
            and existing["actor_export"] == row["actor_export"]):
            return _fail("This original actor/script pair is already in the design plan")
    # Godot JSON actor caches commonly return float64 numeric exports.
    # Normalize once, never store float actors in the new design schema.
    row["actor_export"] = int(row["actor_export"])
    rows.append(row)
    return true

func change_note(index: int, note: String) -> bool:
    if index < 0 or index >= rows.size() or note.length() > MAX_NOTE:
        return _fail("Invalid selected draft row or note length (maximum 400 characters)")
    rows[index]["note"] = note
    last_error = ""
    return true

func remove(index: int) -> bool:
    if index < 0 or index >= rows.size():
        return _fail("No valid planned binding selected")
    rows.remove_at(index)
    last_error = ""
    return true

func make_document() -> Dictionary:
    if not ready:
        return {}
    return {
        "schema": SCHEMA,
        "source_map": source_map,
        "source_map_sha256": map_sha256,
        "script_archive_sha256": archive_sha256,
        "authoring_only": true,
        "native_script_binding_written": false,
        "original_game_assets_modified": false,
        "gameplay_runtime_verified": false,
        "rows": rows.duplicate(true),
    }

func load_document(doc: Dictionary) -> bool:
    last_error = ""
    if (not ready or doc.get("schema") != SCHEMA
        or doc.get("source_map") != source_map
        or doc.get("source_map_sha256") != map_sha256
        or doc.get("script_archive_sha256") != archive_sha256
        or doc.get("authoring_only") != true
        or doc.get("native_script_binding_written") != false
        or doc.get("original_game_assets_modified") != false
        or doc.get("gameplay_runtime_verified") != false
        or typeof(doc.get("rows")) != TYPE_ARRAY
        or doc["rows"].size() > MAX_ROWS):
        return _fail("Design draft is malformed or refers to a different GMP/script archive")
    var accepted: Array[Dictionary] = []
    var seen: Dictionary = {}
    for row in doc["rows"]:
        if not _valid_row(row):
            return _fail("Draft actor, original export or script identity has changed")
        var key := "%d:%s" % [int(row["actor_export"]), str(row["script_id"])]
        if seen.has(key):
            return _fail("Draft duplicates one original actor/script pair")
        seen[key] = true
        accepted.append({
            "script_id": row["script_id"],
            "actor_export": int(row["actor_export"]),
            "actor_name": row["actor_name"],
            "actor_class": row["actor_class"],
            "note": row["note"],
        })
    # Atomic: an invalid document cannot partially replace an active design.
    rows = accepted
    return true

func private_path() -> String:
    if not ready:
        return ""
    return (ProjectSettings.globalize_path("user://mission_logic_design")
        .path_join(map_sha256 + "_" + archive_sha256 + ".json"))

func save_private() -> bool:
    last_error = ""
    var path := private_path()
    if path.is_empty():
        return _fail("No original map/script catalog source loaded")
    var folder := path.get_base_dir()
    if DirAccess.make_dir_recursive_absolute(folder) != OK:
        return _fail("Could not create private DX2Ed design folder")
    var output := FileAccess.open(path, FileAccess.WRITE)
    if output == null:
        return _fail("Could not write private DX2Ed design draft")
    output.store_string(JSON.stringify(make_document(), "  "))
    output.close()
    return true

func load_private() -> bool:
    last_error = ""
    var path := private_path()
    if path.is_empty() or not FileAccess.file_exists(path):
        return _fail("No private mission-logic design draft for this source pair")
    var source := FileAccess.open(path, FileAccess.READ)
    if source == null:
        return _fail("Could not open the private design document")
    if source.get_length() <= 0 or source.get_length() > MAX_DOC_BYTES:
        source.close()
        return _fail("Mission-logic design draft is empty or too large")
    var text := source.get_as_text()
    source.close()
    # Preserve existing rows on corruption. Invalid JSON is not native data.
    if not text.strip_edges().begins_with("{"):
        return _fail("Mission-logic design draft is not JSON")
    var doc: Variant = JSON.parse_string(text)
    if typeof(doc) != TYPE_DICTIONARY:
        return _fail("Mission-logic design draft JSON is invalid")
    return load_document(doc)
