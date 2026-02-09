#!/usr/bin/env python3
"""
Analyze similarity score distribution in canonical slot discovery.

PURPOSE: Diagnose whether the sentence-transformers embedding model produces
meaningful similarity scores or if all scores are 1.0 (indicating the
similarity threshold has no effect).

CONTEXT: After switching from spaCy word vectors to sentence-transformers
(commit 9f402c7), threshold testing from z7gh is invalidated. This script
determines if threshold tuning is necessary.

USAGE:
    uv run python scripts/analyze_similarity_distribution.py <session_id>

OUTPUT:
    - Total mappings count
    - Distribution of similarity scores (histogram)
    - Count and percentage of exact matches (score = 1.0)
    - Statistics for non-1.0 scores (min, max, mean, median, stddev)
    - Conclusion: whether threshold tuning is needed

Bead: z7gh (threshold testing), gjb5 (threshold tuning)
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import aiosqlite

# Statistics
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


async def get_similarity_scores(
    db_path: str, session_id: str
) -> List[Tuple[str, str, float, str, str]]:
    """
    Query all similarity scores from surface_to_slot_mapping.

    Returns:
        List of (surface_node_id, canonical_slot_id, similarity_score, surface_label, canonical_name) tuples
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        query = """
        SELECT
            m.surface_node_id,
            m.canonical_slot_id,
            m.similarity_score,
            n.label as surface_label,
            s.slot_name as canonical_name
        FROM surface_to_slot_mapping m
        JOIN kg_nodes n ON m.surface_node_id = n.id
        JOIN canonical_slots s ON m.canonical_slot_id = s.id
        WHERE n.session_id = ?
        ORDER BY m.similarity_score DESC
        """

        async with db.execute(query, (session_id,)) as cursor:
            rows = await cursor.fetchall()

        return [
            (
                row["surface_node_id"],
                row["canonical_slot_id"],
                row["similarity_score"],
                row["surface_label"],
                row["canonical_name"],
            )
            for row in rows
        ]


def analyze_distribution(
    scores: List[Tuple[str, str, float, str, str]]
) -> Dict:
    """
    Analyze similarity score distribution.

    Returns:
        Dictionary with analysis results
    """
    if not scores:
        return {
            "total_mappings": 0,
            "exact_matches": 0,
            "non_exact_matches": 0,
            "conclusion": "No mappings found",
        }

    total = len(scores)
    similarity_values = [score[2] for score in scores]

    # Count exact matches (1.0)
    exact_matches = sum(1 for s in similarity_values if s == 1.0)
    non_exact = total - exact_matches

    # Get non-1.0 scores for statistics
    non_exact_scores = [s for s in similarity_values if s < 1.0]

    result = {
        "total_mappings": total,
        "exact_matches": exact_matches,
        "exact_match_pct": (exact_matches / total) * 100,
        "non_exact_matches": non_exact,
        "non_exact_pct": (non_exact / total) * 100,
    }

    if non_exact_scores:
        if HAS_NUMPY:
            result["non_exact_stats"] = {
                "min": float(np.min(non_exact_scores)),
                "max": float(np.max(non_exact_scores)),
                "mean": float(np.mean(non_exact_scores)),
                "median": float(np.median(non_exact_scores)),
                "std": float(np.std(non_exact_scores)),
            }
        else:
            result["non_exact_stats"] = {
                "min": min(non_exact_scores),
                "max": max(non_exact_scores),
                "mean": sum(non_exact_scores) / len(non_exact_scores),
            }

        # Create histogram buckets
        buckets = {
            "0.0-0.5": 0,
            "0.5-0.7": 0,
            "0.7-0.8": 0,
            "0.8-0.85": 0,
            "0.85-0.88": 0,
            "0.88-0.90": 0,
            "0.90-0.95": 0,
            "0.95-1.0": 0,
            "1.0": exact_matches,
        }

        for score in non_exact_scores:
            if score < 0.5:
                buckets["0.0-0.5"] += 1
            elif score < 0.7:
                buckets["0.5-0.7"] += 1
            elif score < 0.8:
                buckets["0.7-0.8"] += 1
            elif score < 0.85:
                buckets["0.8-0.85"] += 1
            elif score < 0.88:
                buckets["0.85-0.88"] += 1
            elif score < 0.90:
                buckets["0.88-0.90"] += 1
            elif score < 0.95:
                buckets["0.90-0.95"] += 1
            else:
                buckets["0.95-1.0"] += 1

        result["histogram"] = buckets

    # Determine conclusion
    if non_exact == 0:
        result["conclusion"] = (
            "ALL_EXACT_MATCHES - Threshold has no effect (LLM reuses exact names or creates new slots)"
        )
        result["recommendation"] = (
            "Threshold tuning not needed. Close gjb5/z7gh with current default (0.88)."
        )
    elif non_exact < (total * 0.05):
        result["conclusion"] = (
            f"MOSTLY_EXACT ({non_exact}/{total} non-exact) - Threshold has minimal effect"
        )
        result["recommendation"] = (
            "Consider threshold tuning if non-exact scores cluster near current threshold."
        )
    else:
        result["conclusion"] = (
            f"SIMILARITY_ACTIVE ({non_exact}/{total} non-exact) - Threshold affects slot merging"
        )
        result["recommendation"] = (
            "Threshold tuning needed. Test wider range (0.8, 0.85, 0.9) to optimize."
        )

    return result


