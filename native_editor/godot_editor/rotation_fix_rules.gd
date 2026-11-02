extends RefCounted
## An editor-only, reproducible rotation correction catalogue. Not an
## inference of native game correctness. Every rule is scoped by mission,
## source mesh and all three original Unreal rotator values.

const SCHEMA := "DX2Ed-rotation-fix-rules-v1"
const ROTATOR_TOLERANCE := 0.01
const ALLOWED_MODES := [1, 2, 3, 4, 5]

static func mesh_name(actor: Dictionary) -> String:
    var source: Variant = actor.get("mesh", null)
    if typeof(source) == TYPE_STRING:
        return str(source)
    if typeof(source) == TYPE_DICTIONARY:
        return str(source.get("name", ""))
    return ""


static func rule_for_actor(source_map: String, actor: Dictionary, mode: int) -> Dictionary:
    if source_map.strip_edges().is_empty() or mesh_name(actor).is_empty():
        return {}
    if str(actor.get("class", "")) != "StaticMeshActor" or not ALLOWED_MODES.has(mode):
        return {}
    var raw: Variant = actor.get("rotation", [])
    if typeof(raw) != TYPE_ARRAY or raw.size() != 3:
        return {}
    for value in raw:
        if typeof(value) not in [TYPE_INT, TYPE_FLOAT]:
            return {}
        if is_nan(float(value)) or is_inf(float(value)):
            return {}
    return {
        "map": source_map,
        "mesh": mesh_name(actor),
        "rotator": [float(raw[0]), float(raw[1]), float(raw[2])],
        "mode": mode,
    }


static func validate(raw: Variant, source_map: String) -> Dictionary:
    if typeof(raw) != TYPE_DICTIONARY or not raw.has("mode"):
        return {}
    if str(raw.get("map", "")).to_lower() != source_map.to_lower():
        return {}
    if typeof(raw.get("map", null)) != TYPE_STRING or typeof(raw.get("mesh", null)) != TYPE_STRING:
        return {}
    if str(raw["mesh"]).strip_edges().is_empty() or str(raw["map"]).strip_edges().is_empty():
        return {}
    if typeof(raw.get("mode", null)) != TYPE_INT or not ALLOWED_MODES.has(raw["mode"]):
        return {}
    var rotator: Variant = raw.get("rotator", null)
    if typeof(rotator) != TYPE_ARRAY or rotator.size() != 3:
        return {}
    for value in rotator:
        if typeof(value) not in [TYPE_INT, TYPE_FLOAT] or is_nan(float(value)) or is_inf(float(value)):
            return {}
    return {
        "map": str(raw["map"]),
        "mesh": str(raw["mesh"]),
        "rotator": [float(rotator[0]), float(rotator[1]), float(rotator[2])],
        "mode": int(raw["mode"]),
    }


static func key(rule: Dictionary) -> String:
    # Scope by all original data, not inferred AABB or a vague class family.
    return str(rule.get("map", "")).to_lower() + "|" + str(rule.get("mesh", "")).to_lower() + "|" + JSON.stringify(rule.get("rotator", []))


static func matches(rule: Dictionary, source_map: String, actor: Dictionary) -> bool:
    if str(actor.get("class", "")) != "StaticMeshActor":
        return false
    if str(rule.get("map", "")).to_lower() != source_map.to_lower():
        return false
    if str(rule.get("mesh", "")).to_lower() != mesh_name(actor).to_lower():
        return false
    var actual: Variant = actor.get("rotation", [])
    var expected: Variant = rule.get("rotator", [])
    if typeof(actual) != TYPE_ARRAY or actual.size() != 3 or typeof(expected) != TYPE_ARRAY or expected.size() != 3:
        return false
    for i in range(3):
        if typeof(actual[i]) not in [TYPE_INT, TYPE_FLOAT] or absf(float(actual[i]) - float(expected[i])) > ROTATOR_TOLERANCE:
            return false
    return true


static func default_rules(source_map: String) -> Array:
    # This single narrow correction was visually confirmed by the user in
    # the Seattle WTO terminal: GEN_TRIM5-16ft, 0/32768/16384, invert roll.
    # Trier's demonstrated roll of 32768 (180 degrees) is *not* included:
    # negating 180 degrees is mathematically the same orientation.
    if source_map.to_lower() == "m1_seattle_hub_wtoterminal.gmp":
        return [{
            "map": source_map,
            "mesh": "GEN_TRIM5-16ft",
            "rotator": [0.0, 32768.0, 16384.0],
            "mode": 5,
        }]
    return []
