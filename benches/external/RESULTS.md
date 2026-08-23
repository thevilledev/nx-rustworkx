# External benchmark results

Generated 2026-08-23 by the runners in this directory, at nx-rustworkx `73888a7`.

Machine: Linux-6.18.44-fc-v21-x86_64-with-glibc2.39, 4 CPUs, Python 3.12.3, networkx 3.6.1, rustworkx 0.18.1, nx-rustworkx 0.2.0.

Three complementary measurements: **T1** forces dispatch per call on the NetworkX org's own backend benchmark suite (cold, conversion included); **T2** changes zero benchmark code and lets auto-dispatch decide via `NETWORKX_BACKEND_PRIORITY`; **T3** is a real-world street-network routing/centrality workload.

## Target 1 — `networkx/nx-parallel` asv suite (forced dispatch)

Upstream `c80febed56d3`, one-line backend patch (`backends = ["rustworkx", None]`); `repeat = number = 1`, so every rustworkx cell is a **cold call including nx→rustworkx conversion**.

| benchmark | params | NetworkX | rustworkx (incl. convert) | speedup |
|---|---|---|---|---|
| betweenness_centrality (centrality) | 200, 0.6 | 0.3897 s | 0.02818 s | **13.8x** |
| betweenness_centrality (centrality) | 200, 0.2 | 0.1288 s | 0.01449 s | **8.9x** |
| betweenness_centrality (centrality) | 400, 0.6 | 3.358 s | 0.1829 s | **18.4x** |
| betweenness_centrality (centrality) | 400, 0.2 | 1.01 s | 0.04426 s | **22.8x** |
| edge_betweenness_centrality (centrality) | 200, 0.6 | 0.7376 s | 0.05214 s | **14.1x** |
| edge_betweenness_centrality (centrality) | 200, 0.2 | 0.1775 s | 0.02233 s | **7.9x** |
| edge_betweenness_centrality (centrality) | 400, 0.6 | 6.365 s | 0.3193 s | **19.9x** |
| edge_betweenness_centrality (centrality) | 400, 0.2 | 1.61 s | 0.1117 s | **14.4x** |
| number_connected_components (components) | 200, 0.6 | 0.0003871 s | 0.01399 s | **0.0x** |
| number_connected_components (components) | 200, 0.2 | 0.0003542 s | 0.009099 s | **0.0x** |
| number_connected_components (components) | 400, 0.6 | 0.0004673 s | 0.05311 s | **0.0x** |
| number_connected_components (components) | 400, 0.2 | 0.000464 s | 0.01516 s | **0.0x** |
| number_strongly_connected_components (components) | 200, 0.6 | 0.005634 s | 0.01818 s | **0.3x** |
| number_strongly_connected_components (components) | 200, 0.2 | 0.002417 s | 0.01004 s | **0.2x** |
| number_strongly_connected_components (components) | 400, 0.6 | 0.02216 s | 0.07354 s | **0.3x** |
| number_strongly_connected_components (components) | 400, 0.2 | 0.008526 s | 0.02124 s | **0.4x** |
| number_weakly_connected_components (components) | 200, 0.6 | 0.0003771 s | 0.01743 s | **0.0x** |
| number_weakly_connected_components (components) | 200, 0.2 | 0.0003814 s | 0.009633 s | **0.0x** |
| number_weakly_connected_components (components) | 400, 0.6 | 0.0005498 s | 0.06962 s | **0.0x** |
| number_weakly_connected_components (components) | 400, 0.2 | 0.0005116 s | 0.02023 s | **0.0x** |
| number_of_isolates (isolate) | 200, 0.6 | 0.0003365 s | 0.01391 s | **0.0x** |
| number_of_isolates (isolate) | 200, 0.2 | 0.0003489 s | 0.009257 s | **0.0x** |
| number_of_isolates (isolate) | 400, 0.6 | 0.000416 s | 0.05401 s | **0.0x** |
| number_of_isolates (isolate) | 400, 0.2 | 0.0004147 s | 0.01526 s | **0.0x** |
| all_pairs_shortest_path (shortest_paths) | 200, 0.6 | 0.01276 s | 0.05675 s | **0.2x** |
| all_pairs_shortest_path (shortest_paths) | 200, 0.2 | 0.01529 s | 0.04489 s | **0.3x** |
| all_pairs_shortest_path (shortest_paths) | 400, 0.6 | 0.05117 s | 0.2913 s | **0.2x** |
| all_pairs_shortest_path (shortest_paths) | 400, 0.2 | 0.06579 s | 0.158 s | **0.4x** |
| all_pairs_shortest_path_length (shortest_paths) | 200, 0.6 | 0.009776 s | 0.03339 s | **0.3x** |
| all_pairs_shortest_path_length (shortest_paths) | 200, 0.2 | 0.01118 s | 0.0202 s | **0.6x** |
| all_pairs_shortest_path_length (shortest_paths) | 400, 0.6 | 0.03582 s | 0.2092 s | **0.2x** |
| all_pairs_shortest_path_length (shortest_paths) | 400, 0.2 | 0.04323 s | 0.07556 s | **0.6x** |
| all_pairs_bellman_ford_path (shortest_paths) | 200, 0.6 | 1.915 s | 0.07757 s | **24.7x** |
| all_pairs_bellman_ford_path (shortest_paths) | 200, 0.2 | 0.6702 s | 0.05549 s | **12.1x** |
| all_pairs_bellman_ford_path (shortest_paths) | 400, 0.6 | 21.35 s | 0.6495 s | **32.9x** |
| all_pairs_bellman_ford_path (shortest_paths) | 400, 0.2 | 6.93 s | 0.3623 s | **19.1x** |
| all_pairs_bellman_ford_path_length (shortest_paths) | 200, 0.6 | 1.85 s | 0.04704 s | **39.3x** |
| all_pairs_bellman_ford_path_length (shortest_paths) | 200, 0.2 | 0.5624 s | 0.02646 s | **21.3x** |
| all_pairs_bellman_ford_path_length (shortest_paths) | 400, 0.6 | 19.83 s | 0.5019 s | **39.5x** |
| all_pairs_bellman_ford_path_length (shortest_paths) | 400, 0.2 | 6.158 s | 0.1158 s | **53.2x** |
| all_pairs_dijkstra (shortest_paths) | 200, 0.6 | 0.9833 s | 0.09191 s | **10.7x** |
| all_pairs_dijkstra (shortest_paths) | 200, 0.2 | 0.3231 s | 0.06788 s | **4.8x** |
| all_pairs_dijkstra (shortest_paths) | 400, 0.6 | 8.745 s | 0.6253 s | **14.0x** |
| all_pairs_dijkstra (shortest_paths) | 400, 0.2 | 3.081 s | 0.3244 s | **9.5x** |
| all_pairs_dijkstra_path (shortest_paths) | 200, 0.6 | 0.9302 s | 0.07672 s | **12.1x** |
| all_pairs_dijkstra_path (shortest_paths) | 200, 0.2 | 0.3178 s | 0.06029 s | **5.3x** |
| all_pairs_dijkstra_path (shortest_paths) | 400, 0.6 | 8.239 s | 0.4297 s | **19.2x** |
| all_pairs_dijkstra_path (shortest_paths) | 400, 0.2 | 2.92 s | 0.2567 s | **11.4x** |
| all_pairs_dijkstra_path_length (shortest_paths) | 200, 0.6 | 0.9612 s | 0.04132 s | **23.3x** |
| all_pairs_dijkstra_path_length (shortest_paths) | 200, 0.2 | 0.3092 s | 0.02465 s | **12.5x** |
| all_pairs_dijkstra_path_length (shortest_paths) | 400, 0.6 | 8.913 s | 0.2542 s | **35.1x** |
| all_pairs_dijkstra_path_length (shortest_paths) | 400, 0.2 | 2.977 s | 0.09541 s | **31.2x** |

