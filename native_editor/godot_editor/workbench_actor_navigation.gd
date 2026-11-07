extends RefCounted
## DX2SDK v0.18: pure source-verified actor navigation view projection.
## No GMP read, writes, actor creation, cache modification or editor authority.
const MODE_ALL := "All original actors"
const MODE_STAGED := "Actors with staged edits"
const MODE_UNSTAGED := "Actors without staged edits"
const MAX_QUERY := 128


static func modes() -> PackedStringArray:
    return PackedStringArray([MODE_ALL, MODE_STAGED, MODE_UNSTAGED])


static func projected(original_actors: Array[Dictionary], staged: Array[Dictionary],
                      query: String, mode: String) -> Dictionary:
    if mode not in modes():
        return {"rows": [], "total": original_actors.size(), "visible": 0}
    var needle := query.strip_edges().to_lower().substr(0, MAX_QUERY)
    var result: Array[Dictionary] = []
    for i in range(original_actors.size()):
        var actor: Dictionary = original_actors[i]
        var name := str(actor.get("actor", ""))
        var exp := int(actor.get("export", -1))
        var count := 0
        for row in staged:
            if (row.get("actor") == name
                and row.get("export") == exp):
                count += 1
        if ((mode == MODE_STAGED and count == 0)
            or (mode == MODE_UNSTAGED and count > 0)):
            continue
        if (not needle.is_empty()
            and name.to_lower().find(needle) < 0
            and str(exp).find(needle) < 0):
            continue
        result.append({
            "original_index": i, "actor": name, "export": exp,
            "staged_count": count,
            "label": "#%d  %s  %s" % [
                exp, name, ("[" + str(count) + " staged]" if count > 0 else "[source only]")],
        })
    return {"rows": result, "total": original_actors.size(), "visible": result.size()}


static func original_index_for_export(original_actors: Array[Dictionary],
                                      name: String, export: int) -> int:
    # Native actor identities must match BOTH the original export and name.
    # Ambiguous evidence is refused. This can never grant permission to edit.
    var found := -1
    for i in range(original_actors.size()):
        if (original_actors[i].get("actor") == name
            and original_actors[i].get("export") == export):
            if found >= 0:
                return -1
            found = i
    return found
