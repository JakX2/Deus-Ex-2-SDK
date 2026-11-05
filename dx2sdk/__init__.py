"""Public DX2SDK Python API, built on the open-source DX2Ed research project.

Usage:
    from dx2sdk import DX2Map
    project = DX2Map.open("M1_Seattle_Club.gmp")
    print(project.info())
    print(project.actors(actor_class="StaticMeshActor", limit=20))

This package does not redistribute original game content or implement native
TriggerScript compilation, BSP/collision rebuild or arbitrary actor spawning.
"""
from .api import DX2Map, SDK_SCHEMA, __version__

__all__ = ("DX2Map", "SDK_SCHEMA", "__version__")
