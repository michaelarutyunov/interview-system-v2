# Interview System Visualization - Observable Notebook Template

Copy each cell below into a new Observable notebook at https://observablehq.com/

---

## Cell 1: JSON File Input

```
viewof input = Inputs.file({
  label: "Upload Interview JSON",
  accept: ".json",
  multiple: false
})
```

---

## Cell 2: Parse JSON

```
data = input ? JSON.parse(await input.text()) : null
```

---

## Cell 3: Metadata Display

```
viewof metadata = {
  if (!data) return html`<p style="color: #888;">Upload a JSON file to see metadata</p>`;
  const meta = data.metadata;
  return html`<div style="font-family: system-ui; sans-serif;">
    <h2>Interview Metadata</h2>
    <table style="border-collapse: collapse; width: 100%;">
      <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Concept</strong></td><td style="padding: 8px; border: 1px solid #ddd;">${meta.concept_name}</td></tr>
      <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Methodology</strong></td><td style="padding: 8px; border: 1px solid #ddd;">${meta.methodology}</td></tr>
      <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Persona</strong></td><td style="padding: 8px; border: 1px solid #ddd;">${meta.persona_name}</td></tr>
      <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Total Turns</strong></td><td style="padding: 8px; border: 1px solid #ddd;">${meta.total_turns}</td></tr>
      <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Status</strong></td><td style="padding: 8px; border: 1px solid #ddd;">${meta.status}</td></tr>
      <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Session ID</strong></td><td style="padding: 8px; border: 1px solid #ddd; font-family: monospace; font-size: 0.8em;">${meta.session_id}</td></tr>
    </table>
  </div>`;
}
```

---

## Cell 4: Graph Summary

```
viewof graphSummary = {
  if (!data) return html`<p style="color: #888;">No data</p>`;
  const nodes = data.graph?.nodes ?? [];
  const edges = data.graph?.edges ?? [];
  const slots = data.canonical_graph?.slots ?? [];
  const canonicalEdges = data.canonical_graph?.edges ?? [];
  const nodesByType = data.graph?.summary?.nodes_by_type ?? {};
  const slotsByType = data.canonical_graph?.summary?.slots_by_type ?? {};

  return html`<div style="font-family: system-ui; sans-serif;">
    <h2>Graph Summary</h2>
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
      <div style="border: 1px solid #ddd; padding: 16px; border-radius: 8px;">
        <h3>Surface Graph</h3>
        <p><strong>${nodes.length}</strong> nodes, <strong>${edges.length}</strong> edges</p>
        ${Object.entries(nodesByType).map(([type, count]) =>
          html`<p style="margin: 4px 0;">${type}: ${count}</p>`
        )}
      </div>
      <div style="border: 1px solid #ddd; padding: 16px; border-radius: 8px;">
        <h3>Canonical Graph</h3>
        <p><strong>${slots.length}</strong> slots, <strong>${canonicalEdges.length}</strong> edges</p>
        ${Object.entries(slotsByType).map(([type, count]) =>
          html`<p style="margin: 4px 0;">${type}: ${count}</p>`
        )}
      </div>
    </div>
  </div>`;
}
```

---

## Cell 5: Node Type Colors

```
nodeTypeColors = ({
  job_trigger: "#ef4444",
  pain_point: "#f97316",
  gain_point: "#22c55e",
  solution_approach: "#3b82f6",
  job_to_be_done: "#8b5cf6",
  context: "#6b7280",
  outcome: "#ec4899",
  barrier: "#eab308",
  unknown: "#9ca3af"
})
```

---

## Cell 6: Graph Data for D3

```
graphData = {
  if (!data) return null;
  const nodes = data.graph?.nodes ?? [];
  const edges = data.graph?.edges ?? [];

  const nodeById = new Map(nodes.map(n => [n.id, { ...n }]));
  const links = edges
    .filter(e => nodeById.has(e.source_node_id) && nodeById.has(e.target_node_id))
    .map(e => ({
      source: nodeById.get(e.source_node_id),
      target: nodeById.get(e.target_node_id),
      edge_type: e.edge_type
    }));

  return ({ nodes: Array.from(nodeById.values()), links });
}
```

---

## Cell 7: Force-Directed Graph

