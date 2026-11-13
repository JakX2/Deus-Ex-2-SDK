extends RefCounted
## DX2Ed P104: map-cache-scoped PRIVATE catalog of P103 CSG recipes.
## The index contains only user-chosen recipe paths and fingerprints. It
## never stores a mesh, source map bytes, original actors or DX2 BSP data.
## Every refresh replays the independent Python recipe verifier (P103).
const Recipe = preload("res://private_csg_recipe_bridge.gd")
const SCHEMA = "DX2Ed-private-CSG-catalog-v1"
const MAX_ENTRIES = 64
const MAX_INDEX_BYTES = 128 * 1024
const INDEX_DIR = "user://private_csg_catalogs"
const ENTRY_FIELDS = [
    "path", "file_sha256", "operation", "source_private_a",
    "source_private_b", "computed_result_sha256",
]


static func catalog_path(map_cache: String) -> String:
    if (map_cache.is_empty() or map_cache.length() > 4096
        or not map_cache.is_absolute_path()):
        return ""
    var folder := ProjectSettings.globalize_path(INDEX_DIR)
    if DirAccess.make_dir_recursive_absolute(folder) != OK:
        return ""
    return folder.path_join(map_cache.sha256_text() + ".json")


static func _sha_valid(value: Variant) -> bool:
    if typeof(value) != TYPE_STRING or str(value).length() != 64:
        return false
    for character in str(value):
        if not "0123456789abcdef".contains(character):
            return false
    return true


static func _entry_valid(raw: Variant) -> bool:
    if typeof(raw) != TYPE_DICTIONARY or raw.size() != ENTRY_FIELDS.size():
        return false
    for field in ENTRY_FIELDS:
        if not raw.has(field) or typeof(raw[field]) != TYPE_STRING:
            return false
    if (not str(raw["path"]).is_absolute_path()
        or not str(raw["path"]).to_lower().ends_with(".dx2csg.json")
        or str(raw["operation"]) not in ["intersection", "subtraction"]
        or not str(raw["source_private_a"]).begins_with("DraftProp_")
        or not str(raw["source_private_b"]).begins_with("DraftProp_")
        or str(raw["source_private_a"]) == str(raw["source_private_b"])
        or not _sha_valid(raw["file_sha256"])
        or not _sha_valid(raw["computed_result_sha256"])):
        return false
    return true


static func _document(map_cache: String, entries: Array) -> Dictionary:
    return {
        "schema": SCHEMA,
        "map_cache": map_cache,
        "read_only_source": true,
        "native_bsp_or_collision_writer_enabled": false,
        "entries": entries,
    }


static func load_catalog(map_cache: String) -> Dictionary:
    var path := catalog_path(map_cache)
    if path.is_empty():
        return {"ok": false, "message": "No valid private map cache is selected."}
    if not FileAccess.file_exists(path):
        return {"ok": true, "entries": [], "path": path}
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return {"ok": false, "message": "Private CSG catalog unreadable."}
    if file.get_length() <= 0 or file.get_length() > MAX_INDEX_BYTES:
        file.close()
        return {"ok": false, "message": "Private CSG catalog size refused."}
    var data := file.get_as_text()
    file.close()
    var document: Variant = JSON.parse_string(data)
    if (typeof(document) != TYPE_DICTIONARY or document.size() != 5
        or document.get("schema", null) != SCHEMA
        or document.get("map_cache", null) != map_cache
        or document.get("read_only_source", null) != true
        or document.get("native_bsp_or_collision_writer_enabled", null) != false
        or not document.has("entries")
        or typeof(document["entries"]) != TYPE_ARRAY
        or document["entries"].size() > MAX_ENTRIES):
        return {"ok": false, "message": "Invalid or wrong-map private CSG catalog."}
    var seen := {}
    for raw in document["entries"]:
        if not _entry_valid(raw) or seen.has(raw["path"]):
            return {"ok": false, "message": (
                "Private CSG catalog includes invalid or duplicate recipe paths.")}
        seen[raw["path"]] = true
    return {
        "ok": true,
        "entries": document["entries"].duplicate(true),
        "path": path,
    }


