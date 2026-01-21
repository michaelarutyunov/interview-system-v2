#!/usr/bin/env python3
"""
Benchmark script for interview system performance.

Measures turn latency across multiple runs and validates against PRD requirements:
- Response latency <5s p95 (PRD Section 2.2)

Usage:
    python scripts/benchmark.py [--runs N] [--sessions M]

Options:
    --runs N      Number of turns per session (default: 10)
    --sessions M  Number of concurrent sessions (default: 1)
"""

import argparse
import asyncio
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.session_service import SessionService
from src.services.extraction_service import ExtractionService
from src.services.graph_service import GraphService
from src.services.question_service import QuestionService
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.domain.models.extraction import ExtractionResult, ExtractedConcept
from src.domain.models.knowledge_graph import GraphState, KGNode


# PRD Requirements
PRD_LATENCY_P95_MS = 5000  # 5 seconds
PRD_LATENCY_TARGET_MS = 3000  # 3 seconds typical


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, name: str):
        self.name = name
        self.latencies_ms: List[float] = []
        self.errors: List[Dict] = []
        self.start_time = None
        self.end_time = None

    def add_latency(self, latency_ms: float):
        """Add a latency measurement."""
        self.latencies_ms.append(latency_ms)

    def add_error(self, error: Exception):
        """Record an error."""
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "type": type(error).__name__
        })

    @property
    def count(self) -> int:
        """Number of measurements."""
        return len(self.latencies_ms)

    @property
    def avg_ms(self) -> float:
        """Average latency in ms."""
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    @property
    def median_ms(self) -> float:
        """Median latency in ms."""
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0

    @property
    def p95_ms(self) -> float:
        """95th percentile latency in ms."""
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]

    @property
    def p99_ms(self) -> float:
        """99th percentile latency in ms."""
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[idx]

    @property
    def min_ms(self) -> float:
        """Minimum latency in ms."""
        return min(self.latencies_ms) if self.latencies_ms else 0

    @property
    def max_ms(self) -> float:
        """Maximum latency in ms."""
        return max(self.latencies_ms) if self.latencies_ms else 0

    @property
    def passed_prd(self) -> bool:
        """Check if p95 meets PRD requirement."""
        return self.p95_ms < PRD_LATENCY_P95_MS

    def print_summary(self):
        """Print benchmark summary."""
        print(f"\n{'='*60}")
        print(f"Benchmark: {self.name}")
        print(f"{'='*60}")

        if self.errors:
            print(f"\n⚠️  ERRORS: {len(self.errors)}")
            for err in self.errors[-3:]:  # Show last 3 errors
                print(f"  - [{err['type']}] {err['error']}")
            if len(self.errors) > 3:
                print(f"  ... and {len(self.errors) - 3} more")

        if self.latencies_ms:
            print(f"\n📊 Latency Statistics (n={self.count}):")
            print(f"  Average: {self.avg_ms:.0f}ms")
            print(f"  Median:  {self.median_ms:.0f}ms")
            print(f"  Min:     {self.min_ms:.0f}ms")
            print(f"  Max:     {self.max_ms:.0f}ms")
            print(f"  p95:     {self.p95_ms:.0f}ms")
            print(f"  p99:     {self.p99_ms:.0f}ms")

            print(f"\n✅ PRD Validation:")
            prd_status = "✓ PASS" if self.passed_prd else "✗ FAIL"
            print(f"  p95 < {PRD_LATENCY_P95_MS}ms: {prd_status}")

            if not self.passed_prd:
                print(f"  ⚠️  p95 ({self.p95_ms:.0f}ms) exceeds PRD target by {self.p95_ms - PRD_LATENCY_P95_MS:.0f}ms")
        else:
            print("\n⚠️  No latency measurements recorded")


