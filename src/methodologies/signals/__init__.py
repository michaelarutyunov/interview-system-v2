"""Backward compatibility shim.

This module re-exports everything from src.signals to maintain
backward compatibility with existing imports.

Deprecated: Please import directly from src.signals instead.
"""

# Re-export everything from the new location
from src.signals import *  # noqa: F401, F403