## Target 2 — NetworkX's bundled asv suite (zero-change, env-var A/B)

NetworkX `7530809bfa1e` (tag networkx-3.6.1), **no benchmark-code changes**: the second arm only sets `NETWORKX_BACKEND_PRIORITY=rustworkx`. The offline container dropped the drug-interaction-network parameter. Rows marked "no" are the backend's own honest declines (auto-dispatch floor n<200 / m<400, or a NO_AUTO_DISPATCH function) and are expected to tie.

| benchmark | graph | NetworkX | rustworkx | speedup | auto-dispatch |
|---|---|---|---|---|---|
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.005) | 6.547e-05 s | 9.138e-05 s | **0.7x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=59 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.01) | 6.911e-05 s | 9.118e-05 s | **0.8x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=104 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.05) | 0.0001701 s | 0.0001866 s | **0.9x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=477 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.0002929 s | 0.0003143 s | **0.9x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=947 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.001099 s | 0.001129 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4952 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.0005) | 0.000695 s | 0.0004306 s | **1.6x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.001) | 0.0008355 s | 0.000486 s | **1.7x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.005) | 0.002052 s | 0.0002576 s | **8.0x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.01) | 0.003129 s | 0.0003014 s | **10.4x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.05) | 0.01175 s | 0.00157 s | **7.5x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.00005) | 0.009891 s | 0.005206 s | **1.9x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.0001) | 0.01219 s | 0.005481 s | **2.2x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.0005) | 0.03013 s | 0.004544 s | **6.6x** | yes |
| tarjan_scc (benchmark_algorithms) | Empty (100) | 5.342e-05 s | 7.511e-05 s | **0.7x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Empty (1000) | 0.0005042 s | 0.0007106 s | **0.7x** | no — graph too small for rustworkx conversion (n=1000 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Empty (10000) | 0.006929 s | 0.008926 s | **0.8x** | no — graph too small for rustworkx conversion (n=10000 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Complete (100) | 0.00208 s | 0.002157 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=9900 < 400) |
| tarjan_scc (benchmark_algorithms) | Complete (1000) | 0.2097 s | 0.01947 s | **10.8x** | yes |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.01858 s | 0.01576 s | **1.2x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.04511 s | 0.04498 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 0.05622 s | 0.05491 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 2.055e-05 s | 3.868e-05 s | **0.5x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 1.935e-05 s | 3.847e-05 s | **0.5x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 1.478e-05 s | 3.005e-05 s | **0.5x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.001334 s | 0.001065 s | **1.3x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.002283 s | 0.002159 s | **1.1x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 0.00345 s | 0.003269 s | **1.1x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(10) | 4.342e-05 s | 5.444e-05 s | **0.8x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(100) | 0.004029 s | 0.00423 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(1000) | 1.192 s | 1.335 s | **0.9x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 100) | 8.817e-05 s | 0.0001014 s | **0.9x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 1000) | 0.0007854 s | 0.000825 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 10000) | 0.007757 s | 0.007789 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 20000) | 0.01528 s | 0.01577 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.1, seed=42) | 1.775e-05 s | 2.608e-05 s | **0.7x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.5, seed=42) | 2.576e-05 s | 3.594e-05 s | **0.7x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.9, seed=42) | 2.415e-05 s | 3.675e-05 s | **0.7x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.1, seed=42) | 0.0001552 s | 0.0001829 s | **0.8x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.5, seed=42) | 0.0004791 s | 0.0005234 s | **0.9x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.9, seed=42) | 0.0004934 s | 0.0005345 s | **0.9x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.1, seed=42) | 0.005813 s | 0.00631 s | **0.9x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.5, seed=42) | 0.03602 s | 0.03055 s | **1.2x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.9, seed=42) | 0.02897 s | 0.02825 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| single_source_all_shortest_paths (benchmark_many_components) | — | 5.806e-05 s | 0.0009625 s | **0.1x** | yes |

