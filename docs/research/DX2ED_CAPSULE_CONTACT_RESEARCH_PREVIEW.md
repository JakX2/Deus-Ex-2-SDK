# DX2Ed capsule first-contact research preview

**PR #47, stacked on PR #46.** This opt-in research view extends the existing original Level/Flesh/MOPP source collision inspector. It does not use Havok runtime physics or affect native GMP Save As, actors, brushes, or game collision.

## Editor visualization

Open an original owner-supplied GMP and enable **Inspect source collision**. The **Load capsule research preview...** button then accepts a local source-hash-matched research JSON.

The wireframe shows start/end capsule outlines, trajectory, capsule at first numerical contact, first closest points, a normal arrow when geometrically resolved, and the existing selected original source triangle outline. The Inspector clearly marks these as **research only, not Havok gameplay**.

A no-hit path is also drawable. Turning source collision inspection off or changing the scene clears the overlay. No CollisionShape3D, dynamic physics object, actor, map property, or writable collision is created.

The conversion from original Level XYZ to Godot preview coordinates is **(X/10, Z/10, Y/10)**, with direction vectors permuted but not scaled.

## Owner-GMP export

First obtain the original GMP SHA-256:

~~~powershell
(Get-FileHash "C:\DX2\Maps\M1_Seattle_hub.gmp" -Algorithm SHA256).Hash.ToLowerInvariant()
~~~

Then from the repository root, run the exporter (one line), replacing the map, SHA-256, source Level coordinates and fresh private output path:

~~~powershell
python research/dx2/export_capsule_first_contact_preview.py --map "C:\DX2\Maps\M1_Seattle_hub.gmp" --expected-sha256 "INSERT_64_CHARACTER_LOWERCASE_SHA256" --start 30 20 10 --end 30 20 -10 --radius 0.2 --axis 0 0 1 --axis-half-length 0.5 --output "C:\DX2Ed_Research\capsule_preview_01.json"
~~~

The sample start/end source-Level XYZ may miss every surface in the chosen map. The JSON output MUST be new and outside retail Maps folders. Keep owner-map-derived preview JSON private: it includes point coordinates derived from original geometry. Never commit or publicly distribute that file.

## Safety and validation

Python revalidates the source GMP and SHA-256, independently checks original Level triangle IDs and full-sweep capsule geometric hits, and requires conservative source MOPP candidate coverage. Refuses misleading results and writes only a new private JSON.

Godot requires the exact active map and hash, recognized original triangle ID from the source collision cache, finite geometry, normalized axis and normal, compatible units and consistent numerical contact-time bracket. An unresolved zero-distance normal remains unresolved. Matching the source hash does **not** cryptographically authenticate edited sidecar values, so every display is labeled research-only.

No original GMP/IBD bytes are modified. No game/runtime Havok query, contact manifold, material/filter test or native collision serialization is performed.

## Files and tests

- research/dx2/export_capsule_first_contact_preview.py: read-only source-validated JSON sidecar generator
- native_editor/godot_editor/capsule_contact_preview.gd: validated wireframe and inspector description
- native_editor/godot_editor/main.gd: opt-in UI plus cleanup, independent from Save As
- native_editor/tests/test_dx2_capsule_contact_preview_sidecar.py: 10 asset-free source, shape, timing and file refusal tests
- native_editor/godot_editor/tests/smoke_capsule_contact_preview.gd: Godot 4.3 smoke tests of validation, mesh and main.gd parsing
- .github/workflows/native-dx2ed.yml: new Godot smoke stage

Run the Python asset-free tests:

~~~bash
python -m unittest discover -s native_editor/tests -p "test_dx2_capsule_contact_preview_sidecar.py" -v
~~~

**Remaining work:** Havok runtime comparison, true DX2 shape and material provenance, time-of-impact/contact manifold and controller response, authentic spatial MOPP cooking, and game-compatible native collision writing.
