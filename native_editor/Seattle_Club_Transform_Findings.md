# Seattle Club actor transform audit (research)

Tested privately against user-supplied retail files **M1_Seattle_Club.gmp** and **m1_club.ibd**; neither file is redistributed.

## Reproduced facts

- 1,613 actors; 1,120 static-mesh-linked actors; no actor property-table parse errors.
- 138 unique mesh resource names referenced by the map; 119 resolved in the supplied mission IBD.
- All 119 resolved mesh vertex bounds matched the bounds saved in the map's StaticMesh metadata; no coordinate-decoding error identified.
- MainScale/PostScale tagged properties appeared on 215 brush/volume actors, not placed static mesh actors.
- The mission-only backend exported 1,056 static mesh actors and 1,613 actor metadata records successfully. 64 mesh actors could not be rendered in this isolated run because no shared graphics bundles were supplied. That does not imply they are missing from a complete installation.
- A second native-backend run hit the generated cache successfully.
- Existing actor transform conversion is provisional. The screenshot alone does not identify which render mesh is rotated incorrectly.

Source verification hashes (not source assets):
- GMP SHA-256 `5a63c2de62208686d3508b6e124038cca8db9966fb6f1f93261eca9e5f10bf21`.
- IBD SHA-256 `fe1c169d5fc36e5119fda5c3ee6ea32fc643c7d3381eae86ead1adeacff0fc7d`.

## Next repro

Open Seattle Club with the native viewer, click the questionable model, then press **Copy mesh info**. The diagnostic contains original actor ID, class, resource, position, UE rotator, and transformed Godot bounds. If it is level BSP instead of a placed actor, the viewer reports the render node name.

Until an object is identified, avoid global rotation or scale changes: these would also affect valid geometry. A selected runtime prop might also be intentionally placed or dynamically hidden rather than incorrectly transformed.

## Limits

The Godot UI diagnostic code is source-checked but has not been exercised under a real Godot GPU session in our development environment. The tool performs no binary map write.
