"""Algorithm implementations attached to BackendInterface by name."""

from nx_rustworkx.algorithms.centrality import (
    betweenness_centrality,
    closeness_centrality,
    edge_betweenness_centrality,
    eigenvector_centrality,
)
from nx_rustworkx.algorithms.connectivity import (
    connected_components,
    is_connected,
    is_weakly_connected,
    number_connected_components,
    weakly_connected_components,
)
from nx_rustworkx.algorithms.isomorphism import is_isomorphic
from nx_rustworkx.algorithms.link_analysis import pagerank
from nx_rustworkx.algorithms.shortest_paths import (
    bellman_ford_path,
    dijkstra_path,
    shortest_path,
    shortest_path_length,
    single_source_dijkstra,
)

ALGORITHMS = [
    "betweenness_centrality",
    "edge_betweenness_centrality",
    "closeness_centrality",
    "eigenvector_centrality",
    "shortest_path",
    "shortest_path_length",
    "single_source_dijkstra",
    "dijkstra_path",
    "bellman_ford_path",
    "is_connected",
    "is_weakly_connected",
    "connected_components",
    "weakly_connected_components",
    "number_connected_components",
    "pagerank",
    "is_isomorphic",
]

__all__ = ALGORITHMS + ["ALGORITHMS"]
