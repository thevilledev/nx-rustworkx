"""Backend graph wrapper with a NetworkX node identity map."""

from __future__ import annotations

from typing import Any


class _AdjView:
    """Dict-like adjacency keyed by original node IDs."""

    def __init__(self, graph: RustworkxGraph):
        self._graph = graph

    def __contains__(self, node: Any) -> bool:
        return node in self._graph.node_to_index

    def __getitem__(self, node: Any) -> dict:
        return {nbr: data for nbr, data in self._graph._neighbor_items(node)}

    def __iter__(self):
        return iter(self._graph.node_to_index)

    def __len__(self) -> int:
        return len(self._graph.node_to_index)

    def items(self):
        for node in self._graph.node_to_index:
            yield node, self[node]


class _NodeView:
    """``G.nodes``: iterate nodes, index for attributes, call for data."""

    __slots__ = ("_graph",)

    def __init__(self, graph: RustworkxGraph):
        self._graph = graph

    def __iter__(self):
        return iter(self._graph.node_to_index)

    def __len__(self) -> int:
        return len(self._graph.node_to_index)

    def __contains__(self, node: Any) -> bool:
        try:
            return node in self._graph.node_to_index
        except TypeError:  # unhashable values are simply not nodes
            return False

    def __getitem__(self, node: Any) -> dict:
        if node not in self._graph.node_to_index:
            raise KeyError(node)
        # Hand back the live dict so G.nodes[n][key] = value sticks.
        return self._graph.node_attrs.setdefault(node, {})

    def __call__(self, data=False, default=None):
        if data is False:
            return self
        return _NodeDataView(self._graph, data, default)

    def data(self, data=True, default=None):
        return self(data=data, default=default)

    def __repr__(self) -> str:
        return f"NodeView({list(self)!r})"


class _NodeDataView:
    """``G.nodes(data=True)`` or ``G.nodes(data="key")``."""

    __slots__ = ("_graph", "_data", "_default")

    def __init__(self, graph: RustworkxGraph, data, default):
        self._graph = graph
        self._data = data
        self._default = default

    def __iter__(self):
        attrs = self._graph.node_attrs
        for node in self._graph.node_to_index:
            data = attrs.get(node, {})
            if self._data is True:
                yield node, data
            else:
                yield node, data.get(self._data, self._default)

    def __len__(self) -> int:
        return len(self._graph.node_to_index)

    def __repr__(self) -> str:
        return f"NodeDataView({list(self)!r})"


class _EdgeView:
    """``G.edges``: iterate edges, call for a filtered or data-bearing view."""

    __slots__ = ("_graph",)

    def __init__(self, graph: RustworkxGraph):
        self._graph = graph

    def __iter__(self):
        return iter(_EdgeDataView(self._graph, None, False, None))

    def __len__(self) -> int:
        return self._graph.number_of_edges()

    def __contains__(self, edge) -> bool:
        try:
            u, v = edge
        except (TypeError, ValueError):
            return False
        return self._graph.has_edge(u, v)

    def __call__(self, nbunch=None, data=False, default=None):
        if nbunch is None and data is False:
            return self
        return _EdgeDataView(self._graph, nbunch, data, default)

    def __repr__(self) -> str:
        return f"EdgeView({list(self)!r})"


class _EdgeDataView:
    """``G.edges(nbunch=..., data=...)``."""

    __slots__ = ("_graph", "_nbunch", "_data", "_default")

    def __init__(self, graph: RustworkxGraph, nbunch, data, default):
        self._graph = graph
        self._nbunch = nbunch
        self._data = data
        self._default = default

    def _wanted(self):
        if self._nbunch is None:
            return None
        if self._graph.has_node(self._nbunch):
            return {self._nbunch}
        return set(self._nbunch)

    def __iter__(self):
        graph = self._graph
        wanted = self._wanted()
        index_to_node = graph.index_to_node
        for u_idx, v_idx, payload in graph.rx_graph.weighted_edge_list():
            u = index_to_node[u_idx]
            v = index_to_node[v_idx]
            if wanted is not None and u not in wanted and v not in wanted:
                continue
            if self._data is False:
                yield u, v
                continue
            data = payload if isinstance(payload, dict) else {}
            if self._data is True:
                yield u, v, data
            else:
                yield u, v, data.get(self._data, self._default)

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __repr__(self) -> str:
        return f"EdgeDataView({list(self)!r})"


class _DegreeView:
    """``G.degree``: call or index for a node's degree, iterate for all."""

    __slots__ = ("_graph", "_kind")

    def __init__(self, graph: RustworkxGraph, kind: str = "total"):
        self._graph = graph
        self._kind = kind

    def _degree(self, node) -> int:
        graph = self._graph
        index = graph.node_to_index[node]
        rx_graph = graph.rx_graph
        if not graph.is_directed():
            return int(rx_graph.degree(index))
        if self._kind == "in":
            return int(rx_graph.in_degree(index))
        if self._kind == "out":
            return int(rx_graph.out_degree(index))
        # NetworkX reports a directed node's degree as in plus out.
        return int(rx_graph.in_degree(index)) + int(rx_graph.out_degree(index))

    def __getitem__(self, node) -> int:
        return self._degree(node)

    def __iter__(self):
        for node in self._graph.node_to_index:
            yield node, self._degree(node)

    def __len__(self) -> int:
        return len(self._graph.node_to_index)

    def __call__(self, nbunch=None, weight=None):
        if weight is not None:
            raise NotImplementedError("nx-rustworkx does not implement weighted degree")
        if nbunch is None:
            return self
        if self._graph.has_node(nbunch):
            return self._degree(nbunch)
        return ((node, self._degree(node)) for node in nbunch)

    def __repr__(self) -> str:
        return f"DegreeView({dict(self)!r})"


