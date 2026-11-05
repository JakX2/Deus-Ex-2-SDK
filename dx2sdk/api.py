"""DX2SDK v0.1: public source-backed Python API for Invisible War.

This is a *real library surface* over the project's independently tested
Ion Storm v95 readers, native isolated StaticMeshActor Location-copy writer
and original TriggerScript/IBD readers. It is not a full game compiler,
BSP/Havok writer, native script editor or in-game validity guarantee.

No retail data bundled. Original GMP files are read-only. All editable
outputs are fresh isolated copies and require explicit write=True.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Mapping, Sequence


_ROOT = Path(__file__).resolve().parents[1]
for _folder in (
    _ROOT / "map_exporter",
    _ROOT / "actor_explorer",
    _ROOT / "native_editor" / "godot_editor" / "backend",
    _ROOT / "native_editor" / "package_writer",
    _ROOT / "third_party" / "t3sdk_assets",
):
    if not _folder.is_dir():
        raise ImportError("DX2SDK must be run from its complete DX2Ed source distribution")
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

from dx2inspect import Package  # noqa: E402
from dx2scene import decode_full_actor  # noqa: E402
from dx2_native_save_as import location_float_offsets  # noqa: E402
from dx2level import SCALE, actor_matrix  # noqa: E402
from dx2_gameplay_catalog import audit_actor_cache, build_catalog, hash_path  # noqa: E402
from dx2_script_ibd_provenance import build_evidence  # noqa: E402
from dx2_mission_kernel_script_diff import build_comparison  # noqa: E402
from dx2_native_save_as import (  # noqa: E402
    export_translation_copy, verify_translation_copy,
    audit_native_locations,
)
from dx2_package_roundtrip import inspect_noop  # noqa: E402

__version__ = "0.1.0"
SDK_SCHEMA = "DX2SDK-public-api-v0.1"
MAX_GMP = 256 * 1024 * 1024
MAX_MOVES = 10000


def _source_path(path: str | Path, suffix: str) -> Path:
    file = Path(path).expanduser().resolve(strict=True)
    if (not file.is_file() or file.suffix.casefold() != suffix
            or not 0 < file.stat().st_size <= MAX_GMP):
        raise ValueError("Unsupported source file type or size")
    return file


def _safe_output(original: Path, output: str | Path) -> Path:
    dest = Path(output).expanduser().resolve()
    if (dest.name.casefold() != original.name.casefold()
            or dest.suffix.casefold() != ".gmp"
            or dest.exists()
            or dest == original
            or dest.parent == original.parent
            or original.parent in dest.parents):
        raise ValueError("Save As requires a fresh copy with the original GMP filename outside source Maps")
    parts = tuple(p.casefold() for p in dest.parent.parts)
    if any(parts[i:i+3] == ("content", "dx2", "maps")
           for i in range(max(0, len(parts) - 2))):
        raise ValueError("Never write SDK outputs directly into a game Content/DX2/Maps folder")
    return dest


def _finite_xyz(values: Sequence[float]) -> tuple[float, float, float]:
    if (not isinstance(values, (list, tuple)) or len(values) != 3
            or any(type(n) not in (float, int) for n in values)):
        raise ValueError("Native location must contain exactly three numeric X,Y,Z coordinates")
    xyz = tuple(float(x) for x in values)
    if any(not math.isfinite(n) or abs(n) > 1_000_000 for n in xyz):
        raise ValueError("Native actor location exceeds supported finite limits")
    return xyz


class DX2Map:
    """Open an original GMP, optionally with a matching private actors.json.

    Original reader functions work with *no* cache. Native property 92 and
    compiled-script provenance require a matching DX2Ed actors.json cache.
    Native editing is limited to existing StaticMeshActor Locations.
    """

    def __init__(self, source: str | Path, actors_file: str | Path | None = None):
        self.source = _source_path(source, ".gmp")
        self._package = Package(self.source)
        if (self._package.version != 95 or
                self._package.licensee not in (68, 69)):
            raise ValueError("DX2SDK supports DX2 Ion Storm GMP v95 licensee 68/69 only")
        self.source_sha256 = hashlib.sha256(self._package.data).hexdigest()
        self.actors_file: Path | None = None
        self._actor_cache_sha256: str | None = None
        self._cache: dict | None = None
        if actors_file is not None:
            cache = Path(actors_file).expanduser().resolve(strict=True)
            if cache.stat().st_size > 64 * 1024 * 1024:
                raise ValueError("Source actor cache exceeds supported size")
            audit_actor_cache(self.source, cache)
            document = json.loads(cache.read_text("utf8"))
            # Every cache actor used by a writer must have a matching
            # original export ID, name and native class, never only a SHA.
            for row in document["actors"]:
                idx = row.get("export")
                if (type(idx) is not int or idx < 1 or
                        idx > len(self._package.exports)):
                    raise ValueError("Original actor cache has an invalid export ID")
                native = self._package.exports[idx - 1]
                if (row.get("name") != native["name"] or
                        row.get("class") != self._package.class_name(native)):
                    raise ValueError("Original actor cache identity disagrees with GMP")
            self.actors_file = cache
            self._actor_cache_sha256 = hash_path(cache)
            self._cache = document

    @classmethod
    def open(cls, source: str | Path,
             actors_file: str | Path | None = None) -> "DX2Map":
        return cls(source, actors_file)

    def _check_original_unchanged(self) -> None:
        if hash_path(self.source) != self.source_sha256:
            raise ValueError("Original GMP changed since the DX2SDK map session opened")
        if self.actors_file is not None:
            if hash_path(self.actors_file) != self._actor_cache_sha256:
                raise ValueError("Original actor cache changed since opening SDK map session")
            audit_actor_cache(self.source, self.actors_file)

    def info(self) -> dict:
        """Original package identity and reader capability flags, no game bytes."""
        self._check_original_unchanged()
        pkg = self._package
        return {
            "schema": SDK_SCHEMA,
            "sdk_version": __version__,
            "map": self.source.name,
            "source_sha256": self.source_sha256,
            "package_version": pkg.version,
            "licensee_version": pkg.licensee,
            "names": len(pkg.names),
            "imports": len(pkg.imports),
            "exports": len(pkg.exports),
            "source_actor_cache_verified": self._cache is not None,
            "original_game_assets_modified": False,
            "gameplay_runtime_verified": False,
            "native_supported_writer": "existing_StaticMeshActor_Location_only",
            "script_writer_available": False,
            "dialogue_compiler_available": False,
            "bsp_or_collision_rebuild_available": False,
        }

    def actors(self, *, actor_class: str | None = None,
               limit: int = 5000) -> dict:
        """Read native positioned actors; optional exact class filter."""
        self._check_original_unchanged()
        if type(limit) is not int or not 0 <= limit <= 30000:
            raise ValueError("Actor listing limit must be 0..30000")
        native, failed = self._package.scene_actors()
        rows = []
        cache = {r["export"]: r for r in self._cache["actors"]} if self._cache else {}
        for item in native:
            if actor_class is not None and item["class"] != actor_class:
                continue
            row = {
                "export": item["export"], "name": item["name"],
                "class": item["class"],
                "location_native_xyz": [item["x"], item["y"], item["z"]],
                "runtime_actor_script_link_verified": False,
            }
            original = cache.get(item["export"])
            if original:
                row["mesh"] = original.get("mesh")
                row["has_serialized_trigger_script_field"] = (
                    original.get("trigger_script_serialized") is not None)
            rows.append(row)
        rows.sort(key=lambda r: r["export"])
        return {
            "schema": SDK_SCHEMA,
            "map": self.source.name,
            "count": len(rows),
            "read_decode_failures": failed,
            "shown": rows[:limit],
            "read_only": True,
        }

    def inspect_actor(
        self, *, export: int | None = None, name: str | None = None,
    ) -> dict:
        """Inspect original authored tagged/GameSys properties for one actor.

        Property values are decoded directly from the unchanged native GMP.
        Unsupported blocks are marked opaque, never guessed or interpreted as
        editable scalar fields. Runtime script binding is not established.
        """
        self._check_original_unchanged()
        if (export is None) == (name is None):
            raise ValueError("Specify exactly one original actor export or name")
        native, _ = self._package.scene_actors()
        if export is not None:
            if type(export) is not int or export < 1:
                raise ValueError("Actor export ID must be a positive integer")
            candidates = [r for r in native if r["export"] == export]
        else:
            if type(name) is not str or not name:
                raise ValueError("Actor name must be a nonempty source string")
            candidates = [r for r in native if r["name"] == name]
        if len(candidates) != 1:
            raise ValueError("Actor name/export was not uniquely found in original GMP")
        selected = candidates[0]
        exp = self._package.exports[selected["export"] - 1]
        if (exp["name"] != selected["name"] or
                self._package.class_name(exp) != selected["class"]):
            raise ValueError("Original actor native export identity changed")
        tagged, raw_gamesys = decode_full_actor(self._package, exp, {})
        gamesys = []
        for block in raw_gamesys:
            val = block["value"]
            opaque = isinstance(val, dict) and "raw_hex" in val
            gamesys.append({
                "id": block["id"],
                "name": block["name"],
                "encoding": block["encoding"],
                "version": block["version"],
                "runtime_flag": block["runtime"],
                "decoded": not opaque,
                "value": (
                    {"opaque_byte_length": val.get("byte_length"),
                     "decoded": False}
                    if opaque else val
                ),
                "native_editable": False,
            })
        location_layout = False
        if selected["class"] == "StaticMeshActor":
            try:
                location_float_offsets(self._package, exp)
                location_layout = True
            except (ValueError, IndexError):
                pass
        return {
            "schema": SDK_SCHEMA,
            "source_map": self.source.name,
            "source_map_sha256": self.source_sha256,
            "actor_name": selected["name"],
            "actor_class": selected["class"],
            "actor_export": selected["export"],
            "original_location_native_xyz": [
                selected["x"], selected["y"], selected["z"]],
            "tagged_properties": tagged,
            "gamesys_blocks": gamesys,
            "native_location_field_layout_detected": location_layout,
            "original_values_read_only": True,
            "actor_runtime_script_binding_verified": False,
            "native_property_writer_enabled": False,
            "script_compiler_enabled": False,
        }

    def build_actor_catalog(self, *, system: str | Path | None = None) -> dict:
        """Scan original GMP in memory, without Godot or a private actor cache."""
        from .catalog import scan_original_actor_catalog
        return scan_original_actor_catalog(self, system=system)

    def export_actor_catalog(
        self, output: str | Path, *, system: str | Path | None = None,
    ) -> dict:
        """Write a new source-verified private actors.json outside game paths."""
        from .catalog import write_original_actor_catalog
        return write_original_actor_catalog(self, output, system=system)

    def script_definitions(self, original_trigger_script_zip: str | Path) -> dict:
        """Read the original source ZIP; original matching actors cache required."""
        if self.actors_file is None:
            raise ValueError("Original source-matched DX2Ed actors.json is required for script analysis")
        self._check_original_unchanged()
        doc = build_catalog(self.source, self.actors_file,
                            Path(original_trigger_script_zip))
        return {
            "schema": SDK_SCHEMA,
            "source_map": self.source.name,
            "script_definitions": doc["script_definitions"],
            "counts": doc["counts"],
            "original_game_assets_modified": False,
            "runtime_actor_script_link_verified": False,
        }

    def script_resources(self, original_trigger_script_zip: str | Path,
                         original_ibd: str | Path) -> dict:
        """Read-only, source-bound original TSD vs IBD resource evidence."""
        if self.actors_file is None:
            raise ValueError("Original source-matched actors.json required for IBD resource analysis")
        self._check_original_unchanged()
        doc = build_evidence(
            self.source, self.actors_file,
            Path(original_trigger_script_zip), Path(original_ibd))
        return doc

    def compare_script_bundles(
        self, original_trigger_script_zip: str | Path,
        mission_ibd: str | Path, kernel_ibd: str | Path,
    ) -> dict:
        """Compare owner-original mission and Kernel TSD resource payloads."""
        if self.actors_file is None:
            raise ValueError("Original source-matched actors.json required for IBD comparison")
        self._check_original_unchanged()
        return build_comparison(
            self.source, self.actors_file,
            Path(original_trigger_script_zip),
            Path(mission_ibd), Path(kernel_ibd))

    def native_location_audit(self) -> dict:
        """Inventory existing source StaticMeshActor Location writer coverage."""
        if self.actors_file is None:
            raise ValueError("Source-matched actor cache required for native writer")
        self._check_original_unchanged()
        return audit_native_locations(self.source, self.actors_file)

    def native_noop_audit(self) -> dict:
        """Check the MIT T3SDK writer can reconstruct an identical GMP."""
        self._check_original_unchanged()
        report, unchanged = inspect_noop(self.source)
        if unchanged != self._package.data:
            raise ValueError("Native package no-op bytes were not identical")
        return report

    def save_as_translations(
        self, positions: Mapping[str, Sequence[float]],
        output: str | Path, *, write: bool = False,
    ) -> dict:
        """Translate existing StaticMeshActors in **native** game X,Y,Z.

        Dry-run by default. With write=True, create a *new* GMP in a
        non-game isolated folder and run a second byte-level independent
        verification. No existing file may be overwritten. No collision,
        BSP, light baking, mesh import or runtime script changes.
        """
        if self.actors_file is None or self._cache is None:
            raise ValueError("Source-matched actors.json required for native Save As")
        self._check_original_unchanged()
        dest = _safe_output(self.source, output)
        if (not isinstance(positions, Mapping)
                or not 1 <= len(positions) <= MAX_MOVES):
            raise ValueError("At least one and at most 10000 source actor moves required")
        originals = {row["name"]: row for row in self._cache["actors"]}
        moves = []
        for name, coords in positions.items():
            if type(name) is not str or name not in originals:
                raise ValueError("Cannot translate unknown original actor")
            actor = originals[name]
            if actor.get("class") != "StaticMeshActor" or not actor.get("mesh"):
                raise ValueError("Native Location writer supports only existing rendered StaticMeshActors")
            x, y, z = _finite_xyz(coords)
            ox, oy, oz = _finite_xyz(actor["location"])
            if (abs(x-ox) < 1e-5 and abs(y-oy) < 1e-5 and
                    abs(z-oz) < 1e-5):
                raise ValueError("Native move is identical to source location")
            original_matrix = actor_matrix({
                "x": ox, "y": oy, "z": oz,
                "rotation": actor.get("rotation", [0, 0, 0]),
            })
            # DX2 native coordinates -> original DX2Ed/Godot basis and
            # source-specific Y/Z placement mapping. Never edit the basis.
            matrix = original_matrix
            godot_transform = [
                matrix[0], matrix[1], matrix[2],
                matrix[4], matrix[5], matrix[6],
                matrix[8], matrix[9], matrix[10],
                x * SCALE, z * SCALE, y * SCALE,
            ]
            moves.append({"actor": name, "transform": godot_transform})
        draft = {
            "schema": "DX2Ed-prop-draft-v1",
            "read_only_source": True,
            "map_cache": str(self.actors_file.parent),
            "moved": moves,
            "copies": [], "property_edits": [],
        }
        # A private temporary original-cache-bound draft is consumed by the
        # existing audited binary writer. It is never saved to game folders.
        with TemporaryDirectory(prefix="dx2sdk_private_draft_") as tmp:
            path = Path(tmp) / "native_move_draft.json"
            path.write_text(json.dumps(draft, allow_nan=False), encoding="utf8")
            result = export_translation_copy(
                self.source, self.actors_file, path, dest,
                dry_run=not write)
        if write:
            try:
                verification = verify_translation_copy(self.source, dest)
            except Exception:
                # The underlying exporter already completed and wrote a
                # manifest. Preserve the output as an unverified artifact
                # for inspection rather than falsely claiming success.
                raise RuntimeError(
                    "GMP copy was written but independent binary verification failed; "
                    "treat the isolated output as unsafe and do not install it"
                ) from None
            result["independent_binary_verification"] = {
                "verified_binary_structure":
                    verification["verified_binary_structure"],
                "changed_bytes": verification["changed_bytes"],
                "game_verified": False,
            }
        result["sdk_schema"] = SDK_SCHEMA
        return result

    def verify_saved_translation(self, output: str | Path) -> dict:
        """Independently re-open and byte-audit an existing isolated map copy."""
        self._check_original_unchanged()
        dest = Path(output).expanduser().resolve(strict=True)
        if dest.name.casefold() != self.source.name.casefold():
            raise ValueError("Verified edited GMP must retain original map filename")
        return verify_translation_copy(self.source, dest)
