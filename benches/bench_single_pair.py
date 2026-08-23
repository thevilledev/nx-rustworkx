#!/usr/bin/env python3
"""Measure single-pair shortest-path dispatch against stock NetworkX.

NetworkX answers a weighted single pair with bidirectional Dijkstra, while the
backend runs a full single-source rustworkx kernel; whether that wins depends
on graph shape. This bench times every single-pair function on three shapes —
a long thin path graph and a dense random graph (both adversarial: the search
visits everything) and a road-like geometric graph (friendly: short paths,
small visited sets) — with the conversion cache warm, which is the flattering
case for the backend. A function that loses warm loses cold too, so anything
below ~1x here belongs in NO_AUTO_DISPATCH or behind a should_run decline.

    python benches/bench_single_pair.py
    python benches/bench_single_pair.py --repeat 5 --road-nodes 20000
"""

from __future__ import annotations

import argparse
import gc
import math
import random
import time

import networkx as nx

nx.config.warnings_to_ignore.add("cache")

FUNCTIONS = [
    "shortest_path",
    "shortest_path_length",
    "dijkstra_path",
    "dijkstra_path_length",
    "bellman_ford_path",
    "bellman_ford_path_length",
    "all_shortest_paths",
]


def weighted_path_graph(n: int, seed: int) -> nx.Graph:
    rng = random.Random(seed)
    G = nx.path_graph(n)
    for u, v in G.edges():
        G[u][v]["weight"] = rng.randint(1, n)
    return G


def weighted_dense_graph(n: int, p: float, seed: int) -> nx.Graph:
    rng = random.Random(seed)
    G = nx.gnp_random_graph(n, p, seed=seed)
    for u, v in G.edges():
        G[u][v]["weight"] = rng.randint(1, n)
    return G


def road_graph(n: int, seed: int) -> nx.DiGraph:
    """Road-network-like DiGraph: geometric layout, reciprocal weighted edges."""
    radius = math.sqrt(7 / (math.pi * n))  # ~7 expected neighbors
    G = nx.random_geometric_graph(n, radius, seed=seed)
    G = G.subgraph(max(nx.connected_components(G), key=len))
    pos = nx.get_node_attributes(G, "pos")
    D = nx.DiGraph()
    for u, v in G.edges():
        w = math.dist(pos[u], pos[v]) * 1000
        D.add_edge(u, v, weight=w)
        D.add_edge(v, u, weight=w)
    return D


def far_pair(G) -> tuple:
    source = min(G.nodes)
    lengths = nx.single_source_shortest_path_length.orig_func(G, source)
    target = max(lengths, key=lambda node: lengths[node])
    return source, target


def consume(result):
    if hasattr(result, "__next__"):
        return list(result)
    return result


def best_of(repeat: int, fn) -> float:
    best = math.inf
    for _ in range(repeat):
        gc.collect()
        start = time.perf_counter()
        consume(fn())
        best = min(best, time.perf_counter() - start)
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--path-nodes", type=int, default=10000)
    parser.add_argument("--dense-nodes", type=int, default=1000)
    parser.add_argument("--dense-p", type=float, default=0.5)
    parser.add_argument("--road-nodes", type=int, default=12000)
    args = parser.parse_args()

    graphs = {
        "path": weighted_path_graph(args.path_nodes, args.seed),
        "dense": weighted_dense_graph(args.dense_nodes, args.dense_p, args.seed),
        "road": road_graph(args.road_nodes, args.seed),
    }

    losses = 0
    print(f"{'function':28} {'shape':6} {'NetworkX':>11} {'rustworkx':>11} {'ratio':>7}")
    for shape, G in graphs.items():
        source, target = far_pair(G)
        # Warm the dispatcher's conversion cache so every timed backend call
        # measures the kernel, not the one-off conversion.
        nx.dijkstra_path_length(G, source, target, backend="rustworkx")
        for name in FUNCTIONS:
            func = getattr(nx, name)
            kwargs = {"weight": "weight"}
            t_nx = best_of(args.repeat, lambda: func.orig_func(G, source, target, **kwargs))
            t_rw = best_of(
                args.repeat, lambda: func(G, source, target, backend="rustworkx", **kwargs)
            )
            ratio = t_nx / t_rw
            flag = "" if ratio >= 0.95 else "  <-- LOSS"
            losses += ratio < 0.95
            print(f"{name:28} {shape:6} {t_nx:10.5f}s {t_rw:10.5f}s {ratio:6.1f}x{flag}")

    print(f"\n{losses} losing cells (warm cache, best of {args.repeat})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
