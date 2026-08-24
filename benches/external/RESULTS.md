# External benchmark results

Generated 2026-08-24 by the runners in this directory, at nx-rustworkx `126cfd8`.

Machine: Linux-6.18.44-fc-v21-x86_64-with-glibc2.39, 4 CPUs, Python 3.12.3, networkx 3.6.1, rustworkx 0.18.1, nx-rustworkx 0.2.0.

Three complementary measurements: **T1** forces dispatch per call on the NetworkX org's own backend benchmark suite (cold, conversion included); **T2** changes zero benchmark code and lets auto-dispatch decide via `NETWORKX_BACKEND_PRIORITY`; **T3** is a real-world street-network routing/centrality workload.

## Target 1 — `networkx/nx-parallel` asv suite (forced dispatch)

Upstream `c80febed56d3`, one-line backend patch (`backends = ["rustworkx", None]`); `repeat = number = 1`, so every rustworkx cell is a **cold call including nx→rustworkx conversion**.

| benchmark | params | NetworkX | rustworkx (incl. convert) | speedup |
|---|---|---|---|---|
| betweenness_centrality (centrality) | 200, 0.6 | 0.4515 s | 0.04426 s | **10.2x** |
| betweenness_centrality (centrality) | 200, 0.2 | 0.1521 s | 0.01635 s | **9.3x** |
| betweenness_centrality (centrality) | 400, 0.6 | 3.821 s | 0.2049 s | **18.7x** |
| betweenness_centrality (centrality) | 400, 0.2 | 1.206 s | 0.05006 s | **24.1x** |
| edge_betweenness_centrality (centrality) | 200, 0.6 | 0.7245 s | 0.0483 s | **15.0x** |
| edge_betweenness_centrality (centrality) | 200, 0.2 | 0.2119 s | 0.02251 s | **9.4x** |
| edge_betweenness_centrality (centrality) | 400, 0.6 | 6.626 s | 0.3108 s | **21.3x** |
| edge_betweenness_centrality (centrality) | 400, 0.2 | 1.798 s | 0.08944 s | **20.1x** |
| number_connected_components (components) | 200, 0.6 | 0.0003879 s | 0.01671 s | **0.0x** |
| number_connected_components (components) | 200, 0.2 | 0.0003812 s | 0.01096 s | **0.0x** |
| number_connected_components (components) | 400, 0.6 | 0.0004695 s | 0.05954 s | **0.0x** |
| number_connected_components (components) | 400, 0.2 | 0.0005422 s | 0.01743 s | **0.0x** |
| number_strongly_connected_components (components) | 200, 0.6 | 0.006781 s | 0.02021 s | **0.3x** |
| number_strongly_connected_components (components) | 200, 0.2 | 0.002841 s | 0.01168 s | **0.2x** |
| number_strongly_connected_components (components) | 400, 0.6 | 0.02744 s | 0.07954 s | **0.3x** |
| number_strongly_connected_components (components) | 400, 0.2 | 0.009809 s | 0.02386 s | **0.4x** |
| number_weakly_connected_components (components) | 200, 0.6 | 0.0004074 s | 0.02004 s | **0.0x** |
| number_weakly_connected_components (components) | 200, 0.2 | 0.0004121 s | 0.01262 s | **0.0x** |
| number_weakly_connected_components (components) | 400, 0.6 | 0.0005054 s | 0.07843 s | **0.0x** |
| number_weakly_connected_components (components) | 400, 0.2 | 0.0005224 s | 0.02269 s | **0.0x** |
| number_of_isolates (isolate) | 200, 0.6 | 0.0003622 s | 0.01669 s | **0.0x** |
| number_of_isolates (isolate) | 200, 0.2 | 0.0003305 s | 0.01077 s | **0.0x** |
| number_of_isolates (isolate) | 400, 0.6 | 0.0004377 s | 0.05801 s | **0.0x** |
| number_of_isolates (isolate) | 400, 0.2 | 0.0004172 s | 0.01793 s | **0.0x** |
| all_pairs_shortest_path (shortest_paths) | 200, 0.6 | 0.01959 s | 0.07741 s | **0.3x** |
| all_pairs_shortest_path (shortest_paths) | 200, 0.2 | 0.01797 s | 0.05177 s | **0.3x** |
| all_pairs_shortest_path (shortest_paths) | 400, 0.6 | 0.05896 s | 0.3285 s | **0.2x** |
| all_pairs_shortest_path (shortest_paths) | 400, 0.2 | 0.07208 s | 0.1968 s | **0.4x** |
| all_pairs_shortest_path_length (shortest_paths) | 200, 0.6 | 0.01056 s | 0.03641 s | **0.3x** |
| all_pairs_shortest_path_length (shortest_paths) | 200, 0.2 | 0.014 s | 0.02682 s | **0.5x** |
| all_pairs_shortest_path_length (shortest_paths) | 400, 0.6 | 0.04236 s | 0.2597 s | **0.2x** |
| all_pairs_shortest_path_length (shortest_paths) | 400, 0.2 | 0.05043 s | 0.08994 s | **0.6x** |
| all_pairs_bellman_ford_path (shortest_paths) | 200, 0.6 | 1.928 s | 0.09144 s | **21.1x** |
| all_pairs_bellman_ford_path (shortest_paths) | 200, 0.2 | 0.7342 s | 0.06524 s | **11.3x** |
| all_pairs_bellman_ford_path (shortest_paths) | 400, 0.6 | 19.81 s | 0.7637 s | **25.9x** |
| all_pairs_bellman_ford_path (shortest_paths) | 400, 0.2 | 6.826 s | 0.3994 s | **17.1x** |
| all_pairs_bellman_ford_path_length (shortest_paths) | 200, 0.6 | 1.985 s | 0.06127 s | **32.4x** |
| all_pairs_bellman_ford_path_length (shortest_paths) | 200, 0.2 | 0.6443 s | 0.03335 s | **19.3x** |
| all_pairs_bellman_ford_path_length (shortest_paths) | 400, 0.6 | 18.68 s | 0.4422 s | **42.2x** |
| all_pairs_bellman_ford_path_length (shortest_paths) | 400, 0.2 | 6.191 s | 0.1297 s | **47.7x** |
| all_pairs_dijkstra (shortest_paths) | 200, 0.6 | 0.9308 s | 0.1115 s | **8.3x** |
| all_pairs_dijkstra (shortest_paths) | 200, 0.2 | 0.396 s | 0.08246 s | **4.8x** |
| all_pairs_dijkstra (shortest_paths) | 400, 0.6 | 8.072 s | 0.6345 s | **12.7x** |
| all_pairs_dijkstra (shortest_paths) | 400, 0.2 | 3.149 s | 0.3515 s | **9.0x** |
| all_pairs_dijkstra_path (shortest_paths) | 200, 0.6 | 0.9148 s | 0.09042 s | **10.1x** |
| all_pairs_dijkstra_path (shortest_paths) | 200, 0.2 | 0.341 s | 0.07198 s | **4.7x** |
| all_pairs_dijkstra_path (shortest_paths) | 400, 0.6 | 8.239 s | 0.4498 s | **18.3x** |
| all_pairs_dijkstra_path (shortest_paths) | 400, 0.2 | 2.975 s | 0.2996 s | **9.9x** |
| all_pairs_dijkstra_path_length (shortest_paths) | 200, 0.6 | 1.019 s | 0.04949 s | **20.6x** |
| all_pairs_dijkstra_path_length (shortest_paths) | 200, 0.2 | 0.3502 s | 0.03294 s | **10.6x** |
| all_pairs_dijkstra_path_length (shortest_paths) | 400, 0.6 | 8.672 s | 0.2606 s | **33.3x** |
| all_pairs_dijkstra_path_length (shortest_paths) | 400, 0.2 | 3.004 s | 0.1039 s | **28.9x** |

