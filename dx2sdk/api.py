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
    _ROOT / "research" / "dx2",
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

__version__ = "0.27.0"
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
            "experimental_native_tagged_scalar_writer": "existing_StaticMeshActor_top_level_int32_float32_only",
            "source_native_scalar_Godot_gui": "one_existing_tagged_int32_or_float32_field_per_isolated_copy",
            "source_multi_native_scalar_Godot_gui": "2_to_8_existing_authored_int32_or_float32_fields_across_source_actors",
            "original_actor_property_workbench": "read_only_authored_native_tag_catalog_with_explicit_edit_eligibility",
            "original_actor_property_search_filter_detail_gui": "read_only_source_native_tag_visibility_and_staged_comparison",
            "original_actor_workbench_navigation_gui": "source_actor_name_export_search_staged_filter_and_pinned_actor_switching",
            "original_viewport_actor_workbench_handoff_gui": "single_source_original_StaticMeshActor_SHA_bound_selection_only",
            "experimental_original_static_prop_clone": "source_neutral_unlinked_StaticMeshActor_only",
            "experimental_multi_prop_clone": "2_to_8_existing_neutral_unlinked_StaticMeshActor_only",
            "experimental_existing_gamesys_bLightOn_bool_writer": "source-authored_nonruntime_one_byte_only",
            "native_light_creation_enabled": False,
            "experimental_existing_LightColor_byte_writer": "preexisting_three_byte_tagged_struct_only",
            "source_LightColor_Godot_gui": "one_existing_actor_preview_and_confirmed_private_save_as",
            "source_multi_LightColor_Godot_gui": "2_to_8_original_actors_guarded_private_plan_and_save_as",
            "native_light_region_reconstruction_available": False,
            "source_bsp_plane_side_diagnostics": "read_only_hypothetical_branch_trace",
            "source_original_Light_BSP_anchor_atlas": "read_only_epsilon_concordance_and_conflicts",
            "source_original_cross_class_Actor_Region_atlas": "read_only_explicit_tagged_location_region_and_LevelInfo",
            "native_bsp_point_to_leaf_or_zone_verified": False,
            "experimental_source_multi_LightColor_plan": "2_to_8_original_authored_actors_only",
            "native_gamesys_writer_available": False,
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

    def audit_original_lights(self, *, export: int | None = None) -> dict:
        """Inspect source Light references, BSP region and native frame (no writes)."""
        from .lights import audit_original_lights
        return audit_original_lights(self, export=export)

    def export_original_lights(
        self, output: str | Path, *, export: int | None = None,
    ) -> dict:
        """Create a fresh private source-pinned Light evidence JSON."""
        from .lights import export_original_lights
        return export_original_lights(self, output, export=export)

    def original_actor_property_workbench(self, actor_name: str) -> dict:
        """Read-only, source-tag-bound original Actor property category report."""
        from .actor_workbench import original_actor_property_workbench
        return original_actor_property_workbench(self, actor_name)

    def original_light_switches(self, *, limit: int = 100) -> dict:
        """Read only eligible existing authored GameSys bLightOn values."""
        from .lights import original_light_switches
        return original_light_switches(self, limit=limit)

    def set_existing_light_switch(
        self, *, export: int, actor: str, expected: bool,
        output: str | Path, write: bool = False,
    ) -> dict:
        """Dry run by default; optionally isolate a verified one-byte bLightOn change."""
        from .lights import set_existing_light_switch
        return set_existing_light_switch(
            self, export=export, actor=actor,
            expected=expected, output=output, write=write)

    def verify_saved_light_switch(self, output: str | Path) -> dict:
        """Independently replay original authored bLightOn output across the whole GMP."""
        from .lights import verify_saved_light_switch
        return verify_saved_light_switch(self, output)

    def original_light_colors(self, *, limit: int = 100) -> dict:
        """Read exact existing authored LightColor 10-byte struct candidates."""
        from .light_colors import original_light_colors
        return original_light_colors(self, limit=limit)

    def set_existing_light_color(
        self, *, export: int, actor: str,
        expected: tuple[int, int, int], changes: dict[str, int],
        output: str | Path, write: bool = False,
    ) -> dict:
        """Source-locked 1..3 existing LightColor Byte fields, dry run by default."""
        from .light_colors import set_existing_light_color
        return set_existing_light_color(
            self, export=export, actor=actor, expected=expected,
            changes=changes, output=output, write=write)

    def verify_saved_light_color(self, output: str | Path) -> dict:
        """Independently replay 1..3 original nested LightColor Byte changes."""
        from .light_colors import verify_saved_light_color
        return verify_saved_light_color(self, output)

    def build_lightcolor_plan(self, edits: Sequence[dict]) -> dict:
        """Validate 2..8 original source-authored LightColor actor changes."""
        from .multi_light_colors import build_lightcolor_plan
        return build_lightcolor_plan(self, edits)

    def write_lightcolor_plan(
        self, edits: Sequence[dict], output: str | Path,
    ) -> dict:
        """Write a new private source-bound LightColor project plan JSON."""
        from .multi_light_colors import write_lightcolor_plan
        return write_lightcolor_plan(self, edits, output)

    def load_lightcolor_plan(self, plan: str | Path) -> list[dict]:
        """Revalidate every actor and source byte of an existing plan."""
        from .multi_light_colors import load_lightcolor_plan
        return load_lightcolor_plan(self, plan)

    def apply_lightcolor_plan(
        self, plan: str | Path, output: str | Path, *, write: bool = False,
    ) -> dict:
        """In-memory group dry-run, or explicit isolated native multi-color GMP."""
        from .multi_light_colors import apply_lightcolor_plan
        return apply_lightcolor_plan(self, plan, output, write=write)

    def verify_saved_multi_lightcolor(self, output: str | Path) -> dict:
        """Rebuild source original edits and compare entire multi-color GMP."""
        from .multi_light_colors import verify_saved_multi_lightcolor
        return verify_saved_multi_lightcolor(self, output)

    def trace_bsp_point(
        self, point_unreal_xyz: tuple[float, float, float], *,
        epsilon: float = .01,
    ) -> dict:
        """Trace candidate source BSP plane-side branches, NOT game leaves."""
        from .bsp_trace import trace_bsp_point
        return trace_bsp_point(self, point_unreal_xyz, epsilon=epsilon)

    def trace_original_light_regions(
        self, *, limit: int = 50, epsilon: float = .01,
    ) -> dict:
        """Compare original native Light Region provenance with BSP hypotheses."""
        from .bsp_trace import trace_original_light_regions
        return trace_original_light_regions(self, limit=limit, epsilon=epsilon)

    def save_bsp_diagnostic_report(
        self, report: dict, output: str | Path,
    ) -> dict:
        """Write only a NEW private JSON of read-only BSP diagnostics."""
        from .bsp_trace import save_bsp_diagnostic_report
        return save_bsp_diagnostic_report(self, report, output)

    def original_light_bsp_anchor_atlas(
        self, *, limit: int = 100,
        epsilons: tuple[float, ...] = (.001, .01, .1),
    ) -> dict:
        """Group source-original Light Region evidence by hypothetical BSP terminals."""
        from .bsp_anchors import original_light_bsp_anchor_atlas
        return original_light_bsp_anchor_atlas(self, limit=limit, epsilons=epsilons)

    def compare_point_with_original_light_anchors(
        self, point_unreal_xyz: tuple[float, float, float], *,
        limit: int = 100, epsilons: tuple[float, ...] = (.001, .01, .1),
    ) -> dict:
        """Read-only original Light evidence overlapping an unassigned BSP point."""
        from .bsp_anchors import compare_point_with_original_light_anchors
        return compare_point_with_original_light_anchors(
            self, point_unreal_xyz, limit=limit, epsilons=epsilons)

    def save_light_bsp_anchor_report(
        self, report: dict, output: str | Path,
    ) -> dict:
        """Reconstruct original Light/BSP evidence before fresh private JSON."""
        from .bsp_anchors import save_light_bsp_anchor_report
        return save_light_bsp_anchor_report(self, report, output)

    def original_actor_region_bsp_atlas(
        self, *, limit: int = 250, actor_class: str | None = None,
        epsilons: tuple[float, ...] = (.001, .01, .1),
    ) -> dict:
        """Source-authored Actor Region and candidate BSP terminal cross-class atlas."""
        from .actor_regions import original_actor_region_bsp_atlas
        return original_actor_region_bsp_atlas(
            self, limit=limit, actor_class=actor_class, epsilons=epsilons)

    def compare_point_to_original_actor_regions(
        self, point_unreal_xyz: tuple[float, float, float], *,
        limit: int = 250, actor_class: str | None = None,
        epsilons: tuple[float, ...] = (.001, .01, .1),
    ) -> dict:
        """Compare original Actor Region evidence without deriving a new Region."""
        from .actor_regions import compare_point_to_original_actor_regions
        return compare_point_to_original_actor_regions(
            self, point_unreal_xyz, limit=limit, actor_class=actor_class,
            epsilons=epsilons)

    def save_original_actor_region_atlas(
        self, report: dict, output: str | Path,
    ) -> dict:
        """Regenerate original Actor Region evidence before fresh private JSON output."""
        from .actor_regions import save_original_actor_region_atlas
        return save_original_actor_region_atlas(self, report, output)

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

    def inspect_bsp_plane_mopp_candidates(
        self, *, node: int, replacement: Sequence[float],
    ) -> dict:
        """Read-only original Model plane → render candidate → Level MOPP IDs.

        Exact flattened triangle/MOPP IDs are source-verified, but a BSP
        node's geometric triangle candidates are NOT native ownership links.
        No game file, collision tree, actor Region or BSP node is written.
        """
        from .bsp_mopp_plane_impact import compare_original_plane_mopp_impact
        return compare_original_plane_mopp_impact(
            self, node=node, replacement=replacement)

    def inspect_original_mopp_terminal_bytes(
        self, triangle_ids: Sequence[int],
    ) -> dict:
        """Read-only original Level MOPP opcode positions for selected triangle IDs.

        Original source geometry, code bytes, package and editor state are
        never patched. Reachable MOPP output IDs are not a Havok writer API.
        """
        from .mopp_leaf_bytes import inspect_original_mopp_terminal_bytes
        return inspect_original_mopp_terminal_bytes(self, triangle_ids)

    def inspect_bsp_plane_mopp_terminal_bytes(
        self, *, node: int, replacement: Sequence[float],
    ) -> dict:
        """Read-only candidate Model plane impact → original MOPP leaf opcodes.

        The candidate BSP node-to-triangle relationship is geometric
        inference, not source-authenticated native surface ownership.
        """
        from .mopp_leaf_bytes import inspect_original_plane_affected_terminal_bytes
        return inspect_original_plane_affected_terminal_bytes(
            self, node=node, replacement=replacement)

    def inspect_bsp_surface_provenance_hypotheses(self) -> dict:
        """Compare original world BSP compact field2 against Level/MOPP identity.

        Numeric equalities are hypotheses, not engine-authenticated surface
        pointers. This analysis never edits the original GMP or game assets.
        """
        from .bsp_surface_correlation import inspect_original_bsp_surface_correlation
        return inspect_original_bsp_surface_correlation(self)

    def inspect_bsp_surface_plane_coherence(self) -> dict:
        """Audit original BSP field2 repeated IDs versus native node planes.

        This is source-backed correlation only: raw field2 is not an
        engine-authenticated iSurf, and no native source bytes are written.
        """
        from .bsp_surface_plane_coherence import inspect_original_surface_plane_coherence
        return inspect_original_surface_plane_coherence(self)

    def inspect_original_world_model_noop(self) -> dict:
        """Reassemble original World BSP Model payload byte-identically in memory.

        Read-only structural serialization preflight. Native geometry,
        collision, zone or GMP modification is never enabled.
        """
        from .bsp_model_noop import inspect_original_world_model_noop
        return inspect_original_world_model_noop(self)

    def inspect_original_model_byte_spans(
        self, node_indices: Sequence[int] | None = None,
    ) -> dict:
        """Read-only full original World Model byte ledger and selected node spans.

        This is evidence about native source framing, not a BSP surface index,
        modified Model serializer or verified retail-game edit capability.
        """
        from .bsp_model_spans import inspect_original_model_span_ledger
        return inspect_original_model_span_ledger(self, node_indices)

    def static_prop_clone_candidates(self, limit: int = 200) -> dict:
        """Read-only, conservative original T3SDK clone eligibility list."""
        from .clones import source_clone_candidates
        return source_clone_candidates(self, limit=limit)

    def clone_existing_static_prop(
        self, *, original_export: int, original_actor: str,
        delta_native_xyz: Sequence[float], output: str | Path,
        write: bool = False,
    ) -> dict:
        """Experimental duplicate of one original static-mesh prop only.

        Dry-run by default; new native export + Level ref allowed ONLY for
        a state-idle unlinked source StaticMeshActor. Never modifies source,
        never creates arbitrary new class actors or tests game runtime.
        """
        from .clones import clone_static_prop
        return clone_static_prop(
            self, original_export=original_export,
            original_actor=original_actor,
            delta_native_xyz=delta_native_xyz,
            output=output, write=write)

    def verify_saved_clone(self, output: str | Path) -> dict:
        """Rebuild original prop clone from source and compare every byte."""
        from .clones import verify_saved_clone
        return verify_saved_clone(self, output)

    def build_multi_clone_plan(self, copies: Sequence[dict]) -> dict:
        """Read-only source-locked 2..8 existing original prop duplicate plan."""
        from .multi_clones import build_multi_clone_plan
        return build_multi_clone_plan(self, copies)

    def write_multi_clone_plan(
        self, copies: Sequence[dict], output: str | Path,
    ) -> dict:
        """Save new private source-hash-locked JSON, not a game file."""
        from .multi_clones import write_multi_clone_plan
        return write_multi_clone_plan(self, copies, output)

    def duplicate_existing_static_props(
        self, copies: Sequence[dict], output: str | Path,
        *, write: bool = False,
    ) -> dict:
        """Safely duplicate 2..8 source-eligible props; in-memory by default.

        Explicit isolated writes are binary-provenanced only. The game
        runtime, physics/collision and arbitrary actor spawning are NOT
        established by this operation.
        """
        from .multi_clones import duplicate_existing_static_props
        return duplicate_existing_static_props(self, copies, output, write=write)

    def apply_multi_clone_plan(
        self, plan_file: str | Path, output: str | Path,
        *, write: bool = False,
    ) -> dict:
        """Recheck saved source plan, then dry-run or create new isolated GMP."""
        from .multi_clones import apply_multi_clone_plan
        return apply_multi_clone_plan(self, plan_file, output, write=write)

    def verify_saved_multi_clone(self, output: str | Path) -> dict:
        """Independently re-clone all original source props and compare bytes."""
        from .multi_clones import verify_saved_multi_clone
        return verify_saved_multi_clone(self, output)

    def native_scalar_fields(self, actor_name: str) -> dict:
        """Inspect source-authored, experimental writable numeric tagged fields.

        Only original *top-level* int32/float32 tagged values on existing,
        mesh-resolved source StaticMeshActors are considered. No GameSys
        block edits, script editing or game runtime guarantees.
        """
        from .scalars import original_scalar_fields
        return original_scalar_fields(self, actor_name)

    def save_as_scalar_changes(
        self, changes: Mapping[str, Mapping[str, object]],
        output: str | Path, *, write: bool = False,
    ) -> dict:
        """Experimental isolated GMP copy, only explicit typed scalar patches.

        A full independent MIT T3SDK package no-op roundtrip is required
        before every write. Defaults to dry-run, never modifies source GMP.
        """
        from .scalars import save_as_scalar_copy
        return save_as_scalar_copy(self, changes, output, write=write)

    def verify_saved_scalar_changes(self, output: str | Path) -> dict:
        """Independent entire-original-byte verification for scalar GMP copy."""
        from .scalars import verify_scalar_copy
        return verify_scalar_copy(self, output)

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
