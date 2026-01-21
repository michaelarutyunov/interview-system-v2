#!/bin/bash
# ralph-auto.sh - Ralph automation for interview-system-v2
#
# Reference: AGENTS.md for "Landing the Plane" workflow
# Uses bd (beads) for issue tracking - run `bd onboard` if not set up
#
# Usage:
#   ./scripts/ralph/ralph-auto.sh                 # Interactive menu
#   ./scripts/ralph/ralph-auto.sh prereqs         # Check prerequisites
#   ./scripts/ralph/ralph-auto.sh list            # List all specs
#   ./scripts/ralph/ralph-auto.sh run <spec>      # Run single spec
#   ./scripts/ralph/ralph-auto.sh run-all         # Run all specs in sequence

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPEC_DIR="$PROJECT_ROOT/specs/phase-1"
LOG_DIR="$PROJECT_ROOT/logs/ralph"
BEADS_FILE="$LOG_DIR/beads.json"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# ========================================
# Bead Tracking Functions
# ========================================

init_beads() {
    if [ ! -f "$BEADS_FILE" ]; then
        echo '{"beads": []}' > "$BEADS_FILE"
    fi
}

save_bead() {
    local spec="$1"
    local iteration="$2"
    local status="$3"
    local output="$4"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local bead=$(cat <<EOF
{
  "timestamp": "$timestamp",
  "spec": "$spec",
  "iteration": $iteration,
  "status": "$status",
  "output": $(echo "$output" | jq -Rs .)
}
EOF
)

    # Append to beads array
    local temp=$(mktemp)
    jq --argjson new_bead "$bead" '.beads += [$new_bead]' "$BEADS_FILE" > "$temp"
    mv "$temp" "$BEADS_FILE"

    # Also save individual bead log
    local bead_log="$LOG_DIR/beads/$(date +%Y%m%d-%H%M%S)-${spec//\//-}-iter${iteration}.json"
    mkdir -p "$LOG_DIR/beads"
    echo "$bead" > "$bead_log"
    echo -e "${GREEN}✓ Bead saved: $bead_log${NC}"
}

get_last_iteration() {
    local spec="$1"
    local spec_escaped=$(echo "$spec" | sed 's/"/\\"/g')
    local last_iter=$(jq -r --arg spec "$spec_escaped" '.beads | map(select(.spec == $spec)) | max_by(.iteration) | .iteration // 0' "$BEADS_FILE" 2>/dev/null || echo "0")
    echo $((last_iter + 1))
}

show_beads() {
    if [ ! -f "$BEADS_FILE" ]; then
        echo "No beads recorded yet."
        return
    fi

    echo -e "${BLUE}=== Ralph Beads ===${NC}"
    jq -r '.beads | reverse | .[] | "\(.timestamp) | \(.spec) | iter#\(.iteration) | \(.status)"' "$BEADS_FILE" 2>/dev/null || echo "No beads yet."
}

# ========================================
# Stage 1: Prerequisites
# ========================================

stage_prerequisites() {
    echo -e "${BLUE}======================================"
    echo " Stage 1: Prerequisites"
    echo -e "======================================${NC}"
    echo ""

    PREREQUISITES="$SPEC_DIR/prerequisites.sh"

    if [ ! -f "$PREREQUISITES" ]; then
        echo -e "${RED}❌ prerequisites.sh not found at $PREREQUISITES${NC}"
        exit 1
    fi

    bash "$PREREQUISITES"
    echo -e "${GREEN}✓ Prerequisites satisfied${NC}"
    echo ""
}

# ========================================
# Stage 2: List Specs
# ========================================

