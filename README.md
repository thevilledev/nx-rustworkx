# nx-rustworkx

A [NetworkX](https://networkx.org) 3.x backend that dispatches selected algorithms to [rustworkx](https://www.rustworkx.org).

You keep `import networkx as nx`. This package converts `nx.Graph` to rustworkx, runs the kernel, and remaps results to the original node IDs. It does not reimplement drawing or I/O. Unimplemented functions fall through to NetworkX when the input is still an `nx.Graph`.

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

## Skip conversion (Phase 3)

Build the rustworkx graph once, then algorithms run without `convert_from_nx`:

```python
import networkx as nx

G = nx.Graph([(0, 1), (1, 2), (2, 0)], backend="rustworkx")
nx.betweenness_centrality(G)  # already a rustworkx graph

# Or let generators return rustworkx graphs:
# NETWORKX_BACKEND_PRIORITY_GENERATORS=rustworkx
nx.config.backend_priority.generators = ["rustworkx"]
H = nx.gnp_random_graph(500, 0.05, seed=0)
nx.betweenness_centrality(H)
```

`H` is a `RustworkxGraph`, not an `nx.Graph`. It supports construction (`add_node`, `add_edge`, `add_edges_from`, `clear`) and the methods algorithms need. It is not a drop-in NetworkX graph (no drawing, no MultiGraph).

If you then call an algorithm this backend does not implement, NetworkX raises unless fallback is on:

```bash
NETWORKX_BACKEND_PRIORITY_GENERATORS=rustworkx \
NETWORKX_FALLBACK_TO_NX=true \
python your_script.py
```

```python
nx.config.fallback_to_nx = True
nx.triangles(H)  # converts H to nx.Graph, then runs NetworkX
```

Without `NETWORKX_FALLBACK_TO_NX`, keep using `nx.Graph` plus `NETWORKX_BACKEND_PRIORITY=rustworkx` so unimplemented functions stay on NetworkX.

Tune the cutoff after import:

```python
nx.config.backends.rustworkx.min_nodes = 200
nx.config.backends.rustworkx.min_edges = 400
```

## Supported in 0.2

| Area | Functions |
|---|---|
| Centrality | `betweenness_centrality`, `edge_betweenness_centrality`, `closeness_centrality`, `eigenvector_centrality` |
| Shortest paths | `shortest_path`, `shortest_path_length`, `single_source_dijkstra`, `dijkstra_path`, `bellman_ford_path` |
| Connectivity | `is_connected`, `is_weakly_connected`, `connected_components`, `weakly_connected_components`, `number_connected_components` |
| Link analysis | `pagerank` |
| Isomorphism | `is_isomorphic` (structural VF2) |
| Construction | `nx.Graph` / `nx.DiGraph` (`backend="rustworkx"`), `empty_graph`, `from_edgelist` |

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

- No MultiGraph / MultiDiGraph
- No custom weight callables (`weight=func`)
- Betweenness is unweighted Brandes (no `k=` sampling)
- Closeness is unweighted (`distance=` is not implemented)
- `is_isomorphic` is structural only (`node_match` / `edge_match` fall through)
- Numeric values may differ slightly for PageRank and eigenvector centrality (float order, damping, iteration)
- Do not `import nx_rustworkx as networkx`

## Tests

```bash
pip install -e ".[test]"
pytest tests
NETWORKX_TEST_BACKEND=rustworkx pytest --pyargs networkx.algorithms.centrality.tests -k TestBetweennessCentrality
```

## Layout

```text
nx_rustworkx/
  interface.py          # BackendInterface
  convert.py            # nx <-> rustworkx + node map
  graph.py              # rustworkx-backed graph object
  generators.py         # Graph/DiGraph/empty_graph/from_edgelist
  algorithms/           # thin rustworkx wrappers
  _info.py              # get_info(); no rustworkx import
```

Entry points:

```toml
[project.entry-points."networkx.backends"]
rustworkx = "nx_rustworkx.interface:BackendInterface"

[project.entry-points."networkx.backend_info"]
rustworkx = "nx_rustworkx._info:get_info"
```

## License

BSD-3-Clause (same family as NetworkX, for an easier listing later). rustworkx itself remains Apache-2.0.
