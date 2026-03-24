#!/bin/bash
cd "$(dirname "$0")/.."

echo "Running 15 brief_responder interviews (max 15 turns each)"
echo "8x meal_planning_jtbd_v2, 7x coffee_jtbd_v2"
echo ""

PASS=0
FAIL=0

run_interview() {
  local concept=$1
  local label=$2
  if uv run python scripts/run_simulation.py "$concept" brief_responder 15; then
    PASS=$((PASS + 1))
    echo "  [OK] $label"
  else
    FAIL=$((FAIL + 1))
    echo "  [FAILED] $label — continuing"
  fi
}

for i in {1..8}; do
  echo "=== meal_planning interview $i/8 ==="
  run_interview meal_planning_jtbd_v2 "meal_planning $i/8"
done

for i in {1..7}; do
  echo "=== coffee interview $i/7 ==="
  run_interview coffee_jtbd_v2 "coffee $i/7"
done

echo ""
echo "Done. Passed: $PASS / Failed: $FAIL"
echo "Check synthetic_interviews/ for new files."
