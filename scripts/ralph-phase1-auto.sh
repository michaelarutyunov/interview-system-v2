#!/bin/bash
# ralph-phase1-auto.sh - Fully autonomous Ralph execution with auto-approve
#
# Usage: ./scripts/ralph-phase1-auto.sh

set -e

# Define zai function directly in script
zai() {
    (
        export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
        export ANTHROPIC_AUTH_TOKEN=$Z_API_KEY
        export ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-4.5-air"
        export ANTHROPIC_DEFAULT_SONNET_MODEL="glm-4.7"
        export ANTHROPIC_DEFAULT_OPUS_MODEL="glm-4.7"
        export API_TIMEOUT_MS="3000000"
        claude "$@"
    )
}

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

SPEC_DIR="specs/phase-1"
MAX_ITER=5

# Initialize progress tracking
touch progress.json
echo "[] - Starting Phase 1 at $(date -Iseconds)" >> progress.json

specs=(
  "1.1-project-scaffolding.md"
  "1.2-sqlite-schema.md"
  "1.3-database-module.md"
  "1.4-settings-logging.md"
  "1.5-fastapi-shell.md"
)

echo "======================================"
echo "Ralph Phase 1 - Autonomous Execution"
echo "======================================"
echo "Max iterations: $MAX_ITER per spec"
echo ""

for spec in "${specs[@]}"; do
  echo ""
  echo "======================================"
  echo "Processing: $spec"
  echo "======================================"
  
  spec_path="$SPEC_DIR/$spec"
  
  for i in $(seq 1 $MAX_ITER); do
    echo ""
    echo "--- Iteration $i/$MAX_ITER ---"
    
    # Run zai WITHOUT -p flag for interactive execution
    zai --dangerously-skip-permissions "$(cat $spec_path)"
    
    echo ""
    echo "Running verification..."
    
    if sed -n '/## Verification/,/## Success Criteria/p' "$spec_path" | \
       grep -E '^(test|python3|pytest|sqlite3|cd|uvicorn|curl)' | \
       bash -x 2>&1; then
      
      echo "✅ Verification passed"
      git add -A
      git commit -m "Completed: $spec (iteration $i)"
      echo "{\"spec\": \"$spec\", \"completed_at\": \"$(date -Iseconds)\", \"iterations\": $i, \"status\": \"success\"}" >> progress.json
      break
    else
      echo "⚠️  Verification failed"
      if [ $i -eq $MAX_ITER ]; then
        echo "❌ Max iterations reached"
        echo "{\"spec\": \"$spec\", \"completed_at\": \"$(date -Iseconds)\", \"iterations\": $i, \"status\": \"failed\"}" >> progress.json
      fi
    fi
  done
done

echo ""
echo "======================================"
echo "Phase 1 Complete!"
echo "======================================"
