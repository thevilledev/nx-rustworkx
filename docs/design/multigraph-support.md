# Design note: MultiGraph and MultiDiGraph support

Status: accepted and implemented (2026-08-23).

All semantics claims below were verified against networkx 3.6.1 and
rustworkx 0.18.1 (CPython 3.12). The NetworkX 3.4 floor dispatches the same
names; only the class-constructor dispatch (`nx.MultiGraph(backend=...)`) needs
NetworkX 3.6, as it does for `nx.Graph`.

## Summary

The backend used to refuse every `MultiGraph` and `MultiDiGraph` at `can_run`,
so road networks (OSMnx), transport and infrastructure graphs, and a good share
of NetworkX's own fixtures never dispatched: `NETWORKX_BACKEND_PRIORITY`
silently fell back to NetworkX, and `benches/external/osmnx_demo.py` had to
collapse its `MultiDiGraph` with `ox.convert.to_digraph` first. The README sold
the absence as a feature.

Decision: **accept multigraphs wherever the backend reproduces NetworkX's
multigraph semantics exactly, and fall back where NetworkX itself refuses or
where the kernel cannot be made exact.** The result:

| | functions | how |
|---|---|---|
| accepted with no kernel change | 80 | the rustworkx kernel already agrees with NetworkX on parallel edges |
| accepted after an adaptation | 17 | collapsed view, min-over-parallel, keyed results |
| refused (falls back) | 14 | NetworkX raises, crashes, or keys the result by edge identity the kernel drops |

Rustworkx can do it: `PyGraph`/`PyDiGraph` are multigraphs by default
(`multigraph=True`), store parallel edges natively under stable integer edge
indices, and expose `edge_index_map`, `edge_indices_from_endpoints`,
`get_all_edge_data`, `incident_edge_index_map`, `remove_edge_from_index` and
`has_parallel_edges`. `degree()` counts parallel edges and a self-loop twice,
exactly like NetworkX. What rustworkx lacks is NetworkX's `(u, v, key)`
addressing, which the wrapper supplies, and NetworkX's *multigraph semantics*
in a handful of kernels, which the adaptations supply.

## Where rustworkx and NetworkX disagree on parallel edges

| kernel family | rustworkx | NetworkX | consequence |
|---|---|---|---|
| Dijkstra, Bellman-Ford, BFS, A*, eccentricity family, closeness | the lightest parallel edge wins during relaxation | `_weight_function` takes the minimum over parallel edges | match natively |
| `pagerank`, `hits` | parallel weights are summed (documented) | `to_scipy_sparse_array` sums them | match (1e-16 unweighted) |
| components, DAG family (`dag_longest_path` takes the max in both), VF2 isomorphism (multiplicity honoured), `all_simple_paths` (both emit a node path once per parallel edge), `simple_cycles`, `greedy_color`, degree centralities | agree | agree | match natively |
| `betweenness_centrality` (node, edge, group) | every parallel edge is a distinct shortest path: `{1: .667, 3: .333}` on `0->1 x2, 1->2, 0->3, 3->2` | paths are counted over `G[v]`, so parallels collapse: `{1: .5, 3: .5}`; edge betweenness is keyed `(u, v, key)` with the pair's score split over its minimum-weight keys | run on the collapsed view, then split |
| `bridges` | reports a parallel bundle as a bridge | skips any pair with `len(G[u][v]) > 1` | collapsed view plus multiplicity filter |
| `minimum_spanning_*`, `steiner_tree`, `find_cycle`, `line_graph` | picks the right edge but returns payloads, not edge identities | `(u, v, key, data)` tuples, `MultiGraph` results, `(u, v, key)` line nodes | map through edge index -> key |
| `_path_weight` (`single_source_dijkstra(target=)`, `single_source_bellman_ford(target=)`, `astar_path_length`) | `get_edge_data(u, v)` returns an arbitrary parallel payload | minimum | `min` over `get_all_edge_data` |
| `all_shortest_paths` | the same node path once per equal-weight parallel edge | once | run on the min-collapsed view |
| `core_number`, `cycle_basis`, `chain_decomposition`, `stoer_wagner`, `max_weight_matching`, `eigenvector_centrality`, `katz_centrality(_numpy)`, `transitivity` | "assumes no parallel edges" or garbage | `NetworkXNotImplemented` | keep refusing |
| `is_maximal_matching`, `complement`, `cartesian_product`, `tensor_product`, `vf2pp_all_isomorphisms` | - | crashes on `for u, v in G.edges`; doubles every non-edge; keys product edges by the factors' keys; mapping multiplicity unverified | keep refusing |

