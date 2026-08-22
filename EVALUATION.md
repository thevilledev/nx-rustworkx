# nx-rustworkx: README claims vs. implementation — evaluation

Date: 2026-08-22 · Evaluated at commit `3995a42` · Environment: Linux VM,
Python 3.12, NetworkX 3.6.1, rustworkx 0.18.1

## Verdict

The implementation delivers what the README promises, with one exception that
matters: **the declared dependency floor `rustworkx>=0.15` is wrong — the code
actually requires rustworkx 0.18**. Everything else verified: the 93-algorithm
count is exact, dispatch/fallback/remapping behave as described, the repo's 487
tests pass, the full upstream `networkx.algorithms` suite (4,002 tests) passes
through the backend, and the measured speedups are real (1.4×–345× on this
machine). One dispatch-policy regression surfaced on this hardware:
`dijkstra_path` / `dijkstra_path_length` auto-dispatch while being ~1.6× slower
than NetworkX — fixable, and the fix turns them into a ~3× win.

## Claim-by-claim

| README claim | Verdict | Evidence |
| --- | --- | --- |
| NetworkX 3.x backend registered as `rustworkx` | ✅ | Entry points in `pyproject.toml`; `nx.utils.backends.backends` lists it |
| Converts, runs kernel, remaps to original node IDs | ✅ | Verified with string/tuple/int node IDs; results equal NetworkX's |
| Unsupported calls stay on NetworkX | ✅ | MultiGraph, callable weights, unsupported kwargs all fall back cleanly |
| "The backend implements 93 algorithms" | ✅ | `len(ALGORITHMS) == 93`; website algorithm reference lists exactly the same 93 |
| Measured cutoffs keep small calls on NetworkX | ✅* | 50-node graph: 0 backend calls; 2,000-node graph: dispatched. *Two functions violate the policy on this machine (below) |
| `backend="rustworkx"` explicitly tries the backend | ✅ | Runs even `NO_AUTO_DISPATCH` functions |
| Requires Python 3.10+ | ✅ | Full suite passes on 3.10 (though CI only tests 3.11–3.14) |
| Requires NetworkX 3.4+ | ✅ | Suite passes with networkx 3.4.2 and 3.5; `_compat` probes handle 3.5 behavior changes |
| Requires rustworkx 0.15+ | ❌ | **Suite has 24 failures on rustworkx 0.15.1; true floor is 0.18.0** |
| `pip install nx-rustworkx` | ✅ | v0.1.0 live on PyPI (published 2026-08-22) |
| Limits: no multigraphs, no weight callables, no drawing/I-O, valid-difference caveats | ✅ | Enforced in `can_run` guards; caveats in `_info.py` match code behavior |
| `uv sync --extra test` && `uv run pytest tests` | ✅ | 487 passed in 1.9 s |
| BSD-3-Clause | ✅ | LICENSE and classifier agree |

Also verified: CI's strongest claim — running upstream
`NETWORKX_TEST_BACKEND=rustworkx pytest --pyargs networkx.algorithms` — passes
here: **654 passed through the backend, 3,320 xfailed (declared unsupported),
30 skipped, 0 unexpected failures, 0 xpasses** in 141 s.

## Critical gap 1: the rustworkx version floor

`pyproject.toml` declares `rustworkx>=0.15` and the README says "rustworkx
0.15+", but six dispatched functions call kernels that do not exist before
0.18, and several more hit signature drift:

| Pinned rustworkx | Repo test result | What breaks |
| --- | --- | --- |
| 0.15.1 | **24 failed** | `group_{betweenness,closeness,degree}_centrality`, `condensation`, `descendants_at_distance` (needs `bfs_layers`), `immediate_dominators` → `AttributeError`; `floyd_warshall*`, `closeness_centrality` → `TypeError` (missing kwargs) |
| 0.16.0 | 11 failed | group centralities, `bfs_layers`, kwarg drift |
| 0.17.1 | 7 failed | group centralities, `bfs_layers` |
| 0.18.0 / 0.18.1 | 0 failed | — |

