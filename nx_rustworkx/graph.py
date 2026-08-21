"""Backend graph wrapper with a NetworkX node identity map."""

from __future__ import annotations

from typing import Any


class RustworkxGraph:
    """A rustworkx graph plus the NetworkX node-to-index map.

    rustworkx addresses nodes by dense ``int`` indices. NetworkX uses arbitrary
    hashables. Every algorithm return value that mentions nodes must go through
    ``index_to_node`` / ``node_to_index``.
    """

    __networkx_backend__ = "rustworkx"

    def __init__(
        self,
        rx_graph: Any,
        node_to_index: dict[Any, int],
        index_to_node: list[Any],
        *,
        directed: bool,
        graph_attrs: dict[str, Any] | None = None,
        node_attrs: dict[Any, dict[str, Any]] | None = None,
    ):
        self.rx_graph = rx_graph
        self.node_to_index = node_to_index
        self.index_to_node = index_to_node
        self.graph = dict(graph_attrs) if graph_attrs else {}
        self.node_attrs = node_attrs
        self._directed = directed
        self.__networkx_cache__: dict[str, Any] = {}

    def is_directed(self) -> bool:
        return self._directed

    def is_multigraph(self) -> bool:
        return False

    def number_of_nodes(self) -> int:
        return self.rx_graph.num_nodes()

    def number_of_edges(self) -> int:
        return self.rx_graph.num_edges()

    def __len__(self) -> int:
        return self.rx_graph.num_nodes()

    def __contains__(self, node: Any) -> bool:
        return node in self.node_to_index

    def __str__(self) -> str:
        kind = "DiGraph" if self._directed else "Graph"
        return (
            f"Rustworkx{kind} with {self.number_of_nodes()} nodes "
            f"and {self.number_of_edges()} edges"
        )
