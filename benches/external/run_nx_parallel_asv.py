#!/usr/bin/env python3
"""Drive networkx/nx-parallel's asv benchmark suite against this backend.

The nx-parallel suite treats the backend as a benchmark parameter and passes
it via the ``backend=`` kwarg, so swapping ``"parallel"`` for ``"rustworkx"``
measures forced dispatch (conversion included) against stock NetworkX side by
side, on fully offline synthetic graphs. Only functions this backend
implements are selected; an explicit ``backend=`` on anything else would raise.

    uv run python benches/external/run_nx_parallel_asv.py
    uv run python benches/external/run_nx_parallel_asv.py --workdir /tmp/w --full-grid
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import _common
import _dispatch
import networkx as nx
from _common import log

UPSTREAM = "https://github.com/networkx/nx-parallel"
PIN = "c80febed56d37311735d5db94d63c5ac424e161b"  # main as of 2026-08-23

# time_* functions in the suite that nx-rustworkx implements.
SUPPORTED = [
    "betweenness_centrality",
    "edge_betweenness_centrality",
    "all_pairs_shortest_path_length",
    "all_pairs_shortest_path",
    "all_pairs_dijkstra",
    "all_pairs_dijkstra_path_length",
    "all_pairs_dijkstra_path",
    "all_pairs_bellman_ford_path_length",
    "all_pairs_bellman_ford_path",
    "number_connected_components",
    "number_strongly_connected_components",
    "number_weakly_connected_components",
    "number_of_isolates",
]
DIRECTED_FUNCS = {
    "number_strongly_connected_components",
    "number_weakly_connected_components",
}

BACKEND_PATCH = ('backends = ["parallel", None]', 'backends = ["rustworkx", None]')
GRID_PATCHES = [
    ("num_nodes = [50, 100, 200, 400, 800]", "num_nodes = [200, 400]"),
    ("edge_prob = [0.8, 0.6, 0.4, 0.2]", "edge_prob = [0.6, 0.2]"),
]
# One sample per cell keeps the trimmed grid to minutes; each rustworkx cell
# then times a cold call, i.e. nx->rustworkx conversion included.
TIMING_PATCH = (
    "class Benchmark:\n    pass",
    "class Benchmark:\n"
    "    timeout = 600\n"
    "    repeat = 1\n"
    "    number = 1\n"
    "    min_run_count = 1\n"
    "    warmup_time = 0.0\n",
)


def probe(out_dir: Path, num_nodes: list[int], edge_prob: list[float]) -> None:
    """Record would-auto-dispatch verdicts at the suite's graph sizes.

    The suite forces dispatch via an explicit ``backend=`` kwarg, which
    bypasses ``should_run`` (the n<200/m<400 floor) but not ``can_run``; the
    verdicts document both anyway.
    """
    rows = []
    for n in num_nodes:
        for p in edge_prob:
            undirected = nx.fast_gnp_random_graph(n, p, seed=42)
            directed = nx.fast_gnp_random_graph(n, p, seed=42, directed=True)
            for name in SUPPORTED:
                G = directed if name in DIRECTED_FUNCS else undirected
                row = _dispatch.auto_dispatch_verdict(name, G)
                row["params"] = f"n={n}, p={p}"
                row["forced_by_suite"] = True
                rows.append(row)
    _common.write_json(out_dir / "dispatch-probe.json", rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, default=_common.DEFAULT_WORKDIR)
    parser.add_argument("--out", type=Path, default=None, help="result directory")
    parser.add_argument("--rev", default=PIN, help="nx-parallel commit to pin")
    parser.add_argument("--bench", default=None, help="override the asv -b regex")
    parser.add_argument("--timebox", type=float, default=1500, help="seconds")
    parser.add_argument(
        "--full-grid",
        action="store_true",
        help="keep upstream's n<=800 x 4-density grid (hours, not minutes)",
    )
    args = parser.parse_args()
    out = args.out or (args.workdir / "results-nx-parallel")
    out.mkdir(parents=True, exist_ok=True)

    suite = _common.clone_at(UPSTREAM, args.rev, args.workdir, "nx-parallel")
    patches = [BACKEND_PATCH, TIMING_PATCH]
    if not args.full_grid:
        patches += GRID_PATCHES
    _common.patch_file(suite / "benchmarks" / "benchmarks" / "common.py", patches, "nx-parallel")
    # Upstream bug at the pinned rev: the Attracting/StronglyConnected/
    # WeaklyConnected setups pass seed= to get_cached_gnp_random_graph, which
    # has no such kwarg (the module-global seed is used internally), so they
    # fail on every backend including stock NetworkX. Drop the bogus kwarg.
    _common.patch_file(
        suite / "benchmarks" / "benchmarks" / "bench_components.py",
        [
            (
                "num_nodes, edge_prob, seed=seed, is_directed=True",
                "num_nodes, edge_prob, is_directed=True",
                3,
            )
        ],
        "fix upstream seed kwarg bug",
    )

    # asv matches the regex against "name(param, ...)" for parameterized
    # benchmarks, so anchor on the opening paren rather than end-of-string.
    bench_re = args.bench or r"time_({})(\(|$)".format("|".join(SUPPORTED))
    bench_dir = suite / "benchmarks"
    env = _common.clean_env()
    _common.run([sys.executable, "-m", "asv", "machine", "--yes"], cwd=bench_dir, env=env)

    cmd = [
        sys.executable,
        "-m",
        "asv",
        "run",
        "-E",
        "existing:same",
        "--set-commit-hash",
        args.rev,
        "--show-stderr",
        "-b",
        bench_re,
    ]
    started = time.monotonic()
    timed_out = False
    try:
        result = _common.run(cmd, cwd=bench_dir, env=env, timeout=args.timebox, check=False)
        returncode = result.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        returncode = -1
        log(f"asv run hit the {args.timebox:.0f}s timebox; keeping partial results")
    duration = time.monotonic() - started

    results_dir = bench_dir / "results"
    if results_dir.exists():
        _common.snapshot_tree(results_dir, out / "asv-results")
    captured = _common.asv_result_files(out / "asv-results")
    if not captured:
        log("ERROR: asv produced no result files (discovery/import failure?)")
        returncode = returncode or 1

    num_nodes = [200, 400] if not args.full_grid else [50, 100, 200, 400, 800]
    edge_prob = [0.6, 0.2] if not args.full_grid else [0.8, 0.6, 0.4, 0.2]
    probe(out, num_nodes, edge_prob)

    _common.write_json(
        out / "meta.json",
        {
            "target": "nx-parallel",
            "upstream": UPSTREAM,
            "rev": args.rev,
            "bench_regex": bench_re,
            "grid": {"num_nodes": num_nodes, "edge_prob": edge_prob},
            "asv_returncode": returncode,
            "timed_out": timed_out,
            "duration_s": round(duration, 1),
            "machine": _common.machine_info(),
            "notes": [
                "backend forced per call via backend= kwarg (bypasses the "
                "n<200/m<400 auto-dispatch floor, not can_run)",
                "repeat=number=1: each rustworkx cell is a cold call, so "
                "nx->rustworkx conversion time is included",
            ],
        },
    )
    return 0 if (returncode == 0 or timed_out) else 1


if __name__ == "__main__":
    raise SystemExit(main())
