# External benchmarks: nx-rustworkx dropped into real NetworkX projects

The scripts here take third-party projects that exercise the NetworkX API,
swap this backend in locally, and measure the difference. Third-party code is
cloned into a work directory at run time (never vendored) and pinned to a
known commit. `RESULTS.md` holds the latest committed run; regenerate it with
the commands below.

```bash
uv sync --extra test --extra bench
uv pip install nx-parallel osmnx   # T1 suite imports nx_parallel at discovery; T3 city download
uv run python benches/external/run_nx_parallel_asv.py
uv run python benches/external/run_networkx_asv.py
uv run python benches/external/osmnx_demo.py
uv run python benches/external/summarize.py \
    --t1 benches/external/.work/results-nx-parallel \
    --t2 benches/external/.work/results-networkx \
    --t3 benches/external/.work/results-osmnx/osmnx.json
```

## The three targets

| | project | how the backend gets in | what it shows |
|---|---|---|---|
| T1 | [networkx/nx-parallel](https://github.com/networkx/nx-parallel) `benchmarks/` (asv) | one-line patch: `backends = ["rustworkx", None]` — the suite passes `backend=` per call | forced dispatch, cold calls, conversion included; side-by-side grid vs stock NetworkX |
| T2 | [networkx/networkx](https://github.com/networkx/networkx) `benchmarks/` (asv, bundled in the main repo) | **zero code changes** — second arm sets `NETWORKX_BACKEND_PRIORITY=rustworkx` | the honest "existing user code gets faster" test, auto-dispatch rules and all |
| T3 | [OSMnx](https://github.com/gboeing/osmnx)-style city routing | one line: `ox.convert.to_digraph(G, weight="travel_time")` (OSMnx graphs are MultiDiGraphs, which this backend rejects) | real-world workload: batch routing, weighted closeness, betweenness, pagerank |

Every run proves dispatch actually happened: T1/T3 force `backend="rustworkx"`
(a wrapper counts calls reaching the backend; T3 asserts on it), and T2 ships a
probe (`dispatch-probe.json`) that records, per benchmark graph, whether
`can_run`/`should_run` would auto-dispatch and why not otherwise. A ~1.0×
row must always be explained by that probe.

## Things that bite when dropping this backend into a project

- `NETWORKX_BACKEND_PRIORITY` is read **at import time**; setting
  `os.environ` after `import networkx` does nothing. Generators need
  `NETWORKX_BACKEND_PRIORITY_GENERATORS` separately.
- Auto-dispatch declines graphs with **n < 200 or m < 400**
  (`nx.config.backends.rustworkx.min_nodes/min_edges`) and 22 functions are
  implemented but never auto-selected (`NO_AUTO_DISPATCH` in
  `nx_rustworkx/algorithms/_utils.py`). Explicit `backend="rustworkx"`
  bypasses the size floor, not compatibility.
- **MultiGraph/MultiDiGraph never dispatch** — OSMnx, momepy and pandapower
  all hand NetworkX multigraphs, so they need a DiGraph conversion first.
- **Weighted betweenness falls back** (unweighted is supported), as do
  callable weights, `cutoff=`, betweenness `k=` sampling, and other kwargs
  listed in `nx_rustworkx/_info.py`.
- NetworkX caches conversions on the graph (`cache_converted_graphs`, default
  on since 3.4); any graph mutation clears the cache. Repeat-call workloads
  pay conversion once — don't mutate the graph between calls.

## Other projects evaluated

Also viable, not scripted here:

- **[graphblas-algorithms](https://github.com/python-graphblas/graphblas-algorithms)**
  `scripts/bench.py` — single-function CLI timer on real SuiteSparse graphs.
  Zero-change via `-b networkx` + `NETWORKX_BACKEND_PRIORITY=rustworkx`
  (its networkx arm is a bare `getattr(nx, func)`). `sparse.tamu.edu` is
  blocked from some CI containers; fine on a laptop, or pass `-d local.mtx`.
- **[momepy](https://github.com/pysal/momepy)** — street-network centralities;
  `momepy.closeness_centrality` dispatches if the graph is built with
  `gdf_to_nx(..., multigraph=False)`. Its weighted-betweenness and
  `ego_graph` radius modes fall back.

Evaluated and skipped:

- **[nx-cugraph](https://github.com/rapidsai/nx-cugraph)** pytest-benchmark
  suite — the broadest coverage (~65 benchmarks), but module-level
  `cupy`/`cugraph` imports and `cugraph.datasets` make it GPU-stack-only;
  its benchmark bodies are good harvest material later.
- **[nxbench](https://github.com/dPys/nxbench)** — purpose-built
  cross-backend suite, but stale (early 2025) and needs Prefect + Dask +
  PostgreSQL running.
- **[retworkx-comparison-benchmarks](https://github.com/mtreinish/retworkx-comparison-benchmarks)**
  — the 2021 rustworkx-paper workloads (DIMACS road networks); predates the
  dispatch mechanism, per-library venvs, no reusable harness.

Will **not** benefit from any NetworkX backend (verified against their
sources): karateclub, cdlib, GraphRAG (hand-rolled loops or non-NetworkX
engines on the hot path), pgmpy/dowhy (tiny causal DAGs below the dispatch
floor, key calls unimplemented), Airflow/Snakemake (no NetworkX dependency).
