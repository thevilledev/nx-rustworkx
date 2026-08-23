# External benchmark results

Generated 2026-08-23 by the runners in this directory, at nx-rustworkx `c7172fd`.

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
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.005) | 7.52e-05 s | 8.826e-05 s | **0.9x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=59 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.01) | 7.231e-05 s | 9.049e-05 s | **0.8x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=104 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.05) | 0.0001654 s | 0.0001944 s | **0.9x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=477 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.000291 s | 0.0003606 s | **0.8x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=947 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.00114 s | 0.001111 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4952 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.0005) | 0.0006287 s | 0.0006323 s | **1.0x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.001) | 0.0008052 s | 0.0004484 s | **1.8x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.005) | 0.002189 s | 0.000302 s | **7.3x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.01) | 0.003395 s | 0.0003087 s | **11.0x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.05) | 0.01183 s | 0.001492 s | **7.9x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.00005) | 0.01065 s | 0.005001 s | **2.1x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.0001) | 0.01278 s | 0.005699 s | **2.2x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.0005) | 0.03169 s | 0.004571 s | **6.9x** | yes |
| tarjan_scc (benchmark_algorithms) | Empty (100) | 6.025e-05 s | 7.241e-05 s | **0.8x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Empty (1000) | 0.0005381 s | 0.0007143 s | **0.8x** | no — graph too small for rustworkx conversion (n=1000 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Empty (10000) | 0.006836 s | 0.009463 s | **0.7x** | no — graph too small for rustworkx conversion (n=10000 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Complete (100) | 0.002128 s | 0.002125 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=9900 < 400) |
| tarjan_scc (benchmark_algorithms) | Complete (1000) | 0.2131 s | 0.01953 s | **10.9x** | yes |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.01535 s | 0.01648 s | **0.9x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.04473 s | 0.04367 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 0.05471 s | 0.05431 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 3.687e-05 s | 4.603e-05 s | **0.8x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 1.716e-05 s | 3.296e-05 s | **0.5x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 1.485e-05 s | 3.277e-05 s | **0.5x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.001201 s | 0.0008751 s | **1.4x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.002199 s | 0.002144 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 0.003148 s | 0.003122 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(10) | 4.334e-05 s | 6.22e-05 s | **0.7x** | no — graph too small for rustworkx conversion (n=10 < 200 or m=45 < 400) |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(100) | 0.004138 s | 0.004174 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4950 < 400) |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(1000) | 1.257 s | 3.008 s | **0.4x** | yes |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 100) | 8.254e-05 s | 0.0001184 s | **0.7x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=99 < 400) |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 1000) | 0.0007672 s | 0.002034 s | **0.4x** | yes |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 10000) | 0.00789 s | 0.1228 s | **0.1x** | yes |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 20000) | 0.01554 s | 0.533 s | **0.0x** | yes |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.1, seed=42) | 1.644e-05 s | 3.33e-05 s | **0.5x** | no — graph too small for rustworkx conversion (n=10 < 200 or m=6 < 400) |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.5, seed=42) | 2.285e-05 s | 4.006e-05 s | **0.6x** | no — graph too small for rustworkx conversion (n=10 < 200 or m=20 < 400) |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.9, seed=42) | 2.263e-05 s | 4.115e-05 s | **0.5x** | no — graph too small for rustworkx conversion (n=10 < 200 or m=38 < 400) |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.1, seed=42) | 0.0001511 s | 0.0001709 s | **0.9x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=552 < 400) |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.5, seed=42) | 0.0004598 s | 0.0005468 s | **0.8x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2421 < 400) |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.9, seed=42) | 0.0004374 s | 0.0005353 s | **0.8x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4426 < 400) |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.1, seed=42) | 0.006537 s | 0.05814 s | **0.1x** | yes |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.5, seed=42) | 0.03642 s | 0.7256 s | **0.1x** | yes |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.9, seed=42) | 0.03018 s | 1.917 s | **0.0x** | yes |
| single_source_all_shortest_paths (benchmark_many_components) | — | 6.695e-05 s | 0.0009542 s | **0.1x** | yes |

