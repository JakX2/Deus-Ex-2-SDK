# DX2 Level MOPP-linked collision triangle topology (PR #31)

A read-only, fail-closed diagnostic of **geometric adjacency** in the previously verified DX2 Level flattened geometry. Uses the exact geometry/collision-leaf/provenance chain from PRs #27–30. It is **not a Havok shape, physics material, BSP, CSG, cooking or writable map implementation**.

## Evidence from 19 original retail GMP maps

The original user-owned 19-map Seattle corpus (UE95, licensees 65/67/68/69) was checked with the entire existing render-block → flattened mesh → MOPP leaves → triangle provenance → debug atlas chain. The new topology inspection ran on each atlas independently, without editing original maps. No original vertices, triangle arrays, code streams, or binary assets are included in the repository.

| Measurement | Retail corpus |
|---|---:|
| Source maps | 19/19 |
| Flattened source vertices | 76,732 |
| Unique vertex positions, **exact f32 XYZ equality** | **22,387** |
| Repeated source vertex positions | 54,345 |
| Flattened triangles | 43,154 |
| MOPP-linked triangles included | **43,152** |
| Source zero-area, non-MOPP triangles excluded | 2 |
| Triangle-edge incidences | 129,456 |
| Distinct exact-position geometric edges | **66,389** |
| Edges used by one triangle | **3,343** |
| Edges used by exactly two triangles | **63,034** |
| Edges used by 3+ triangles | **12** |
| Two-face edges having inconsistent same-direction orientation | **0** |
| Two-face edges crossing **render** material IDs | **16,532** |
| Edge-connected components across maps | 69 |

The edge-incidence identity (3 × 43,152) = 3,343 + (2 × 63,034) + incidences of twelve 3+-face edges is checked for every map. No map is rejected merely for an open edge, extra edge incidences, disconnected components or multiple render materials. These properties are not inherently errors in a triangle soup, and the Havok runtime's shape constraints have **not** been authenticated.

## Algorithm

1. Require the exact original vertex/triangle counts from the PR #30 atlas. Validate every ordered source triangle ID, three in-range vertex indices, material index and MOPP-link boolean.
2. Canonicalize only **bit-exact-equivalent position values** (Python float equality after reading source f32; signed zero compares equal). Do not weld near-equal coordinates with an arbitrary epsilon.
3. Recompute every source face's cross-product area. Exclude only original triangles independently classified as zero area and absent from MOPP. Refuse nonzero-area non-leaves or zero-area MOPP-linked triangles.
4. Index the three undirected geometric edges per MOPP triangle by exact-position welded endpoint IDs, retaining their directed winding and source triangle ID.
5. Count edges by incident-face multiplicity, check paired-edge orientation, detect render-material boundaries, and derive edge-connected components with union-find.
6. Output compact JSON metrics and up to twelve **triangle-ID-only** non-manifold examples with `--include-examples`. No original coordinates or proprietary binary contents are emitted by the default auditor.

### Reproduce on the user's own GMPs

```powershell
python research/dx2/inspect_level_mopp_collision_topology.py "C:\DX2\Content\DX2\Maps\M1_Seattle_hub.gmp" --report "C:\DX2_Research_Reports\collision_topology.json"
python -m unittest discover -s native_editor/tests -p "test_dx2_level_mopp_collision_topology.py" -v
```

Use a fresh report file outside all original map directories. Reports are created exclusively, never overwritten. The input GMP bytes are read and remain untouched. Tests are fixture-only and require no retail files.

## Interpretation for future SDK work

- Exact-position welding collapses duplicate render vertices at coincident positions. This produces a more meaningful connectivity graph than unmodified render vertex IDs, which are duplicated across render sections.
- The **16,532 shared geometric edges crossing render-material boundaries** are visible segmentation information. They do not identify a Havok `hkpMaterial`, friction, restitution, footstep type, filter info or gameplay surface flags.
- The **12 multi-face edges** are diagnostic cases to preserve, not automatically 'repair'. Arbitrary welding, removing open edges, or reorienting faces could change gameplay collision.
- This analysis validates the *input soup* for potential future shape rebuilding. It cannot produce or serialize a new MOPP bytecode tree, instantiate a Havok shape, rebuild World Model BSP vertex/surface pools, or test acceptance in Deus Ex: Invisible War.

Next logical investigations: map actual Havok shape/material consumers in the game binaries or Thief 3 equivalents; verify how runtime flags map to render-section metadata, and develop a separate experimental **writer** only against disposable map copies after strict round-trip checks.