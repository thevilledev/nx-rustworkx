# nx-rustworkx

A [NetworkX](https://networkx.org/) 3.x backend that accelerates selected graph
algorithms with [rustworkx](https://www.rustworkx.org/).

Keep `import networkx as nx`. nx-rustworkx converts an `nx.Graph`, runs the
rustworkx kernel, and remaps the result to the original node IDs. Unsupported
calls stay on NetworkX.

## How much faster?

Real NetworkX projects with the backend switched on, application code
unchanged — measured by the runners in
[`benches/external/`](benches/external/RESULTS.md) on one 4-CPU machine:

| workload | NetworkX | nx-rustworkx | speedup |
|---|---:|---:|---:|
| City street network (OSMnx MultiDiGraph), weighted closeness centrality | 358 s | 2.6 s | **136×** |
| Same network, betweenness centrality | 115 s | 1.5 s | **78×** |
| Same network, 200 point-to-point travel-time routes | 8.0 s | 2.3 s | **3.4×** |
| nx-parallel's benchmark suite, all-pairs Bellman–Ford lengths (n=400) | 18.7 s | 0.44 s | **42×** |
| NetworkX's own benchmark suite, strongly connected components (n=10,000) | 32 ms | 4 ms | **8×** |

**Good fit:** CPU-heavy whole-graph algorithms on graphs from a few hundred
nodes up — centralities, all-pairs shortest paths, components, isomorphism —
and repeat-call pipelines, where the one-time conversion is cached across
calls. Street networks work as-is: MultiDiGraphs with parallel ways dispatch
with NetworkX's parallel-edge semantics.

**Not the tool:** tiny graphs (auto-dispatch declines below 200 nodes or 400
edges on purpose), one-off calls to linear-time functions where conversion
costs more than NetworkX's answer, algorithms NetworkX already runs on
C-backed SciPy (`pagerank`), custom weight callables, and code that walks
`G.adj` itself instead of calling `nx.*` functions — a backend can only
accelerate the NetworkX API.

## Install

```bash
pip install nx-rustworkx
```

Requires Python 3.10+, NetworkX 3.4+, and rustworkx 0.18+.

## Use

Set rustworkx as a preferred backend:

```bash
NETWORKX_BACKEND_PRIORITY=rustworkx python your_script.py
```

Or configure it in Python:

```python
import networkx as nx

G = nx.erdos_renyi_graph(2_000, 0.01, seed=1)
nx.config.backend_priority = ["rustworkx"]

scores = nx.betweenness_centrality(G)
```

The backend implements 111 algorithms. Its measured cutoffs keep small or
conversion-heavy calls on NetworkX; `backend="rustworkx"` explicitly tries the
rustworkx implementation.

Generators such as `nx.path_graph` and `nx.gnp_random_graph` can construct
rustworkx-backed graphs directly, so whole pipelines skip conversion; the
[usage guide](https://ville.dev/nx-rustworkx/usage.html) covers enabling
generator dispatch.

## Documentation

Usage, configuration, supported algorithms, caveats, and benchmarks:
[ville.dev/nx-rustworkx](https://ville.dev/nx-rustworkx/)

## Limits

- `MultiGraph` and `MultiDiGraph` dispatch with NetworkX's parallel-edge
  semantics (minimum weight for paths, summed weights for PageRank, collapsed
  bundles for betweenness and bridges, keyed results for spanning trees). The
  14 functions NetworkX itself refuses on multigraphs, plus `complement`, the
  graph products and `vf2pp_all_isomorphisms`, fall back to NetworkX; so do
  the native generators when `create_using` is a multigraph class.
- No custom weight callables.
- The rustworkx-backed graph object does not implement drawing or I/O.
- Some valid results may differ in ordering or floating-point rounding.
- Seeded random generators reproduce NetworkX's graphs unless
  `native_seeded_generators` is enabled; the opt-in draws from rustworkx's
  RNG, so the same seed gives a different, equally valid graph.

The [algorithm reference](https://ville.dev/nx-rustworkx/algorithms.html) lists
the exact behavior and fallback conditions.

## Development

```bash
uv sync --extra test
uv run pytest tests
```

See the [development guide](https://ville.dev/nx-rustworkx/development.html) for
the full test, lint, benchmark, and architecture notes.

## License

BSD-3-Clause.
