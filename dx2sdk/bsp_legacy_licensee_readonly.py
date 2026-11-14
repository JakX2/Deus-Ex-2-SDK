"""Strict read-only World BSP research adapter for UE95 licensees 65/67.

The public DX2Map editor/writer API intentionally stays 68/69-only.
This isolated adapter uses the previously source-validated UE95 research
Level -> Model reader and the exact P105 Model byte-ledger / BSP node gates.
It is NEVER a native actor, BSP, GMP or collision editing capability.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from dx2inspect import Package
from inspect_level_world_model import _parse_world_model
from .bsp_node_dossier import inspect_model_node_bytes

SCHEMA = "DX2SDK-original-BSP-source-node-dossier-v1"
MAX_SOURCE_BYTES = 128 * 1024 * 1024
LEGACY_OBSERVED_LICENSEES = frozenset((65, 67))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_legacy_original_bsp_node(
    original_gmp: str | Path, pinned_sha256: str, node_index: int,
) -> dict:
    """Original licensee-65/67 node dossier; JSON metadata ONLY, no writes."""
    if (type(pinned_sha256) is not str
        or re.fullmatch(r"[0-9a-fA-F]{64}", pinned_sha256) is None
        or type(node_index) is not int
        or not 0 <= node_index < 20_000):
        raise ValueError("Original GMP SHA-256 or source BSP ordinal invalid")
    source = Path(original_gmp).expanduser().resolve(strict=True)
    if source.suffix.lower() != ".gmp" or not source.is_file():
        raise ValueError("Legacy original BSP source must be regular .gmp")
    size = source.stat().st_size
    if not 100 <= size <= MAX_SOURCE_BYTES:
        raise ValueError("Legacy original BSP GMP exceeds bounded source size")
    expected = pinned_sha256.lower()
    if _file_sha256(source) != expected:
        raise ValueError("Original legacy GMP SHA-256 changed before parsing")
    pkg = Package(source)
    if pkg.version != 95 or pkg.licensee not in LEGACY_OBSERVED_LICENSEES:
        raise ValueError("Read-only research adapter accepts UE95 licensee 65/67 only")
    if hashlib.sha256(pkg.data).hexdigest() != expected:
        raise ValueError("In-memory original legacy GMP source SHA-256 mismatch")
    direct = _parse_world_model(pkg)
    if (direct["world_model_initial_9_zero_bytes"] is not True
        or direct["world_model_zero_bounds_and_sphere"] is not True
        or direct["world_model_first_plane_normal_unit"] is not True
        or direct["direct_model_ref_not_in_actor_list"] is not True):
        raise ValueError("Original legacy GMP Level/Model structural preflight failed")
    ref = direct["world_model_export_ref"]
    if type(ref) is not int or not 1 <= ref <= len(pkg.exports):
        raise ValueError("Original legacy GMP World Model reference invalid")
    export = pkg.exports[ref-1]
    if pkg.class_name(export) != "Model":
        raise ValueError("Original Level reference does not target a Model")
    offset, count = export["offset"], export["size"]
    if (type(offset) is not int or type(count) is not int
        or offset < 0 or count < 100 or count > len(pkg.data)-offset):
        raise ValueError("Original legacy World Model export outside source GMP")
    payload = pkg.payload(export)
    if (payload != pkg.data[offset:offset+count]
        or len(payload) != direct["world_model_payload_bytes"]
        or hashlib.sha256(payload).hexdigest()
            != direct["world_model_payload_sha256"]):
        raise ValueError("Original legacy Level/World Model source bytes differ")
    node = inspect_model_node_bytes(payload, node_index)
    if (node["original_node_count"] != direct["world_model_compact_node_count_at_50"]
        or node["original_model_sha256"] != direct["world_model_payload_sha256"]
        or node["original_model_exact_noop_verified"] is not True
        or node["original_model_full_span_ledger_verified"] is not True
        or node["native_BSP_or_Havok_collision_writer_enabled"] is not False):
        raise ValueError("Legacy World Model node and direct Level evidence disagree")
    if _file_sha256(source) != expected:
        raise ValueError("Original legacy GMP SHA-256 changed during inspection")
    return {
        **node,
        "schema": SCHEMA,
        "source_map": source.name,
        "source_gmp_sha256": expected,
        "world_model_export": ref,
        "source_gmp_model_absolute_offset": offset,
        "source_gmp_node_absolute_offset": offset + node["native_model_node_offset"],
        "original_source_gmp_modified": False,
        "source_original_licensee": pkg.licensee,
        "read_only_legacy_research_adapter": True,
        "general_DX2Map_writer_licensee_allowlist_extended": False,
        "native_BSP_or_Havok_collision_writer_enabled": False,
        "limitations": [
            "UE95 licensee 65/67 inspected via independent read-only research grammar only.",
            "Public DX2Map and native GMP writers are still limited to their existing licensee allowlists.",
            "Compact node field2 remains a surface ID hypothesis, not native iSurf.",
            "No original polygon vertex XYZ or material/UV bindings, BSP/CSG cooking, MOPP or gameplay writes.",
        ],
    }
