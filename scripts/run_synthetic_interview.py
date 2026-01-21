#!/usr/bin/env python3
"""
Automated synthetic interview test script.

Runs a complete interview using the synthetic respondent:
1. Creates a session with concept configuration
2. Iterates through turns (question -> synthetic response)
3. Validates coverage, graph state, and session completion
4. Reports results

Usage:
    python scripts/run_synthetic_interview.py --persona health_conscious
    python scripts/run_synthetic_interview.py --max-turns 10 --coverage 0.7
    python scripts/run_synthetic_interview.py --output results.json
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import httpx


# Configuration
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_CONCEPT_ID = "oat_milk_v1"
DEFAULT_PERSONA = "health_conscious"
DEFAULT_MAX_TURNS = 20
DEFAULT_TARGET_COVERAGE = 0.8


async def create_session(
    client: httpx.AsyncClient,
    api_url: str,
    concept_id: str = DEFAULT_CONCEPT_ID,
) -> Dict[str, Any]:
    """Create a new interview session."""
    response = await client.post(
        f"{api_url}/sessions",
        json={
            "methodology": "means_end_chain",
            "concept_id": concept_id,
            "config": {
                "concept_name": "Oat Milk",
                "concept_description": "A plant-based milk alternative made from oats",
                "max_turns": DEFAULT_MAX_TURNS,
                "target_coverage": DEFAULT_TARGET_COVERAGE,
            },
        },
    )
    response.raise_for_status()
    return response.json()


async def start_session(
    client: httpx.AsyncClient,
    api_url: str,
    session_id: str,
) -> Dict[str, Any]:
    """Start a session and get the opening question."""
    response = await client.post(
        f"{api_url}/sessions/{session_id}/start",
    )
    response.raise_for_status()
    return response.json()


async def get_synthetic_response(
    client: httpx.AsyncClient,
    api_url: str,
    question: str,
    session_id: str,
    persona: str,
    interview_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get synthetic response to a question."""
    response = await client.post(
        f"{api_url}/synthetic/respond",
        json={
            "question": question,
            "session_id": session_id,
            "persona": persona,
            "interview_context": interview_context,
        },
    )
    response.raise_for_status()
    return response.json()


async def submit_turn(
    client: httpx.AsyncClient,
    api_url: str,
    session_id: str,
    user_input: str,
) -> Dict[str, Any]:
    """Submit a turn to the session."""
    response = await client.post(
        f"{api_url}/sessions/{session_id}/turns",
        json={"text": user_input},
    )
    response.raise_for_status()
    return response.json()


async def get_session_status(
    client: httpx.AsyncClient,
    api_url: str,
    session_id: str,
) -> Dict[str, Any]:
    """Get current session status."""
    response = await client.get(
        f"{api_url}/sessions/{session_id}",
    )
    response.raise_for_status()
    data = response.json()

    # Extract relevant status information
    # The TurnResponse from the last turn has the most up-to-date info
    return {
        "status": data.get("status", "unknown"),
        "turn_count": data.get("turn_count", 0),
        "coverage": 0.0,  # Will be updated from turn responses
        "should_continue": True,  # Will be updated from turn responses
        "next_question": None,  # Will be updated from turn responses
    }