class RustworkxGraph:
    """A rustworkx graph plus the NetworkX node-to-index map.

    rustworkx addresses nodes by dense ``int`` indices. NetworkX uses arbitrary
    hashables. Every algorithm return value that mentions nodes must go through
    ``index_to_node`` / ``node_to_index``.

    This object is not a NetworkX ``Graph`` subclass. Construction via
    ``nx.Graph(..., backend="rustworkx")`` or generator priority stores the
    rustworkx graph directly so later algorithm calls skip conversion.
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
        self.node_attrs = dict(node_attrs) if node_attrs else {}
        self._directed = directed
        self.__networkx_cache__: dict[str, Any] = {}

    @classmethod
    def empty(cls, *, directed: bool = False, graph_attrs: dict[str, Any] | None = None):
        import rustworkx as rx

        rx_graph = rx.PyDiGraph(multigraph=False) if directed else rx.PyGraph(multigraph=False)
        return cls(
            rx_graph,
            {},
            [],
            directed=directed,
            graph_attrs=graph_attrs,
        )

    @classmethod
    def from_incoming(
        cls,
        data=None,
        *,
        directed: bool = False,
        graph_attrs: dict[str, Any] | None = None,
    ):
        """Build from ``None``, an edgelist, a NetworkX graph, or another wrapper."""
        import networkx as nx

        from nx_rustworkx.convert import convert_from_nx

        attrs = dict(graph_attrs) if graph_attrs else {}
        if data is None:
            return cls.empty(directed=directed, graph_attrs=attrs)
        if isinstance(data, cls):
            out = data.copy()
            if out.is_directed() != directed:
                out = out.to_directed() if directed else out.to_undirected()
            out.graph.update(attrs)
            return out
        if isinstance(data, nx.Graph):
            if data.is_multigraph():
                raise nx.NetworkXError("nx-rustworkx does not support MultiGraph")
            out = convert_from_nx(data, preserve_all_attrs=True)
            if out.is_directed() != directed:
                out = out.to_directed() if directed else out.to_undirected()
            out.graph.update(attrs)
            return out
        out = cls.empty(directed=directed, graph_attrs=attrs)
        try:
            out.add_edges_from(data)
        except Exception:
            tmp = nx.DiGraph(data) if directed else nx.Graph(data)
            if tmp.is_multigraph():
                raise nx.NetworkXError("nx-rustworkx does not support MultiGraph")
            out = convert_from_nx(tmp, preserve_all_attrs=True)
            out.graph.update(attrs)
        return out

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
        return self.has_node(node)

    def __iter__(self):
        return iter(self.node_to_index)

    def __getitem__(self, node: Any):
        return self.adj[node]

    @property
    def name(self) -> str:
        return self.graph.get("name", "")

    @name.setter
    def name(self, value: str) -> None:
        self.graph["name"] = value

    @property
    def adj(self) -> _AdjView:
        return _AdjView(self)

    @property
    def nodes(self) -> _NodeView:
        return _NodeView(self)

    @property
    def edges(self) -> _EdgeView:
        return _EdgeView(self)

    @property
    def degree(self) -> _DegreeView:
        return _DegreeView(self)

    @property
    def in_degree(self) -> _DegreeView:
        if not self._directed:
            raise AttributeError("in_degree is only defined for directed graphs")
        return _DegreeView(self, "in")

    @property
    def out_degree(self) -> _DegreeView:
        if not self._directed:
            raise AttributeError("out_degree is only defined for directed graphs")
        return _DegreeView(self, "out")

    def has_node(self, n) -> bool:
        try:
            return n in self.node_to_index
        except TypeError:  # an unhashable value is simply not a node
            return False

    def has_edge(self, u, v) -> bool:
        try:
            return bool(self.rx_graph.has_edge(self.node_to_index[u], self.node_to_index[v]))
        except KeyError:
            return False

    def add_node(self, node_for_adding, **attr):
        if node_for_adding in self.node_to_index:
            if attr:
                self.node_attrs.setdefault(node_for_adding, {}).update(attr)
            return self.node_to_index[node_for_adding]
        if attr:
            self.node_attrs.setdefault(node_for_adding, {}).update(attr)
        idx = self.rx_graph.add_node(node_for_adding)
        self._bind_index(idx, node_for_adding)
        self.__networkx_cache__.clear()
        return idx

    def add_nodes_from(self, nodes_for_adding, **attr):
        for node in nodes_for_adding:
            if isinstance(node, tuple) and len(node) == 2 and isinstance(node[1], dict):
                self.add_node(node[0], **{**attr, **node[1]})
            else:
                self.add_node(node, **attr)

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        self.add_node(u_of_edge)
        self.add_node(v_of_edge)
        payload = dict(attr) if attr else None
        self.rx_graph.add_edge(
            self.node_to_index[u_of_edge],
            self.node_to_index[v_of_edge],
            payload,
        )
        self.__networkx_cache__.clear()

    def add_edges_from(self, ebunch_to_add, **attr):
        for edge in ebunch_to_add:
            if len(edge) == 2:
                u, v = edge
                data = dict(attr)
            elif len(edge) == 3:
                u, v, data = edge
                if data is None:
                    data = dict(attr)
                elif isinstance(data, dict):
                    data = {**attr, **data}
                else:
                    data = {**attr, "weight": data}
            else:
                raise ValueError(f"edge tuple must be 2 or 3 values, got {edge!r}")
            if data:
                self.add_edge(u, v, **data)
            else:
                self.add_edge(u, v)

    def remove_node(self, n):
        idx = self.node_to_index[n]
        self.rx_graph.remove_node(idx)
        del self.node_to_index[n]
        self.node_attrs.pop(n, None)
        if idx < len(self.index_to_node):
            self.index_to_node[idx] = None
        self._compact()
        self.__networkx_cache__.clear()

    def remove_edge(self, u, v):
        self.rx_graph.remove_edge(self.node_to_index[u], self.node_to_index[v])
        self.__networkx_cache__.clear()

    def clear(self):
        self.rx_graph.clear()
        self.node_to_index.clear()
        self.index_to_node.clear()
        self.node_attrs.clear()
        self.graph.clear()
        self.__networkx_cache__.clear()

    def neighbors(self, n):
        idx = self.node_to_index[n]
        return (self.index_to_node[i] for i in self.rx_graph.neighbors(idx))

    def copy(self) -> RustworkxGraph:
        copied = type(self)(
            self.rx_graph.copy(),
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=self._directed,
            graph_attrs=self.graph,
            node_attrs=self.node_attrs,
        )
        return copied

    def to_directed(self) -> RustworkxGraph:
        if self._directed:
            return self.copy()
        import rustworkx as rx

        directed = rx.PyDiGraph(multigraph=False)
        directed.add_nodes_from(self._dense_payloads())
        for u, v, data in self.rx_graph.weighted_edge_list():
            directed.add_edge(u, v, data)
            if u != v:
                directed.add_edge(v, u, data)
        return type(self)(
            directed,
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=True,
            graph_attrs=self.graph,
            node_attrs=self.node_attrs,
        )

    def to_undirected(self) -> RustworkxGraph:
        if not self._directed:
            return self.copy()
        import rustworkx as rx

        undirected = rx.PyGraph(multigraph=False)
        undirected.add_nodes_from(self._dense_payloads())
        seen = set()
        for u, v, data in self.rx_graph.weighted_edge_list():
            key = (u, v) if u <= v else (v, u)
            if key in seen:
                continue
            seen.add(key)
            undirected.add_edge(u, v, data)
        return type(self)(
            undirected,
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=False,
            graph_attrs=self.graph,
            node_attrs=self.node_attrs,
        )

    def _dense_payloads(self) -> list:
        return [self.rx_graph.get_node_data(i) for i in self.rx_graph.node_indices()]

    def _bind_index(self, idx: int, node: Any) -> None:
        if idx >= len(self.index_to_node):
            self.index_to_node.extend([None] * (idx + 1 - len(self.index_to_node)))
        self.index_to_node[idx] = node
        self.node_to_index[node] = idx

    def _compact(self) -> None:
        """Rewrite rustworkx indices to a dense 0..n-1 range after removals."""
        nodes = [self.index_to_node[i] for i in self.rx_graph.node_indices()]
        edges = [
            (self.index_to_node[u], self.index_to_node[v], data)
            for u, v, data in self.rx_graph.weighted_edge_list()
        ]
        graph_attrs = dict(self.graph)
        node_attrs = dict(self.node_attrs)
        directed = self._directed
        self.clear()
        self._directed = directed
        self.graph.update(graph_attrs)
        self.node_attrs.update(node_attrs)
        self.add_nodes_from(nodes)
        for u, v, data in edges:
            if isinstance(data, dict) and data:
                self.add_edge(u, v, **data)
            elif data is None:
                self.add_edge(u, v)
            else:
                self.add_edge(u, v, weight=data)

    def _neighbor_items(self, node: Any):
        idx = self.node_to_index[node]
        for nbr_idx in self.rx_graph.neighbors(idx):
            payload = None
            if self.rx_graph.has_edge(idx, nbr_idx):
                try:
                    payload = self.rx_graph.get_edge_data(idx, nbr_idx)
                except Exception:
                    payload = None
            yield self.index_to_node[nbr_idx], payload if payload is not None else {}

    def __str__(self) -> str:
        kind = "DiGraph" if self._directed else "Graph"
        return (
            f"Rustworkx{kind} with {self.number_of_nodes()} nodes "
            f"and {self.number_of_edges()} edges"
        )