## Target 2 — NetworkX's bundled asv suite (zero-change, env-var A/B)

NetworkX `7530809bfa1e` (tag networkx-3.6.1), **no benchmark-code changes**: the second arm only sets `NETWORKX_BACKEND_PRIORITY=rustworkx`. The offline container dropped the drug-interaction-network parameter. Rows marked "no" are the backend's own honest declines (auto-dispatch floor n<200 / m<400, or a NO_AUTO_DISPATCH function) and are expected to tie.

| benchmark | graph | NetworkX | rustworkx | speedup | auto-dispatch |
|---|---|---|---|---|---|
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.005) | 7.114e-05 s | 0.0001459 s | **0.5x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=59 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.01) | 0.0001388 s | 0.0001169 s | **1.2x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=104 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.05) | 0.000288 s | 0.0002231 s | **1.3x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=477 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.0003281 s | 0.0003663 s | **0.9x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=947 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.001326 s | 0.001391 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4952 < 400) |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.0005) | 0.0008153 s | 0.0005018 s | **1.6x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.001) | 0.0009503 s | 0.0005193 s | **1.8x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.005) | 0.002411 s | 0.0003002 s | **8.0x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.01) | 0.003636 s | 0.0003573 s | **10.2x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (1000, 0.05) | 0.0138 s | 0.001074 s | **12.9x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.00005) | 0.01082 s | 0.00522 s | **2.1x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.0001) | 0.0131 s | 0.005621 s | **2.3x** | yes |
| tarjan_scc (benchmark_algorithms) | Erdos Renyi (10000, 0.0005) | 0.03206 s | 0.004021 s | **8.0x** | yes |
| tarjan_scc (benchmark_algorithms) | Empty (100) | 6.404e-05 s | 8.916e-05 s | **0.7x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Empty (1000) | 0.0006206 s | 0.0008371 s | **0.7x** | no — graph too small for rustworkx conversion (n=1000 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Empty (10000) | 0.007852 s | 0.009885 s | **0.8x** | no — graph too small for rustworkx conversion (n=10000 < 200 or m=0 < 400) |
| tarjan_scc (benchmark_algorithms) | Complete (100) | 0.002561 s | 0.002549 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=9900 < 400) |
| tarjan_scc (benchmark_algorithms) | Complete (1000) | 0.2518 s | 0.02576 s | **9.8x** | yes |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.01882 s | 0.01942 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.05708 s | 0.05526 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| betweenness_centrality (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 0.06753 s | 0.06671 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 2.793e-05 s | 4.607e-05 s | **0.6x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 1.919e-05 s | 4.36e-05 s | **0.4x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| connected_components (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 1.519e-05 s | 4.236e-05 s | **0.4x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.1) | 0.00129 s | 0.001269 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=478 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.5) | 0.002553 s | 0.002378 s | **1.1x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=2454 < 400) |
| pagerank (benchmark_algorithms) | Erdos Renyi (100, 0.9) | 0.003753 s | 0.003593 s | **1.0x** | no — graph too small for rustworkx conversion (n=100 < 200 or m=4455 < 400) |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(10) | 5.062e-05 s | 6.068e-05 s | **0.8x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(100) | 0.004739 s | 0.004336 s | **1.1x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | dijkstra_relaxation_worst_case(1000) | 1.177 s | 1.151 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 100) | 0.0001036 s | 0.0001208 s | **0.9x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 1000) | 0.0008936 s | 0.001011 s | **0.9x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 10000) | 0.008981 s | 0.00926 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, path_graph, 20000) | 0.01917 s | 0.02024 s | **0.9x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.1, seed=42) | 2.02e-05 s | 3.313e-05 s | **0.6x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.5, seed=42) | 3.181e-05 s | 4.073e-05 s | **0.8x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 10, 0.9, seed=42) | 3.15e-05 s | 4.188e-05 s | **0.8x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.1, seed=42) | 0.0001777 s | 0.0002419 s | **0.7x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.5, seed=42) | 0.0005899 s | 0.0005862 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 100, 0.9, seed=42) | 0.0006886 s | 0.0005869 s | **1.2x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.1, seed=42) | 0.006752 s | 0.006234 s | **1.1x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.5, seed=42) | 0.03822 s | 0.03297 s | **1.2x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| shortest_path (benchmark_algorithms) | weighted_graph(42, gnp_random_graph, 1000, 0.9, seed=42) | 0.02971 s | 0.02854 s | **1.0x** | no — NetworkX's bidirectional Dijkstra is faster for a weighted single pair |
| single_source_all_shortest_paths (benchmark_many_components) | — | 6.01e-05 s | 0.001048 s | **0.1x** | yes |