## Target 3 — OSMnx-style city routing demo (forced dispatch)

Graph: **synthetic** DiGraph (11,920 nodes / 83,764 edges, largest SCC); centrality subgraph n=6,000. Stock arm = `orig_func`, backend arm = `backend="rustworkx"` with a dispatch counter asserting every call.

_Measured at `73888a7`, when the demo still collapsed the street network to a DiGraph with `ox.convert.to_digraph`. Since #19 the backend routes the MultiDiGraph directly and the demo no longer converts; rerun `osmnx_demo.py` to refresh this section._

| workload | NetworkX | rustworkx | speedup | parity |
|---|---|---|---|---|
| shortest_path x200 (weight=travel_time) | 3.053 s | 2.061 s | **1.48x** | 0 of 200 route costs differ |
| closeness_centrality (distance=travel_time) | 109.7 s | 2.332 s | **47.06x** | max abs diff 1.82e-17 |
| betweenness_centrality (unweighted) | 106 s | 1.322 s | **80.17x** | max abs diff 6.94e-16 |
| pagerank | 0.0802 s | 0.1422 s | **0.56x** | max abs diff 4.05e-05 |

Routing detail: first backend call (includes graph conversion) 124.0 ms; steady state 9.731 ms/route vs NetworkX 15.26 ms/route.

## Reading the numbers

