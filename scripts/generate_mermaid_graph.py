#!/usr/bin/env python3
"""
Generate Mermaid tree visualization from interview simulation JSON.

Creates a left-to-right column-aligned diagram where each turn occupies its own
column. Nodes are color-coded by turn and cross-column edges show relationships.
Both a .mmd source file and a rendered .png are saved next to the input JSON.

Usage:
    uv run python scripts/generate_mermaid_graph.py <json_file> [options]

Examples:
    # Full graph, auto-saved as <json_file>.mmd + <json_file>.png
    uv run python scripts/generate_mermaid_graph.py synthetic_interviews/foo.json

    # Simplified graph (top connected nodes only), saved as foo_simple.mmd + .png
    uv run python scripts/generate_mermaid_graph.py synthetic_interviews/foo.json -s

    # Simplified with custom node limit
    uv run python scripts/generate_mermaid_graph.py synthetic_interviews/foo.json -s --max-nodes 20

    # Custom output path (PNG saved alongside it)
    uv run python scripts/generate_mermaid_graph.py synthetic_interviews/foo.json -o /tmp/out.mmd

    # High resolution output (2x scale for 4800x2800)
    uv run python scripts/generate_mermaid_graph.py synthetic_interviews/foo.json --scale 2

Flags:
    json_file           Path to simulation JSON file (required)
    -s, --simplified    Simplified version: top connected nodes per turn only
    --max-nodes N       Max nodes in simplified mode (default: 30)
    -o, --output PATH   Override output .mmd path (default: same folder as JSON)
    --scale N           Output scale factor for PNG (default: 1, try 2 or 3 for higher resolution)
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def load_simulation_json(path: str) -> dict:
    """Load simulation JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def sanitize_label(label: str, max_length: int = 40) -> str:
    """Sanitize node label for Mermaid (remove special chars, truncate)."""
    # Remove characters that break Mermaid syntax
    label = label.replace('"', "'")
    label = label.replace('(', '[').replace(')', ']')
    label = label.replace('{', '[').replace('}', ']')

    # Truncate if too long
    if len(label) > max_length:
        label = label[:max_length-3] + '...'

    return label


def create_node_id(node_uuid: str) -> str:
    """Create a valid Mermaid node ID from UUID."""
    return 'n_' + node_uuid.replace('-', '_')[:8]


def build_node_turn_mapping(simulation: dict) -> dict:
    """Map node IDs to the turn they were created in."""
    node_to_turn = {}

    for turn in simulation['turns']:
        turn_num = turn['turn_number']
        nodes_added = turn.get('nodes_added') or []
        for node in nodes_added:
            node_to_turn[node['id']] = turn_num

    return node_to_turn


def build_focus_tracking(simulation: dict) -> dict:
    """
    Build focus tracking from score_decomposition.
    Returns dict mapping node_id to list of focus turn numbers.
    """
    node_focus_turns = defaultdict(list)

    for turn in simulation['turns']:
        turn_num = turn['turn_number']

        # Check score_decomposition for selected node-level entries
        score_decomposition = turn.get('score_decomposition') or []
        for score_item in score_decomposition:
            node_id = score_item.get('node_id', '')

            # Skip strategy-level entries (node_id == "")
            if node_id and score_item.get('selected', False):
                node_focus_turns[node_id].append(turn_num)

    return node_focus_turns


def build_turn_nodes(node_to_turn: dict, nodes: list) -> dict:
    """Group nodes by turn number."""
    turn_nodes = defaultdict(list)

    for node in nodes:
        node_id = node['id']
        if node_id in node_to_turn:
            turn_num = node_to_turn[node_id]
            turn_nodes[turn_num].append(node)

    return turn_nodes


# Focused nodes get highlighted color; non-focused are neutral
FOCUSED_COLOR = ('#fff9c4', '#f57f17')  # gold/yellow for focused nodes
DEFAULT_COLOR = ('#f5f5f5', '#616161')   # neutral grey for non-focused