## Target 3 — OSMnx-style city routing demo (forced dispatch)

Graph: **synthetic** (11,920 nodes / 83,764 edges, largest SCC); centrality subgraph n=6,000. Stock arm = `orig_func`, backend arm = `backend="rustworkx"` with a dispatch counter asserting every call.

| workload | NetworkX | rustworkx | speedup | parity |
|---|---|---|---|---|
| shortest_path x200 (weight=travel_time) | 3.053 s | 2.061 s | **1.48x** | 0 of 200 route costs differ |
| closeness_centrality (distance=travel_time) | 109.7 s | 2.332 s | **47.06x** | max abs diff 1.82e-17 |
| betweenness_centrality (unweighted) | 106 s | 1.322 s | **80.17x** | max abs diff 6.94e-16 |
| pagerank | 0.0802 s | 0.1422 s | **0.56x** | max abs diff 4.05e-05 |

Routing detail: first backend call (includes graph conversion) 124.0 ms; steady state 9.731 ms/route vs NetworkX 15.26 ms/route.

## Reading the numbers

- Auto-dispatch declines graphs with n<200 or m<400 (`nx.config.backends.rustworkx.min_nodes/min_edges`) and 22 functions are never auto-selected; an explicit `backend="rustworkx"` bypasses only the size floor. MultiGraph/MultiDiGraph and weighted betweenness always fall back to NetworkX.
- T1 cells time a single cold call (conversion included); T2 cells are asv medians where NetworkX's conversion cache (default on since 3.4) amortizes conversion; T3 reports both cold and steady-state routing.
- **Cold-call economics**: T1's sub-1x rows are all near-linear functions (component counts, isolates, unweighted BFS all-pairs on dense low-diameter graphs) where a single cold call cannot amortize the O(m) conversion. Superlinear kernels (betweenness, weighted all-pairs) win 5-50x even cold; repeat-call workloads amortize conversion through the cache either way.
- **Known gap found by T2**: weighted single-pair `shortest_path` auto-dispatches but can lose badly (0.02-0.4x on path-shaped and dense graphs). NetworkX answers a weighted pair with bidirectional Dijkstra, while the backend runs a full single-source kernel whose rustworkx PathMapping materializes paths for every visited node and pays a per-edge Python weight callback. On road-network shapes it still wins modestly (T3: 1.5x), so the fix is should_run tuning or a lengths+predecessor kernel, not removal.
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
- T2 shortest_path (benchmark_algorithms) [dijkstra_relaxation_worst_case(1000)]: backend dispatched and LOST (0.42x) — should_run tuning candidate
- T2 shortest_path (benchmark_algorithms) [weighted_graph(42, path_graph, 1000)]: backend dispatched and LOST (0.38x) — should_run tuning candidate
- T2 shortest_path (benchmark_algorithms) [weighted_graph(42, path_graph, 10000)]: backend dispatched and LOST (0.06x) — should_run tuning candidate
- T2 shortest_path (benchmark_algorithms) [weighted_graph(42, path_graph, 20000)]: backend dispatched and LOST (0.03x) — should_run tuning candidate
- T2 shortest_path (benchmark_algorithms) [weighted_graph(42, gnp_random_graph, 1000, 0.1, seed=42)]: backend dispatched and LOST (0.11x) — should_run tuning candidate
- T2 shortest_path (benchmark_algorithms) [weighted_graph(42, gnp_random_graph, 1000, 0.5, seed=42)]: backend dispatched and LOST (0.05x) — should_run tuning candidate
- T2 shortest_path (benchmark_algorithms) [weighted_graph(42, gnp_random_graph, 1000, 0.9, seed=42)]: backend dispatched and LOST (0.02x) — should_run tuning candidate
- T2 single_source_all_shortest_paths (benchmark_many_components) []: backend dispatched and LOST (0.07x) — should_run tuning candidate
