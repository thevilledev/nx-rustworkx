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

    def _nbunch_nodes(self) -> list:
        """The nbunch as in-graph nodes, in given order; missing ones are
        quietly ignored, as NetworkX's nbunch_iter does."""
        graph = self._graph
        if graph.has_node(self._nbunch):
            return [self._nbunch]
        node_to_index = graph.node_to_index
        return [n for n in dict.fromkeys(self._nbunch) if n in node_to_index]

    def __iter__(self):
        if self._nbunch is None:
            yield from self._iter_all()
        else:
            yield from self._iter_nbunch()

    def _iter_all(self):
        graph = self._graph
        index_to_node = graph.index_to_node
        for u_idx, v_idx, payload in graph.rx_graph.weighted_edge_list():
            yield self._edge(index_to_node[u_idx], index_to_node[v_idx], payload)

    def _iter_nbunch(self):
        """NetworkX's nbunch semantics: walk the nbunch nodes in order, each
        yielding its incident (undirected) or outgoing (directed) edges with
        itself first; an edge between two nbunch nodes appears once, from the
        first of them."""
        graph = self._graph
        node_to_index = graph.node_to_index
        index_to_node = graph.index_to_node
        rx_graph = graph.rx_graph
        seen: set[int] = set()
        for node in self._nbunch_nodes():
            # (queried, neighbor, payload) rows; outgoing only on a PyDiGraph.
            incident = rx_graph.incident_edge_index_map(node_to_index[node])
            for edge_idx in sorted(incident):
                if edge_idx in seen:
                    continue
                seen.add(edge_idx)
                _u, nbr_idx, payload = incident[edge_idx]
                yield self._edge(node, index_to_node[nbr_idx], payload)

    def _edge(self, u, v, payload):
        if self._data is False:
            return (u, v)
        data = payload if isinstance(payload, dict) else {}
        if self._data is True:
            return (u, v, data)
        return (u, v, data.get(self._data, self._default))

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

    #: rustworkx edge index -> NetworkX edge key. Only ``RustworkxMultiGraph``
    #: tracks keys; a simple graph has none, so this stays ``None`` here.
    edge_keys: dict[int, Any] | None = None

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

    @staticmethod
    def _new_container(directed: bool):
        """Empty rustworkx container of the kind this wrapper class manages."""
        import rustworkx as rx

        return rx.PyDiGraph(multigraph=False) if directed else rx.PyGraph(multigraph=False)

    @classmethod
    def empty(cls, *, directed: bool = False, graph_attrs: dict[str, Any] | None = None):
        rx_graph = cls._new_container(directed)
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
        if isinstance(data, RustworkxGraph):
            out = cls._adopt(data)
            if out.is_directed() != directed:
                out = out.to_directed() if directed else out.to_undirected()
            out.graph.update(attrs)
            return out
        if isinstance(data, nx.Graph):
            if data.is_multigraph() and not cls._is_multigraph_class():
                raise nx.NetworkXError("nx-rustworkx does not collapse a MultiGraph into a Graph")
            out = cls._from_fresh(convert_from_nx(data, preserve_all_attrs=True))
            if out.is_directed() != directed:
                out = out.to_directed() if directed else out.to_undirected()
            out.graph.update(attrs)
            return out
        out = cls.empty(directed=directed, graph_attrs=attrs)
        try:
            out.add_edges_from(data)
        except Exception:
            tmp = cls._nx_class(directed)(data)
            out = cls._from_fresh(convert_from_nx(tmp, preserve_all_attrs=True))
            out.graph.update(attrs)
        return out

    @classmethod
    def _from_fresh(cls, converted: RustworkxGraph) -> RustworkxGraph:
        """Take ownership of a wrapper nothing else references.

        ``convert_from_nx`` built ``converted`` with its own containers and
        dicts, so adopting it as-is shares nothing with the caller's graph;
        only a class mismatch (simple data into a multigraph class) still
        needs ``_adopt`` to widen, which copies.
        """
        if type(converted) is cls:
            return converted
        return cls._adopt(converted)

    @classmethod
    def _is_multigraph_class(cls) -> bool:
        return False

    @classmethod
    def _nx_class(cls, directed: bool):
        import networkx as nx

        return nx.DiGraph if directed else nx.Graph

    @classmethod
    def _adopt(cls, other: RustworkxGraph) -> RustworkxGraph:
        """A copy of ``other`` as this class; only a multigraph class can widen."""
        import networkx as nx

        if type(other) is cls:
            return other.copy()
        if other.is_multigraph():
            raise nx.NetworkXError("nx-rustworkx does not collapse a MultiGraph into a Graph")
        return other.copy()

    def is_directed(self) -> bool:
        return self._directed

    def is_multigraph(self) -> bool:
        return False

    def number_of_nodes(self) -> int:
        return self.rx_graph.num_nodes()

    def number_of_edges(self, u=None, v=None) -> int:
        if u is None:
            return self.rx_graph.num_edges()
        return int(self.has_edge(u, v))

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

    def get_edge_data(self, u, v, default=None):
        try:
            u_idx = self.node_to_index[u]
            v_idx = self.node_to_index[v]
        except KeyError:
            return default
        rx_graph = self.rx_graph
        if not rx_graph.has_edge(u_idx, v_idx):
            return default
        payload = rx_graph.get_edge_data(u_idx, v_idx)
        return payload if payload is not None else {}

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
        u_idx = self.node_to_index[u_of_edge]
        v_idx = self.node_to_index[v_of_edge]
        rx_graph = self.rx_graph
        # NetworkX add_edge merges new attrs into an existing edge's dict and
        # never drops what is already there (a bare re-add is a no-op). The
        # has_edge check covers both container kinds: kernel-built containers
        # report multigraph=True, where rustworkx's add_edge would create a
        # parallel edge, and on multigraph=False it would replace the payload.
        if rx_graph.has_edge(u_idx, v_idx):
            if attr:
                payload = rx_graph.get_edge_data(u_idx, v_idx)
                if isinstance(payload, dict):
                    payload.update(attr)  # the stored dict itself, so this sticks
                else:
                    rx_graph.update_edge(u_idx, v_idx, dict(attr))
        else:
            rx_graph.add_edge(u_idx, v_idx, dict(attr) if attr else None)
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

    def add_weighted_edges_from(self, ebunch_to_add, weight="weight", **attr):
        self.add_edges_from(((u, v, {weight: d}) for u, v, d in ebunch_to_add), **attr)

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
        rx_graph = self.rx_graph.copy()
        # rustworkx's copy shares payload objects; NetworkX's copy gives every
        # edge its own attribute dict.
        for idx, (_u, _v, payload) in rx_graph.edge_index_map().items():
            if isinstance(payload, dict):
                rx_graph.update_edge_by_index(idx, dict(payload))
        copied = type(self)(
            rx_graph,
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=self._directed,
            graph_attrs=self.graph,
            node_attrs=_copy_node_attrs(self.node_attrs),
        )
        return copied

    def to_directed(self) -> RustworkxGraph:
        if self._directed:
            return self.copy()
        directed = self._new_container(True)
        directed.add_nodes_from(self._dense_payloads())
        # NetworkX gives each direction its own attribute dict.
        for u, v, data in self.rx_graph.weighted_edge_list():
            directed.add_edge(u, v, _copy_payload(data))
            if u != v:
                directed.add_edge(v, u, _copy_payload(data))
        return type(self)(
            directed,
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=True,
            graph_attrs=self.graph,
            node_attrs=_copy_node_attrs(self.node_attrs),
        )

    def to_undirected(self) -> RustworkxGraph:
        if not self._directed:
            return self.copy()
        undirected = self._new_container(False)
        undirected.add_nodes_from(self._dense_payloads())
        slots: dict = {}
        # NetworkX merges a reciprocal (v, u) into the (u, v) edge; later data
        # wins key by key, and the surviving edge gets its own dict.
        for u, v, data in self.rx_graph.weighted_edge_list():
            slot = (u, v) if u <= v else (v, u)
            existing = slots.get(slot)
            if existing is None:
                slots[slot] = undirected.add_edge(u, v, _copy_payload(data))
                continue
            payload = undirected.get_edge_data_by_index(existing)
            if isinstance(payload, dict) and isinstance(data, dict):
                payload.update(data)
            elif data is not None:
                undirected.update_edge_by_index(existing, _copy_payload(data))
        return type(self)(
            undirected,
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=False,
            graph_attrs=self.graph,
            node_attrs=_copy_node_attrs(self.node_attrs),
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
        # One Rust crossing for the whole row. PyDiGraph.adj mixes in both
        # directions, so ask for the outgoing side explicitly, as G.adj means.
        row = self.rx_graph.adj_direction(idx, False) if self._directed else self.rx_graph.adj(idx)
        index_to_node = self.index_to_node
        for nbr_idx, payload in row.items():
            yield index_to_node[nbr_idx], payload if payload is not None else {}

    def __str__(self) -> str:
        kind = "DiGraph" if self._directed else "Graph"
        return (
            f"Rustworkx{kind} with {self.number_of_nodes()} nodes "
            f"and {self.number_of_edges()} edges"
        )


class _MultiAdjView(_AdjView):
    """``G.adj`` for a multigraph: ``{nbr: {key: attrs}}`` keyed by node IDs."""

    def __getitem__(self, node: Any) -> dict:
        return self._graph._keyed_neighbor_items(node)


class _MultiEdgeView(_EdgeView):
    """``G.edges`` for a multigraph: iterates ``(u, v, key)`` like NetworkX."""

    __slots__ = ()

    def __iter__(self):
        return iter(_MultiEdgeDataView(self._graph, None, False, None, True))

    def __contains__(self, edge) -> bool:
        try:
            u, v, key = edge
        except ValueError:
            try:
                u, v = edge
            except ValueError:
                raise ValueError("MultiEdge must have length 2 or 3") from None
            key = 0
        return self._graph.has_edge(u, v, key)

    def __call__(self, nbunch=None, data=False, *, default=None, keys=False):
        if nbunch is None and data is False and keys is True:
            return self
        return _MultiEdgeDataView(self._graph, nbunch, data, default, keys)


class _MultiEdgeDataView(_EdgeDataView):
    """``G.edges(nbunch=..., data=..., keys=...)`` for a multigraph."""

    __slots__ = ("_keys",)

    def __init__(self, graph: RustworkxGraph, nbunch, data, default, keys):
        super().__init__(graph, nbunch, data, default)
        self._keys = keys

    def _iter_all(self):
        graph = self._graph
        index_to_node = graph.index_to_node
        for idx, (u_idx, v_idx, payload) in graph.rx_graph.edge_index_map().items():
            yield self._keyed(index_to_node[u_idx], index_to_node[v_idx], payload, idx)

    def _iter_nbunch(self):
        graph = self._graph
        node_to_index = graph.node_to_index
        index_to_node = graph.index_to_node
        rx_graph = graph.rx_graph
        seen: set[int] = set()
        for node in self._nbunch_nodes():
            incident = rx_graph.incident_edge_index_map(node_to_index[node])
            for edge_idx in sorted(incident):
                if edge_idx in seen:
                    continue
                seen.add(edge_idx)
                _u, nbr_idx, payload = incident[edge_idx]
                yield self._keyed(node, index_to_node[nbr_idx], payload, edge_idx)

    def _keyed(self, u, v, payload, idx):
        edge = (u, v, self._graph.edge_keys[idx]) if self._keys else (u, v)
        if self._data is False:
            return edge
        data = payload if isinstance(payload, dict) else {}
        if self._data is True:
            return (*edge, data)
        return (*edge, data.get(self._data, self._default))


class RustworkxMultiGraph(RustworkxGraph):
    """A rustworkx multigraph plus NetworkX's edge keys.

    rustworkx stores parallel edges natively and addresses every edge by a
    stable integer index. NetworkX addresses them by ``(u, v, key)``, so this
    wrapper keeps ``edge_keys`` (edge index -> key) next to the node map. The
    dict is insertion-ordered by edge addition, which is what gives
    ``remove_edge(u, v)`` NetworkX's "pop the most recently added key"
    behaviour even though rustworkx reuses freed indices.
    """

    def __init__(
        self,
        rx_graph: Any,
        node_to_index: dict[Any, int],
        index_to_node: list[Any],
        *,
        directed: bool,
        graph_attrs: dict[str, Any] | None = None,
        node_attrs: dict[Any, dict[str, Any]] | None = None,
        edge_keys: dict[int, Any] | None = None,
    ):
        super().__init__(
            rx_graph,
            node_to_index,
            index_to_node,
            directed=directed,
            graph_attrs=graph_attrs,
            node_attrs=node_attrs,
        )
        if edge_keys is None:
            # A container without parallel edges: every NetworkX key is 0.
            edge_keys = dict.fromkeys(rx_graph.edge_indices(), 0)
        self.edge_keys: dict[int, Any] = edge_keys

    @staticmethod
    def _new_container(directed: bool):
        import rustworkx as rx

        return rx.PyDiGraph(multigraph=True) if directed else rx.PyGraph(multigraph=True)

    @classmethod
    def _is_multigraph_class(cls) -> bool:
        return True

    @classmethod
    def _nx_class(cls, directed: bool):
        import networkx as nx

        return nx.MultiDiGraph if directed else nx.MultiGraph

    @classmethod
    def _adopt(cls, other: RustworkxGraph) -> RustworkxMultiGraph:
        """A copy of ``other`` as a multigraph; a simple graph's edges get key 0."""
        if isinstance(other, RustworkxMultiGraph):
            return other.copy()
        container = cls._new_container(other.is_directed())
        container.add_nodes_from(other._dense_payloads())
        container.add_edges_from(
            [(u, v, _copy_payload(data)) for u, v, data in other.rx_graph.weighted_edge_list()]
        )
        return cls(
            container,
            dict(other.node_to_index),
            list(other.index_to_node),
            directed=other.is_directed(),
            graph_attrs=other.graph,
            node_attrs=_copy_node_attrs(other.node_attrs),
        )

    def is_multigraph(self) -> bool:
        return True

    @property
    def adj(self) -> _AdjView:
        return _MultiAdjView(self)

    @property
    def edges(self) -> _EdgeView:
        return _MultiEdgeView(self)

    # --- keyed edge lookup ---------------------------------------------------

    def _edge_indices(self, u, v) -> list[int]:
        """rustworkx indices of the u-v bundle, oldest first (NetworkX key order)."""
        try:
            u_idx = self.node_to_index[u]
            v_idx = self.node_to_index[v]
        except KeyError:
            return []
        # rustworkx lists the newest edge first; NetworkX keydicts are oldest first.
        return sorted(self.rx_graph.edge_indices_from_endpoints(u_idx, v_idx))

    def _payload_dict(self, idx: int) -> dict:
        payload = self.rx_graph.get_edge_data_by_index(idx)
        return payload if isinstance(payload, dict) else {}

    def has_edge(self, u, v, key=None) -> bool:
        indices = self._edge_indices(u, v)
        if key is None:
            return bool(indices)
        edge_keys = self.edge_keys
        return any(edge_keys[idx] == key for idx in indices)

    def get_edge_data(self, u, v, key=None, default=None):
        indices = self._edge_indices(u, v)
        if not indices:
            return default
        edge_keys = self.edge_keys
        if key is None:
            return {edge_keys[idx]: self._payload_dict(idx) for idx in indices}
        for idx in indices:
            if edge_keys[idx] == key:
                return self._payload_dict(idx)
        return default

    def number_of_edges(self, u=None, v=None) -> int:
        if u is None:
            return self.rx_graph.num_edges()
        return len(self._edge_indices(u, v))

    def new_edge_key(self, u, v):
        """NetworkX's key allocator: the bundle size, bumped past any collision."""
        edge_keys = self.edge_keys
        used = {edge_keys[idx] for idx in self._edge_indices(u, v)}
        key = len(used)
        while key in used:
            key += 1
        return key

    def _keyed_neighbor_items(self, node: Any) -> dict:
        idx = self.node_to_index[node]
        # Outgoing edges only on a PyDiGraph, as G.adj means. rustworkx reports
        # every incident edge oriented away from the queried node, a self-loop once.
        incident = self.rx_graph.incident_edge_index_map(idx)
        index_to_node = self.index_to_node
        edge_keys = self.edge_keys
        out: dict = {}
        for edge_idx in sorted(incident):
            _u, nbr_idx, payload = incident[edge_idx]
            keyed = out.setdefault(index_to_node[nbr_idx], {})
            keyed[edge_keys[edge_idx]] = payload if payload is not None else {}
        return out

    # --- mutation -----------------------------------------------------------

    def _add_keyed_edge(self, u, v, key, data: dict | None):
        """Add or update the (u, v, key) edge; returns the key NetworkX would."""
        rx_graph = self.rx_graph
        edge_keys = self.edge_keys
        if key is None:
            key = self.new_edge_key(u, v)
        else:
            for idx in self._edge_indices(u, v):
                if edge_keys[idx] == key:
                    if data:
                        payload = rx_graph.get_edge_data_by_index(idx)
                        if isinstance(payload, dict):
                            payload.update(data)
                        else:
                            rx_graph.update_edge_by_index(idx, dict(data))
                    self.__networkx_cache__.clear()
                    return key
        idx = rx_graph.add_edge(self.node_to_index[u], self.node_to_index[v], data)
        # Assign, never setdefault: rustworkx reuses a freed index, and the old
        # key was dropped from the map when that edge was removed.
        edge_keys[idx] = key
        self.__networkx_cache__.clear()
        return key

    def add_edge(self, u_of_edge, v_of_edge, key=None, **attr):
        self.add_node(u_of_edge)
        self.add_node(v_of_edge)
        return self._add_keyed_edge(u_of_edge, v_of_edge, key, dict(attr) if attr else None)

    def add_edges_from(self, ebunch_to_add, **attr):
        import networkx as nx

        keys = []
        for edge in ebunch_to_add:
            count = len(edge)
            if count == 4:
                u, v, key, dd = edge
            elif count == 3:
                u, v, dd = edge
                key = None
            elif count == 2:
                u, v = edge
                dd = {}
                key = None
            else:
                raise nx.NetworkXError(f"Edge tuple {edge} must be a 2-tuple, 3-tuple or 4-tuple.")
            data = dict(attr)
            try:
                data.update(dd)
            except (TypeError, ValueError):
                if count != 3:
                    raise
                key = dd  # a 3-tuple whose third value is not a dict names the key
            self.add_node(u)
            self.add_node(v)
            keys.append(self._add_keyed_edge(u, v, key, data or None))
        return keys

    def remove_node(self, n):
        idx = self.node_to_index[n]
        rx_graph = self.rx_graph
        incident = (
            rx_graph.incident_edge_index_map(idx, all_edges=True)
            if self._directed
            else rx_graph.incident_edge_index_map(idx)
        )
        for edge_idx in incident:
            self.edge_keys.pop(edge_idx, None)
        super().remove_node(n)

    def remove_edge(self, u, v, key=None):
        import networkx as nx

        indices = self._edge_indices(u, v)
        if not indices:
            raise nx.NetworkXError(f"The edge {u}-{v} is not in the graph.")
        edge_keys = self.edge_keys
        if key is None:
            # NetworkX pops the most recently added key of the bundle.
            bundle = set(indices)
            idx = next(i for i in reversed(edge_keys) if i in bundle)
        else:
            idx = next((i for i in indices if edge_keys[i] == key), None)
            if idx is None:
                raise nx.NetworkXError(f"The edge {u}-{v} with key {key} is not in the graph.")
        self.rx_graph.remove_edge_from_index(idx)
        del edge_keys[idx]
        self.__networkx_cache__.clear()

    def clear(self):
        super().clear()
        self.edge_keys.clear()

    def copy(self) -> RustworkxMultiGraph:
        rx_graph = self.rx_graph.copy()
        # rustworkx's copy shares payload objects; NetworkX's copy gives every
        # edge its own attribute dict.
        for idx, (_u, _v, payload) in rx_graph.edge_index_map().items():
            if isinstance(payload, dict):
                rx_graph.update_edge_by_index(idx, dict(payload))
        return type(self)(
            rx_graph,
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=self._directed,
            graph_attrs=self.graph,
            node_attrs=_copy_node_attrs(self.node_attrs),
            edge_keys=dict(self.edge_keys),
        )

    def to_directed(self) -> RustworkxMultiGraph:
        if self._directed:
            return self.copy()
        directed = self._new_container(True)
        directed.add_nodes_from(self._dense_payloads())
        edge_map = self.rx_graph.edge_index_map()
        edge_keys: dict[int, Any] = {}
        # NetworkX emits (u, v, k) and (v, u, k) with copied data; a self-loop once.
        for idx, key in self.edge_keys.items():
            u, v, data = edge_map[idx]
            edge_keys[directed.add_edge(u, v, _copy_payload(data))] = key
            if u != v:
                edge_keys[directed.add_edge(v, u, _copy_payload(data))] = key
        return type(self)(
            directed,
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=True,
            graph_attrs=self.graph,
            node_attrs=_copy_node_attrs(self.node_attrs),
            edge_keys=edge_keys,
        )

    def to_undirected(self) -> RustworkxMultiGraph:
        if not self._directed:
            return self.copy()
        undirected = self._new_container(False)
        undirected.add_nodes_from(self._dense_payloads())
        edge_map = self.rx_graph.edge_index_map()
        edge_keys: dict[int, Any] = {}
        slots: dict = {}
        # NetworkX merges (u, v, k) and (v, u, k) into one edge; later data wins.
        for idx, key in self.edge_keys.items():
            u, v, data = edge_map[idx]
            slot = (u, v, key) if u <= v else (v, u, key)
            existing = slots.get(slot)
            if existing is None:
                new_idx = undirected.add_edge(u, v, _copy_payload(data))
                slots[slot] = new_idx
                edge_keys[new_idx] = key
                continue
            payload = undirected.get_edge_data_by_index(existing)
            if isinstance(payload, dict) and isinstance(data, dict):
                payload.update(data)
            elif data is not None:
                undirected.update_edge_by_index(existing, _copy_payload(data))
        return type(self)(
            undirected,
            dict(self.node_to_index),
            list(self.index_to_node),
            directed=False,
            graph_attrs=self.graph,
            node_attrs=_copy_node_attrs(self.node_attrs),
            edge_keys=edge_keys,
        )

    def _compact(self) -> None:
        """Rewrite rustworkx indices densely, keeping parallel edges and keys."""
        edge_map = self.rx_graph.edge_index_map()
        index_to_node = self.index_to_node
        keys = list(self.edge_keys.values())
        edges = [
            (index_to_node[edge_map[idx][0]], index_to_node[edge_map[idx][1]], edge_map[idx][2])
            for idx in self.edge_keys
        ]
        nodes = [index_to_node[i] for i in self.rx_graph.node_indices()]
        graph_attrs = dict(self.graph)
        node_attrs = dict(self.node_attrs)
        directed = self._directed
        self.clear()
        self._directed = directed
        self.graph.update(graph_attrs)
        self.node_attrs.update(node_attrs)
        self.add_nodes_from(nodes)
        node_to_index = self.node_to_index
        new_indices = self.rx_graph.add_edges_from(
            [(node_to_index[u], node_to_index[v], data) for u, v, data in edges]
        )
        self.edge_keys = dict(zip(new_indices, keys))

    def __str__(self) -> str:
        kind = "MultiDiGraph" if self._directed else "MultiGraph"
        return (
            f"Rustworkx{kind} with {self.number_of_nodes()} nodes "
            f"and {self.number_of_edges()} edges"
        )


def _copy_payload(data):
    return dict(data) if isinstance(data, dict) else data


def _copy_node_attrs(node_attrs: dict) -> dict:
    return {node: dict(data) for node, data in node_attrs.items()}