def print_report(analysis: Dict, scores: List[Tuple[str, str, float, str, str]]):
    """Print analysis report to stdout."""
    print("=" * 80)
    print("CANONICAL SLOT SIMILARITY DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print()

    print("SUMMARY")
    print("-" * 80)
    print(f"Total Mappings:        {analysis['total_mappings']}")
    print(
        f"Exact Matches (1.0):   {analysis['exact_matches']} ({analysis['exact_match_pct']:.1f}%)"
    )
    print(
        f"Similarity Matches:    {analysis['non_exact_matches']} ({analysis['non_exact_pct']:.1f}%)"
    )
    print()

    if analysis["non_exact_matches"] > 0:
        print("SIMILARITY SCORE STATISTICS (non-1.0 scores)")
        print("-" * 80)
        stats = analysis["non_exact_stats"]
        print(f"Min:    {stats['min']:.4f}")
        print(f"Max:    {stats['max']:.4f}")
        print(f"Mean:   {stats['mean']:.4f}")
        if "median" in stats:
            print(f"Median: {stats['median']:.4f}")
            print(f"StdDev: {stats['std']:.4f}")
        print()

        print("HISTOGRAM (Similarity Score Distribution)")
        print("-" * 80)
        histogram = analysis["histogram"]
        max_count = max(histogram.values())
        for bucket, count in histogram.items():
            bar_length = int((count / max_count) * 50) if max_count > 0 else 0
            bar = "█" * bar_length
            pct = (count / analysis["total_mappings"]) * 100
            print(f"{bucket:12s} | {count:4d} ({pct:5.1f}%) {bar}")
        print()

        # Show sample non-exact matches
        non_exact_samples = [s for s in scores if s[2] < 1.0][:10]
        if non_exact_samples:
            print("SAMPLE NON-EXACT MATCHES (top 10 by similarity)")
            print("-" * 80)
            for _surface_id, _slot_id, sim, surface_label, slot_name in non_exact_samples:
                print(f"  {sim:.4f} | {surface_label:30s} → {slot_name}")
            print()

    print("CONCLUSION")
    print("-" * 80)
    print(f"{analysis['conclusion']}")
    print()
    print(f"Recommendation: {analysis['recommendation']}")
    print()
    print("=" * 80)


async def main():
    parser = argparse.ArgumentParser(
        description="Analyze similarity score distribution in canonical slot discovery"
    )
    parser.add_argument("session_id", help="Session ID to analyze")
    parser.add_argument(
        "--db",
        default="data/interview.db",
        help="Database path (default: data/interview.db)",
    )

    args = parser.parse_args()

    # Check DB exists
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    # Get similarity scores
    print(f"Querying session {args.session_id}...", file=sys.stderr)
    scores = await get_similarity_scores(str(db_path), args.session_id)

    if not scores:
        print(
            f"Error: No surface-to-slot mappings found for session {args.session_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Analyze
    analysis = analyze_distribution(scores)

    # Report
    print_report(analysis, scores)


if __name__ == "__main__":
    asyncio.run(main())
