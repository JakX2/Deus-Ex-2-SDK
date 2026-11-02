"""Read-only coverage accounting for DX2 GMP -> GLB mesh imports.

A missing render node can be caused by an unresolved GMP mesh reference,
an absent IBD resource, or a source mesh with no non-empty render section.
Non-mesh gameplay actors are *not* missing geometry.
"""
from __future__ import annotations


def _identity(actor, reason):
    return {
        "actor": actor.get("name"),
        "export": actor.get("export"),
        "class": actor.get("class"),
        "mesh": (actor.get("mesh") or {}).get("name")
                if isinstance(actor.get("mesh"), dict) else actor.get("mesh"),
        "reason": reason,
    }


def summarize_mesh_export_coverage(actors, rendered, missing_resources, empty_sections):
    """Describe inspectable gaps without claiming that game geometry is absent.

    Args:
        actors: source GMP scene actors after staticmesh reference resolution.
        rendered: source actor records that got actual GLB mesh nodes.
        missing_resources: importer records with actor/export/mesh.
        empty_sections: importer records with actor/export/mesh.
    """
    static_actors = [a for a in actors if a.get("class") == "StaticMeshActor"]
    mesh_linked = [a for a in actors if bool(a.get("mesh"))]
    unresolved = [_identity(a, "unresolved_gmp_mesh_reference")
                  for a in static_actors if not a.get("mesh")]
    rendered_ids = {a["export"] for a in rendered}
    missing_ids = {a["export"] for a in missing_resources}
    empty_ids = {a["export"] for a in empty_sections}
    # These sets are mutually exclusive inside the exporter's branch logic.
    # Any remaining reference has silently failed to become a rendered node.
    unexplained = [_identity(a, "unaccounted_nonrendered_mesh_actor")
                   for a in mesh_linked if a["export"] not in
                   rendered_ids | missing_ids | empty_ids]
    return {
        "schema": "DX2Ed-mesh-export-coverage-v1",
        "not_game_verified": True,
        "source_scene_actor_count": len(actors),
        "source_staticmesh_actor_count": len(static_actors),
        "source_mesh_linked_actor_count": len(mesh_linked),
        "rendered_mesh_actor_count": len(rendered_ids),
        "missing_ibd_resource_count": len(missing_resources),
        "empty_render_sections_count": len(empty_sections),
        "unresolved_gmp_staticmesh_reference_count": len(unresolved),
        "unaccounted_nonrendered_mesh_actor_count": len(unexplained),
        "unresolved_gmp_staticmesh_references": unresolved,
        "missing_ibd_resources": list(missing_resources),
        "empty_render_sections": list(empty_sections),
        "unaccounted_nonrendered_mesh_actors": unexplained,
        "warning": (
            "These are parser/export coverage diagnostics, not proof that the "
            "original game rendered every listed StaticMeshActor. BSP blocks "
            "and engine-managed procedural effects are tracked separately."
        ),
    }
