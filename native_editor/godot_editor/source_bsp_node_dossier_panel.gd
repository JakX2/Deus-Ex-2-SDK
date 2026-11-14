extends VBoxContainer
## P105: source-original World BSP node dossier, NEVER editable BSP geometry.
## The original native Model parser and full byte-span ledger are source SHA
## checked by Python; this panel only displays validated numeric evidence.
const PythonRuntime = preload("res://python_runtime.gd")
const WORKER := "res://backend/dx2_bsp_node_dossier_worker.py"
const SCHEMA := "DX2SDK-original-BSP-source-node-dossier-v1"
const MAX_OUTPUT := 128 * 1024

var original_gmp := ""
var original_sha256 := ""
var node_spin: SpinBox
var inspect_button: Button
var details: Label
var last_report: Dictionary = {}
var last_error := ""


func initialize() -> void:
    visible = false
    var title_label := Label.new()
    title_label.text = "ORIGINAL WORLD BSP | SOURCE BYTES ONLY"
    title_label.add_theme_color_override("font_color", Color(0.94, 0.7, 0.44))
    add_child(title_label)
    var warning := Label.new()
    warning.text = (
        "Read-only native Model plane and byte offsets. "
        + "Compact field 2 is NOT proven iSurf; no vertex pool, "
        + "UV/material decoding, BSP rebuild or collision write.")
    warning.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    add_child(warning)
    var row := HBoxContainer.new()
    add_child(row)
    var label := Label.new()
    label.text = "Original node #"
    row.add_child(label)
    node_spin = SpinBox.new()
    node_spin.min_value = 0
    node_spin.max_value = 19999
    node_spin.step = 1
    node_spin.rounded = true
    node_spin.custom_minimum_size.x = 104
    row.add_child(node_spin)
    inspect_button = Button.new()
    inspect_button.text = "Inspect BSP node"
    inspect_button.tooltip_text = (
        "Reopen the original GMP SHA-locked in Python, independently "
        + "validate complete World Model framing/tree/zone masks/no-op, "
        + "and report one source node. Never writes a GMP.")
    inspect_button.pressed.connect(_inspect_clicked)
    row.add_child(inspect_button)
    details = Label.new()
    details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    details.text = "Select an original node ordinal. Structural evidence only."
    add_child(details)


func reset_context() -> void:
    original_gmp = ""
    original_sha256 = ""
    last_report.clear()
    last_error = ""
    if node_spin != null:
        node_spin.max_value = 19999
        node_spin.set_value_no_signal(0)
    if inspect_button != null:
        inspect_button.disabled = true
    if details != null:
        details.text = "No verified original GMP source selected."
    visible = false


static func _is_sha256(sha: String) -> bool:
    if sha.length() != 64:
        return false
    for index in range(sha.length()):
        if not "0123456789abcdef".contains(sha[index].to_lower()):
            return false
    return true


func configure_original(path: String, sha: String) -> bool:
    reset_context()
    var expected := sha.to_lower()
    if (path.is_empty() or not path.is_absolute_path()
        or path.get_extension().to_lower() != "gmp"
        or not FileAccess.file_exists(path) or not _is_sha256(expected)
        or FileAccess.get_sha256(path) != expected):
        return false
    original_gmp = path
    original_sha256 = expected
    inspect_button.disabled = false
    details.text = (
        "Ready: " + path.get_file()
        + ". Source SHA-256 pinned; choose node #0 to start.")
    visible = true
    return true


func _reject(message: String) -> bool:
    last_report.clear()
    last_error = message
    if details != null:
        details.text = "BSP original-source inspector REFUSED: " + message
    return false


