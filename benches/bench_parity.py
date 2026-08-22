#!/usr/bin/env python3
"""Compare every dispatched function against stock NetworkX.

The point of a backend is that dispatching wins. This walks a representative
call for each supported function and reports the speedup including conversion,
so a function that is slower here does not belong in the backend.

    python benches/bench_parity.py
    python benches/bench_parity.py --nodes 2000 --slowest 15
"""

from __future__ import annotations

import argparse
import gc
import sys
import time

import networkx as nx

from nx_rustworkx.algorithms import ALGORITHMS
from nx_rustworkx.interface import BackendInterface

nx.config.warnings_to_ignore.add("cache")


def _graphs(n: int, seed: int) -> dict:
    undirected = nx.gnp_random_graph(n, min(0.02, 20 / n), seed=seed)
    for u, v in undirected.edges():
        undirected[u][v]["weight"] = 1 + ((u * 7 + v * 13) % 9)
    # All-pairs and dense results are quadratic in n, so give them a smaller
    # graph rather than letting one row dominate the run.
    small = nx.gnp_random_graph(max(40, n // 4), 0.05, seed=seed)
    for u, v in small.edges():
        small[u][v]["weight"] = 1 + ((u * 7 + v * 13) % 9)
    directed = nx.gnp_random_graph(n, min(0.02, 20 / n), seed=seed, directed=True)
    for u, v in directed.edges():
        directed[u][v]["weight"] = 1 + ((u * 5 + v * 3) % 7)
    dag = nx.DiGraph()
    dag.add_nodes_from(range(n))
    dag.add_edges_from((u, v) for u in range(n) for v in range(u + 1, min(n, u + 6)) if (u + v) % 3)
    return {"undirected": undirected, "directed": directed, "dag": dag, "small": small}


def _calls(graphs, n):
    """Yield ``(name, kwargs_free_callable_factory)`` for each supported function."""
    U, D, A = graphs["undirected"], graphs["directed"], graphs["dag"]
    half = [i for i in range(0, n, max(1, n // 8))][:8]
    single = {
        # graph-only calls, grouped by the graph they need
        "undirected": [
            "betweenness_centrality",
            "edge_betweenness_centrality",
            "closeness_centrality",
            "eigenvector_centrality",
            "degree_centrality",
            "hits",
            "pagerank",
            "is_connected",
            "connected_components",
            "number_connected_components",
            "articulation_points",
            "bridges",
            "biconnected_components",
            "cycle_basis",
            "core_number",
            "is_bipartite",
            "isolates",
            "number_of_isolates",
            "transitivity",
            "greedy_color",
            "minimum_spanning_tree",
            "minimum_spanning_edges",
            "complement",
            "max_weight_matching",
            "negative_edge_cycle",
        ],
        "small": [
            "floyd_warshall",
            "floyd_warshall_numpy",
            "floyd_warshall_predecessor_and_distance",
            "all_pairs_dijkstra",
            "all_pairs_dijkstra_path",
            "all_pairs_dijkstra_path_length",
            "all_pairs_bellman_ford_path",
            "all_pairs_bellman_ford_path_length",
            "all_pairs_shortest_path",
            "all_pairs_shortest_path_length",
            "shortest_path",
            "shortest_path_length",
        ],
        "directed": [
            "in_degree_centrality",
            "out_degree_centrality",
            "is_weakly_connected",
            "weakly_connected_components",
            "number_weakly_connected_components",
            "strongly_connected_components",
            "number_strongly_connected_components",
            "is_strongly_connected",
            "is_semiconnected",
            "condensation",
        ],
        "dag": [
            "is_directed_acyclic_graph",
            "topological_sort",
            "topological_generations",
            "dag_longest_path",
            "dag_longest_path_length",
            "transitive_reduction",
        ],
    }
    graph_for = {"undirected": U, "directed": D, "dag": A, "small": graphs["small"]}
    for kind, names in single.items():
        G = graph_for[kind]
        for name in names:
            yield name, G, (), {}

    src, tgt = 0, n - 1
    for name in (
        "single_source_dijkstra",
        "single_source_dijkstra_path",
        "single_source_dijkstra_path_length",
        "single_source_bellman_ford",
        "single_source_bellman_ford_path",
        "single_source_bellman_ford_path_length",
        "single_source_shortest_path",
        "single_source_shortest_path_length",
    ):
        yield name, U, (src,), {}
    for name in ("single_target_shortest_path", "single_target_shortest_path_length"):
        yield name, U, (tgt,), {}
    # Use a node in the middle of the DAG so both directions have work to do.
    middle = n // 2
    for name in ("ancestors", "descendants"):
        yield name, A, (middle,), {}
    yield "node_connected_component", U, (src,), {}
    # Cycle and path enumeration is exponential, so keep those graphs sparse.
    sparse_directed = nx.gnp_random_graph(40, 0.05, seed=2, directed=True)
    sparse_undirected = nx.gnp_random_graph(24, 0.12, seed=2)
    yield "simple_cycles", sparse_directed, (), {}
    yield "all_simple_paths", sparse_undirected, (0, 23), {}
    yield "all_shortest_paths", U, (src, tgt), {}
    yield "has_path", U, (src, tgt), {}
    yield "bidirectional_shortest_path", U, (src, tgt), {}
    yield "dijkstra_path", U, (src, tgt), {}
    yield "dijkstra_path_length", U, (src, tgt), {}
    yield "bellman_ford_path", U, (src, tgt), {}
    yield "bellman_ford_path_length", U, (src, tgt), {}
    yield "astar_path", U, (src, tgt), {}
    yield "astar_path_length", U, (src, tgt), {}
    yield (
        "find_negative_cycle",
        nx.DiGraph([(0, 1, {"weight": 1}), (1, 2, {"weight": -3}), (2, 0, {"weight": 1})]),
        (0,),
        {},
    )
    # Katz needs alpha below 1 / lambda_max, which shrinks as the graph grows.
    alpha = 0.5 / max(dict(U.degree()).values())
    yield "katz_centrality", U, (alpha,), {}
    yield "katz_centrality_numpy", U, (alpha,), {}
    yield "descendants_at_distance", A, (src, 2), {}
    yield "immediate_dominators", A, (src,), {}
    yield "dfs_edges", U, (src,), {}
    yield (
        "average_shortest_path_length",
        nx.connected_watts_strogatz_graph(min(n, 400), 4, 0.3, seed=1),
        (),
        {},
    )
    # stoer_wagner needs a connected, non-negatively weighted graph.
    connected = nx.connected_watts_strogatz_graph(min(n, 300), 4, 0.3, seed=1)
    for u, v in connected.edges():
        connected[u][v]["weight"] = 1 + ((u + v) % 5)
    yield "stoer_wagner", connected, (), {}
    yield "group_betweenness_centrality", U, (half,), {}
    yield "group_closeness_centrality", U, (half,), {}
    yield "group_degree_centrality", U, (half,), {}
    yield "steiner_tree", U, (half,), {}
    yield "is_isomorphic", U, (U.copy(),), {}
    yield "vf2pp_is_isomorphic", U, (U.copy(),), {}
    yield "cartesian_product", nx.path_graph(60), (nx.cycle_graph(30),), {}
    yield "tensor_product", nx.path_graph(60), (nx.cycle_graph(30),), {}


def _consume(value):
    if hasattr(value, "__next__") or isinstance(value, (map, filter)):
        return list(value)
    return value


def _time(fn, budget=0.25, max_loops=200):
    fn()  # warm up caches and imports
    loops, start = 0, time.perf_counter()
    while time.perf_counter() - start < budget and loops < max_loops:
        fn()
        loops += 1
    elapsed = time.perf_counter() - start
    return elapsed / max(loops, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=800)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--slowest", type=int, default=10)
    args = parser.parse_args()

    graphs = _graphs(args.nodes, args.seed)
    rows = []
    for name, G, extra, kwargs in _calls(graphs, args.nodes):
        func = getattr(nx, name, None) or getattr(nx.approximation, name, None)
        if func is None:
            continue
        print(f"  timing {name} ...", file=sys.stderr, flush=True)
        try:
            backend = _time(lambda: _consume(func(G, *extra, backend="rustworkx", **kwargs)))
            reference = _time(lambda: _consume(func.orig_func(G, *extra, **kwargs)))
        except Exception as exc:  # noqa: BLE001 - report, do not stop the sweep
            rows.append((name, None, None, f"{type(exc).__name__}: {exc}", False))
            continue
        auto = BackendInterface.should_run(name, (G, *extra), kwargs) is True
        rows.append((name, backend, reference, None, auto))
        gc.collect()

    covered = {row[0] for row in rows}
    missing = sorted(set(ALGORITHMS) - covered)

    timed = [r for r in rows if r[1] is not None]
    timed.sort(key=lambda r: r[2] / r[1])
    print(f"{'function':<42}{'rustworkx':>12}{'networkx':>12}{'speedup':>10}  auto")
    for name, backend, reference, _, auto in timed:
        mark = "yes" if auto else "no"
        print(f"{name:<42}{backend:>12.5f}{reference:>12.5f}{reference / backend:>9.1f}x  {mark}")

    slower = [r for r in timed if r[2] / r[1] < 1.0]
    # Only a material, repeatable loss is worth changing the dispatch policy for;
    # anything within 10% of NetworkX is parity on a noisy machine.
    material = [r for r in timed if r[2] / r[1] < 0.9]
    errors = [r for r in rows if r[3] is not None]
    print(f"\ntimed {len(timed)} functions, {len(slower)} slower than NetworkX")
    gated = sorted(r[0] for r in slower if not r[4])
    ungated = sorted(r[0] for r in material if r[4])
    if gated:
        print(f"slower, and should_run already declines them: {', '.join(gated)}")
    if ungated:
        print(f"SLOWER AND STILL AUTO-DISPATCHED: {', '.join(ungated)}")
    if slower:
        print("slower: " + ", ".join(f"{r[0]} ({r[2] / r[1]:.2f}x)" for r in slower))
    if errors:
        print("errors:")
        for name, _, _, message, _auto in errors:
            print(f"  {name}: {message}")
    if missing:
        print(f"not benchmarked ({len(missing)}): {', '.join(missing)}")
    return 1 if errors or ungated else 0


if __name__ == "__main__":
    raise SystemExit(main())
