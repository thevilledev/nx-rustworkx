#!/usr/bin/env python3
"""Compare every native generator against stock NetworkX.

Generators skip ``should_run`` entirely (the dispatcher only consults it when
a conversion is involved), so there is no dispatch gate to tune: if a
generator measures materially slower here, the remedy is dropping its kernel.
The backend timing includes building the node-identity wrapper.

    python benches/bench_generators.py
    python benches/bench_generators.py --nodes 2000
"""

from __future__ import annotations

import argparse
import gc
import sys
import time

import networkx as nx

import nx_rustworkx.interface  # noqa: F401  ensure the backend is registered

nx.config.warnings_to_ignore.add("cache")


def _calls(n: int):
    """Yield ``(name, args, kwargs)`` sized so one row cannot dominate."""
    side = max(2, int(n**0.5))
    order = max(1, n.bit_length() - 1)
    yield "path_graph", (n,), {}
    yield "cycle_graph", (n,), {}
    yield "star_graph", (n,), {}
    # complete_graph is quadratic in n; keep the row comparable to the others.
    yield "complete_graph", (max(40, n // 4),), {}
    yield "barbell_graph", (n // 2, n // 4), {}
    yield "lollipop_graph", (n // 2, n // 4), {}
    yield "binomial_tree", (order,), {}
    yield "full_rary_tree", (3, n), {}
    yield "karate_club_graph", (), {}
    yield "grid_2d_graph", (side, side), {}
    yield "gnp_random_graph", (n, min(0.05, 20 / n)), {"seed": 1}
    yield "fast_gnp_random_graph", (n, min(0.05, 20 / n)), {"seed": 1}
    yield "gnm_random_graph", (n, 4 * n), {"seed": 1}
    yield "dense_gnm_random_graph", (n, 4 * n), {"seed": 1}
    yield "random_regular_graph", (4, n), {"seed": 1}
    yield (
        "stochastic_block_model",
        ([n // 2, n - n // 2], [[0.02, 0.005], [0.005, 0.02]]),
        {"seed": 1},
    )
    yield "random_geometric_graph", (n, 0.05), {"seed": 1}
    yield "barabasi_albert_graph", (n, 3), {"seed": 1}
    yield "hexagonal_lattice_graph", (side // 2, side // 2), {}
    yield "random_graph", (n // 2, n - n // 2, min(0.05, 20 / n)), {"seed": 1}


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
    args = parser.parse_args()

    # Seeded rows need the opt-in to exercise the native kernels.
    nx.config.backends.rustworkx.native_seeded_generators = True
    rows = []
    try:
        for name, call_args, kwargs in _calls(args.nodes):
            func = getattr(nx, name, None) or getattr(nx.bipartite, name)
            print(f"  timing {name} ...", file=sys.stderr, flush=True)

            def _orig_kwargs():
                if "seed" in kwargs:
                    resolved = dict(kwargs)
                    resolved["seed"] = nx.utils.create_py_random_state(kwargs["seed"])
                    return resolved
                return kwargs

            try:
                backend = _time(lambda: func(*call_args, backend="rustworkx", **kwargs))
                reference = _time(lambda: func.orig_func(*call_args, **_orig_kwargs()))
            except Exception as exc:  # noqa: BLE001 - report, do not stop the sweep
                rows.append((name, None, None, f"{type(exc).__name__}: {exc}"))
                continue
            rows.append((name, backend, reference, None))
            gc.collect()
    finally:
        nx.config.backends.rustworkx.native_seeded_generators = False

    timed = [r for r in rows if r[1] is not None]
    timed.sort(key=lambda r: r[2] / r[1])
    print(f"{'generator':<28}{'rustworkx':>12}{'networkx':>12}{'speedup':>10}")
    for name, backend, reference, _ in timed:
        print(f"{name:<28}{backend:>12.5f}{reference:>12.5f}{reference / backend:>9.1f}x")

    # Only a material, repeatable loss matters; within 10% is parity on a
    # noisy machine.
    material = [r for r in timed if r[2] / r[1] < 0.9]
    errors = [r for r in rows if r[3] is not None]
    if material:
        print("MATERIALLY SLOWER: " + ", ".join(f"{r[0]} ({r[2] / r[1]:.2f}x)" for r in material))
    if errors:
        print("errors:")
        for name, _, _, message in errors:
            print(f"  {name}: {message}")
    return 1 if errors or material else 0


if __name__ == "__main__":
    raise SystemExit(main())