func accept_verified_report(raw: Variant) -> bool:
    if (typeof(raw) != TYPE_DICTIONARY
        or original_sha256.is_empty()
        or str(raw.get("schema", "")) != SCHEMA
        or raw.get("status", null) !=
            "source-original-read-only-node-structure"
        or raw.get("source_gmp_sha256", null) != original_sha256
        or raw.get("source_map", null) != original_gmp.get_file()
        or raw.get("original_source_gmp_modified", null) != false
        or raw.get("native_BSP_or_Havok_collision_writer_enabled", null) != false
        or raw.get("native_surface_material_uv_binding_verified", null) != false
        or raw.get("compact_field2_native_surface_id_authenticated", null) != false
        or raw.get("native_vertex_xyz_pool_recovered", null) != false
        or raw.get("retail_runtime_verified", null) != false
        or raw.get("original_model_exact_noop_verified", null) != true
        or raw.get("original_model_full_span_ledger_verified", null) != true
        or not _is_sha256(str(raw.get("original_model_sha256", "")))):
        return _reject("Unsupported source, schema, native capability or model proof.")
    var legacy: Variant = raw.get("read_only_legacy_research_adapter", false)
    if legacy == true:
        var licensee: Variant = raw.get("source_original_licensee", -1)
        if (typeof(licensee) not in [TYPE_INT, TYPE_FLOAT]
            or float(licensee) != float(int(licensee))
            or int(licensee) not in [65, 67]
            or raw.get("general_DX2Map_writer_licensee_allowlist_extended", true) != false):
            return _reject("Unverified legacy source licensee or claimed GMP writer permission.")
    elif legacy != false:
        return _reject("Original BSP source reader capability invalid.")
    var count: Variant = raw.get("original_node_count", -1)
    var ordinal: Variant = raw.get("original_node_ordinal", -1)
    var length: Variant = raw.get("native_model_node_record_bytes", -1)
    var model_pos: Variant = raw.get("native_model_node_offset", -1)
    var gmp_pos: Variant = raw.get("source_gmp_node_absolute_offset", -1)
    var model_base: Variant = raw.get("source_gmp_model_absolute_offset", -1)
    if (typeof(count) not in [TYPE_INT, TYPE_FLOAT]
        or typeof(ordinal) not in [TYPE_INT, TYPE_FLOAT]
        or typeof(length) not in [TYPE_INT, TYPE_FLOAT]
        or typeof(model_pos) not in [TYPE_INT, TYPE_FLOAT]
        or typeof(gmp_pos) not in [TYPE_INT, TYPE_FLOAT]
        or typeof(model_base) not in [TYPE_INT, TYPE_FLOAT]
        or int(count) < 1 or int(count) > 20000
        or int(ordinal) < 0 or int(ordinal) >= int(count)
        or int(length) < 109 or int(length) > 116
        or int(model_pos) < 50 or int(model_base) < 0
        or int(gmp_pos) != int(model_base) + int(model_pos)
        or float(count) != float(int(count))
        or float(ordinal) != float(int(ordinal))
        or float(length) != float(int(length))
        or float(model_pos) != float(int(model_pos))
        or float(gmp_pos) != float(int(gmp_pos))
        or float(model_base) != float(int(model_base))):
        return _reject("Original node ordinal or byte boundary invalid.")
    var plane: Variant = raw.get("candidate_plane_source_f32", [])
    var fields: Variant = raw.get("raw_compact_fields", [])
    var positions: Variant = raw.get("raw_compact_offsets_in_model", [])
    var widths: Variant = raw.get("raw_compact_byte_widths", [])
    var zones: Variant = raw.get("source_candidate_zone_u16", [])
    var spans: Variant = raw.get("node_source_spans", [])
    if (typeof(plane) != TYPE_ARRAY or plane.size() != 4
        or typeof(fields) != TYPE_ARRAY or fields.size() != 8
        or typeof(positions) != TYPE_ARRAY or positions.size() != 8
        or typeof(widths) != TYPE_ARRAY or widths.size() != 8
        or typeof(zones) != TYPE_ARRAY or zones.size() != 2
        or typeof(spans) != TYPE_ARRAY or spans.size() != 19):
        return _reject("Original BSP node fields or source-span counts invalid.")
    var normal_sq := 0.0
    for i in range(4):
        if (typeof(plane[i]) not in [TYPE_FLOAT, TYPE_INT]
            or not is_finite(float(plane[i]))):
            return _reject("Original BSP plane contains nonfinite values.")
        if i < 3:
            normal_sq += float(plane[i]) * float(plane[i])
    if abs(normal_sq - 1.) > 0.002:
        return _reject("Original BSP plane normal is not source-normalized.")
    for i in range(8):
        if (typeof(fields[i]) not in [TYPE_INT, TYPE_FLOAT]
            or typeof(positions[i]) not in [TYPE_INT, TYPE_FLOAT]
            or typeof(widths[i]) not in [TYPE_INT, TYPE_FLOAT]
            or float(fields[i]) != float(int(fields[i]))
            or float(positions[i]) != float(int(positions[i]))
            or float(widths[i]) != float(int(widths[i]))
            or int(widths[i]) < 1 or int(widths[i]) > 5
            or int(positions[i]) < int(model_pos) + 48):
            return _reject("Original compact field position or value invalid.")
        if i > 0 and int(positions[i]) != (
            int(positions[i-1]) + int(widths[i-1])):
            return _reject("Original compact field positions are not contiguous.")
    var expected := int(model_pos)
    var expected_roles := [
        "node.candidate_plane_f32_bits", "node.subtree_zone_mask_bits",
        "node.compact_field_0", "node.compact_field_1",
        "node.compact_field_2", "node.compact_field_3",
        "node.compact_field_4", "node.compact_field_5",
        "node.compact_field_6", "node.compact_field_7",
        "node.opaque_spatial_f32_bits", "node.opaque_spatial_reserved",
        "node.zone_candidate_a_u16", "node.zone_candidate_b_u16",
        "node.vertex_slot_count_u8", "node.opaque_bounded_i32_0",
        "node.opaque_bounded_i32_1", "node.observed_zero_u32",
        "node.opaque_last_u32",
    ]
    for i in range(spans.size()):
        var span: Variant = spans[i]
        if (typeof(span) != TYPE_DICTIONARY
            or span.get("role", null) != expected_roles[i]
            or span.get("native_writer_permission", null) != false
            or not _is_sha256(str(span.get("source_span_sha256", "")))
            or int(span.get("original_model_relative_offset", -1)) != expected
            or int(span.get("byte_count", -1)) < 1):
            return _reject("Native BSP original-byte span integrity invalid.")
        expected += int(span["byte_count"])
    if expected != int(model_pos) + int(length):
        return _reject("Original node field spans do not cover source record.")
    last_report = (raw as Dictionary).duplicate(true)
    last_error = ""
    node_spin.max_value = max(0, int(count) - 1)
    node_spin.set_value_no_signal(int(ordinal))
    var parts := [
        "SOURCE ORIGINAL, READ ONLY: " + original_gmp.get_file(),
        ("Original UE95 licensee " + str(raw["source_original_licensee"])
         + " | RESEARCH READ ONLY, general GMP writer unchanged"
         if legacy == true else
         "Original v95 licensee 68/69 | source-verified read only"),
        "World Model export #" + str(raw.get("world_model_export", "?"))
        + " | Node #" + str(int(ordinal)) + " / " + str(int(count)),
        "Record: " + str(int(length)) + " bytes at Model +"
        + str(int(model_pos)) + " | GMP absolute +" + str(int(gmp_pos)),
        "Original plane (float32): " + str(plane),
        "Eight compact integer values (raw; names not proven): " + str(fields),
        "Compact field 2 = " + str(fields[2])
        + " (surface ID candidate ONLY, not authenticated)",
        "Candidate node zones u16: " + str(zones)
        + " | polygon vertex slots: "
        + str(raw.get("source_polygon_vertex_slot_count_u8", "?")),
        "Full node byte spans, Model no-op and tree evidence: VERIFIED",
        "Native vertex XYZ, UV/material and BSP/collision writer: UNAVAILABLE",
    ]
    details.text = "\n".join(parts)
    return true


func _inspect_clicked() -> void:
    if (original_gmp.is_empty() or not FileAccess.file_exists(original_gmp)
        or FileAccess.get_sha256(original_gmp) != original_sha256):
        _reject("Original source GMP changed, vanished or was never pinned.")
        return
    var worker := ProjectSettings.globalize_path(WORKER)
    if not FileAccess.file_exists(worker):
        _reject("Bundled BSP dossier worker missing.")
        return
    var args := PackedStringArray([
        worker, "--gmp", original_gmp,
        "--source-sha256", original_sha256,
        "--node", str(int(node_spin.value)),
    ])
    var output: Array = []
    var code := OS.execute(PythonRuntime.executable(), args, output, true)
    if code == -1:
        output.clear()
        var fallback := PackedStringArray(["-3"])
        fallback.append_array(args)
        code = OS.execute("py", fallback, output, true)
    var combined := "\n".join(output).strip_edges()
    if code != 0 or combined.is_empty() or combined.length() > MAX_OUTPUT:
        _reject("Source-only BSP worker refused: " + combined.substr(0, 250))
        return
    var parsed: Variant = JSON.parse_string(combined)
    if not accept_verified_report(parsed):
        return
