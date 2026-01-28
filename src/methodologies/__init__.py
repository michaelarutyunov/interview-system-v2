"""Methodologies module - YAML-based configuration with signal pools.

This module uses:
- YAML configs for methodology definitions (config/*.yaml)
- Shared signal pools (signals/graph, signals/llm, signals/temporal, signals/meta)
- Shared technique pool (techniques/)
- MethodologyRegistry for loading configs

Usage:
    from src.methodologies.registry import MethodologyRegistry
    registry = MethodologyRegistry()
    config = registry.get_methodology("means_end_chain")
    detector = registry.create_signal_detector(config)
"""

from src.methodologies.registry import (
    MethodologyRegistry,
    MethodologyConfig,
    StrategyConfig,
)

# Global registry instance
_registry: MethodologyRegistry | None = None


def get_registry() -> MethodologyRegistry:
    """Get the global methodology registry instance."""
    global _registry
    if _registry is None:
        _registry = MethodologyRegistry()
    return _registry


def get_methodology(name: str) -> MethodologyConfig:
    """Get a methodology configuration by name.

    Convenience function that uses the global registry.
    """
    return get_registry().get_methodology(name)


def list_methodologies() -> list[str]:
    """List all available methodology names.

    Convenience function that uses the global registry.
    """
    return get_registry().list_methodologies()


__all__ = [
    "MethodologyRegistry",
    "MethodologyConfig",
    "StrategyConfig",
    "get_registry",
    "get_methodology",
    "list_methodologies",
]