## Dispatch mechanics that constrain the design

1. NetworkX caches `convert_from_nx` results on the NetworkX graph keyed only by
   the attribute-preservation flags, never by function name. The converted graph
   must therefore be *faithful* (every parallel edge kept); any collapsing
   happens inside the wrappers and is cached on the wrapper object.
2. NetworkX's test harness (`NETWORKX_TEST_BACKEND=rustworkx`, the CI gate)
   strict-compares graph-valued results: `_adj`, `_node`, `graph` and
   `is_multigraph()`. Keys must round-trip exactly.
3. `can_run` sees the NetworkX graph before conversion and also already-wrapped
   backend graphs, so the wrapper's `is_multigraph()` must be honest.
4. `nx.MultiGraph(backend=...)` dispatches to the backend names
   `multigraph__new__` and `multidigraph__new__`.

## The design

### Faithful conversion and an honest wrapper subclass

`RustworkxMultiGraph(RustworkxGraph)` in `nx_rustworkx/graph.py` is a subclass
rather than a flag: the simple-graph methods stay untouched, `copy`,
`to_directed`, `to_undirected` and `from_incoming` already propagate the class,
and `add_edge(u, v, key=None, **attr)` cannot share a signature with the simple
class, where an edge attribute literally named `key` is legal. The subclass
holds `edge_keys: dict[int, Any]` (rustworkx edge index -> NetworkX key),
insertion-ordered by edge addition, with the invariant
`set(edge_keys) == set(rx_graph.edge_indices())`. That order is what gives
`remove_edge(u, v)` NetworkX's "pop the most recently added key" behaviour even
though rustworkx reuses freed indices.

`convert_from_nx` walks `G.adj[u][v]` as a key dict and emits one rustworkx
edge per key (the same adjacency walk as before, a self-loop once);
`rustworkx_graph_to_nx` rebuilds a `MultiGraph`/`MultiDiGraph` from 4-tuples
`(u, v, key, attrs)` so an attribute named `key` cannot collide with the
keyword. `as_directed_rx` builds a `multigraph=True` container for multigraph
wrappers so the weight-summing kernels (pagerank, hits, Floyd-Warshall,
negative-cycle detection) see every parallel edge.

### One central capability gate

Every function declares `func.multigraph = True` next to its `func.can_run`
line (opt-in; default refuses). `BackendInterface.can_run` applies
`multigraph_reason` before the function's own checker, so a refused multigraph
never reaches a checker that indexes `G.adj[u][v]` expecting an attribute dict.
`create_using=nx.MultiGraph` passes a class, which the gate special-cases. The
old `reject_multigraph` helper and its 37 call sites are gone; `_info.py`
mirrors the refused set in `_MULTIGRAPH_REFUSED` (it cannot import the
kernels) and `tests/test_multigraph.py` asserts the two agree.

### The collapsed view

