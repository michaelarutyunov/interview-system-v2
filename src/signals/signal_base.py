"""Base classes for signal detection with auto-registration and dependency resolution.

Signal detectors analyze context, graph state, and response text to extract
structured signals for methodology-based strategy selection.

Core classes:
- SignalDetector: Abstract base with auto-registration and dependency ordering
- ComposedSignalDetector: YAML-driven signal composition from shared pools
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from src.services.node_state_tracker import NodeStateTracker


class SignalDetector(ABC):
    """Abstract base for signal detectors with auto-registration and dependency resolution.

    Signal detectors extract structured signals from pipeline context, graph state,
    and response text. These signals drive methodology-based strategy selection.

    Features:
    - Auto-registration via __init_subclass__ (no manual registry updates)
    - Declarative dependencies (topological sort for detection order)
    - Node-level signal marker (requires_node_tracker for per-node scoring)
    - Namespaced signals (graph.*, llm.*, temporal.*, meta.*, graph.node.*, technique.node.*)

    Subclass pattern:
        class MySignal(SignalDetector):
            signal_name = "namespace.signal_name"
            description = "Human-readable description for YAML config"
            dependencies = ["namespace.dep_signal"]  # Optional

            async def detect(self, context, graph_state, response_text):
                return {self.signal_name: value}

    Attributes:
        signal_name: Namespaced signal name (e.g., "graph.node_count")
        description: Human-readable description for YAML methodology configs
        dependencies: List of signal names this detector requires
        requires_node_tracker: Whether detector needs NodeStateTracker for per-node signals
        node_tracker: NodeStateTracker instance (set if requires_node_tracker=True)
    """

    # Class attributes (subclasses override)
    signal_name: ClassVar[str]
    description: ClassVar[str] = ""
    dependencies: ClassVar[list[str]] = []
    requires_node_tracker: ClassVar[bool] = False

    # Auto-registration registry
    _registry: ClassVar[dict[str, type["SignalDetector"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-register signal detector subclasses in global registry.

        Automatically registers any SignalDetector subclass that defines signal_name.
        This enables zero-boilerplate signal discovery via SignalDetector.get_signal_class().

        Registration happens at import time when the class body executes.
        Classes without signal_name (intermediate base classes) are skipped.

        Pattern:
            class MySignal(SignalDetector):
                signal_name = "my.signal"  # Triggers auto-registration
        """
        super().__init_subclass__(**kwargs)

        # Only register if signal_name is defined (skip intermediate bases)
        if "signal_name" in cls.__dict__:
            cls._registry[cls.signal_name] = cls

    @classmethod
    def get_registered_signals(cls) -> dict[str, type["SignalDetector"]]:
        """Get all registered signal detector classes.

        Returns dictionary of signal_name -> detector_class for all detectors
        that have been auto-registered via __init_subclass__.

        Returns:
            Dictionary mapping namespaced signal names to detector classes
        """
        return cls._registry.copy()

    @classmethod
    def get_signal_class(cls, signal_name: str) -> type["SignalDetector"] | None:
        """Get signal detector class by namespaced signal name.

        Used by ComposedSignalDetector to instantiate detectors from YAML
        methodology configs. Enables dynamic signal composition.

        Args:
            signal_name: Namespaced signal name (e.g., "graph.node_count")

        Returns:
            Signal detector class or None if signal name not registered
        """
        return cls._registry.get(signal_name)

    def __init__(self, node_tracker: NodeStateTracker | None = None) -> None:
        """Initialize signal detector with optional NodeStateTracker.

        Args:
            node_tracker: NodeStateTracker for per-node signal detection.
                Required when requires_node_tracker=True, optional otherwise.

        Raises:
            ValueError: If detector requires node_tracker but none provided
        """
        if self.requires_node_tracker and node_tracker is None:
            raise ValueError(
                f"{self.__class__.__name__} requires NodeStateTracker but none provided"
            )
        self.node_tracker = node_tracker

    @abstractmethod
    async def detect(
        self,
        context: Any,  # PipelineContext (circular import avoided)
        graph_state: Any,  # GraphState (circular import avoided)
        response_text: str,
    ) -> dict[str, Any]:
        """Detect and return signal value(s) from context and response.

        Subclasses implement specific signal detection logic here.
        Signals can access dependency signals via context.signals dictionary.

        Args:
            context: Pipeline context with conversation state, signals,
                and methodology metadata
            graph_state: Current knowledge graph state with node/edge counts,
                depth metrics, and structure information
            response_text: User's response text to analyze

        Returns:
            Dictionary mapping signal names to detected values.
            Typically returns single key: {self.signal_name: value}
            May return multiple related signals for efficiency (e.g.,
            batched LLM signals or computed aggregates).
        """
        ...

    @classmethod
    def get_dependency_order(cls, signal_names: list[str]) -> list[str]:
        """Compute topological sort order for signal detection using Kahn's algorithm.

        Resolves declared signal dependencies to produce a detection order where
        all dependencies are detected before dependents. Ensures signals can
        safely access dependency values from context.signals.

        Used by ComposedSignalDetector to determine signal execution order
        from YAML methodology configs.

        Args:
            signal_names: List of namespaced signal names to order

        Returns:
            List of signal names in dependency order (dependencies before dependents)

        Raises:
            ValueError: If circular dependency detected among signals

        Example:
            ["graph.edge_count", "graph.edge_density"]
            Returns: ["graph.edge_count", "graph.edge_density"]
            Because edge_density depends on edge_count
        """
        # Build dependency graph
        in_degree: dict[str, int] = {name: 0 for name in signal_names}
        adj_list: dict[str, set[str]] = {name: set() for name in signal_names}

        for signal_name in signal_names:
            signal_class = cls.get_signal_class(signal_name)
            if signal_class is None:
                continue

            # Count dependencies that are also in our signal list
            for dep in signal_class.dependencies:
                if dep in signal_names:
                    in_degree[signal_name] += 1
                    adj_list[dep].add(signal_name)

        # Kahn's algorithm: start with signals that have no dependencies
        queue = [name for name in signal_names if in_degree[name] == 0]
        result: list[str] = []

        while queue:
            # Sort for deterministic order (important for tests)
            queue.sort()
            current = queue.pop(0)
            result.append(current)

            # Reduce in-degree for dependent signals
            for dependent in sorted(adj_list[current]):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check for circular dependencies
        if len(result) != len(signal_names):
            # Find signals not in result (part of cycle)
            cycle = [name for name in signal_names if name not in result]
            raise ValueError(
                f"Circular dependency detected in signals: {cycle}. "
                f"Check signal dependencies and break the cycle."
            )

        return result
