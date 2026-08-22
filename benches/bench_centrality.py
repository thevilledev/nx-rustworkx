#!/usr/bin/env python3
"""Compare rustworkx-backed betweenness with stock NetworkX.

Reports convert time and kernel time separately. Graphs use the same
construction as the v0.1 milestone: ``gnp_random_graph(n, p, seed=1)``.
"""

from __future__ import annotations

import argparse
import time

import networkx as nx
import rustworkx as rx

from nx_rustworkx.convert import convert_from_nx
from nx_rustworkx.interface import BackendInterface


def _time(fn, loops: int) -> float:
    start = time.perf_counter()
    for _ in range(loops):
        fn()
    return (time.perf_counter() - start) / loops


def bench_one(n: int, p: float, seed: int, loops: int, run_networkx: bool) -> dict:
    G = nx.gnp_random_graph(n, p, seed=seed)
    convert_s = _time(lambda: convert_from_nx(G), loops)
    rwg = convert_from_nx(G)

    def kernel():
        return rx.betweenness_centrality(rwg.rx_graph, normalized=True)

    kernel_s = _time(kernel, loops)
    dispatch_s = _time(
        lambda: nx.betweenness_centrality(G, backend="rustworkx"),
        loops,
    )
    nx_s = None
    if run_networkx:
        nx_s = _time(lambda: nx.betweenness_centrality.orig_func(G), max(1, loops))
    ratio = None if nx_s is None else nx_s / dispatch_s
    convert_share = convert_s / dispatch_s if dispatch_s else 0.0
    return {
        "n": n,
        "m": G.number_of_edges(),
        "p": p,
        "convert_s": convert_s,
        "kernel_s": kernel_s,
        "dispatch_s": dispatch_s,
        "nx_s": nx_s,
        "ratio": ratio,
        "convert_share": convert_share,
        "should_run": BackendInterface.should_run("betweenness_centrality", (G,), {}),
    }


def _fmt(value, digits=4):
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--loops", type=int, default=3)
    parser.add_argument("--skip-nx-20k", action="store_true", default=True)
    args = parser.parse_args(argv)

    cases = (
        (200, 0.1),
        (2000, 0.01),
        (20000, 0.001),
    )
    rows = []
    for n, p in cases:
        run_nx = not (n >= 20000 and args.skip_nx_20k)
        print(f"benchmarking n={n} p={p} networkx={run_nx} ...", flush=True)
        rows.append(bench_one(n, p, args.seed, args.loops, run_nx))

    print()
    header = (
        "| n | m | convert (s) | kernel (s) | rustworkx total (s) "
        "| NetworkX (s) | speedup | convert share |"
    )
    print(header)
    print(
        "|---|---|-------------|------------|---------------------|"
        "--------------|---------|---------------|"
    )
    for row in rows:
        print(
            f"| {row['n']} | {row['m']} | {_fmt(row['convert_s'])} | "
            f"{_fmt(row['kernel_s'])} | {_fmt(row['dispatch_s'])} | "
            f"{_fmt(row['nx_s'])} | {_fmt(row['ratio'], 3)}x | "
            f"{_fmt(100 * row['convert_share'], 3)}% |"
        )
    print()
    print("should_run decisions:")
    for row in rows:
        print(f"  n={row['n']} m={row['m']}: {row['should_run']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