## Target 3 — OSMnx-style city routing demo (forced dispatch)

Graph: **synthetic** MultiDiGraph (11,920 nodes / 90,524 edges, 6,760 parallel-way bundles, largest SCC); centrality subgraph n=6,000. Stock arm = `orig_func`, backend arm = `backend="rustworkx"` with a dispatch counter asserting every call.

| workload | NetworkX | rustworkx | speedup | parity |
|---|---|---|---|---|
| shortest_path x200 (weight=travel_time) | 8.01 s | 2.329 s | **3.44x** | 0 of 200 route costs differ |
| closeness_centrality (distance=travel_time) | 357.8 s | 2.638 s | **135.66x** | max abs diff 1.56e-17 |
| betweenness_centrality (unweighted) | 115.3 s | 1.474 s | **78.2x** | max abs diff 8.60e-16 |
| pagerank | 0.0906 s | 0.2647 s | **0.34x** | max abs diff 4.03e-05 |

Routing detail: first backend call (includes graph conversion) 204.6 ms; steady state 10.677 ms/route vs NetworkX 40.05 ms/route.

## Reading the numbers

- Auto-dispatch declines graphs with n<200 or m<400 (`nx.config.backends.rustworkx.min_nodes/min_edges`) and 22 functions are never auto-selected; an explicit `backend="rustworkx"` bypasses only the size floor. Weighted betweenness always falls back to NetworkX; MultiGraph/MultiDiGraph dispatch with NetworkX's parallel-edge rules except for the functions NetworkX itself refuses on them.
- T1 cells time a single cold call (conversion included); T2 cells are asv medians where NetworkX's conversion cache (default on since 3.4) amortizes conversion; T3 reports both cold and steady-state routing.
- **Cold-call economics**: T1's sub-1x rows are all near-linear functions (component counts, isolates, unweighted BFS all-pairs on dense low-diameter graphs) where a single cold call cannot amortize the O(m) conversion. Superlinear kernels (betweenness, weighted all-pairs) win 5-50x even cold; repeat-call workloads amortize conversion through the cache either way.
- **Gap found by T2, now fixed**: weighted single-pair `shortest_path` used to auto-dispatch and lose badly (0.02-0.4x on path-shaped and dense graphs) — NetworkX answers a weighted pair with bidirectional Dijkstra, while the backend's single-source paths kernel materializes a path for every visited node. `should_run` now declines single pairs (`benches/bench_single_pair.py` holds the measurements); the goal-stopped `*_length` variants win 1.2-9x everywhere and keep dispatching, and forced `backend=` still runs the paths kernels, which road-network shapes reward (T3: 1.5x).
- `single_source_all_shortest_paths` keeps dispatching deliberately: it wins 6.9x/1.3x on connected path/dense shapes; the many-components row flags a sub-millisecond loss because only the source's 5-node component is reachable while conversion covers the whole graph.
- Same machine, same process pattern for both arms in every target; still: single-machine numbers, expect variance.

