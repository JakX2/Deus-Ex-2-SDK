extends RefCounted
## Editor-private Godot light previews. These are not native DX2 Light actors,
## projectors, baked lightmaps, GameSys records or cooked map data.

const KINDS = ["Point", "Spot"]
const MAX_LIGHTS := 32
const MAX_SHADOW_LIGHTS := 8
const NODE_NAME := "DX2Ed_LightPreview_EDITOR_ONLY"


static func default_spec(kind: String) -> Dictionary:
    if not KINDS.has(kind):
        return {}
    return {
        "kind": kind,
        "color": [1.0, 0.78, 0.52, 1.0],
        "energy": 1.25,
        "range": 8.0,
        "spot_angle": 42.0,
        "shadows": false,
        "enabled": true
    }


static func validate(raw: Variant, expected_kind: String = "") -> Dictionary:
    if typeof(raw) != TYPE_DICTIONARY or raw.size() != 7:
        return {}
    var kind: Variant = raw.get("kind", null)
    if (typeof(kind) != TYPE_STRING or not KINDS.has(kind)
        or (not expected_kind.is_empty() and kind != expected_kind)):
        return {}
    var color: Variant = raw.get("color", null)
    if typeof(color) != TYPE_ARRAY or color.size() != 4:
        return {}
    var checked_color: Array[float] = []
    for component in color:
        if typeof(component) not in [TYPE_INT, TYPE_FLOAT]:
            return {}
        var number := float(component)
        if not is_finite(number) or number < 0.0 or number > 1.0:
            return {}
        checked_color.append(number)
    for key in ["energy", "range", "spot_angle"]:
        var value: Variant = raw.get(key, null)
        if typeof(value) not in [TYPE_INT, TYPE_FLOAT] or not is_finite(float(value)):
            return {}
    var energy := float(raw["energy"])
    var light_range := float(raw["range"])
    var spot_angle := float(raw["spot_angle"])
    if energy < 0.0 or energy > 16.0:
        return {}
    if light_range < 0.5 or light_range > 128.0:
        return {}
    if spot_angle < 5.0 or spot_angle > 80.0:
        return {}
    if typeof(raw.get("shadows", null)) != TYPE_BOOL:
        return {}
    if typeof(raw.get("enabled", null)) != TYPE_BOOL:
        return {}
    return {
        "kind": kind,
        "color": checked_color,
        "energy": energy,
        "range": light_range,
        "spot_angle": spot_angle,
        "shadows": raw["shadows"],
        "enabled": raw["enabled"]
    }


static func create_preview_node(kind: String) -> MeshInstance3D:
    var spec := default_spec(kind)
    if spec.is_empty():
        return null
    var marker := MeshInstance3D.new()
    var sphere := SphereMesh.new()
    sphere.radius = 0.14
    sphere.height = 0.28
    sphere.radial_segments = 16
    sphere.rings = 8
    marker.mesh = sphere
    marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    marker.layers = 1
    marker.set_meta("editor_only", true)
    marker.set_meta("dx2ed_draft_light", true)
    var light: Light3D = null
    if kind == "Point":
        light = OmniLight3D.new()
    else:
        light = SpotLight3D.new()
    light.name = NODE_NAME
    light.cull_mask = 1
    light.set_meta("editor_only", true)
    marker.add_child(light)
    if not apply_to_node(marker, spec):
        marker.free()
        return null
    return marker


static func apply_to_node(marker: MeshInstance3D, raw: Variant) -> bool:
    if not is_instance_valid(marker):
        return false
    var spec := validate(raw)
    if spec.is_empty():
        return false
    var light := marker.get_node_or_null(NODE_NAME) as Light3D
    if not is_instance_valid(light):
        return false
    var color_values: Array = spec["color"]
    var color := Color(
        float(color_values[0]), float(color_values[1]),
        float(color_values[2]), float(color_values[3]))
    light.light_color = color
    light.light_energy = float(spec["energy"])
    light.shadow_enabled = bool(spec["shadows"])
    light.visible = bool(spec["enabled"])
    if spec["kind"] == "Point":
        var point := light as OmniLight3D
        if point == null:
            return false
        point.omni_range = float(spec["range"])
        point.omni_attenuation = 1.0
    else:
        var spot := light as SpotLight3D
        if spot == null:
            return false
        spot.spot_range = float(spec["range"])
        spot.spot_angle = float(spec["spot_angle"])
        spot.spot_angle_attenuation = 1.0
    var material := marker.material_override as StandardMaterial3D
    if material == null:
        material = StandardMaterial3D.new()
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.albedo_color = color
    material.emission_enabled = true
    material.emission = color
    marker.material_override = material
    return true
