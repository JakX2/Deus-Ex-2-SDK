"""Public DX2SDK v0.15 Python API, built on the open-source DX2Ed research project.

Usage:
    from dx2sdk import DX2Map
    project = DX2Map.open("M1_Seattle_Club.gmp")
    print(project.info())
    print(project.actors(actor_class="StaticMeshActor", limit=20))

This package does not redistribute original game content or implement native
TriggerScript compilation, BSP/collision rebuild or arbitrary actor spawning.
"""
from .api import DX2Map, SDK_SCHEMA, __version__
from .projects import (
    SCHEMA as POSITION_PLAN_SCHEMA,
    build_position_plan,
    write_position_plan,
    load_position_plan,
    apply_position_plan,
)

__all__ = (
    "DX2Map", "SDK_SCHEMA", "__version__", "POSITION_PLAN_SCHEMA",
    "build_position_plan", "write_position_plan",
    "load_position_plan", "apply_position_plan",
)