## Sanity flags

- T1 number_connected_components (components) [200, 0.6]: rustworkx slower (0.02x)
- T1 number_connected_components (components) [200, 0.2]: rustworkx slower (0.03x)
- T1 number_connected_components (components) [400, 0.6]: rustworkx slower (0.01x)
- T1 number_connected_components (components) [400, 0.2]: rustworkx slower (0.03x)
- T1 number_strongly_connected_components (components) [200, 0.6]: rustworkx slower (0.34x)
- T1 number_strongly_connected_components (components) [200, 0.2]: rustworkx slower (0.24x)
- T1 number_strongly_connected_components (components) [400, 0.6]: rustworkx slower (0.34x)
- T1 number_strongly_connected_components (components) [400, 0.2]: rustworkx slower (0.41x)
- T1 number_weakly_connected_components (components) [200, 0.6]: rustworkx slower (0.02x)
- T1 number_weakly_connected_components (components) [200, 0.2]: rustworkx slower (0.03x)
- T1 number_weakly_connected_components (components) [400, 0.6]: rustworkx slower (0.01x)
- T1 number_weakly_connected_components (components) [400, 0.2]: rustworkx slower (0.02x)
- T1 number_of_isolates (isolate) [200, 0.6]: rustworkx slower (0.02x)
- T1 number_of_isolates (isolate) [200, 0.2]: rustworkx slower (0.03x)
- T1 number_of_isolates (isolate) [400, 0.6]: rustworkx slower (0.01x)
- T1 number_of_isolates (isolate) [400, 0.2]: rustworkx slower (0.02x)
- T1 all_pairs_shortest_path (shortest_paths) [200, 0.6]: rustworkx slower (0.25x)
- T1 all_pairs_shortest_path (shortest_paths) [200, 0.2]: rustworkx slower (0.35x)
- T1 all_pairs_shortest_path (shortest_paths) [400, 0.6]: rustworkx slower (0.18x)
- T1 all_pairs_shortest_path (shortest_paths) [400, 0.2]: rustworkx slower (0.37x)
- T1 all_pairs_shortest_path_length (shortest_paths) [200, 0.6]: rustworkx slower (0.29x)
- T1 all_pairs_shortest_path_length (shortest_paths) [200, 0.2]: rustworkx slower (0.52x)
- T1 all_pairs_shortest_path_length (shortest_paths) [400, 0.6]: rustworkx slower (0.16x)
- T1 all_pairs_shortest_path_length (shortest_paths) [400, 0.2]: rustworkx slower (0.56x)
- T2 single_source_all_shortest_paths (benchmark_many_components) []: backend dispatched and LOST (0.06x) — should_run tuning candidate