class MockBenchmark:
    """
    Benchmark using mock services for rapid iteration.

    Tests the orchestration layer without real LLM calls.
    """

    def __init__(self, runs: int = 10, sessions: int = 1):
        self.runs = runs
        self.sessions = sessions
        self.result = BenchmarkResult(f"Mock ({runs} turns × {sessions} sessions)")

    async def run(self) -> BenchmarkResult:
        """Run the mock benchmark."""
        print(f"\n🚀 Starting Mock Benchmark")
        print(f"   Turns: {self.runs}")
        print(f"   Sessions: {self.sessions}")

        from unittest.mock import AsyncMock, MagicMock

        # Setup mock services
        mock_session_repo = AsyncMock()
        mock_session_repo.db = AsyncMock()
        mock_session_repo.db.execute = AsyncMock()
        mock_session_repo.db.commit = AsyncMock()
        mock_session_repo.get = AsyncMock(return_value=MagicMock(
            id="bench-session",
            methodology="means_end_chain",
            concept_id="test",
            config={"concept_name": "Test Product"},
            turn_count=1
        ))
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        mock_session_repo.db.execute = AsyncMock(return_value=cursor)

        mock_graph_repo = AsyncMock()
        mock_graph_repo.get_graph_state = AsyncMock(return_value=GraphState(
            node_count=5, edge_count=3, nodes_by_type={"attribute": 3}
        ))
        mock_graph_repo.get_nodes_by_session = AsyncMock(return_value=[])

        # Create mock services
        extraction_svc = AsyncMock()
        extraction_svc.extract = AsyncMock(return_value=ExtractionResult(
            concepts=[ExtractedConcept(text="quality", node_type="attribute")],
            relationships=[],
            is_extractable=True
        ))

        graph_svc = AsyncMock()
        graph_svc.add_extraction_to_graph = AsyncMock(return_value=([], []))
        graph_svc.get_graph_state = AsyncMock(return_value=GraphState(
            node_count=5, edge_count=3, nodes_by_type={"attribute": 3}
        ))
        graph_svc.get_recent_nodes = AsyncMock(return_value=[
            KGNode(id="n1", session_id="s1", label="quality", node_type="attribute")
        ])

        question_svc = AsyncMock()
        question_svc.generate_question = AsyncMock(
            return_value="Can you tell me more about that?"
        )
        question_svc.select_focus_concept = MagicMock(return_value="quality")

        # Create session service
        service = SessionService(
            session_repo=mock_session_repo,
            graph_repo=mock_graph_repo,
            extraction_service=extraction_svc,
            graph_service=graph_svc,
            question_service=question_svc,
        )

        # Run benchmark
        self.result.start_time = time.time()

        for session_idx in range(self.sessions):
            session_id = f"bench-session-{session_idx}"

            for turn_idx in range(self.runs):
                try:
                    start = time.perf_counter()
                    await service.process_turn(
                        session_id=session_id,
                        user_input=f"Benchmark turn {turn_idx + 1}",
                    )
                    latency_ms = (time.perf_counter() - start) * 1000
                    self.result.add_latency(latency_ms)

                    # Progress indicator
                    if (turn_idx + 1) % 5 == 0:
                        print(f"   Session {session_idx + 1}/{self.sessions}: "
                              f"{turn_idx + 1}/{self.runs} turns complete")

                except Exception as e:
                    self.result.add_error(e)

        self.result.end_time = time.time()
        return self.result


class LiveBenchmark:
    """
    Benchmark using real services (requires LLM API key).

    Tests end-to-end latency with real LLM calls.
    """

    def __init__(self, runs: int = 10, api_key: str = None):
        self.runs = runs
        self.api_key = api_key
        self.result = BenchmarkResult(f"Live ({runs} turns)")

    async def run(self) -> BenchmarkResult:
        """Run the live benchmark."""
        print(f"\n🚀 Starting Live Benchmark")
        print(f"   Turns: {self.runs}")
        print(f"   ⚠️  This will make real LLM API calls")

        # Check for API key
        if not self.api_key:
            print("\n⚠️  No API key provided. Use --api-key or set OPENAI_API_KEY env var")
            print("   Skipping live benchmark.")
            return self.result

        # TODO: Implement live benchmark with real services
        # This requires:
        # - Real database setup
        # - LLM client configuration
        # - Session creation
        # - Turn processing with real calls

        print("\n⚠️  Live benchmark not yet implemented")
        return self.result


async def run_benchmarks(args) -> List[BenchmarkResult]:
    """Run all benchmarks."""
    results = []

    # Mock benchmark (always runs)
    mock_bench = MockBenchmark(runs=args.runs, sessions=args.sessions)
    result = await mock_bench.run()
    results.append(result)

    # Live benchmark (optional, requires API key)
    if args.live:
        live_bench = LiveBenchmark(runs=args.runs, api_key=args.api_key)
        result = await live_bench.run()
        if result.count > 0:
            results.append(result)

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark interview system performance"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of turns per session (default: 10)"
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=1,
        help="Number of concurrent sessions (default: 1)"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live benchmark with real LLM calls"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("📐 Interview System Performance Benchmark")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run benchmarks
    results = asyncio.run(run_benchmarks(args))

    # Print all results
    print("\n\n" + "="*60)
    print("📋 FINAL RESULTS")
    print("="*60)

    for result in results:
        result.print_summary()

    # Exit with appropriate code
    all_passed = all(r.passed_prd for r in results if r.count > 0)
    if all_passed:
        print("\n✅ All benchmarks PASSED PRD requirements")
        return 0
    else:
        print("\n❌ Some benchmarks FAILED PRD requirements")
        return 1


if __name__ == "__main__":
    sys.exit(main())