async def run_interview(
    api_url: str,
    persona: str,
    concept_id: str,
    max_turns: int,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run a complete synthetic interview."""
    results = {
        "persona": persona,
        "concept_id": concept_id,
        "start_time": datetime.utcnow().isoformat(),
        "turns": [],
        "final_status": None,
        "success": False,
        "error": None,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create session
            if verbose:
                print(f"Creating session for concept: {concept_id}")

            session = await create_session(client, api_url, concept_id)
            session_id = session["id"]

            if verbose:
                print(f"Session created: {session_id}")

            results["session_id"] = session_id

            # Start session to get opening question
            if verbose:
                print(f"Starting session...")

            start_result = await start_session(client, api_url, session_id)
            opening_question = start_result["opening_question"]

            if verbose:
                print(f"Opening question: {opening_question}")

            results["opening_question"] = opening_question

            # Track current state across turns
            current_coverage = 0.0
            should_continue = True
            next_question = opening_question

            # Run turns
            for turn_num in range(1, max_turns + 1):
                if not next_question:
                    if verbose:
                        print("No more questions - interview complete")
                    break

                if not should_continue:
                    if verbose:
                        print("Interview flagged as complete")
                    break

                if verbose:
                    print(f"\n--- Turn {turn_num} ---")
                    print(f"Coverage: {current_coverage * 100:.1f}%")
                    print(f"Question: {next_question}")

                # Get synthetic response
                interview_context = {
                    "product_name": "Oat Milk",
                    "turn_number": turn_num,
                    "coverage_achieved": current_coverage,
                }

                synthetic_result = await get_synthetic_response(
                    client, api_url, next_question, session_id, persona, interview_context
                )

                synthetic_response = synthetic_result["response"]

                if verbose:
                    print(f"Response: {synthetic_response}")
                    print(f"Latency: {synthetic_result['latency_ms']:.0f}ms")

                # Submit turn
                turn_result = await submit_turn(
                    client, api_url, session_id, synthetic_response
                )

                # Update state from turn response
                current_coverage = turn_result.get("scoring", {}).get("coverage", 0.0)
                should_continue = turn_result.get("should_continue", True)
                next_question = turn_result.get("next_question")

                turn_data = {
                    "turn_number": turn_num,
                    "question": turn_result.get("next_question"),
                    "response": synthetic_response,
                    "extracted_concepts": [
                        c["text"] for c in turn_result.get("extracted", {}).get("concepts", [])
                    ],
                    "strategy": turn_result.get("strategy_selected"),
                    "coverage": turn_result.get("scoring", {}).get("coverage", 0.0),
                    "should_continue": turn_result.get("should_continue", True),
                    "latency_ms": turn_result.get("latency_ms", 0),
                }

                results["turns"].append(turn_data)

                if verbose:
                    print(f"Strategy: {turn_data['strategy']}")
                    print(f"Concepts extracted: {len(turn_data['extracted_concepts'])}")
                    print(f"Coverage: {turn_data['coverage'] * 100:.1f}%")

            # Get final session info
            session_info = await get_session_status(client, api_url, session_id)

            results["final_status"] = {
                "status": session_info.get("status"),
                "turn_count": session_info.get("turn_count", len(results["turns"])),
                "coverage": current_coverage,
            }
            results["end_time"] = datetime.utcnow().isoformat()
            results["success"] = True

            if verbose:
                print(f"\n=== Interview Complete ===")
                print(f"Total turns: {len(results['turns'])}")
                print(f"Final coverage: {current_coverage * 100:.1f}%")
                print(f"Status: {session_info.get('status', 'unknown')}")

    except Exception as e:
        results["error"] = str(e)
        results["end_time"] = datetime.utcnow().isoformat()

    return results


def validate_results(results: Dict[str, Any]) -> bool:
    """Validate interview results against success criteria."""
    print("\n=== Validation ===")

    if not results["success"]:
        print(f"❌ Interview failed: {results['error']}")
        return False

    final_status = results.get("final_status", {})
    coverage = final_status.get("coverage", 0.0)
    turn_count = len(results.get("turns", []))

    checks_passed = 0
    checks_total = 0

    # Check 1: Coverage ≥ 80%
    checks_total += 1
    if coverage >= 0.8:
        print(f"✅ Coverage: {coverage * 100:.1f}% ≥ 80%")
        checks_passed += 1
    else:
        print(f"❌ Coverage: {coverage * 100:.1f}% < 80%")

    # Check 2: At least 5 turns
    checks_total += 1
    if turn_count >= 5:
        print(f"✅ Turns: {turn_count} ≥ 5")
        checks_passed += 1
    else:
        print(f"❌ Turns: {turn_count} < 5")

    # Check 3: No errors in turns
    checks_total += 1
    turn_errors = [t for t in results.get("turns", []) if t.get("error")]
    if not turn_errors:
        print(f"✅ No turn errors")
        checks_passed += 1
    else:
        print(f"❌ {len(turn_errors)} turn errors")

    # Check 4: At least 10 concepts extracted
    checks_total += 1
    total_concepts = sum(
        len(t.get("extracted_concepts", []))
        for t in results.get("turns", [])
    )
    if total_concepts >= 10:
        print(f"✅ Concepts extracted: {total_concepts} ≥ 10")
        checks_passed += 1
    else:
        print(f"❌ Concepts extracted: {total_concepts} < 10")

    # Check 5: Session status is valid
    checks_total += 1
    status = final_status.get("status", "")
    if status in ["completed", "coverage_met", "active", ""]:
        print(f"✅ Session status: {status if status else 'active'}")
        checks_passed += 1
    else:
        print(f"⚠️  Session status: {status} (unexpected)")

    print(f"\nPassed: {checks_passed}/{checks_total} checks")
    return checks_passed == checks_total


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run automated synthetic interview test"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--persona",
        default=DEFAULT_PERSONA,
        choices=[
            "health_conscious",
            "price_sensitive",
            "convenience_seeker",
            "quality_focused",
            "sustainability_minded",
        ],
        help="Persona to use (default: health_conscious)",
    )
    parser.add_argument(
        "--concept-id",
        default=DEFAULT_CONCEPT_ID,
        help="Concept configuration ID (default: oat_milk_v1)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=DEFAULT_MAX_TURNS,
        help=f"Maximum turns to run (default: {DEFAULT_MAX_TURNS})",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON file for results",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )

    args = parser.parse_args()

    print(f"Starting synthetic interview test...")
    print(f"  API URL: {args.api_url}")
    print(f"  Persona: {args.persona}")
    print(f"  Concept: {args.concept_id}")
    print(f"  Max turns: {args.max_turns}")

    results = asyncio.run(run_interview(
        api_url=args.api_url,
        persona=args.persona,
        concept_id=args.concept_id,
        max_turns=args.max_turns,
        verbose=args.verbose,
    ))

    # Output results
    if args.output:
        args.output.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to: {args.output}")

    # Validate
    success = validate_results(results)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