The failure mode is the bad kind: `can_run` returns True, so NetworkX commits
to the backend, converts the graph, and then the wrapper raises
`AttributeError` mid-call — no fallback, wrong exception type. Any user with
rustworkx 0.15–0.17 already installed (Qiskit environments commonly pin older
rustworkx) gets a working install and broken calls.

**Fix (small):** bump to `rustworkx>=0.18` in `pyproject.toml`, README, and the
website install page. Add a CI leg that installs the declared floors
(`python 3.10`, `networkx==3.4.*`, minimum rustworkx) so the floor stays
tested. Guarding with `hasattr` fallbacks instead would preserve the 0.15 floor
but costs complexity for little value.

## Critical gap 2: two functions auto-dispatch while slower

`benches/bench_parity.py` (n=800, this machine) exits 1 by its own policy gate:

```
SLOWER AND STILL AUTO-DISPATCHED: dijkstra_path, dijkstra_path_length
dijkstra_path         0.64×   dijkstra_path_length  0.61×
```

Root cause: for a single `(source, target)` pair, `shortest_path` /
`shortest_path_length` run a **full single-source** kernel and then pick one
entry — the `target=` / `goal=` parameters that rustworkx's Dijkstra and
Bellman-Ford kernels accept for early termination are never passed (the
`shortest_path` family; `single_source_dijkstra` does pass them but runs *two*
kernels, once for paths and once for lengths). NetworkX's early-stopping
Dijkstra wins the race.

Measured on the parity graph (n=800):

| Variant | Time |
| --- | --- |
| Backend today (full single-source) | 1.42 ms |
| NetworkX `dijkstra_path` | 1.20 ms |
| rustworkx kernel with `target=` | **0.43 ms** |
| rustworkx lengths kernel with `goal=` | **0.28 ms** |

**Fix (small):** pass `target=`/`goal=` in the single-pair branches of
`shortest_path` / `shortest_path_length`; this flips a 0.6× regression into a
~3× win and un-breaks the parity gate. While there: `single_source_dijkstra`
and `single_source_bellman_ford` with a target should run one kernel and sum
edge weights along the returned path (as `astar_path_length` already does)
instead of running a second kernel.

## Minor findings

- `_compat.py`'s module docstring says "The package declares `networkx>=3.2`" —
  stale; pyproject says `>=3.4`.
- The parity benchmark's docstring/website say results "include conversion",
  but the timing loop reuses NetworkX's conversion cache after warm-up, so the
  steady-state numbers are cache-warm. Conclusions are unaffected (the gated
  functions are gated for structural reasons), but a `--cold` mode or a
  clarifying sentence would make the claim exact. `bench_centrality.py`
  already reports conversion separately and honestly.
- CI never runs Python 3.10 or NetworkX 3.4/3.5, all of which the package
  claims to support (they do pass locally — but nothing guards them).
- The parity gate (`bench_parity.py` exit code) runs only manually; a
  scheduled/nightly CI job would catch policy regressions like gap 2.

## Feature-parity roadmap

93 of ~780 dispatchable NetworkX functions are implemented. rustworkx 0.18
already ships kernels for a meaningful next tranche. Direct name-and-semantics
matches, all confirmed dispatchable in NetworkX 3.6:

