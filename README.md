# nx-rustworkx

A [NetworkX](https://networkx.org) 3.x backend that dispatches selected algorithms to [rustworkx](https://www.rustworkx.org).

You keep `import networkx as nx`. This package converts `nx.Graph` to rustworkx, runs the kernel, and remaps results to the original node IDs. It does not reimplement `Graph`, drawing, or I/O. Unimplemented functions fall through to NetworkX.

This is not a drop-in NetworkX replacement and not a rustworkx fork. Install it, set the backend, and the functions below get faster.

## Install

```bash
pip install nx-rustworkx
```

From this repository:

```bash
pip install -e .
```

Requires Python 3.10+ , NetworkX 3.2+, and a published rustworkx wheel. v0 does not compile custom Rust.

## Enable

```bash
NETWORKX_BACKEND_PRIORITY=rustworkx python your_script.py
```

```python
import networkx as nx

G = nx.erdos_renyi_graph(500, 0.05, seed=0)
nx.config.backend_priority = ["rustworkx"]
nx.betweenness_centrality(G)  # hits rustworkx when the graph is large enough
```

Or select a call explicitly:

```python
import networkx as nx
import nx_rustworkx as nxrx  # optional; not the primary UX

G = nx.gnp_random_graph(2000, 0.01, seed=1)
nx.betweenness_centrality(G, backend="rustworkx")
```

`should_run` skips conversion on small graphs (default **n < 200** or **m < 400**) so tiny examples stay on NetworkX. `backend="rustworkx"` always tries the kernel.

Tune the cutoff after import:

```python
nx.config.backends.rustworkx.min_nodes = 200
nx.config.backends.rustworkx.min_edges = 400
```

## Supported functions

93 NetworkX entry points dispatch to rustworkx. Anything not listed runs on
NetworkX as usual.

| Area | Functions |
|---|---|
| Centrality | `betweenness_centrality`, `closeness_centrality`, `degree_centrality`, `edge_betweenness_centrality`, `eigenvector_centrality`, `group_betweenness_centrality`, `group_closeness_centrality`, `group_degree_centrality`, `hits`, `in_degree_centrality`, `katz_centrality`, `katz_centrality_numpy`, `out_degree_centrality` |
| Link analysis | `pagerank` |
| Shortest paths | `shortest_path`, `shortest_path_length`, `dijkstra_path`, `dijkstra_path_length`, `bellman_ford_path`, `bellman_ford_path_length`, `bidirectional_shortest_path`, `has_path`, `all_shortest_paths` |
| Single source | `single_source_dijkstra`, `single_source_dijkstra_path`, `single_source_dijkstra_path_length`, `single_source_bellman_ford`, `single_source_bellman_ford_path`, `single_source_bellman_ford_path_length`, `single_source_shortest_path`, `single_source_shortest_path_length`, `single_target_shortest_path`, `single_target_shortest_path_length` |
| All pairs | `all_pairs_dijkstra`, `all_pairs_dijkstra_path`, `all_pairs_dijkstra_path_length`, `all_pairs_bellman_ford_path`, `all_pairs_bellman_ford_path_length`, `all_pairs_shortest_path`, `all_pairs_shortest_path_length`, `floyd_warshall`, `floyd_warshall_numpy`, `floyd_warshall_predecessor_and_distance`, `average_shortest_path_length` |
| Heuristic search | `astar_path`, `astar_path_length` |
| Negative cycles | `negative_edge_cycle`, `find_negative_cycle` |
| DAG | `is_directed_acyclic_graph`, `topological_sort`, `topological_generations`, `ancestors`, `descendants`, `descendants_at_distance`, `dag_longest_path`, `dag_longest_path_length`, `transitive_reduction`, `immediate_dominators` |
| Traversal | `dfs_edges` |
| Connectivity | `is_connected`, `is_weakly_connected`, `is_strongly_connected`, `is_semiconnected`, `connected_components`, `weakly_connected_components`, `strongly_connected_components`, `number_connected_components`, `number_weakly_connected_components`, `number_strongly_connected_components`, `node_connected_component`, `articulation_points`, `bridges`, `biconnected_components`, `condensation`, `stoer_wagner` |
| Cycles and cores | `simple_cycles`, `cycle_basis`, `core_number` |
| Structure | `is_bipartite`, `isolates`, `number_of_isolates`, `transitivity` |
| Matching and coloring | `max_weight_matching`, `greedy_color` |
| Trees | `minimum_spanning_tree`, `minimum_spanning_edges`, `steiner_tree` |
| Operators | `complement`, `cartesian_product`, `tensor_product` |
| Simple paths | `all_simple_paths` |
| Isomorphism | `is_isomorphic`, `vf2pp_is_isomorphic` |

Every function's caveats are published through `get_info()`, so
`help(nx.betweenness_centrality)` shows what this backend does and does not
honor.

## Benchmarks

Same graphs, same seeds. Convert time is reported separately from the rustworkx kernel. If convert is more than ~30% of runtime, `should_run` should have said no.

Command:

```bash
python benches/bench_centrality.py
```

`betweenness_centrality` on `gnp_random_graph(n, p, seed=1)`, measured on a 4-core Linux VM:

| n | m | convert (s) | kernel (s) | rustworkx total (s) | NetworkX (s) | speedup | convert share |
|---|---|-------------|------------|---------------------|--------------|---------|---------------|
| 200 | 2035 | 0.00031 | 0.0019 | 0.0048 | 0.067 | 14x | 6.5% |
| 2000 | 20050 | 0.0043 | 0.19 | 0.30 | 8.4 | **28x** | 1.4% |
| 20000 | 200473 | 0.098 | 50 | 52 | — | — | 0.19% |

The 2k-node row is the public milestone graph (`n=2000`, `p=0.01`, `seed=1`). Conversion stays well under 30% of runtime, so `should_run` correctly accepts these graphs. NetworkX on 20k nodes is omitted because Brandes is impractical there.

## Limits

Arguments this backend cannot honor are rejected in `can_run`, so NetworkX
runs those calls itself and the answer stays correct:

- No MultiGraph / MultiDiGraph
- No custom weight callables (`weight=func`)
- `cutoff` on the shortest-path functions
- Betweenness is unweighted Brandes (no `k=` sampling); closeness is unweighted
- `is_isomorphic` is structural only (`node_match` / `edge_match` fall through)
- `greedy_color` implements `largest_first` only
- `max_weight_matching` needs integer edge weights
- `astar_path` needs a heuristic that is consistent, not merely admissible.
  `can_run` verifies that over the edge set and falls back when it does not
  hold; set `nx.config.backends.rustworkx.astar_heuristic_check = False` to
  skip the check when you already know your heuristic is consistent.

Where an answer is not unique, rustworkx may return a different valid one than
NetworkX: `topological_sort` order, `dag_longest_path`, `cycle_basis`, the
predecessors from `floyd_warshall_predecessor_and_distance`, the starting node
of `find_negative_cycle`, and which minimum spanning forest
`minimum_spanning_tree` picks when weights tie.

Functions left to NetworkX on purpose, because rustworkx would answer
differently rather than faster: `bfs_layers` (NetworkX documents ordered layers
and rustworkx orders them differently), `dominance_frontiers` (rustworkx
disagrees when the start node lies on a cycle),
`lexicographical_topological_sort` (rustworkx needs a `str` key, which reorders
non-string nodes), and `is_matching` / `is_maximal_matching` (linear checks
where conversion costs more than the check).

Numeric values may differ slightly for PageRank, HITS, Katz and eigenvector
centrality (float order, damping, iteration).

Graph-returning functions (`minimum_spanning_tree`, `transitive_reduction`,
`complement`, `condensation`, `steiner_tree`, the products) return real
NetworkX graphs. NetworkX does not convert backend results back for you, so
returning the backend wrapper would hand you an object with no `.nodes`.

Do not `import nx_rustworkx as networkx`.

## Tests

```bash
pip install -e ".[test]"
pytest tests
```

The package suite checks results against NetworkX function by function, and
`tests/test_signatures.py` asserts every backend function accepts NetworkX's
positional parameters in the same order and with the same defaults.

NetworkX's own suite is the real compatibility check. It runs every dispatchable
call through this backend and compares against NetworkX:

```bash
NETWORKX_TEST_BACKEND=rustworkx pytest --pyargs networkx.algorithms
```

## Layout

```text
nx_rustworkx/
  interface.py          # BackendInterface
  convert.py            # nx <-> rustworkx + node map
  graph.py              # wrapper with __networkx_backend__
  algorithms/           # thin rustworkx wrappers, one module per area
  _info.py              # get_info(); no rustworkx import
```

Each module in `algorithms/` lists the NetworkX names it implements in
`__all__`. `algorithms.ALGORITHMS` is the union of those lists and drives both
the backend interface and the metadata in `_info.py`.

Entry points:

```toml
[project.entry-points."networkx.backends"]
rustworkx = "nx_rustworkx.interface:BackendInterface"

[project.entry-points."networkx.backend_info"]
rustworkx = "nx_rustworkx._info:get_info"
```

## License

BSD-3-Clause (same family as NetworkX, for an easier listing later). rustworkx itself remains Apache-2.0.
