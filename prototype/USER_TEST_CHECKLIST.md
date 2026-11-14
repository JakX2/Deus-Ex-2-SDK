# DX2Ed: first Windows alpha hands-on checklist (November 2026)

This checklist uses only original retail files from the tester's own DX2
installation. The editor is not yet a complete T3Ed replacement.

## Prepare

1. Download the **DX2Ed_Windows_Prototype_Godot43** artifact from a
   successful Windows GitHub Actions prototype workflow run.
2. Extract it into a writable new directory **outside** the retail game
   folder. Keep the included source, Python workers and bundled Godot
   runtime together.
3. Install Python 3.11+ if absent; test the packaged launcher using
   **START_DX2ED.cmd --self-test** and then **START_DX2ED.cmd**.
4. Preserve a pristine installation and saves. All experimental GMP
   Save As output belongs in a different folder and all gameplay tests
   should use a separate disposable copied game installation.

## Editor smoke test (no retail changes)

- Open the **synthetic demo** before selecting an original retail map.
  Verify cubes, actor selection, Inspector and camera controls work.
- Open a small original GMP through **Open DX2 map (.gmp)**; supply the
  matching mission IBD or manual IBD override if discovery fails.
- Check texture/geometry coverage, the actor tree, Actor Workbench,
  Search/Filter, Focus selected and selection details.
- Switch Perspective, Top, Front and Side views, and quad mode if
  available. Try fly/orbit/pan/zoom, grid snap and undo/redo.
- Add a **private** Box or Polygon brush, edit a draft face/vertex,
  apply a preview material, save the private draft, reopen, verify
  identical authored state. This is **not** a game-compatible map.
- If viewing geometry, report a screenshot with the map name, editor
  status line and any visible rotated/missing scene sections.

## Original-game compatibility experiments (isolated copies only)

- **Read-only:** run the new P107 interactive candidate audit on an
  original GMP. Record only candidate counts and the first few
  original actor/mesh/class names. Do not distribute original assets.
- **Static-prop Save As:** if testing existing native move/clone
  workflows, choose a non-critical decorative original
  StaticMeshActor that passes source checks. Never select an
  interactive door, a vending machine, an NPC or an original with
  unresolved links as an experimental native clone.
- Verify any generated private GMP with its independent manifest
  verifier before considering a disposable retail A/B test.
- In the copied game, record: fresh level load, prop visible at the
  intended position, player collision, normal NPC behavior, leave and
  re-enter, save and load, and successful restoration of the original.
- Report a **failed** candidate honestly even if it passes the byte
  verifier: format validity does not establish runtime compatibility.

## Useful issue report fields

- **Branch/commit:** exact GitHub branch and commit SHA from the artifact.
- **Windows/GPU:** Windows version, GPU model and renderer error if any.
- **Map:** original GMP basename only (not original file uploads).
- **Original cache/IBD:** whether matching mission/shared resources were found.
- **Test step:** action, expected result and actual result.
- **Evidence:** screenshot, editor status or error trace; source/candidate
  SHA-256 when a private modified-map test is involved.
- **Recovery:** original files and saves unchanged / restored.

There is no verified native BSP compiler, new interactive actor
spawner or general GameSys/script writer in this milestone.
