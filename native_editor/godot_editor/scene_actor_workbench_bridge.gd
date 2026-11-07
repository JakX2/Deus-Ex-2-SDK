extends RefCounted
## v0.19 read-only scene-selection to original Actor Workbench gate.
## This is a SOURCE IDENTIFICATION bridge, not a native actor field writer.
## All final inventory and original GMP/cache bytes are rechecked by the
## workbench Python worker before any original tag becomes editable.


static func candidate(
        selected: Dictionary, indexed_original: Dictionary,
        scene_mesh_name: String, selected_mesh_count: int,
        original_source_name: String, original_gmp_name: String,
        declared_sha256: String, pinned_sha256: String,
        current_actors_json: String, pinned_actors_json: String) -> Dictionary:
    if (selected_mesh_count != 1 or scene_mesh_name.is_empty()
        or original_source_name.is_empty() or original_gmp_name.is_empty()
        or original_source_name.to_lower() != original_gmp_name.to_lower()
        or declared_sha256.length() != 64
        or not declared_sha256.is_valid_hex_number()
        or declared_sha256.to_lower() != pinned_sha256.to_lower()
        or current_actors_json.is_empty() or pinned_actors_json.is_empty()
        or current_actors_json.simplify_path() != pinned_actors_json.simplify_path()):
        return {}
    if (selected.is_empty() or indexed_original.is_empty()
        or selected.get("class") != "StaticMeshActor"
        or indexed_original.get("class") != "StaticMeshActor"
        or typeof(selected.get("name")) != TYPE_STRING
        or typeof(indexed_original.get("name")) != TYPE_STRING
        or str(selected["name"]) != scene_mesh_name
        or str(indexed_original["name"]) != scene_mesh_name
        or typeof(selected.get("export")) != TYPE_INT
        or typeof(indexed_original.get("export")) != TYPE_INT
        or int(selected["export"]) <= 0
        or selected["export"] != indexed_original["export"]):
        return {}
    # Reject recognized draft identities even if a tool accidentally reused
    # a real original actor's name or export. The owner also checks that the
    # selected Godot mesh is exactly the immutable imported actor mesh.
    for key in ["draft", "is_draft", "draft_clone", "is_clone", "new_actor"]:
        if selected.get(key, false) == true or indexed_original.get(key, false) == true:
            return {}
    return {
        "actor": scene_mesh_name,
        "export": int(selected["export"]),
        "source_map": original_gmp_name,
        "source_sha256": pinned_sha256.to_lower(),
    }
