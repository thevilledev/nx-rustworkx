# nx-rustworkx

A [NetworkX](https://networkx.org/) 3.x backend that accelerates selected graph
algorithms with [rustworkx](https://www.rustworkx.org/).

Keep `import networkx as nx`. nx-rustworkx converts an `nx.Graph`, runs the
rustworkx kernel, and remaps the result to the original node IDs. Unsupported
calls stay on NetworkX.

## Install

```bash
pip install nx-rustworkx
```

Requires Python 3.10+, NetworkX 3.4+, and rustworkx 0.15+.

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

The backend implements 93 algorithms. Its measured cutoffs keep small or
conversion-heavy calls on NetworkX; `backend="rustworkx"` explicitly tries the
rustworkx implementation.

## Documentation

Usage, configuration, supported algorithms, caveats, and benchmarks:
[ville.dev/nx-rustworkx](https://ville.dev/nx-rustworkx/)

## Limits

- Simple graphs and digraphs only; no multigraphs.
- No custom weight callables.
- The rustworkx-backed graph object does not implement drawing or I/O.
- Some valid results may differ in ordering or floating-point rounding.

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
