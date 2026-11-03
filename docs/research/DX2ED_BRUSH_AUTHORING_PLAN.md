# DX2Ed brush-authoring intent plan (experimental)

The Godot Brushes tab already offers Box, Wall, Floor and Stairs **preview-only** primitives and saves their metadata in private `DX2Ed-prop-draft-v1` JSON sidecars. This feature translates **only validated Box, Wall and Floor drafts** into an explicit, independently inspectable **geometry-authoring plan** measured in the project's existing Unreal-unit coordinate convention.

This is **not a game map compiler, Unreal CSG operation, Thief 3 export, DX2 BSP writer or collision generator**.

## Usage

Save your private brush draft in DX2Ed, locate its `user://prop_drafts/<hash>.json` sidecar, then run:

```powershell
python native_editor/godot_editor/backend/dx2_brush_plan.py --draft "C:\DX2EdDrafts\brush-draft.json" --output "C:\DX2EdPlans\brush-plan.json"
```

The output must be a **new file outside the source draft folder** and records:
- Each source brush's type, dimensions, world-space center, eight Unreal-unit vertices, six outward-facing quadrilateral faces with normals, material placeholders and bounds.
- Original source draft SHA-256 and hashed map-cache identity, not raw map-cache paths.
- Explicit flags `native_gmp_written: false`, `native_bsp_compiled: false`, `collision_generated: false`, `game_runtime_verified: false`.

Input is limited to a maximum 2 MB, 128 exclusively-brush copies, numeric finite values, dimensions 0.05–256 Godot metres, and supported non-sheared, non-mirrored affine transforms. Drafts mixing brush and prop/property edits are refused instead of silently dropping changes. Stairs are deliberately refused because their current overlapping preview-box geometry is **not** native CSG union.

Conversions follow the existing DX2Ed display convention (`Godot X=UE X; Godot Z=UE Y; Godot Y=UE Z`, one Unreal unit = 0.01905 metres). This convention is **not independently verified for every DX2 game asset** and must be revisited before designing a native writer.

Run tests:

```powershell
python -m unittest discover -s native_editor/tests -p "test_dx2_brush_plan.py" -v
```

## The next real DX2 writer milestone

Convert the plan into **editable native brush / Model / Polys actor exports** only after independently decoding the DX2 licensee 68 structures. Then build a separately researched DX2-specific Flesh BSP and collision compiler. T3Ed's user-confirmed runtime geometry build validates the *T3* pipeline only, not the DX2 serializer.
