## Cell 11: Node Exhaustion Heatmap (Surface nodes with canonical labels)

```
viewof nodeHeatmap = {
  if (!data?.turns) return html`<p style="color: #888;">No data</p>`;
  const Plot = await require("@observablehq/plot@0.6");

  // Build mapping from surface_node_id -> canonical_slot_name
  const surfaceToCanonical = new Map();
  if (data.canonical_graph?.slots) {
    data.canonical_graph.slots.forEach(slot => {
      slot.surface_node_ids.forEach(surfaceId => {
        surfaceToCanonical.set(surfaceId, slot.slot_name);
      });
    });
  }

  const exhaustionData = [];

  data.turns.forEach((turn, i) => {
    if (turn.node_signals) {
      Object.entries(turn.node_signals).forEach(([surfaceNodeId, signals]) => {
        const score = signals?.["graph.node.exhaustion_score"];
        if (typeof score === "number" && score > 0) {
          // Use canonical name if available, otherwise surface node label
          const canonicalName = surfaceToCanonical.get(surfaceNodeId);
          const node = data.graph?.nodes?.find(n => n.id === surfaceNodeId);
          const label = canonicalName ?? node?.label?.slice(0, 40) ?? surfaceNodeId.slice(0, 20);
          exhaustionData.push({ turn: i + 1, node: label, score, isCanonical: !!canonicalName });
        }
      });
    }
  });

  if (exhaustionData.length === 0) {
    return html`<div style="padding: 12px; background: #fef3c7; border-radius: 6px;">
      <strong>No exhaustion data found</strong>
    </div>`;
  }

  return Plot.plot({
    title: "Node Exhaustion Score Over Turns (canonical names where available)",
    width: 700,
    height: Math.max(20, exhaustionData.map(d => d.node).length * 3),
    marks: [
      Plot.cell(exhaustionData, { x: "turn", y: "node", fill: "score", inset: 1 })
    ],
    x: { label: "Turn" },
    y: { label: "Node / Canonical Slot", labelAnchor: "top" },
    color: { scheme: "viridis", legend: true, label: "Score" }
  });
}
```

**How it works:**
1. Shows ALL nodes with exhaustion > 0 (not just canonical)
2. Uses canonical slot name when available (e.g., "online_community")
3. Falls back to surface node label when no canonical mapping exists
4. Filters out nodes with score = 0 for cleaner visualization
