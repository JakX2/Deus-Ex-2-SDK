extends RefCounted
## DX2SDK v0.17: pure, read-only Actor Workbench presentation.
## This never returns a write authorization. Native numeric edit eligibility
## is decided exclusively by the original GMP+actors.json SHA-bound SDK.
const MODE_ALL := "All source tags"
const MODE_ELIGIBLE := "Editable existing numeric"
const MODE_READONLY := "Read-only and opaque"
const MODE_STAGED := "Staged changes"
const MAX_QUERY_LENGTH := 128


static func modes() -> PackedStringArray:
    return PackedStringArray([
        MODE_ALL, MODE_ELIGIBLE, MODE_READONLY, MODE_STAGED,
    ])


static func _stage_for(
        staged: Array, actor: String, export: int, field: Dictionary) -> Dictionary:
    if field.get("editable_existing_tag") != true:
        return {}
    for row in staged:
        if (typeof(row) == TYPE_DICTIONARY
            and row.get("actor") == actor
            and row.get("export") == export
            and row.get("property") == field.get("property")):
            return row
    return {}


static func filtered(catalog: Dictionary, query: String, mode: String,
                     staged: Array) -> Dictionary:
    # Catalog has already passed the GUI's source-identity/structure gate.
    # Filtering controls visibility only. It never changes the catalog,
    # typed original fields, staging, source SHA or output authorization.
    if catalog.is_empty() or mode not in modes():
        return {"groups": [], "shown": 0, "total": 0}
    var needle := query.strip_edges().to_lower().substr(0, MAX_QUERY_LENGTH)
    var groups: Array[Dictionary] = []
    var visible := 0
    var original := int(catalog.get("source_top_level_tag_count", 0))
    for category in catalog.get("categories", []):
        var rows: Array[Dictionary] = []
        for field in category["fields"]:
            var editable: bool = field["editable_existing_tag"] == true
            var stage := _stage_for(
                staged, str(catalog["actor"]), int(catalog["export"]), field)
            var changed := not stage.is_empty()
            if ((mode == MODE_ELIGIBLE and not editable)
                or (mode == MODE_READONLY and editable)
                or (mode == MODE_STAGED and not changed)):
                continue
            var search_text := (
                str(field["property"]) + " " +
                str(field["native_kind_label"]) + " " +
                str(category["label"]) + " " +
                str(field["category"]) + " " +
                str(field["native_kind"]) + " " +
                str(field["source_byte_offset"])
            ).to_lower()
            if not needle.is_empty() and search_text.find(needle) == -1:
                continue
            var row: Dictionary = field.duplicate(true)
            row["has_staged_change"] = changed
            row["staged_replacement"] = stage.get("replacement")
            rows.append(row)
            visible += 1
        # Keep all six categories visible in the unfiltered overview.
        if not rows.is_empty() or (needle.is_empty() and mode == MODE_ALL):
            groups.append({
                "key": category["key"],
                "label": category["label"],
                "count": rows.size(),
                "fields": rows,
            })
    return {"groups": groups, "shown": visible, "total": original}


static func detail(catalog: Dictionary, field: Dictionary, staged: Array) -> String:
    if catalog.is_empty() or field.is_empty():
        return "Choose a source-native tag to inspect its serialized evidence."
    var eligible: bool = field.get("editable_existing_tag") == true
    var stage := _stage_for(
        staged, str(catalog["actor"]), int(catalog["export"]), field)
    var result := (
        "Original actor: " + str(catalog["actor"])
        + "  |  export #" + str(catalog["export"])
        + "\nGMP SHA-256: " + str(catalog["source_sha256"])
        + "\nactors.json SHA-256: " + str(catalog["actors_sha256"])
        + "\nOriginal tag: " + str(field["property"])
        + "\nTag ordinal: " + str(field["tag_ordinal"])
        + "  | native kind: " + str(field["native_kind"])
        + " (" + str(field["native_kind_label"]) + ")"
        + "\nPayload: " + str(field["serialized_payload_size"])
        + " bytes  | original byte offset: " + str(field["source_byte_offset"])
        + "\nIndexed / special: " + ("yes" if field["indexed_or_special"] else "no")
        + "\nClassification: " + str(field["category"])
    )
    if eligible:
        result += (
            "\nOriginal value: " + str(field["original_value"])
            + "\nStaged replacement: "
            + (str(stage["replacement"]) if not stage.is_empty() else "(none)")
            + "\nWrite scope: existing 4-byte numeric tag only, guarded Save As")
    else:
        result += (
            "\nOriginal value: not decoded (opaque/protected layout)"
            + "\nWrite scope: READ ONLY; no native edit control")
    return result + (
        "\nRetail gameplay effect: UNVERIFIED"
        + "\nNever grants new tags, GameSys, script, collision or BSP writes."
    )