def generate_mermaid_tree(simulation: dict) -> str:
    """Generate Mermaid flowchart LR (left-to-right) syntax."""

    node_to_turn = build_node_turn_mapping(simulation)
    nodes_by_turn = build_turn_nodes(node_to_turn, simulation['graph']['nodes'])
    node_focus_turns = build_focus_tracking(simulation)

    all_turns = sorted(nodes_by_turn.keys())

    # Theme configuration for taller boxes and styling
    lines = [
        '%%{init: {\'theme\': \'base\', \'themeVariables\': {',
        '  \'fontSize\': \'16px\',',
        '  \'fontFamily\': \'Arial\',',
        '  \'padding\': \'12px\'',
        '}}}%%',
        '',
        'graph LR'
    ]

    # Hidden anchor nodes — one per turn — force column alignment
    anchor_ids = [f't{t}' for t in all_turns]
    lines.append('')
    lines.append('    %% Hidden anchor nodes per turn (for column alignment)')
    for aid in anchor_ids:
        lines.append(f'    {aid}(( ))')

    # Chain anchors left-to-right to establish column order
    lines.append('')
    lines.append('    %% Anchor chain sets column order')
    lines.append('    ' + ' ~~~ '.join(anchor_ids))

    # Fan out from each anchor to its turn's nodes (invisible links)
    lines.append('')
    lines.append('    %% Invisible links from anchors to turn nodes')
    for turn_num in all_turns:
        anchor = f't{turn_num}'
        for node in nodes_by_turn.get(turn_num, []):
            mermaid_id = create_node_id(node['id'])
            lines.append(f'    {anchor} ~~~ {mermaid_id}')

    # Define all nodes and track focused vs non-focused
    lines.append('')
    lines.append('    %% Node definitions')
    focused_nodes = []
    non_focused_nodes = []

    for node in simulation['graph']['nodes']:
        node_id = node['id']
        if node_id not in node_to_turn:
            continue

        turn_num = node_to_turn[node_id]
        label = sanitize_label(node['label'])

        focus_list = node_focus_turns.get(node_id, [])
        focus_indicator = ''
        if focus_list:
            focus_str = ' '.join([f'F{t}' for t in focus_list])
            focus_indicator = f' {focus_str}'

        mermaid_id = create_node_id(node_id)
        node_label = f'({turn_num}) {label}{focus_indicator}'
        lines.append(f'    {mermaid_id}["{node_label}"]')

        # Track focused vs non-focused for styling
        if focus_list:
            focused_nodes.append(mermaid_id)
        else:
            non_focused_nodes.append(mermaid_id)

    # Add real edges — all edges where both endpoints are in the selected node set
    # (intra-turn, forward cross-turn, and backward cross-turn)
    selected_node_ids = {
        node['id']
        for turn_num in all_turns
        for node in nodes_by_turn.get(turn_num, [])
    }
    lines.append('')
    lines.append('    %% Real edges')
    for edge in simulation['graph']['edges']:
        src_id = edge['source_node_id']
        tgt_id = edge['target_node_id']
        if src_id not in selected_node_ids or tgt_id not in selected_node_ids:
            continue
        source_id = create_node_id(src_id)
        target_id = create_node_id(tgt_id)
        edge_label = edge.get('edge_type', '')
        if edge_label:
            lines.append(f'    {source_id} -->|{edge_label}| {target_id}')
        else:
            lines.append(f'    {source_id} --> {target_id}')

    # Styling classes - focused nodes get color, others are neutral
    lines.append('')
    focused_fill, focused_stroke = FOCUSED_COLOR
    default_fill, default_stroke = DEFAULT_COLOR
    lines.append(f'    classDef focused fill:{focused_fill},stroke:{focused_stroke},stroke-width:3px')
    lines.append(f'    classDef default fill:{default_fill},stroke:{default_stroke},stroke-width:1px')
    lines.append('    classDef anchor fill:none,stroke:none')

    # Assign classes to nodes
    lines.append('')
    if focused_nodes:
        lines.append(f'    class {",".join(focused_nodes)} focused')
    if non_focused_nodes:
        lines.append(f'    class {",".join(non_focused_nodes)} default')
    lines.append(f'    class {",".join(anchor_ids)} anchor')

    return '\n'.join(lines)