**Tier 1 — drop-in wrappers (same shape as existing code):**
- `single_source_all_shortest_paths` ← `rx.single_source_all_shortest_paths`
- `bfs_layers` ← `rx.bfs_layers` (kernel already used by `descendants_at_distance`)
- `find_cycle` ← `rx.digraph_find_cycle` (directed, `orientation=None` only; else fall back)
- `chain_decomposition` ← `rx.chain_decomposition`
- `dominance_frontiers` ← `rx.dominance_frontiers`
- `is_planar` ← `rx.is_planar` (`check_planarity` stays NetworkX — embedding needed)
- `line_graph` ← `rx.graph_line_graph` (undirected)
- `is_matching` / `is_maximal_matching` ← `rx.is_matching` / `rx.is_maximal_matching`
- `metric_closure` ← `rx.metric_closure` (payload is `(distance, path)` — remap to nx's `distance`/`path` edge attrs)

**Tier 2 — close documented caveats (fallbacks become wins):**
- `closeness_centrality(distance="attr")` ← `rx.newman_weighted_closeness_centrality`
  (signature matches incl. `wf_improved`); removes the "unweighted only" caveat
- `greedy_color` strategies `saturation_largest_first` → `ColoringStrategy.Saturation`
  and `independent_set` → `ColoringStrategy.IndependentSet`
- `bridges(root=...)`: compute all bridges, filter to `root`'s component
- `all_simple_paths` with a collection of targets: loop the kernel per target
- `vf2pp_isomorphism` / `vf2pp_all_isomorphisms` (structural) ← `rx.vf2_mapping`

**Tier 3 — native generators (biggest end-to-end lever):**
Deterministic generators (`path_graph`, `cycle_graph`, `star_graph`,
`complete_graph`, `lollipop_graph`, `barbell_graph`, `full_rary_tree`, …) map
exactly to `rx.generators.*` and can return `RustworkxGraph` directly under
`backend_priority.generators`, eliminating conversion for whole pipelines —
conversion is precisely what the current cutoffs exist to amortize. Random
generators (`gnp_random_graph`, `gnm_random_graph`, `barabasi_albert_graph`,
`random_geometric_graph`, `random_regular_graph`) also map, with a documented
caveat that seeds produce different (equally valid) graphs than NetworkX's RNG
stream.

**Tier 4 — larger design decisions (evaluate, don't rush):**
- `eccentricity` / `diameter` / `radius` / `center` / `periphery` via
  `rx.distance_matrix` — fast but O(n²) memory; needs a size guard in `should_run`.
- Multigraph support: rustworkx graphs natively support `multigraph=True`; the
  restriction is a deliberate scope choice in this backend. Node-valued
  algorithms (components, connectivity, traversal) could lift it without
  result-shape issues; edge-identity results are where it gets hard. Worth a
  design note before committing.
- `lexicographical_topological_sort` exists in rustworkx but its `key` must
  return strings — only safe when node sort order survives stringification;
  probably not worth the guard complexity.
- Not mappable today (no kernel): weighted betweenness, `k`-sampling,
  `clustering`/`triangles`, `shortest_simple_paths` (Yen), `transitive_closure`.
  Custom weight callables would require per-call graph rebuilds — the documented
  limit is the right call.

## Performance roadmap (beyond gap 2)

- `all_pairs_dijkstra` materializes both full dicts before yielding; pairing
  per-source results lazily would halve peak memory on large graphs.
- `_AdjView.__getitem__` / `_neighbor_items` do `has_edge` + `get_edge_data`
  per neighbor (two Rust boundary crossings each); `rx_graph.adj(idx)` returns
  the neighbor→payload map in one call.
- `convert_from_nx` builds the edge list with a per-edge Python loop; a
  comprehension per adjacency row measurably trims the dominant conversion cost
  for large graphs.
- The `NO_AUTO_DISPATCH` list and 200/400 cutoffs were calibrated on one
  machine at n∈{400, 2000}. They held up well here (18 of 20 slower functions
  correctly gated). Re-running `bench_parity.py` on a second hardware profile
  before each release — or in a scheduled CI job — would keep the policy honest.

## Measured speedups (this machine, n=800, cache-warm)

Top of the table: `is_isomorphic` 345×, `bridges` 186×, `group_betweenness` 62×,
`katz_centrality` 61×, `transitivity` 54×, `vf2pp_is_isomorphic` 44×,
`betweenness_centrality` 41×, `is_semiconnected` 24×, `floyd_warshall` 21×,
`max_weight_matching` 21×. Median across all 93 timed functions ≈ 2.2×. The
website's published n=2,000 numbers are consistent in direction and magnitude.

## Bottom line

Ship-blocking: none — the package works as advertised on current dependencies.
Fix before the next release: (1) `rustworkx>=0.18` floor everywhere it is
stated, with a floor-pinned CI leg; (2) `target=`/`goal=` passthrough for
single-pair shortest paths. Then the highest-leverage growth is Tier 3
(native generators), which attacks conversion cost — the one structural tax
this backend design pays.
