# Fixed Cells 10 and 11 for Observable

## Cell 11: Canonical Slot Exhaustion Heatmap (UPDATED - uses canonical slots)

```
viewof canonicalExhaustionHeatmap = {
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
  const allSignals = new Set();

  data.turns.forEach((turn, i) => {
    if (turn.node_signals) {
      Object.entries(turn.node_signals).forEach(([surfaceNodeId, signals]) => {
        if (signals && typeof signals === "object") {
          Object.keys(signals).forEach(s => allSignals.add(s));
          const score = signals["graph.node.exhaustion_score"];
          if (typeof score === "number") {
            // Map to canonical slot, skip if no mapping exists
            const canonicalName = surfaceToCanonical.get(surfaceNodeId);
            if (canonicalName) {
              exhaustionData.push({ turn: i + 1, node: canonicalName, score });
            }
          }
        }
      });
    }
  });

  if (exhaustionData.length === 0) {
    return html`<div style="font-family: system-ui; sans-serif; padding: 12px; background: #fef3c7; border-radius: 6px;">
      <strong>No exhaustion data</strong><br/>
      <small>Available signals: ${[...allSignals].join(", ")}</small><br/>
      <small>Canonical slots: ${data.canonical_graph?.slots?.length ?? 0}</small>
    </div>`;
  }

  return Plot.plot({
    title: "Canonical Slot Exhaustion Score Over Turns",
    width: 700,
    height: Math.max(200, exhaustionData.map(d => d.node).length * 30),
    marks: [
      Plot.cell(exhaustionData, { x: "turn", y: "node", fill: "score", inset: 1 })
    ],
    x: { label: "Turn" },
    y: { label: "Canonical Slot", labelAnchor: "top" },
    color: { scheme: "viridis", legend: true, label: "Score" }
  });
}
```

---

## Cell 10: Strategy Distribution Bar Chart (WORKING)

This version uses a simple horizontal bar chart showing strategy counts:

```
viewof strategyTimeline = {
  if (!data?.turns) return html`<p style="color: #888;">No data</p>`;

  const Plot = await require("@observablehq/plot@0.6");

  // Count strategies per turn
  const counts = {};
  data.turns.forEach(t => {
    const s = t.strategy_selected;
    if (s && s !== "none") {
      counts[s] = (counts[s] || 0) + 1;
    }
  });

  // Convert to array and sort by count
  const strategyData = Object.entries(counts)
    .map(([strategy, count]) => ({ strategy, count }))
    .sort((a, b) => b.count - a.count);

  if (strategyData.length === 0) {
    return html`<p style="color: #888;">No strategy data</p>`;
  }

  return Plot.plot({
    width: 700,
    height: 200,
    marginLeft: 120,
    marks: [
      Plot.barX(strategyData, {
        x: "count",
        y: "strategy",
        fill: "#6366f1",
        tip: true
      })
    ],
    x: { label: "Number of Turns" },
    y: { label: null }
  });
}
```

---

## Cell 10b: Strategy Timeline Over Turns (Dot Plot)

Shows which strategy was used each turn:

```
viewof strategyDotPlot = {
  if (!data?.turns) return html`<p style="color: #888;">No data</p>`;

  const Plot = await require("@observablehq/plot@0.6");

  const strategyData = data.turns
    .map((t, i) => ({ turn: i + 1, strategy: t.strategy_selected }))
    .filter(d => d.strategy && d.strategy !== "none");

  if (strategyData.length === 0) {
    return html`<p style="color: #888;">No strategy data</p>`;
  }

  return Plot.plot({
    width: 700,
    height: 200,
    marks: [
      Plot.dot(strategyData, {
        x: "turn",
        y: "strategy",
        fill: "strategy",
        r: 6,
        tip: true
      })
    ],
    x: { label: "Turn Number" },
    y: { label: null },
    color: { legend: true }
  });
}
```

---

## Cell 11: Node Exhaustion Heatmap (WORKING)

```
viewof nodeHeatmap = {
  if (!data?.turns) return html`<p style="color: #888;">No data</p>`;

  const Plot = await require("@observablehq/plot@0.6");

  const exhaustionData = [];

  data.turns.forEach((turn, i) => {
    if (turn.node_signals) {
      Object.entries(turn.node_signals).forEach(([nodeId, signals]) => {
        if (signals && typeof signals === "object") {
          const score = signals["graph.node.exhaustion_score"];
          if (typeof score === "number") {
            const node = data.graph?.nodes?.find(n => n.id === nodeId);
            const label = node?.label ?? nodeId.slice(0, 12);
            exhaustionData.push({ turn: i + 1, node: label, score });
          }
        }
      });
    }
  });

  if (exhaustionData.length === 0) {
    return html`<div style="padding: 16px; background: #fffbeb; border-radius: 8px;">
      <strong style="color: #92400e;">No exhaustion data found</strong>
      <p style="color: #78716c; margin-top: 8px;">
        Looking for <code>graph.node.exhaustion_score</code> in node_signals
      </p>
    </div>`;
  }

  return Plot.plot({
    width: 700,
    height: Math.max(200, exhaustionData.map(d => d.node).length * 30),
    marks: [
      Plot.cell(exhaustionData, {
        x: "turn",
        y: "node",
        fill: "score",
        inset: 1
      })
    ],
    x: { label: "Turn" },
    y: { label: "Node" },
    color: {
      scheme: "viridis",
      legend: true,
      label: "Exhaustion Score"
    }
  });
}
```

---

## Cell 11b: Debug - Check Available Node Signals

```
viewof nodeSignalDebug = {
  if (!data?.turns) return html`<p style="color: #888;">No data</p>`;

  const allSignals = new Set();
  const sampleNodeSignals = {};

  data.turns.forEach((turn, i) => {
    if (turn.node_signals) {
      Object.entries(turn.node_signals).forEach(([nodeId, signals]) => {
        if (signals && typeof signals === "object") {
          Object.keys(signals).forEach(s => allSignals.add(s));
          if (!sampleNodeSignals[nodeId]) {
            sampleNodeSignals[nodeId] = signals;
          }
        }
      });
    }
  });

  return html`<div style="padding: 16px; background: #f8fafc; border-radius: 8px;">
    <h3 style="margin-top: 0;">Node Signals Debug</h3>
    <p><strong>Total signals found:</strong> ${allSignals.size}</p>
    <p><strong>Signal names:</strong></p>
    <ul style="column-count: 2;">
      ${[...allSignals].map(s => html`<li><code>${s}</code></li>`)}
    </ul>
    <p><strong>Sample node signals (first 3 nodes):</strong></p>
    <pre style="background: white; padding: 8px; border-radius: 4px; overflow: auto;">${JSON.stringify(Object.fromEntries(
      Object.entries(sampleNodeSignals).slice(0, 3)
    ), null, 2)}</pre>
  </div>`;
}
```