static func _save_catalog(map_cache: String, entries: Array) -> bool:
    if entries.size() > MAX_ENTRIES:
        return false
    var loaded := load_catalog(map_cache)
    if not bool(loaded.get("ok", false)):
        return false
    var path: String = loaded["path"]
    var seen := {}
    for raw in entries:
        if not _entry_valid(raw) or seen.has(raw["path"]):
            return false
        seen[raw["path"]] = true
    var payload := JSON.stringify(_document(map_cache, entries), "  ")
    if payload.to_utf8_buffer().size() > MAX_INDEX_BYTES:
        return false
    var pending := path + ".pending"
    var backup := path + ".bak"
    # Failed/interrupted writes never truncate a registered catalog.
    if FileAccess.file_exists(pending):
        return false
    var file := FileAccess.open(pending, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(payload)
    file.flush()
    file.close()
    var staged := FileAccess.open(pending, FileAccess.READ)
    if staged == null:
        DirAccess.remove_absolute(pending)
        return false
    var exact := staged.get_as_text() == payload
    staged.close()
    if not exact:
        DirAccess.remove_absolute(pending)
        return false
    var existing := FileAccess.file_exists(path)
    if existing:
        if FileAccess.file_exists(backup) and DirAccess.remove_absolute(backup) != OK:
            DirAccess.remove_absolute(pending)
            return false
        if DirAccess.rename_absolute(path, backup) != OK:
            DirAccess.remove_absolute(pending)
            return false
    if DirAccess.rename_absolute(pending, path) != OK:
        if existing:
            DirAccess.rename_absolute(backup, path)
        return false
    return true


static func add_recipe(map_cache: String, recipe_path: String) -> Dictionary:
    var loaded := load_catalog(map_cache)
    if not bool(loaded.get("ok", false)):
        return loaded
    if loaded["entries"].size() >= MAX_ENTRIES:
        return {"ok": false, "message": "Private CSG catalog limited to 64 recipes."}
    for item in loaded["entries"]:
        if str(item["path"]) == recipe_path:
            return {"ok": false, "message": "CSG recipe is already registered."}
    # Reverify recipe data and resulting geometry BEFORE registering.
    var before := FileAccess.get_sha256(recipe_path)
    var replay: Dictionary = Recipe.load_recipe(recipe_path)
    var after := FileAccess.get_sha256(recipe_path)
    if (not bool(replay.get("ok", false)) or before != after
        or not _sha_valid(after)):
        return {"ok": false, "message": (
            "Unverifiable or changed CSG recipe cannot be registered.")}
    var entry := {
        "path": recipe_path,
        "file_sha256": after,
        "operation": str(replay["operation"]),
        "source_private_a": str(replay["source_private_a"]),
        "source_private_b": str(replay["source_private_b"]),
        "computed_result_sha256": str(replay["computed_result_sha256"]),
    }
    if not _entry_valid(entry):
        return {"ok": false, "message": "Private CSG recipe provenance invalid."}
    var entries: Array = loaded["entries"]
    entries.append(entry)
    if not _save_catalog(map_cache, entries):
        return {"ok": false, "message": "Could not transactionally write CSG catalog."}
    return {"ok": true, "entries": entries, "entry": entry,
            "index": entries.size() - 1}


static func refresh_recipe(map_cache: String, index: int) -> Dictionary:
    var loaded := load_catalog(map_cache)
    if not bool(loaded.get("ok", false)):
        return loaded
    var entries: Array = loaded["entries"]
    if index < 0 or index >= entries.size():
        return {"ok": false, "message": "Choose a registered private CSG recipe."}
    var entry: Dictionary = entries[index]
    var path: String = entry["path"]
    var before := FileAccess.get_sha256(path)
    if before != str(entry["file_sha256"]):
        return {"ok": false, "message": (
            "Registered CSG recipe changed, moved or vanished. "
            + "Remove and re-add only after verifying its source.")}
    var replay: Dictionary = Recipe.load_recipe(path)
    var after := FileAccess.get_sha256(path)
    if (not bool(replay.get("ok", false))
        or after != before
        or str(replay.get("operation", "")) != str(entry["operation"])
        or str(replay.get("source_private_a", "")) != str(entry["source_private_a"])
        or str(replay.get("source_private_b", "")) != str(entry["source_private_b"])
        or str(replay.get("computed_result_sha256", "")) !=
           str(entry["computed_result_sha256"])):
        return {"ok": false, "message": (
            "Registered CSG recipe failed independent recomputation or provenance.")}
    return {"ok": true, "entries": entries, "entry": entry,
            "replay": replay, "index": index}


static func remove_recipe(map_cache: String, index: int) -> Dictionary:
    var loaded := load_catalog(map_cache)
    if not bool(loaded.get("ok", false)):
        return loaded
    var entries: Array = loaded["entries"]
    if index < 0 or index >= entries.size():
        return {"ok": false, "message": "No private CSG recipe selected."}
    var removed: Dictionary = entries[index].duplicate(true)
    entries.remove_at(index)
    if not _save_catalog(map_cache, entries):
        return {"ok": false, "message": "Unable to update private CSG catalog."}
    # The referenced recipe file is intentionally NEVER deleted here.
    return {"ok": true, "entries": entries, "removed": removed}