```
viewof graph = {
  if (!graphData) return html`<p style="color: #888;">Upload JSON to see graph</p>`;
  const d3 = await require("d3@7", "d3-force@3");

  const width = 800;
  const height = 600;
  const svg = d3.create("svg")
    .attr("viewBox", [0, 0, width, height])
    .attr("style", "max-width: 100%; height: auto; font: 12px system-ui, sans-serif;");

  const g = svg.append("g");

  const zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on("zoom", (event) => g.attr("transform", event.transform));
  svg.call(zoom);

  const simulation = d3.forceSimulation(graphData.nodes)
    .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(100))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(30));

  svg.append("defs").selectAll("marker")
    .data(["causes", "enables", "prevents", "solution_for"])
    .join("marker")
    .attr("id", d => `arrow-${d}`)
    .attr("viewBox", "0 0 10 10")
    .attr("refX", 25)
    .attr("refY", 5)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M 0 0 L 10 5 L 0 10 z")
    .attr("fill", "#999");

  const link = g.append("g")
    .attr("stroke", "#999")
    .attr("stroke-opacity", 0.6)
    .selectAll("line")
    .data(graphData.links)
    .join("line")
    .attr("stroke-width", 1.5)
    .attr("marker-end", d => d.edge_type ? `url(#arrow-${d.edge_type})` : null);

  const node = g.append("g")
    .attr("stroke", "#fff")
    .attr("stroke-width", 1.5)
    .selectAll("circle")
    .data(graphData.nodes)
    .join("circle")
    .attr("r", 12)
    .attr("fill", d => nodeTypeColors[d.node_type] ?? nodeTypeColors.unknown)
    .attr("cursor", "pointer")
    .call(drag(simulation));

  const label = g.append("g")
    .selectAll("text")
    .data(graphData.nodes)
    .join("text")
    .text(d => d.label.length > 25 ? d.label.slice(0, 25) + "..." : d.label)
    .attr("font-size", 10)
    .attr("dx", 16)
    .attr("dy", 4)
    .style("pointer-events", "none")
    .style("text-shadow", "1px 1px 0 #fff, -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff");

  node.append("title")
    .text(d => `${d.label}\nType: ${d.node_type}\nConfidence: ${d.confidence}`);

  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node
      .attr("cx", d => d.x)
      .attr("cy", d => d.y);

    label
      .attr("x", d => d.x)
      .attr("y", d => d.y);
  });

  function drag(simulation) {
    function dragstarted(event) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);
  }

  return svg.node();
}
```

---

## Cell 8: Turns Table

```
viewof turnsTable = {
  if (!data?.turns) return html`<p style="color: #888;">No turns data</p>`;
  const tableData = data.turns.map((t, i) => ({
    turn: t.turn_number + 1,
    strategy: t.strategy_selected ?? "-",
    signals: t.signals ? Object.keys(t.signals).length : 0,
    nodes: t.extraction_summary?.nodes_added ?? 0,
    edges: t.extraction_summary?.edges_added ?? 0,
    question: t.question?.slice(0, 80) + (t.question?.length > 80 ? "..." : ""),
    response: t.response?.slice(0, 80) + (t.response?.length > 80 ? "..." : "")
  }));

  return Inputs.table(tableData, {
    columns: [
      "turn", "strategy", "signals", "nodes", "edges",
      { label: "question", value: d => d.question },
      { label: "response", value: d => d.response }
    ],
    rows: 10
  });
}
```

---

## Cell 9: Signal Evolution Chart

```
viewof signalChart = {
  if (!data?.turns) return html`<p style="color: #888;">No data</p>`;
  const Plot = await require("@observablehq/plot@0.6");

  const signalValues = [];
  const signalNames = new Set();

  data.turns.forEach((turn, i) => {
    if (turn.signals) {
      Object.entries(turn.signals).forEach(([key, value]) => {
        if (typeof value === "number") {
          signalNames.add(key);
          signalValues.push({ turn: i + 1, signal: key, value });
        }
      });
    }
  });

  // Filter out high-scale signals (node_count, edge_count, etc.)
  const excludeSignals = ["node_count", "edge_count", "total_nodes", "total_edges"];
  const filteredNames = [...signalNames].filter(s => !excludeSignals.some(excl => s.toLowerCase().includes(excl)));
  const topSignals = filteredNames.slice(0, 8);
  const filteredValues = signalValues.filter(d => topSignals.includes(d.signal));

  if (filteredValues.length === 0) {
    return html`<p style="color: #888;">No numeric signals found</p>`;
  }

  return Plot.plot({
    width: 700,
    height: 400,
    marks: [
      Plot.line(filteredValues, { x: "turn", y: "value", stroke: "signal", strokeWidth: 2 }),
      Plot.dot(filteredValues, { x: "turn", y: "value", fill: "signal", r: 3 })
    ],
    x: { label: "Turn Number" },
    y: { label: "Signal Value", grid: true },
    color: { legend: true, columns: 2 },
    style: { fontFamily: "system-ui, sans-serif" }
  });
}
```

---

## Cell 10: Strategy Timeline (Dot Plot)

```
viewof strategyTimeline = {
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
        r: 8,
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

## Cell 10b: Strategy Counts (Debug)

```
viewof strategyCounts = {
  if (!data?.turns) return html`<p style="color: #888;">No data</p>`;

  const counts = {};
  data.turns.forEach(t => {
    const s = t.strategy_selected ?? "none";
    if (s !== "none" && s !== null) {
      counts[s] = (counts[s] || 0) + 1;
    }
  });

  return html`
    <div style="font-family: system-ui; sans-serif; padding: 12px; background: #f9fafb; border-radius: 8px;">
      <strong>Strategy Distribution:</strong><br/>
      ${Object.entries(counts).map(([k, v]) => `${k}: ${v}`).join(" | ")}
    </div>
  `;
}
```

---

## Cell 11: Node Exhaustion Heatmap

```
viewof nodeHeatmap = {
  if (!data?.turns) return html`<p style="color: #888;">No data</p>`;
  const Plot = await require("@observablehq/plot@0.6");

  const heatmapData = [];
  const allSignals = new Set();

  data.turns.forEach((turn, i) => {
    if (turn.node_signals) {
      Object.entries(turn.node_signals).forEach(([nodeId, signals]) => {
        const node = data.graph?.nodes?.find(n => n.id === nodeId);
        const nodeLabel = node?.label ?? nodeId.slice(0, 12);

        if (typeof signals === "object" && signals !== null) {
          Object.entries(signals).forEach(([signalKey, value]) => {
            allSignals.add(signalKey);
            if (typeof value === "number" && !isNaN(value)) {
              heatmapData.push({ turn: i + 1, node: nodeLabel, signal: signalKey, value });
            }
          });
        }
      });
    }
  });

  if (heatmapData.length === 0) {
    return html`<p style="color: #888;">No node signal data found</p>`;
  }

  // Use the correct signal name: graph.node.exhaustion_score
  const exhaustionData = heatmapData.filter(d => d.signal === "graph.node.exhaustion_score");

  if (exhaustionData.length > 0) {
    return Plot.plot({
      title: "Node Exhaustion Score Over Turns",
      width: 700,
      height: Math.max(200, exhaustionData.map(d => d.node).length * 30),
      marks: [
        Plot.cell(exhaustionData, { x: "turn", y: "node", fill: "value", inset: 1 })
      ],
      x: { label: "Turn" },
      y: { label: "Node", labelAnchor: "top" },
      color: { scheme: "viridis", legend: true, label: "Score" },
      style: { fontFamily: "system-ui, sans-serif" }
    });
  }

  return html`<div style="font-family: system-ui; sans-serif;">
    <p style="color: #888;">Node signals found, but no exhaustion_score data.</p>
    <p style="font-size: 0.9em;">Available signals: ${[...allSignals].join(", ")}</p>
  </div>`;
}
```

---

## Cell 12: Full Transcript

```
viewof transcript = {
  if (!data?.turns) return html`<p style="color: #888;">No transcript data</p>`;
  return html`<div style="font-family: system-ui; sans-serif;">
    <details open>
      <summary style="cursor: pointer; padding: 8px; background: #f3f4f6; border-radius: 4px;">
        <strong>Full Transcript (${data.turns.length} turns)</strong>
      </summary>
      <div style="margin-top: 16px; max-height: 600px; overflow-y: auto;">
        ${data.turns.map((t, i) => html`
          <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #e5e7eb;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <strong style="color: #3b82f6;">Turn ${t.turn_number + 1}</strong>
              <span style="color: #6b7280; font-size: 0.875rem;">
                Strategy: ${t.strategy_selected ?? "N/A"}
              </span>
            </div>
            <div style="margin-bottom: 8px;">
              <strong>Q:</strong>
              <p style="margin: 4px 0 0 16px; color: #374151;">${t.question}</p>
            </div>
            <div>
              <strong>A:</strong>
              <p style="margin: 4px 0 0 16px; color: #374151;">${t.response}</p>
            </div>
            ${t.signals ? html`
              <details style="margin-top: 8px;">
                <summary style="cursor: pointer; color: #6b7280; font-size: 0.875rem;">
                  Signals (${Object.keys(t.signals).length})
                </summary>
                <div style="margin-left: 16px; font-size: 0.75rem; color: #6b7280;">
                  ${Object.entries(t.signals).map(([k, v]) =>
                    html`<span style="margin-right: 12px;">${k}: ${JSON.stringify(v)}</span>`
                  )}
                </div>
              </details>
            ` : ""}
          </div>
        `)}
      </div>
    </details>
  </div>`;
}
```

---

## Cell 13: Legend

```
viewof legend = {
  return html`
    <div style="font-family: system-ui; sans-serif; padding: 16px; background: #f9fafb; border-radius: 8px;">
      <h3>Node Type Legend</h3>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px;">
        ${Object.entries(nodeTypeColors).map(([type, color]) => html`
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 16px; height: 16px; border-radius: 50%; background: ${color};"></span>
            <span style="font-size: 0.875rem;">${type}</span>
          </div>
        `)}
      </div>
    </div>
  `;
}
```

---

## Cell 14: Dashboard View (Combined - No Code Visible)

```
viewof dashboard = {
  if (!data) return html`<p style="color: #888;">Upload JSON to see dashboard</p>`;
  return html`
    <div style="font-family: system-ui; sans-serif; padding: 20px; max-width: 1400px; margin: 0 auto;">
      <h1 style="margin-bottom: 24px;">Interview Analysis Dashboard</h1>

      <!-- Metadata and Legend Row -->
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 24px;">
        <div style="border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px; background: white;">
          <h2 style="margin-top: 0;">${data.metadata.concept_name}</h2>
          <p><strong>Persona:</strong> ${data.metadata.persona_name}</p>
          <p><strong>Methodology:</strong> ${data.metadata.methodology}</p>
          <p><strong>Turns:</strong> ${data.metadata.total_turns} | <strong>Status:</strong> ${data.metadata.status}</p>
        </div>
        ${legend}
      </div>

      <!-- Strategy Counts (Debug) -->
      ${strategyCounts}

      <!-- Graph Section -->
      <div style="border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px; margin-bottom: 24px; background: white;">
        <h2 style="margin-top: 0;">Knowledge Graph</h2>
        ${graph}
      </div>

      <!-- Charts Row -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
        <div style="border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px; background: white;">
          <h3 style="margin-top: 0;">Strategy Timeline</h3>
          ${strategyTimeline}
        </div>
        <div style="border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px; background: white;">
          <h3 style="margin-top: 0;">Signal Evolution</h3>
          ${signalChart}
        </div>
      </div>

      <!-- Node Heatmap -->
      <div style="border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px; margin-bottom: 24px; background: white;">
        <h3 style="margin-top: 0;">Node Exhaustion Over Time</h3>
        ${nodeHeatmap}
      </div>

      <!-- Transcript -->
      <div style="border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px; background: white;">
        <h3 style="margin-top: 0;">Full Transcript</h3>
        ${transcript}
      </div>
    </div>
  `;
}
```

---

## How to Hide Cell Code in Observable

1. **Collapse individual cells**: Click the cell name (left side) to toggle code visibility
2. **Use the dashboard cell**: Cell 14 combines all visualizations in one clean view
3. **Publish mode**: When you publish/share, cell code is hidden by default
```

---

## Key Changes

All `viewof` cells now explicitly `return` their HTML/DOM elements. This is required in Observable blocks.

---

## How to Use

1. Go to https://observablehq.com/
2. Create a new notebook
3. Copy each cell content (inside code blocks) into Observable
4. Upload any interview JSON from `synthetic_interviews/`
5. Explore the visualizations!
