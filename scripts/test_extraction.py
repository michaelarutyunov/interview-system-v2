"""
Quick test script for LLM extraction - no full simulation needed.

Usage:
    uv run python scripts/test_extraction.py

This tests just the extraction LLM call with a sample text,
without running the full simulation pipeline.
"""

import asyncio
import sys

# Add project root to path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from src.services.extraction_service import ExtractionService
from src.core.schema_loader import load_methodology
from src.llm.client import get_extraction_llm_client


async def test_extraction():
    """Test extraction with a sample response."""

    # Sample text that would come from a skeptical analyst persona
    sample_text = """
    I need to see actual cupping scores and origin transparency before I'll consider
    switching from my current single-origin Ethiopian. Most brands just make vague
    claims about "premium quality" without any verifiable data. I typically research
    roasters extensively - checking if they publish actual cupping notes, whether
    they have direct trade relationships, and if they provide harvest dates. Without
    that information, I'm not willing to experiment with unknown brands.
    """

    print("=" * 60)
    print("Testing LLM Extraction")
    print("=" * 60)

    # Initialize extraction service with LLM client
    llm_client = get_extraction_llm_client()
    print(f"LLM Client: {type(llm_client).__name__}")
    if hasattr(llm_client, "model"):
        print(f"Model: {llm_client.model}")
    print()

    extraction_service = ExtractionService(
        llm_client=llm_client,
        concept_id="coffee_jtbd_legacy",
    )

    # Load schema for validation
    schema = load_methodology("jobs_to_be_done")

    print("\nMethodology: jobs_to_be_done")
    print(f"Valid node types: {list(schema.get_valid_node_types())}")
    print(f"Valid edge types: {schema.get_valid_edge_types()}")

    print(f"\nSample text ({len(sample_text)} chars):")
    print("-" * 40)
    print(sample_text[:200] + "..." if len(sample_text) > 200 else sample_text)
    print("-" * 40)

    print("\nCalling extraction LLM...")
    print("(This may take 5-15 seconds)\n")

    try:
        result = await extraction_service.extract(
            text=sample_text,
            context="What matters to you when choosing coffee?",
            methodology="jobs_to_be_done",
        )

        print("✓ Extraction successful!")
        print("\nResults:")
        print(f"  Concepts extracted: {len(result.concepts)}")
        print(f"  Relationships extracted: {len(result.relationships)}")
        print(f"  Latency: {result.latency_ms}ms")

        if result.concepts:
            print("\n  Concepts:")
            for c in result.concepts[:5]:  # Show first 5
                print(f"    - {c.text} ({c.node_type})")
            if len(result.concepts) > 5:
                print(f"    ... and {len(result.concepts) - 5} more")

        if result.relationships:
            print("\n  Relationships:")
            for r in result.relationships[:5]:  # Show first 5
                print(
                    f"    - {r.source_text} --[{r.relationship_type}]--> {r.target_text}"
                )
            if len(result.relationships) > 5:
                print(f"    ... and {len(result.relationships) - 5} more")

        return True

    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_extraction())
    sys.exit(0 if success else 1)
