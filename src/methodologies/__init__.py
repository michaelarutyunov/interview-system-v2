from typing import Dict, Optional
from src.methodologies.base import MethodologyModule

_REGISTRY: Dict[str, MethodologyModule] = {}


def register_methodology(module: MethodologyModule) -> None:
    """Register a methodology module."""
    _REGISTRY[module.name] = module


def get_methodology(name: str) -> Optional[MethodologyModule]:
    """Get a registered methodology module by name."""
    return _REGISTRY.get(name)


def list_methodologies() -> list[str]:
    """List all registered methodology names."""
    return list(_REGISTRY.keys())


# Auto-register methodologies on import
def _auto_register():
    from src.methodologies.means_end_chain import MECModule
    from src.methodologies.jtbd import JTBDModule

    register_methodology(MECModule())
    register_methodology(JTBDModule())


_auto_register()