def generate_simplified_tree(simulation: dict, max_nodes: int = 30) -> str:
    """
    Generate a simplified Mermaid tree with fewer nodes.
    Shows only the most connected/important nodes per turn.
    """

    # Build node connection counts
    node_connections = defaultdict(int)
    for edge in simulation['graph']['edges']:
        node_connections[edge['source_node_id']] += 1
        node_connections[edge['target_node_id']] += 1

    # Select top connected nodes per turn
    node_to_turn = build_node_turn_mapping(simulation)
    turn_nodes = build_turn_nodes(node_to_turn, simulation['graph']['nodes'])

    selected_nodes = set()

    # Always include first turn nodes (foundational concepts)
    for node in turn_nodes.get(1, []):
        selected_nodes.add(node['id'])

    # For subsequent turns, pick most connected nodes
    for turn_num in sorted(turn_nodes.keys()):
        nodes = turn_nodes[turn_num]
        if turn_num == 1:
            continue

        # Sort by connection count and pick top 2-3
        sorted_nodes = sorted(nodes, key=lambda n: node_connections[n['id']], reverse=True)

        # Pick up to 3 nodes per turn
        for node in sorted_nodes[:3]:
            selected_nodes.add(node['id'])

        # Limit total
        if len(selected_nodes) >= max_nodes:
            break

    # Filter edges to only those between selected nodes
    filtered_edges = [
        e for e in simulation['graph']['edges']
        if e['source_node_id'] in selected_nodes and e['target_node_id'] in selected_nodes
    ]

    # Build simplified simulation dict
    simplified = {
        'graph': {
            'nodes': [n for n in simulation['graph']['nodes'] if n['id'] in selected_nodes],
            'edges': filtered_edges
        },
        'turns': simulation['turns']
    }

    return generate_mermaid_tree(simplified)


def main():
    parser = argparse.ArgumentParser(
        description='Generate Mermaid tree diagram from interview simulation JSON'
    )
    parser.add_argument('json_file', help='Path to simulation JSON file')
    parser.add_argument('-o', '--output', help='Output file path (default: stdout)')
    parser.add_argument('-s', '--simplified', action='store_true',
                        help='Generate simplified version with fewer nodes')
    parser.add_argument('--max-nodes', type=int, default=30,
                        help='Maximum nodes for simplified version (default: 30)')
    parser.add_argument('--scale', type=float, default=1.0,
                        help='PNG output scale factor (default: 1.0; use 2.0 or 3.0 for higher resolution)')

    args = parser.parse_args()

    # Load simulation
    simulation = load_simulation_json(args.json_file)

    # Generate Mermaid
    if args.simplified:
        mermaid = generate_simplified_tree(simulation, args.max_nodes)
        print(f"// Simplified tree with ~{min(args.max_nodes, len(simulation['graph']['nodes']))} nodes", file=sys.stderr)
    else:
        mermaid = generate_mermaid_tree(simulation)
        print(f"// Full tree with {len(simulation['graph']['nodes'])} nodes", file=sys.stderr)

    # Output
    if args.output:
        output_path = Path(args.output)
    else:
        suffix = '_simple' if args.simplified else ''
        output_path = Path(args.json_file).with_suffix('').parent / (Path(args.json_file).stem + suffix + '.mmd')

    with open(output_path, 'w') as f:
        f.write(mermaid)
    print(f"Mermaid diagram written to: {output_path}", file=sys.stderr)

    # Render PNG via mmdc
    png_path = output_path.with_suffix('.png')
    scale = args.scale
    # Higher base height for taller boxes, width auto-scales
    result = subprocess.run(
        ['npx', '@mermaid-js/mermaid-cli', '-i', str(output_path), '-o', str(png_path),
         '-w', '3200', '-H', '2400', '-s', str(scale), '-q'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"PNG rendered to: {png_path}", file=sys.stderr)
    else:
        print(f"PNG rendering failed: {result.stderr}", file=sys.stderr)


if __name__ == '__main__':
    main()
