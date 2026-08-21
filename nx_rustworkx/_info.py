"""Backend metadata for NetworkX docs. This module must not import rustworkx."""


def get_info():
    """Return backend metadata used by NetworkX's documentation box."""
    extra = (
        "Runs the rustworkx kernel after converting the NetworkX graph. "
        "MultiGraph inputs, custom weight callables, and k-sampled "
        "betweenness are not implemented."
    )
    functions = {
        "betweenness_centrality": {
            "additional_docs": extra + " Unweighted Brandes only.",
        },
        "edge_betweenness_centrality": {
            "additional_docs": extra + " Unweighted only.",
        },
        "closeness_centrality": {
            "additional_docs": extra + " Unweighted only; ``distance`` is not supported.",
        },
        "eigenvector_centrality": {
            "additional_docs": extra + " ``nstart`` is not supported.",
        },
        "shortest_path": {
            "additional_docs": extra,
        },
        "shortest_path_length": {
            "additional_docs": extra,
        },
        "single_source_dijkstra": {
            "additional_docs": extra + " ``cutoff`` is not supported.",
        },
        "dijkstra_path": {
            "additional_docs": extra,
        },
        "bellman_ford_path": {
            "additional_docs": extra,
        },
        "is_connected": {
            "additional_docs": "Undirected graphs only.",
        },
        "is_weakly_connected": {
            "additional_docs": "Directed graphs only.",
        },
        "connected_components": {
            "additional_docs": "Undirected graphs only.",
        },
        "weakly_connected_components": {
            "additional_docs": "Directed graphs only.",
        },
        "number_connected_components": {
            "additional_docs": "Undirected graphs only.",
        },
        "pagerank": {
            "additional_docs": extra + " Numeric values may differ slightly from NetworkX.",
        },
        "is_isomorphic": {
            "additional_docs": extra + " Structural VF2 only; ``node_match`` / ``edge_match`` are not supported.",
        },
    }
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
