"""Strategy scoring package - DEPRECATED.

This module has been replaced by the methodology-centric architecture.

Phase 6 Cleanup (2026-01-28):
- The two-tier scoring system has been replaced by methodology-specific signal detection
- See src/methodologies/ for the new implementation
- Each methodology (MEC, JTBD) now has its own signals and strategies

For new code, use:
- src.methodologies.get_methodology() to get a methodology module
- src.services.methodology_strategy_service.MethodologyStrategyService for strategy selection
"""

# This module is kept as a stub for backward compatibility
# All imports below are deprecated and will be removed in a future release

__all__ = []  # Empty exports - use new methodology modules instead
