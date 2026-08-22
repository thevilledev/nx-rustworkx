"""Backend metadata for NetworkX docs. This module must not import rustworkx."""

_CONVERTED = (
    "Runs the rustworkx kernel after converting the NetworkX graph and remaps "
    "the result to the original node IDs."
)
_NO_MULTIGRAPH = "MultiGraph and MultiDiGraph inputs fall back to NetworkX."
_NO_CALLABLE_WEIGHT = "Callable ``weight`` arguments fall back to NetworkX."
_NO_CUTOFF = "``cutoff`` falls back to NetworkX."
_TIE_BREAK = (
    "The answer is one of several equally valid ones, and rustworkx may pick a "
    "different one than NetworkX."
)

#: name -> the caveats that apply on top of ``_CONVERTED``.
_FUNCTIONS = {
    # --- centrality -------------------------------------------------------
    "betweenness_centrality": ["Unweighted Brandes only; ``k`` sampling falls back."],
    "edge_betweenness_centrality": ["Unweighted only; ``k`` sampling falls back."],
    "closeness_centrality": ["Unweighted only; ``distance`` falls back."],
    "eigenvector_centrality": ["``nstart`` falls back to NetworkX."],
    "degree_centrality": [
        "rustworkx divides by n - 1 where NetworkX multiplies by 1 / (n - 1), "
        "so values can land one ULP apart."
    ],
    "in_degree_centrality": ["Directed graphs only."],
    "out_degree_centrality": ["Directed graphs only."],
    "katz_centrality": [
        "Always L2-normalized, so ``normalized=False`` falls back.",
        "``nstart`` falls back to NetworkX.",
    ],
    "katz_centrality_numpy": ["Always L2-normalized, so ``normalized=False`` falls back."],
    "hits": ["Undirected edges are counted in both directions, as NetworkX does."],
    "group_betweenness_centrality": [
        "Unweighted only; ``weight`` and ``endpoints`` fall back to NetworkX."
    ],
    "group_closeness_centrality": ["Unweighted only; ``weight`` falls back to NetworkX."],
    "group_degree_centrality": [],
    # --- link analysis ----------------------------------------------------
    "pagerank": ["Numeric values may differ slightly from NetworkX."],
    # --- shortest paths ---------------------------------------------------
    "shortest_path": [],
    "shortest_path_length": [],
    "single_source_dijkstra": [_NO_CUTOFF],
    "single_source_dijkstra_path": [_NO_CUTOFF],
    "single_source_dijkstra_path_length": [_NO_CUTOFF],
    "single_source_bellman_ford": [],
    "single_source_bellman_ford_path": [],
    "single_source_bellman_ford_path_length": [],
    "single_source_shortest_path": [_NO_CUTOFF],
    "single_source_shortest_path_length": [_NO_CUTOFF],
    "single_target_shortest_path": [_NO_CUTOFF],
    "single_target_shortest_path_length": [_NO_CUTOFF],
    "bidirectional_shortest_path": [],
    "all_pairs_dijkstra": [_NO_CUTOFF],
    "all_pairs_dijkstra_path": [_NO_CUTOFF],
    "all_pairs_dijkstra_path_length": [_NO_CUTOFF],
    "all_pairs_bellman_ford_path": [],
    "all_pairs_bellman_ford_path_length": [],
    "all_pairs_shortest_path": [_NO_CUTOFF],
    "all_pairs_shortest_path_length": [_NO_CUTOFF],
    "all_shortest_paths": ["Only the ``dijkstra`` method; ``bellman-ford`` falls back."],
    "dijkstra_path": [],
    "dijkstra_path_length": [],
    "bellman_ford_path": [],
    "bellman_ford_path_length": [],
    "astar_path": [
        "rustworkx never reopens a settled node, so it needs a consistent "
        "heuristic while NetworkX only needs an admissible one. ``can_run`` "
        "checks consistency over the edge set and falls back when it does not "
        "hold. Set ``nx.config.backends.rustworkx.astar_heuristic_check = "
        "False`` to skip that check.",
        _NO_CUTOFF,
    ],
    "astar_path_length": ["Same heuristic requirement as ``astar_path``.", _NO_CUTOFF],
    "has_path": [],
    "floyd_warshall": [],
    "floyd_warshall_numpy": [
        "A ``nodelist`` that does not cover every node falls back to NetworkX."
    ],
    "floyd_warshall_predecessor_and_distance": [
        "Distances match exactly. Predecessors may name a different equally "
        "short path when several exist."
    ],
    "negative_edge_cycle": [],
    "find_negative_cycle": [
        "Returns a negative cycle reachable from ``source``. The cycle may start "
        "at a different node than NetworkX's."
    ],
    "average_shortest_path_length": [
        "Unweighted only; ``weight`` and other ``method`` values fall back."
    ],
    # --- DAG and traversal ------------------------------------------------
    "is_directed_acyclic_graph": [],
    "topological_sort": [_TIE_BREAK],
    "topological_generations": [
        "NetworkX documents each generation as a set; the order inside one "
        "generation is unspecified."
    ],
    "ancestors": [],
    "descendants": [],
    "descendants_at_distance": [],
    "dag_longest_path": [_TIE_BREAK],
    "dag_longest_path_length": [],
    "transitive_reduction": ["Returns a NetworkX DiGraph."],
    "immediate_dominators": [],
    "dfs_edges": ["``depth_limit`` and ``sort_neighbors`` fall back to NetworkX."],
    # --- connectivity and components --------------------------------------
    "is_connected": ["Undirected graphs only."],
    "is_weakly_connected": ["Directed graphs only."],
    "is_strongly_connected": ["Directed graphs only."],
    "is_semiconnected": ["Directed graphs only."],
    "connected_components": ["Undirected graphs only."],
    "number_connected_components": ["Undirected graphs only."],
    "node_connected_component": ["Undirected graphs only."],
    "weakly_connected_components": ["Directed graphs only."],
    "number_weakly_connected_components": ["Directed graphs only."],
    "strongly_connected_components": ["Directed graphs only."],
    "number_strongly_connected_components": ["Directed graphs only."],
    "articulation_points": ["Undirected graphs only."],
    "bridges": ["Undirected graphs only; ``root`` falls back to NetworkX."],
    "biconnected_components": ["Undirected graphs only."],
    "condensation": [
        "Returns a NetworkX DiGraph with the ``members`` attribute and graph "
        "``mapping``. Component numbering follows rustworkx's component order.",
        "A supplied ``scc`` falls back to NetworkX.",
    ],
    "stoer_wagner": [
        "Undirected graphs only. NetworkX's ``heap`` argument only selects a "
        "priority queue and is ignored."
    ],
    # --- cycles and cores --------------------------------------------------
    "simple_cycles": ["Directed graphs only; ``length_bound`` falls back to NetworkX."],
    "cycle_basis": [
        "Undirected graphs only; ``root`` falls back to NetworkX.",
        "A cycle basis is not unique.",
    ],
    "core_number": [],
    # --- structure ---------------------------------------------------------
    "is_bipartite": [],
    "isolates": [],
    "number_of_isolates": [],
    "transitivity": [],
    # --- matching, coloring, trees ----------------------------------------
    "max_weight_matching": [
        "Undirected graphs only. rustworkx's blossom kernel takes integer edge "
        "weights, so non-integer weights fall back to NetworkX."
    ],
    "greedy_color": [
        "Only ``strategy='largest_first'``; other strategies and "
        "``interchange=True`` fall back to NetworkX."
    ],
    "minimum_spanning_tree": [
        "Undirected graphs only. Returns a NetworkX Graph.",
        "rustworkx always runs Kruskal's algorithm. A minimum spanning forest is "
        "not unique when weights tie, so the edges may differ from NetworkX's "
        "while the total weight matches.",
        "``ignore_nan`` falls back to NetworkX.",
    ],
    "minimum_spanning_edges": [
        "Undirected graphs only; same tie-breaking note as "
        "``minimum_spanning_tree``.",
        "``ignore_nan`` falls back to NetworkX.",
    ],
    "steiner_tree": [
        "Undirected graphs only. Returns a NetworkX Graph built by rustworkx's "
        "Kou approximation; other ``method`` values fall back to NetworkX."
    ],
    # --- operators and paths ----------------------------------------------
    "complement": ["Returns a NetworkX graph."],
    "cartesian_product": ["Returns a NetworkX graph; node and edge attributes are dropped."],
    "tensor_product": ["Returns a NetworkX graph; node and edge attributes are dropped."],
    "all_simple_paths": ["A collection of targets falls back to NetworkX."],
    # --- isomorphism -------------------------------------------------------
    "is_isomorphic": ["Structural VF2 only; ``node_match`` and ``edge_match`` fall back."],
    "vf2pp_is_isomorphic": ["Structural only; ``node_label`` falls back to NetworkX."],
}