stage_list_specs() {
    echo -e "${BLUE}======================================"
    echo " Available Specs"
    echo -e "======================================${NC}"
    echo ""

    specs=("$SPEC_DIR"/*.md)
    spec_count=0

    for spec in "${specs[@]}"; do
        if [ -f "$spec" ]; then
            spec_count=$((spec_count + 1))
            basename=$(basename "$spec")
            title=$(head -n 5 "$spec" | grep -E "^# " | sed 's/^# //')
            echo -e "${GREEN}$spec_count.${NC} $basename"
            echo "   $title"
            echo ""
        fi
    done

    echo "Total: $spec_count specs"
}

# ========================================
# Stage 3: Run Single Spec
# ========================================

run_spec() {
    local spec_file="$1"
    local max_iterations="${2:-5}"

    if [ ! -f "$spec_file" ]; then
        echo -e "${RED}❌ Spec not found: $spec_file${NC}"
        exit 1
    fi

    local spec_name=$(basename "$spec_file" .md)
    local spec_content=$(cat "$spec_file")

    init_beads
    local iteration=$(get_last_iteration "$spec_name")

    echo -e "${BLUE}======================================"
    echo " Running Spec: $spec_name"
    echo -e "======================================${NC}"
    echo "File: $spec_file"
    echo "Max Iterations: $max_iterations"
    echo "Starting Iteration: $iteration"
    echo ""

    # Run Ralph Loop via Claude Code CLI
    local start_time=$(date +%s)

    # The actual Ralph Loop command (run by Claude Code plugin)
    # This script is a launcher - the plugin handles the iteration
    echo -e "${YELLOW}To run this spec, use in Claude Code:${NC}"
    echo "/ralph-loop \"\$(cat $spec_file)\" --max-iterations $max_iterations"
}

# ========================================
# Stage 4: Run All Specs
# ========================================

run_all_specs() {
    echo -e "${BLUE}======================================"
    echo " Running All Phase 1 Specs"
    echo -e "======================================${NC}"
    echo ""

    specs=(
        "1.1-project-scaffolding.md"
        "1.2-sqlite-schema.md"
        "1.3-database-module.md"
        "1.4-settings-logging.md"
        "1.5-fastapi-shell.md"
        "1.6-session-repository.md"
        "1.7-session-api-endpoints.md"
        "1.8-integration-test.md"
    )

    for spec in "${specs[@]}"; do
        local spec_path="$SPEC_DIR/$spec"
        if [ -f "$spec_path" ]; then
            echo ""
            echo -e "${YELLOW}▶ Next: $spec${NC}"
            echo -e "   Command: /ralph-loop \"\$(cat $spec_path)\" --max-iterations 5"
            echo ""
        fi
    done

    echo ""
    echo -e "${GREEN}Copy and paste each command above into Claude Code${NC}"
}

# ========================================
# Main
# ========================================

show_help() {
    cat << EOF
Ralph Auto - interview-system-v2 Phase 1

Reference: AGENTS.md (bd workflow, "Landing the Plane")

Usage:
  $0 [command] [args]

Commands:
  prereqs         Check and install prerequisites
  list            List all available specs
  run <spec>      Show command to run a specific spec
  run-all         Show commands to run all specs in sequence
  beads           Show recorded beads (iteration history)
  help            Show this help

Examples:
  $0 prereqs                    # Check prerequisites
  $0 list                       # List all specs
  $0 run 1.1-project-scaffolding  # Show command for spec 1.1
  $0 run-all                    # Show all spec commands
  $0 beads                      # Show bead history

Files:
  specs/phase-1/
    ├── prerequisites.sh        # Environment setup
    ├── 1.1-*.md               # Spec files
    └── ...
  logs/ralph/
    ├── beads.json             # Bead tracking (all iterations)
    └── beads/                 # Individual bead logs
  scripts/ralph/
    ├── prd.json               # User stories reference
    └── ralph-auto.sh          # This script

To run specs in Claude Code:
  /ralph-loop "\$(cat specs/phase-1/1.1-*.md)" --max-iterations 5

IMPORTANT - After completing work (AGENTS.md):
  1. bd sync                   # Sync issue status
  2. git push                  # PUSH IS MANDATORY
  3. git status                # Verify "up to date"

EOF
}

case "${1:-}" in
    prereqs|prerequisites)
        stage_prerequisites
        ;;
    list|ls)
        stage_list_specs
        ;;
    run)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}Error: Please specify a spec file${NC}"
            echo "Usage: $0 run <spec-file>"
            echo "Example: $0 run 1.1-project-scaffolding.md"
            exit 1
        fi
        run_spec "$SPEC_DIR/$2" "${3:-5}"
        ;;
    run-all)
        run_all_specs
        ;;
    beads)
        init_beads
        show_beads
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