`simple_view(rwg, weight=None)` in `algorithms/_utils.py` returns a cached
`SimpleView`: a `multigraph=False` container over the same node indices whose
edge payload is the *original* edge index of the bundle's representative (the
first key, or the first of the lightest keys when weighted, which is NetworkX's
min-over-parallel rule with its stable first-key tie-break), plus the bundles.
It is built with one Rust call: on a `multigraph=False` container
`add_edges_from` updates a duplicate pair in place and returns the existing
index, so the returned list is the original -> collapsed map. The view lives in
the wrapper's `__networkx_cache__` under a backend-private key, so every
mutator's existing `.clear()` invalidates it and NetworkX's `"backends"` entry
is untouched. Measured at 23 ms for 200k edges.

Betweenness (node, group), articulation points and biconnected components run
on the view. Edge betweenness runs on the view and splits each pair's score
over its keys. Bridges run on the view and drop pairs with multiplicity above
one. `is_planar` collapses to a simple undirected container. `all_shortest_paths`
and `single_source_all_shortest_paths` run on the weighted view. The spanning
trees and `steiner_tree` run on the weighted view so the payload leads back to
the key; `minimum_spanning_edges` honours `keys`/`data` with NetworkX's four
tuple shapes, calls the kernel lazily so a NaN weight raises on iteration as
NetworkX's generator does, and refuses `algorithm="boruvka"` on a multigraph
because NetworkX does. `find_cycle` attaches the first key of each pair, as
`edge_dfs` reports it. `line_graph` names its nodes `(u, v, key)` and
deduplicates the line edges rustworkx emits once per shared endpoint.

### Constructors

`multigraph__new__` and `multidigraph__new__` mirror the simple constructors;
`empty_graph` and `from_edgelist` pick the wrapper class from `create_using`.
`RustworkxMultiGraph.from_incoming` widens a simple graph (every edge gets key
0, attribute dicts copied); a simple class never silently collapses a
multigraph. The native kernel generators still fall back for a multigraph
`create_using` (non-goal below).

## Measured effect

NetworkX's algorithm suite through the backend: multigraph-related `can_run`
refusals fell from 437 to 53 (the remaining 53 are the kernel generators with a
multigraph `create_using`, the two products and one boruvka case); accepted
calls rose from 5933 to 6339 with no failures and no new `on_start_tests`
xfail. `benches/bench_parity.py` gained `name[multi]` rows; every one measures
faster than NetworkX at n=800 (betweenness 54x, bridges 25x, weighted closeness
101x, pagerank 1.6x, minimum spanning tree 6x) and stays auto-dispatched.

## Non-goals

- Native kernel generators with a multigraph `create_using`: NetworkX produces
  parallel edges in degenerate sizes (`cycle_graph(2, create_using=MultiGraph)`,
  periodic grids) that are not worth reproducing in Rust; the fallback is cheap.
- `complement`, `cartesian_product`, `tensor_product`, `vf2pp_all_isomorphisms`
  on multigraphs: NetworkX keys these by edge identity the rustworkx kernels
  drop (or, for `complement`, doubles every non-edge, a quirk not worth
  mirroring).
- Weighted betweenness: still refused by `can_run`; unrelated to multigraphs.
- `nx.Graph(multigraph, backend="rustworkx")`: NetworkX merges the parallel
  attribute dicts in key order; the backend keeps refusing rather than
  approximating that.

## Settled and remaining items

1. **Settled:** parallel-edge semantics follow NetworkX exactly or the function
   falls back; no "documented divergence" path was opened for multigraphs.
2. **Settled:** the collapsed view is cached per wrapper and weight, never
   across wrappers, so NetworkX's own conversion cache remains the only
   cross-call state.
3. Surfaced while auditing, fixed in passing: undirected `degree_centrality`
   now counts a self-loop twice like NetworkX (`rx.degree_centrality` counts it
   once), and `G.edges(nbunch)` on a directed wrapper now yields out-edges only,
   as NetworkX's `OutEdgeDataView` does.
4. Follow-up for `benches/external/osmnx_demo.py` (PR #17): route on the
   `MultiDiGraph` directly and drop the `to_digraph` step and the "never
   dispatch" notes.
