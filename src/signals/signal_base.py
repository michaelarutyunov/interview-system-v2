"""Base classes for signal detection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from src.services.node_state_tracker import NodeStateTracker


class SignalDetector(ABC):
    """Base class for signal detectors with auto-registration.

    A signal detector analyzes context, graph state, and response text
    to extract structured signals for strategy selection.

    Features:
    - Auto-registration via __init_subclass__
    - Declarative dependencies
    - Node-level signal marker

    Attributes:
        signal_name: Namespaced signal name (e.g., "graph.node_count")
        dependencies: List of signal names this detector depends on
        requires_node_tracker: Whether this detector needs NodeStateTracker
        description: Human-readable description of the signal

    Example:
        class GraphNodeCountSignal(SignalDetector):
            signal_name = "graph.node_count"
            description = "Total number of concepts in the graph"
            dependencies = []  # No dependencies

            async def detect(self, context, graph_state, response_text):
                return {self.signal_name: graph_state.node_count}

        class InterviewProgressSignal(SignalDetector):
            signal_name = "meta.interview_progress"
            description = "Overall interview progress 0-1"
            dependencies = ["graph.chain_completion", "graph.max_depth", "graph.node_count"]

            async def detect(self, context, graph_state, response_text):
                # Uses signals from context.signals
                ...
    """

    # Class attributes (subclasses override)
    signal_name: ClassVar[str]
    description: ClassVar[str] = ""
    dependencies: ClassVar[list[str]] = []
    requires_node_tracker: ClassVar[bool] = False

    # Auto-registration registry
    _registry: ClassVar[dict[str, type["SignalDetector"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-register signal subclasses when they are defined.

        Any class that:
        1. Inherits from SignalDetector
        2. Defines a signal_name class attribute

        Is automatically registered in _registry.
        """
        super().__init_subclass__(**kwargs)

        # Only register if signal_name is defined (skip intermediate bases)
        if "signal_name" in cls.__dict__:
            cls._registry[cls.signal_name] = cls

    @classmethod
    def get_registered_signals(cls) -> dict[str, type["SignalDetector"]]:
        """Return all registered signal classes.

        Returns:
            Dictionary mapping signal_name -> signal_class
        """
        return cls._registry.copy()

    @classmethod
    def get_signal_class(cls, signal_name: str) -> type["SignalDetector"] | None:
        """Get a signal class by name.

        Args:
            signal_name: Namespaced signal name

        Returns:
            Signal class or None if not found
        """
        return cls._registry.get(signal_name)

    def __init__(self, node_tracker: NodeStateTracker | None = None) -> None:
        """Initialize the signal detector.

        Args:
            node_tracker: Optional NodeStateTracker for node-level signals
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
        """Detect and return signal value(s).

        Args:
            context: Pipeline context with conversation state
            graph_state: Current knowledge graph state
            response_text: User's response text to analyze

        Returns:
            Dictionary mapping signal names to values.
            Usually single key: {self.signal_name: value}
            May return multiple related signals for efficiency.
        """
        ...

    @classmethod
    def get_dependency_order(cls, signal_names: list[str]) -> list[str]:
        """Compute topological sort order for signal detection.

        Uses Kahn's algorithm to resolve dependencies and return
        signals in an order that ensures all dependencies are
        detected before dependents.

        Args:
            signal_names: List of signal names to detect

        Returns:
            List of signal names in dependency order

        Raises:
            ValueError: If circular dependency detected
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
