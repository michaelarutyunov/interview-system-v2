"""
Semantic Deduplication Experiment for Knowledge Graph Nodes

Tests semantic similarity-based deduplication on real interview data.
Uses sentence embeddings to identify duplicate concepts with different phrasings.

INSTRUCTIONS FOR GOOGLE COLAB:
1. Create new notebook
2. Paste this entire file into ONE cell
3. Run
4. Download 2 output files

OUTPUT: Deduplication analysis showing which nodes should be merged,
with metrics on how much this reduces node count and improves graph quality.
"""

# ============================================
# STEP 1: Install
# ============================================
print("=" * 80)
print("INSTALLING...")
print("=" * 80)

import subprocess
import sys

print("Installing sentence-transformers...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "sentence-transformers"])

print("\n" + "=" * 80)
print("✓ INSTALLED")
print("=" * 80 + "\n")

# ============================================
# STEP 2: Import and Load
# ============================================
print("=" * 80)
print("LOADING...")
print("=" * 80)

import json
import numpy as np
from dataclasses import dataclass
from typing import List
from collections import defaultdict, deque

try:
    from google.colab import files
    print("✓ Google Colab detected")
except ImportError:
    print("⚠ Not in Colab - files saved locally")
    class DummyFiles:
        def download(self, f):
            print(f"  Saved: {f}")
    files = DummyFiles()

from sentence_transformers import SentenceTransformer, util

print("Loading sentence embedding model (all-MiniLM-L6-v2)...")
model = SentenceTransformer('all-MiniLM-L6-v2')

print("\n" + "=" * 80)
print("✓ READY")
print("=" * 80)
print("Model: all-MiniLM-L6-v2 (384-dim embeddings)")
print("Method: Cosine similarity for semantic matching")
print()

# ============================================
# STEP 3: Data (From Real Session)
# ============================================

# Real nodes from session 5d2e7092-af8b-4655-916a-9935aba6cad7
# 68 nodes extracted from interview about oat milk preferences
NODES = [
    {"id": "3e035ebe-8e23-4ca8-ae45-12d75ab0f4a3", "label": "minimal ingredients", "node_type": "attribute"},
    {"id": "e821e47a-417b-42c1-94ae-4f8037018b9b", "label": "no added oils", "node_type": "attribute"},
    {"id": "720c91cc-450c-4c67-9d24-6f10db00c018", "label": "low sugar content", "node_type": "attribute"},
    {"id": "3894828f-82c3-40c6-a930-9f87bdc39531", "label": "no weird additives or gums", "node_type": "attribute"},
    {"id": "b56b69ac-a837-4f3e-884c-4ace11dacc23", "label": "healthier alternative", "node_type": "functional_consequence"},
    {"id": "6d22179f-d58c-45c1-8b5a-3d6da2a2ba97", "label": "avoid added oils", "node_type": "instrumental_value"},
    {"id": "1c0b8060-604f-4c5e-805b-a208a6e4267c", "label": "excessive sugar in alternatives", "node_type": "attribute"},
    {"id": "cf2fb77f-a0cb-4085-898a-895cdc5c7abe", "label": "avoiding oils and additives", "node_type": "attribute"},
    {"id": "e0429b07-57d9-4c22-8025-e4e6d89ba4d7", "label": "processed ingredients", "node_type": "attribute"},
    {"id": "20a02fc9-c282-4d55-973b-2820f2676afc", "label": "can cause inflammation in the body", "node_type": "functional_consequence"},
    {"id": "34d82b76-1912-40f6-97c9-da13648bc0a0", "label": "feel better", "node_type": "psychosocial_consequence"},
    {"id": "cc5fd363-716f-4af4-8908-89820d9ad165", "label": "cleaner foods", "node_type": "attribute"},
    {"id": "41c84453-821f-4e14-9391-c42c87562b33", "label": "better digestion", "node_type": "functional_consequence"},
    {"id": "490f03c6-e7bb-408e-b904-9d5ad015d7c5", "label": "being mindful about what I'm putting into my body", "node_type": "instrumental_value"},
    {"id": "5ff5e713-6097-4fc9-bb67-d6908deda503", "label": "long-term health", "node_type": "terminal_value"},
    {"id": "285e4b9c-6b8f-4caf-927b-0e4e29411184", "label": "being intentional with what I put into my body", "node_type": "instrumental_value"},
    {"id": "3c7edb3d-87cf-4148-af3e-d63a09089adf", "label": "affect my energy levels", "node_type": "functional_consequence"},
    {"id": "ef4cdc22-35f3-485d-9251-594f0b7e7c5a", "label": "affect my gut health", "node_type": "functional_consequence"},
    {"id": "65652292-f892-4e86-9a68-7f434f899f21", "label": "how I age down the line", "node_type": "psychosocial_consequence"},
    {"id": "4d184b1e-593b-4e24-b5ee-256c8a86d30f", "label": "whole, minimally processed foods", "node_type": "attribute"},
    {"id": "e2789588-ee62-4b91-b670-4478305efc67", "label": "ingredients I can actually recognize and pronounce", "node_type": "attribute"},
    {"id": "5431ee81-ebe6-415a-9966-956c21660b88", "label": "being mindful", "node_type": "instrumental_value"},
    {"id": "56f1323d-e8e0-4f39-9acf-1e27781be098", "label": "treat it well", "node_type": "instrumental_value"},
    {"id": "7e525afe-0fe9-4b4b-9480-68a73d7294f8", "label": "my body is going to be with me for hopefully a long time", "node_type": "terminal_value"},
    {"id": "7f08213e-8e79-4d90-b920-315695087565", "label": "I only get one body", "node_type": "instrumental_value"},
    {"id": "36af4ec1-e322-4dbd-8269-df37fb0ce621", "label": "want it to last", "node_type": "terminal_value"},
    {"id": "6ed1d334-12a6-47d0-bab9-36d08b5c80b1", "label": "difference in energy levels", "node_type": "functional_consequence"},
    {"id": "f876bc6d-50e9-4bbd-8b2d-bf7718a40fa7", "label": "overall how I feel", "node_type": "psychosocial_consequence"},
    {"id": "136d1f78-9713-45e1-a5c8-6d767502e2db", "label": "putting good things in versus processed stuff", "node_type": "instrumental_value"},
    {"id": "7b58a7d6-b276-450a-9809-a173d95781f1", "label": "mom dealt with health issues", "node_type": "psychosocial_consequence"},
    {"id": "5a771079-899d-4934-bbe2-91cca8dc6f8a", "label": "could've been prevented with better nutrition", "node_type": "functional_consequence"},
    {"id": "73b8bd1e-b0f6-471c-a58a-0b6eb832b01b", "label": "being proactive now", "node_type": "instrumental_value"},
    {"id": "2bb5bb0b-0c9b-48e3-895d-7285ada49f21", "label": "avoiding problems later", "node_type": "terminal_value"},
    {"id": "36cb7938-1da6-4c95-b962-810f2f1e4eb0", "label": "making intentional choices", "node_type": "instrumental_value"},
    {"id": "652f4e27-ba1e-4a1c-a1eb-c7a47811ce0b", "label": "plant-based", "node_type": "attribute"},
    {"id": "c2290692-aa49-4739-b149-1625967aa55b", "label": "easier on my digestive system", "node_type": "functional_consequence"},
    {"id": "e66f968e-44ce-412b-b74d-b06dc65f610f", "label": "has fiber", "node_type": "attribute"},
    {"id": "5a2d74e9-66b6-4923-be2f-8ecf753d3214", "label": "good for gut health", "node_type": "functional_consequence"},
    {"id": "fb6de899-38eb-4196-acc9-b95e7056695b", "label": "avoiding the hormones and antibiotics", "node_type": "functional_consequence"},
    {"id": "86b0aa7a-3b91-4f5d-beca-f271e3ff8295", "label": "daily decisions that add up", "node_type": "instrumental_value"},
    {"id": "5e71c308-7b49-46db-a70e-b5564135adab", "label": "preventing issues before they start", "node_type": "instrumental_value"},
    {"id": "dbbff737-f482-48bf-84e4-b430b20c904e", "label": "fortified with vitamins D and B12", "node_type": "attribute"},
    {"id": "c4206fd3-9699-4d0f-bf91-51364b6cb5d7", "label": "nourishing my body", "node_type": "psychosocial_consequence"},
    {"id": "ebe38f53-7db6-4928-827d-2dd5597a8e83", "label": "being intentional about what I'm putting into my body", "node_type": "instrumental_value"},
    {"id": "d73b01fa-8fdf-41a1-b99b-370b2ead8537", "label": "sustained energy throughout the day", "node_type": "functional_consequence"},
    {"id": "e026f74a-0aec-48d7-a32a-e9eb0467cec3", "label": "support my immune system", "node_type": "functional_consequence"},
    {"id": "362bd4de-b809-42d5-8774-6e7c3f4a0a70", "label": "whole ingredients that my body can actually recognize and use", "node_type": "attribute"},
    {"id": "731e2cf9-9672-4c37-8989-d112add6a70a", "label": "not empty calories", "node_type": "attribute"},
    {"id": "9f680ddc-2877-4e94-bfdb-38c7aa7aa31b", "label": "not processed stuff", "node_type": "attribute"},
    {"id": "66e7f426-944f-4f47-ba72-1023c69dae3b", "label": "feel good from the inside out", "node_type": "psychosocial_consequence"},
    {"id": "6f44d2b8-6d75-4cc4-983f-c1e919040666", "label": "feeling sluggish", "node_type": "functional_consequence"},
    {"id": "e064c817-3915-459f-b923-e215481b8efd", "label": "more energy to get through my day", "node_type": "functional_consequence"},
    {"id": "ccf0e73a-c7e6-4371-90f4-775eeeeeef39", "label": "not dealing with afternoon crash", "node_type": "functional_consequence"},
    {"id": "84fe26b0-e01d-42f4-b32d-78f608ac6583", "label": "not feeling sluggish", "node_type": "functional_consequence"},
    {"id": "6ddda529-94c8-4e22-acba-edcd13735611", "label": "can actually focus at work", "node_type": "functional_consequence"},
    {"id": "46d93088-e6bc-4dae-8979-5923726b120f", "label": "have energy to hit the gym", "node_type": "functional_consequence"},
    {"id": "093b27ba-6378-4c86-af03-c672c6fa3eb2", "label": "have energy to meet up with friends", "node_type": "functional_consequence"},
    {"id": "f2b913c9-9287-465d-9a04-4d9e4e2290d8", "label": "everything else just flows better", "node_type": "psychosocial_consequence"},
    {"id": "56bc5843-5b13-4006-a6dd-1aa1ea7c479e", "label": "feeling good", "node_type": "psychosocial_consequence"},
    {"id": "e3e4a244-8882-446c-a2a2-194478143b65", "label": "digestion working smoothly", "node_type": "functional_consequence"},
    {"id": "0faa51be-9950-4a2f-9814-d30e85933d44", "label": "more energy throughout the day", "node_type": "functional_consequence"},
    {"id": "bb20878e-b60c-4490-8005-92cf3e7554cc", "label": "not feeling bloated or sluggish", "node_type": "functional_consequence"},
    {"id": "94baa6e7-8cfd-4cb7-9718-151d6e8e4162", "label": "better workouts", "node_type": "functional_consequence"},
    {"id": "e7e353fe-8df2-4112-9e54-9eb9b692b304", "label": "better focus at work", "node_type": "functional_consequence"},
    {"id": "10dd8037-9b22-4a36-a1fc-d052d9ea8e9c", "label": "better mood", "node_type": "psychosocial_consequence"},
    {"id": "819154cf-a365-460e-a51f-a35483525d28", "label": "gut health connected to immunity and inflammation", "node_type": "functional_consequence"},
    {"id": "3db81f45-c7c0-451f-95cd-dcc388892846", "label": "keeping things regular", "node_type": "functional_consequence"},
    {"id": "e1581c72-ad88-46c7-aacf-3e556b60e791", "label": "foundational for overall wellness", "node_type": "instrumental_value"}
]

SESSION_ID = "5d2e7092-af8b-4655-916a-9935aba6cad7"

print(f"Loaded {len(NODES)} nodes from session {SESSION_ID[:8]}...")

# ============================================
# STEP 4: Analysis Functions
# ============================================

@dataclass
class DuplicateCluster:
    """Group of semantically similar nodes"""
    representative: dict  # The node to keep
    duplicates: List[dict]  # Nodes to merge into representative
    similarity_scores: List[float]  # Similarity score for each duplicate

    @property
    def size(self):
        return len(self.duplicates) + 1  # Include representative

    @property
    def node_savings(self):
        return len(self.duplicates)  # How many nodes we'd eliminate

def has_negation(text: str) -> bool:
    """Check if text contains negation words"""
    negation_words = {'not', 'no', "don't", "doesn't", "didn't", "won't", "can't",
                     "isn't", "aren't", "wasn't", "weren't", "never", "neither"}
    words = text.lower().split()
    return any(word in negation_words for word in words)

def are_opposite_polarity(label1: str, label2: str) -> bool:
    """Check if two labels have opposite polarity (one negated, one not)"""
    neg1 = has_negation(label1)
    neg2 = has_negation(label2)
    return neg1 != neg2  # One has negation, other doesn't

def compute_embeddings(nodes: List[dict]) -> np.ndarray:
    """Compute embeddings for all node labels"""
    labels = [node['label'] for node in nodes]
    embeddings = model.encode(labels, convert_to_numpy=True, show_progress_bar=True)
    return embeddings

def find_duplicate_clusters(nodes: List[dict], embeddings: np.ndarray,
                           threshold: float = 0.85,
                           same_type_only: bool = True) -> List[DuplicateCluster]:
    """
    Find clusters of semantically similar nodes.

    Args:
        nodes: List of node dictionaries
        embeddings: Precomputed embeddings
        threshold: Cosine similarity threshold (0.0-1.0)
        same_type_only: Only cluster nodes of the same type

    Returns:
        List of duplicate clusters
    """
    n = len(nodes)
    clusters = []
    assigned = set()  # Track which nodes are already in a cluster

    # Compute pairwise similarities
    similarities = util.cos_sim(embeddings, embeddings).numpy()

    for i in range(n):
        if i in assigned:
            continue

        # Find all nodes similar to node i
        duplicates = []
        scores = []

        for j in range(i + 1, n):
            if j in assigned:
                continue

            # Check type constraint
            if same_type_only and nodes[i]['node_type'] != nodes[j]['node_type']:
                continue

            # Check similarity
            sim = similarities[i][j]
            if sim >= threshold:
                duplicates.append(nodes[j])
                scores.append(float(sim))
                assigned.add(j)

        # Create cluster if we found duplicates
        if duplicates:
            cluster = DuplicateCluster(
                representative=nodes[i],
                duplicates=duplicates,
                similarity_scores=scores
            )
            clusters.append(cluster)
            assigned.add(i)

    # Sort by cluster size (largest first)
    clusters.sort(key=lambda c: c.size, reverse=True)

    return clusters

def find_duplicate_clusters_connected_components(
        nodes: List[dict],
        embeddings: np.ndarray,
        threshold: float = 0.85,
        same_type_only: bool = True,
        check_negation: bool = True) -> List[DuplicateCluster]:
    """
    Find clusters using connected components (transitive closure).

    More thorough than greedy approach - finds all transitively connected nodes.
    Example: If A→B and B→C, creates cluster {A, B, C} even if A-C < threshold.

    Args:
        nodes: List of node dictionaries
        embeddings: Precomputed embeddings
        threshold: Cosine similarity threshold
        same_type_only: Only cluster nodes of same type
        check_negation: Filter out opposite-polarity pairs (e.g., "X" vs "not X")

    Returns:
        List of duplicate clusters
    """
    n = len(nodes)
    similarities = util.cos_sim(embeddings, embeddings).numpy()

    # Build adjacency graph
    graph = defaultdict(set)
    for i in range(n):
        for j in range(i + 1, n):
            # Check type constraint
            if same_type_only and nodes[i]['node_type'] != nodes[j]['node_type']:
                continue

            # Check similarity
            if similarities[i][j] < threshold:
                continue

            # Check negation polarity
            if check_negation and are_opposite_polarity(nodes[i]['label'], nodes[j]['label']):
                continue

            # Add edge
            graph[i].add(j)
            graph[j].add(i)

    # Find connected components using BFS
    visited = set()
    clusters = []

    for start in range(n):
        if start in visited:
            continue

        # BFS to find connected component
        component = []
        queue = deque([start])

        while queue:
            node_idx = queue.popleft()
            if node_idx in visited:
                continue

            visited.add(node_idx)
            component.append(node_idx)

            # Add unvisited neighbors
            for neighbor in graph[node_idx]:
                if neighbor not in visited:
                    queue.append(neighbor)

        # Create cluster if component has multiple nodes
        if len(component) > 1:
            # Choose representative: longest label (most specific)
            rep_idx = max(component, key=lambda i: len(nodes[i]['label']))
            representative = nodes[rep_idx]

            # Gather duplicates and their similarity scores to representative
            duplicates = []
            scores = []
            for idx in component:
                if idx != rep_idx:
                    duplicates.append(nodes[idx])
                    scores.append(float(similarities[rep_idx][idx]))

            cluster = DuplicateCluster(
                representative=representative,
                duplicates=duplicates,
                similarity_scores=scores
            )
            clusters.append(cluster)

    # Sort by cluster size (largest first)
    clusters.sort(key=lambda c: c.size, reverse=True)

    return clusters

def analyze_threshold_sweep(nodes: List[dict], embeddings: np.ndarray) -> dict:
    """Test multiple thresholds to find optimal deduplication setting"""
    thresholds = [0.75, 0.80, 0.85, 0.90, 0.95]
    results = {}

    for threshold in thresholds:
        clusters = find_duplicate_clusters(nodes, embeddings, threshold, same_type_only=True)
        total_duplicates = sum(c.node_savings for c in clusters)
        reduction_pct = (total_duplicates / len(nodes)) * 100

        results[threshold] = {
            'clusters': len(clusters),
            'nodes_eliminated': total_duplicates,
            'nodes_remaining': len(nodes) - total_duplicates,
            'reduction_percent': reduction_pct
        }

    return results

# ============================================
# STEP 5: Run Analysis
# ============================================

print("\n" + "=" * 80)
print("COMPUTING EMBEDDINGS...")
print("=" * 80)

embeddings = compute_embeddings(NODES)
print(f"✓ Computed {len(embeddings)} embeddings ({embeddings.shape[1]} dimensions each)\n")

print("=" * 80)
print("ANALYZING DUPLICATE CLUSTERS...")
print("=" * 80)

# Test multiple thresholds
print("\nThreshold sweep:")
threshold_results = analyze_threshold_sweep(NODES, embeddings)
for threshold, stats in threshold_results.items():
    print(f"  {threshold:.2f}: {stats['clusters']} clusters, "
          f"{stats['nodes_eliminated']} nodes eliminated ({stats['reduction_percent']:.1f}%), "
          f"{stats['nodes_remaining']} remaining")

# Use 0.85 as default (good balance)
DEFAULT_THRESHOLD = 0.85

print(f"\nComparing clustering methods at threshold {DEFAULT_THRESHOLD}...")
print("\n1. GREEDY (original) - star clusters:")
clusters_greedy = find_duplicate_clusters(NODES, embeddings, DEFAULT_THRESHOLD, same_type_only=True)
print(f"   Found {len(clusters_greedy)} clusters")
print(f"   Can eliminate {sum(c.node_savings for c in clusters_greedy)} nodes ({(sum(c.node_savings for c in clusters_greedy) / len(NODES)) * 100:.1f}%)")

print("\n2. CONNECTED COMPONENTS - transitive closure + negation filter:")
clusters_cc = find_duplicate_clusters_connected_components(
    NODES, embeddings, DEFAULT_THRESHOLD, same_type_only=True, check_negation=True
)
print(f"   Found {len(clusters_cc)} clusters")
print(f"   Can eliminate {sum(c.node_savings for c in clusters_cc)} nodes ({(sum(c.node_savings for c in clusters_cc) / len(NODES)) * 100:.1f}%)")

# Use connected components as default (better algorithm)
clusters = clusters_cc
print("\n✓ Using CONNECTED COMPONENTS method for detailed analysis")
print(f"✓ Total: {len(clusters)} duplicate clusters, {sum(c.node_savings for c in clusters)} nodes eliminated")

# ============================================
# STEP 6: Generate Report
# ============================================

def generate_report(nodes: List[dict], clusters: List[DuplicateCluster],
                   threshold: float, threshold_results: dict,
                   clusters_greedy: List[DuplicateCluster] = None) -> str:
    """Generate human-readable deduplication report"""
    lines = []
    lines.append("=" * 80)
    lines.append("SEMANTIC DEDUPLICATION ANALYSIS (IMPROVED)")
    lines.append("=" * 80)
    lines.append(f"\nSession: {SESSION_ID}")
    lines.append(f"Total nodes: {len(nodes)}")
    lines.append("Embedding model: all-MiniLM-L6-v2 (384-dim)")
    lines.append("Similarity metric: Cosine similarity")
    lines.append(f"Threshold: {threshold}")
    lines.append("Clustering method: Connected components (transitive closure)")
    lines.append("Type constraint: Same type only")
    lines.append("Negation filter: Enabled (prevents 'X' vs 'not X' merges)")

    total_eliminated = sum(c.node_savings for c in clusters)
    total_remaining = len(nodes) - total_eliminated
    reduction_pct = (total_eliminated / len(nodes)) * 100

    lines.append(f"\n{'=' * 80}")
    lines.append("SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Duplicate clusters found: {len(clusters)}")
    lines.append(f"Nodes to eliminate: {total_eliminated} ({reduction_pct:.1f}%)")
    lines.append(f"Nodes after dedup: {total_remaining}")
    lines.append(f"Expected node reduction: {len(nodes)} → {total_remaining}")

    # Add comparison if greedy results provided
    if clusters_greedy is not None:
        greedy_eliminated = sum(c.node_savings for c in clusters_greedy)
        greedy_pct = (greedy_eliminated / len(nodes)) * 100
        improvement = total_eliminated - greedy_eliminated
        lines.append(f"\n{'=' * 80}")
        lines.append("METHOD COMPARISON")
        lines.append("=" * 80)
        lines.append(f"Greedy (original):        {len(clusters_greedy)} clusters, {greedy_eliminated} nodes ({greedy_pct:.1f}%)")
        lines.append(f"Connected components:     {len(clusters)} clusters, {total_eliminated} nodes ({reduction_pct:.1f}%)")
        lines.append(f"Improvement:              +{improvement} nodes ({(improvement/len(nodes))*100:.1f}% more reduction)")
        if improvement > 0:
            lines.append(f"\n✓ Connected components found {improvement} additional duplicates via transitive closure")

    lines.append(f"\n{'=' * 80}")
    lines.append("THRESHOLD SWEEP")
    lines.append("=" * 80)
    lines.append(f"{'Threshold':<12} {'Clusters':<12} {'Eliminated':<12} {'Remaining':<12} {'Reduction':<12}")
    lines.append("-" * 80)
    for thresh, stats in sorted(threshold_results.items()):
        lines.append(f"{thresh:<12.2f} {stats['clusters']:<12} {stats['nodes_eliminated']:<12} "
                    f"{stats['nodes_remaining']:<12} {stats['reduction_percent']:<12.1f}%")

    lines.append(f"\n{'=' * 80}")
    lines.append(f"TOP 20 DUPLICATE CLUSTERS (threshold={threshold})")
    lines.append("=" * 80)

    for i, cluster in enumerate(clusters[:20], 1):
        lines.append(f"\n{'─' * 80}")
        lines.append(f"CLUSTER {i} ({cluster.size} nodes, saves {cluster.node_savings})")
        lines.append("─" * 80)
        lines.append(f"✓ KEEP: [{cluster.representative['node_type']}] {cluster.representative['label']}")
        lines.append(f"\n❌ MERGE ({len(cluster.duplicates)} duplicates):")
        for dup, score in zip(cluster.duplicates, cluster.similarity_scores):
            lines.append(f"   [{dup['node_type']}] {dup['label']} (similarity: {score:.3f})")

    if len(clusters) > 20:
        lines.append(f"\n... and {len(clusters) - 20} more clusters")

    lines.append(f"\n{'=' * 80}")
    lines.append("RECOMMENDATIONS")
    lines.append("=" * 80)
    lines.append("\n1. CLUSTERING METHOD:")
    lines.append("   ✓ Use CONNECTED COMPONENTS (implemented here)")
    lines.append("   - Finds transitive similarities (A→B→C creates one cluster)")
    lines.append("   - Better than greedy star clusters")
    lines.append("   - Negation filter prevents 'X' vs 'not X' false positives")

    lines.append("\n2. THRESHOLD SELECTION:")
    lines.append("   - 0.85: Good balance (current default)")
    lines.append("   - 0.90: More conservative, fewer false positives")
    lines.append("   - 0.80: More aggressive, catches more variations")
    lines.append("   - 0.75: Maximum recall, more false positives")

    lines.append("\n3. REPRESENTATIVE SELECTION:")
    lines.append("   ✓ Use LONGEST LABEL (implemented here)")
    lines.append("   - Most specific concept (e.g., 'sustained energy throughout the day')")
    lines.append("   - Better than arbitrary first-node selection")

    lines.append("\n4. INTEGRATION APPROACH:")
    lines.append("   - Add semantic similarity check to GraphService.add_node()")
    lines.append("   - Before creating new node, search existing nodes with embeddings")
    lines.append("   - Use connected components logic for cluster detection")
    lines.append("   - Add negation filter to prevent opposite-meaning merges")
    lines.append("   - Store embeddings in database or cache for fast lookup")

    lines.append("\n5. EXPECTED IMPACT:")
    lines.append(f"   - Node count: {len(nodes)} → {total_remaining} ({reduction_pct:.1f}% reduction)")
    lines.append("   - Edge/node ratio: Improves as duplicate nodes collapse")
    lines.append("   - Orphan nodes: Reduces as duplicates get merged with connected nodes")
    lines.append("   - False positives: Reduced by negation filter")

    return '\n'.join(lines)

report = generate_report(NODES, clusters, DEFAULT_THRESHOLD, threshold_results, clusters_greedy)
print("\n" + report)

# ============================================
# STEP 7: Save Files
# ============================================

print("\n" + "=" * 80)
print("SAVING FILES...")
print("=" * 80)

# 1. Human-readable report
with open('deduplication_analysis.txt', 'w') as f:
    f.write(report)

# 2. Structured JSON for integration
dedup_data = {
    'session_id': SESSION_ID,
    'config': {
        'model': 'all-MiniLM-L6-v2',
        'threshold': DEFAULT_THRESHOLD,
        'same_type_only': True,
        'embedding_dim': embeddings.shape[1]
    },
    'summary': {
        'total_nodes': len(NODES),
        'clusters_found': len(clusters),
        'nodes_eliminated': sum(c.node_savings for c in clusters),
        'nodes_remaining': len(NODES) - sum(c.node_savings for c in clusters),
        'reduction_percent': (sum(c.node_savings for c in clusters) / len(NODES)) * 100
    },
    'threshold_sweep': threshold_results,
    'clusters': [
        {
            'cluster_id': i,
            'size': cluster.size,
            'node_savings': cluster.node_savings,
            'representative': {
                'id': cluster.representative['id'],
                'label': cluster.representative['label'],
                'node_type': cluster.representative['node_type']
            },
            'duplicates': [
                {
                    'id': dup['id'],
                    'label': dup['label'],
                    'node_type': dup['node_type'],
                    'similarity': float(score)
                }
                for dup, score in zip(cluster.duplicates, cluster.similarity_scores)
            ]
        }
        for i, cluster in enumerate(clusters, 1)
    ]
}

with open('deduplication_clusters.json', 'w') as f:
    json.dump(dedup_data, f, indent=2)

print("\n✅ FILES READY:")
print("=" * 80)
print("1. deduplication_analysis.txt  - Human-readable report")
print("2. deduplication_clusters.json - Structured data for integration")
print("\nDownloading...")

files.download('deduplication_analysis.txt')
files.download('deduplication_clusters.json')

print("\n✅ DONE!")
print("\n" + "=" * 80)
print("KEY IMPROVEMENTS IN THIS VERSION:")
print("=" * 80)
print("✓ Connected components clustering (finds transitive similarities)")
print("✓ Longest-label representative selection (most specific concept)")
print("✓ Negation filter (prevents 'X' vs 'not X' false positives)")
print("\nUSAGE: Use these files to guide semantic deduplication integration.")
print("The connected components method is more thorough and robust than greedy clustering.")