- Auto-dispatch declines graphs with n<200 or m<400 (`nx.config.backends.rustworkx.min_nodes/min_edges`) and 22 functions are never auto-selected; an explicit `backend="rustworkx"` bypasses only the size floor. Weighted betweenness always falls back to NetworkX; MultiGraph/MultiDiGraph dispatch with NetworkX's parallel-edge rules except for the functions NetworkX itself refuses on them.
- T1 cells time a single cold call (conversion included); T2 cells are asv medians where NetworkX's conversion cache (default on since 3.4) amortizes conversion; T3 reports both cold and steady-state routing.
- **Cold-call economics**: T1's sub-1x rows are all near-linear functions (component counts, isolates, unweighted BFS all-pairs on dense low-diameter graphs) where a single cold call cannot amortize the O(m) conversion. Superlinear kernels (betweenness, weighted all-pairs) win 5-50x even cold; repeat-call workloads amortize conversion through the cache either way.
- **Gap found by T2, now fixed**: weighted single-pair `shortest_path` used to auto-dispatch and lose badly (0.02-0.4x on path-shaped and dense graphs) — NetworkX answers a weighted pair with bidirectional Dijkstra, while the backend's single-source paths kernel materializes a path for every visited node. `should_run` now declines single pairs (`benches/bench_single_pair.py` holds the measurements); the goal-stopped `*_length` variants win 1.2-9x everywhere and keep dispatching, and forced `backend=` still runs the paths kernels, which road-network shapes reward (T3: 1.5x).
- `single_source_all_shortest_paths` keeps dispatching deliberately: it wins 6.9x/1.3x on connected path/dense shapes; the many-components row flags a sub-millisecond loss because only the source's 5-node component is reachable while conversion covers the whole graph.
- Same machine, same process pattern for both arms in every target; still: single-machine numbers, expect variance.

## Sanity flags

- T1 number_connected_components (components) [200, 0.6]: rustworkx slower (0.03x)
- T1 number_connected_components (components) [200, 0.2]: rustworkx slower (0.04x)
- T1 number_connected_components (components) [400, 0.6]: rustworkx slower (0.01x)
- T1 number_connected_components (components) [400, 0.2]: rustworkx slower (0.03x)
- T1 number_strongly_connected_components (components) [200, 0.6]: rustworkx slower (0.31x)
- T1 number_strongly_connected_components (components) [200, 0.2]: rustworkx slower (0.24x)
- T1 number_strongly_connected_components (components) [400, 0.6]: rustworkx slower (0.30x)
- T1 number_strongly_connected_components (components) [400, 0.2]: rustworkx slower (0.40x)
- T1 number_weakly_connected_components (components) [200, 0.6]: rustworkx slower (0.02x)
- T1 number_weakly_connected_components (components) [200, 0.2]: rustworkx slower (0.04x)
- T1 number_weakly_connected_components (components) [400, 0.6]: rustworkx slower (0.01x)
- T1 number_weakly_connected_components (components) [400, 0.2]: rustworkx slower (0.03x)
- T1 number_of_isolates (isolate) [200, 0.6]: rustworkx slower (0.02x)
- T1 number_of_isolates (isolate) [200, 0.2]: rustworkx slower (0.04x)
- T1 number_of_isolates (isolate) [400, 0.6]: rustworkx slower (0.01x)
- T1 number_of_isolates (isolate) [400, 0.2]: rustworkx slower (0.03x)
- T1 all_pairs_shortest_path (shortest_paths) [200, 0.6]: rustworkx slower (0.22x)
- T1 all_pairs_shortest_path (shortest_paths) [200, 0.2]: rustworkx slower (0.34x)
- T1 all_pairs_shortest_path (shortest_paths) [400, 0.6]: rustworkx slower (0.18x)
- T1 all_pairs_shortest_path (shortest_paths) [400, 0.2]: rustworkx slower (0.42x)
- T1 all_pairs_shortest_path_length (shortest_paths) [200, 0.6]: rustworkx slower (0.29x)
- T1 all_pairs_shortest_path_length (shortest_paths) [200, 0.2]: rustworkx slower (0.55x)
- T1 all_pairs_shortest_path_length (shortest_paths) [400, 0.6]: rustworkx slower (0.17x)
- T1 all_pairs_shortest_path_length (shortest_paths) [400, 0.2]: rustworkx slower (0.57x)
- T2 single_source_all_shortest_paths (benchmark_many_components) []: backend dispatched and LOST (0.06x) — should_run tuning candidate
