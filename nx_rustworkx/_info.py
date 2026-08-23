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
    "closeness_centrality": [
        "A string ``distance`` runs rustworkx's weighted kernel; callable "
        "``distance`` falls back to NetworkX."
    ],
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
    "single_source_all_shortest_paths": [
        "Only the ``dijkstra`` method; ``bellman-ford`` falls back."
    ],
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
    "dominance_frontiers": [],
    "dfs_edges": ["``depth_limit`` and ``sort_neighbors`` fall back to NetworkX."],
    "bfs_layers": [
        "Each layer holds the right nodes, but the order inside one layer may "
        "differ from NetworkX's discovery order."
    ],
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
    "bridges": ["Undirected graphs only."],
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
    "find_cycle": [
        "Directed graphs only; ``orientation`` falls back to NetworkX.",
        _TIE_BREAK,
    ],
    "chain_decomposition": [
        "Undirected graphs only.",
        "A chain decomposition is not unique, so the chains may differ from "
        "NetworkX's while still being a valid decomposition.",
    ],
    "core_number": [],
    # --- structure ---------------------------------------------------------
    "is_bipartite": [],
    "is_planar": ["Directed input is checked on its undirected form, as NetworkX does."],
    "isolates": [],
    "number_of_isolates": [],
    "transitivity": [],
    # --- matching, coloring, trees ----------------------------------------
    "max_weight_matching": [
        "Undirected graphs only. rustworkx's blossom kernel takes integer edge "
        "weights, so non-integer weights fall back to NetworkX."
    ],
    "is_matching": ["Undirected graphs only."],
    "is_maximal_matching": ["Undirected graphs only."],
    "greedy_color": [
        "``largest_first``, ``saturation_largest_first``/``DSATUR``, and "
        "``independent_set`` map to rustworkx strategies; other strategies and "
        "``interchange=True`` fall back to NetworkX.",
        "A greedy coloring is not unique, so colors may differ from NetworkX's "
        "while using the same strategy.",
    ],
    "minimum_spanning_tree": [
        "Undirected graphs only. Returns a NetworkX Graph.",
        "rustworkx always runs Kruskal's algorithm. A minimum spanning forest is "
        "not unique when weights tie, so the edges may differ from NetworkX's "
        "while the total weight matches.",
        "``ignore_nan`` falls back to NetworkX.",
    ],
    "minimum_spanning_edges": [
        "Undirected graphs only; same tie-breaking note as ``minimum_spanning_tree``.",
        "``ignore_nan`` falls back to NetworkX.",
    ],
    "steiner_tree": [
        "Undirected graphs only. Returns a NetworkX Graph built by rustworkx's "
        "Kou approximation; other ``method`` values fall back to NetworkX."
    ],
    "metric_closure": [
        "Undirected connected graphs only. Returns a NetworkX Graph whose "
        "``path`` attributes may name a different equally short path than "
        "NetworkX's when several exist.",
    ],
    # --- operators and paths ----------------------------------------------
    "complement": ["Returns a NetworkX graph."],
    "cartesian_product": ["Returns a NetworkX graph; node and edge attributes are dropped."],
    "tensor_product": ["Returns a NetworkX graph; node and edge attributes are dropped."],
    "line_graph": [
        "Undirected graphs only; ``create_using`` falls back to NetworkX. Returns a NetworkX Graph."
    ],
    "all_simple_paths": [
        "With a collection of targets, paths arrive grouped by target rather "
        "than in NetworkX's traversal order."
    ],
    # --- isomorphism -------------------------------------------------------
    "is_isomorphic": ["Structural VF2 only; ``node_match`` and ``edge_match`` fall back."],
    "vf2pp_is_isomorphic": ["Structural only; ``node_label`` falls back to NetworkX."],
    "vf2pp_isomorphism": [
        "Structural only; ``node_label`` falls back to NetworkX.",
        "When several isomorphisms exist, the returned mapping may differ from NetworkX's.",
    ],
    "vf2pp_all_isomorphisms": [
        "Structural only; ``node_label`` falls back to NetworkX.",
        "Mappings may arrive in a different order than NetworkX yields them.",
    ],
}


_NATIVE_EXACT = (
    "Builds the graph natively with a rustworkx kernel and returns a "
    "rustworkx-backed graph identical to NetworkX's, so later algorithm calls "
    "skip conversion. MultiGraph ``create_using`` falls back to NetworkX."
)

_NATIVE_RANDOM = (
    "Samples natively with rustworkx's RNG and returns a rustworkx-backed "
    "graph. Unseeded calls always run; a seeded call yields a different "
    "(equally valid) graph than NetworkX's for the same seed, so it falls "
    "back to NetworkX's sampler unless "
    "``nx.config.backends.rustworkx.native_seeded_generators`` is True. With "
    "the opt-in, the same seed reproduces the same graph for a pinned "
    "rustworkx version. ``create_using`` falls back to NetworkX."
)

#: name -> additional_docs for the graph constructors, which build a rustworkx
#: graph directly instead of converting one.
_GENERATORS = {
    "graph__new__": ("Returns a rustworkx-backed graph so later algorithm calls skip conversion."),
    "digraph__new__": (
        "Returns a rustworkx-backed digraph so later algorithm calls skip conversion."
    ),
    "empty_graph": (
        "Constructs a rustworkx-backed empty graph. MultiGraph create_using is rejected."
    ),
    "from_edgelist": "Constructs a rustworkx-backed graph from an edgelist.",
    "path_graph": _NATIVE_EXACT,
    "cycle_graph": _NATIVE_EXACT,
    "star_graph": _NATIVE_EXACT,
    "complete_graph": _NATIVE_EXACT,
    "barbell_graph": _NATIVE_EXACT,
    "lollipop_graph": _NATIVE_EXACT,
    "binomial_tree": _NATIVE_EXACT,
    "full_rary_tree": _NATIVE_EXACT,
    "karate_club_graph": (
        "Returns a rustworkx-backed graph identical to NetworkX's, including "
        "the ``club`` node attribute, edge weights, and graph name."
    ),
    "grid_2d_graph": _NATIVE_EXACT
    + " Periodic grids and directed ``create_using`` fall back to NetworkX.",
    "gnp_random_graph": _NATIVE_RANDOM,
    "fast_gnp_random_graph": _NATIVE_RANDOM + " Shares ``gnp_random_graph``'s kernel, so "
    "on this backend the same seed produces the same graph under both names.",
    "gnm_random_graph": _NATIVE_RANDOM,
    "dense_gnm_random_graph": _NATIVE_RANDOM + " Shares ``gnm_random_graph``'s kernel.",
}


def _docs(notes):
    return " ".join([_CONVERTED, _NO_MULTIGRAPH, *notes])


def get_info():
    """Return backend metadata used by NetworkX's documentation box."""
    functions = {name: {"additional_docs": _docs(notes)} for name, notes in _FUNCTIONS.items()}
    functions.update({name: {"additional_docs": docs} for name, docs in _GENERATORS.items()})
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
            "native_seeded_generators": False,
        },
        "functions": functions,
    }