#: name -> additional_docs for the graph constructors, which build a rustworkx
#: graph directly instead of converting one.
_GENERATORS = {
    "graph__new__": (
        "Returns a rustworkx-backed graph so later algorithm calls skip conversion."
    ),
    "digraph__new__": (
        "Returns a rustworkx-backed digraph so later algorithm calls skip conversion."
    ),
    "empty_graph": (
        "Constructs a rustworkx-backed empty graph. MultiGraph create_using is rejected."
    ),
    "from_edgelist": "Constructs a rustworkx-backed graph from an edgelist.",
}


def _docs(notes):
    return " ".join([_CONVERTED, _NO_MULTIGRAPH, *notes])


def get_info():
    """Return backend metadata used by NetworkX's documentation box."""
    functions = {name: {"additional_docs": _docs(notes)} for name, notes in _FUNCTIONS.items()}
    functions.update(
        {name: {"additional_docs": docs} for name, docs in _GENERATORS.items()}
    )
    return {
        "backend_name": "rustworkx",
        "project": "nx-rustworkx",
        "package": "nx_rustworkx",
        "url": "https://github.com/thevilledev/nx-rustworkx",
        "short_summary": "Dispatch selected NetworkX algorithms to rustworkx.",
        "default_config": {
            "min_nodes": 200,
            "min_edges": 400,
            "astar_heuristic_check": True,
        },
        "functions": functions,
    }
