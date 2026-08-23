#!/usr/bin/env python3
"""Drive NetworkX's own bundled asv benchmark suite as a zero-change A/B test.

The suite (in the networkx repo's ``benchmarks/`` directory) calls plain
``nx.<func>(G)`` with no backend awareness, so running it twice — once with a
clean environment and once with ``NETWORKX_BACKEND_PRIORITY=rustworkx`` — is
the honest "existing user code, zero changes" comparison. Auto-dispatch rules
apply: graphs below the n<200/m<400 floor stay on NetworkX by design, and the
dispatch probe records the expected verdict per benchmark graph.

The one deviation, applied only when snap.stanford.edu is unreachable (it is
from some CI containers): the drug-interaction-network parameter is dropped
from ``benchmark_algorithms.py``, because the 3.6.1 suite downloads it at
import time with no error handling.

    uv run python benches/external/run_networkx_asv.py --workdir /tmp/w
"""

from __future__ import annotations

import argparse
import random
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import _common
import _dispatch
import networkx as nx
from _common import log

UPSTREAM = "https://github.com/networkx/networkx"
PIN = "7530809bfa1ea7ed6fdf918a4d1431488953cb1f"  # tag networkx-3.6.1
DRUG_URL = (
    "https://snap.stanford.edu/biodata/datasets/10001/files/"
    "ChCh-Miner_durgbank-chem-chem.tsv.gz"
)
DRUG_PATCHES = [
    ("        fetch_drug_interaction_network(),\n", ""),
    ('        "Drug Interaction network",\n', ""),
]

BENCH_PATTERNS = [
    r"benchmark_algorithms\.UndirectedAlgorithmBenchmarks\."
    r"time_(betweenness_centrality|pagerank|connected_components)$",
    r"benchmark_algorithms\.DirectedAlgorithmBenchmarks\.time_tarjan_scc$",
    r"benchmark_algorithms\.WeightedGraphBenchmark\.time_shortest_path$",
    r"benchmark_many_components\.ManyComponentsBenchmark\."
    r"time_single_source_all_shortest_paths$",
]


def drug_url_reachable(timeout: float = 15) -> bool:
    try:
        with urllib.request.urlopen(DRUG_URL, timeout=timeout) as resp:
            return resp.status == 200
    except Exception as exc:
        log(f"drug-network URL unreachable ({exc!r})")
        return False


def _dijkstra_relaxation_worst_case(n: int) -> nx.Graph:
    # Mirrors the suite's worst-case builder so verdicts use the real shape.
    G = nx.empty_graph(n)
    for i in range(n):
        for j in range(i + 1, n):
            G.add_edge(i, j, weight=2 * (j - 1 - i) + 1)
    return G


def _weighted(graph_func, *args, seed=42, **kwargs) -> nx.Graph:
    rng = random.Random(seed)
    G = graph_func(*args, **kwargs)
    for u, v in G.edges():
        G[u][v]["weight"] = rng.randint(1, len(G))
    return G


def probe(out_dir: Path) -> None:
    """Record would-auto-dispatch verdicts for each benchmark's graphs.

    Large ER graphs are rebuilt with ``fast_gnp_random_graph`` stand-ins
    (same type/size/density; the verdict depends only on those).
    """
    rows: list[dict] = []

    def add(func: str, G, label: str, kwargs: dict | None = None) -> None:
        row = _dispatch.auto_dispatch_verdict(func, G, kwargs)
        row["params"] = label
        rows.append(row)

    for p in (0.1, 0.5, 0.9):
        G = nx.fast_gnp_random_graph(100, p, seed=42)
        for func in ("betweenness_centrality", "pagerank", "connected_components"):
            add(func, G, f"Erdos Renyi (100, {p})")

    # Labels must match the suite's literal param strings (str(0.00005) would
    # render as "5e-05" and miss).
    directed_specs = [
        (100, "0.005"), (100, "0.01"), (100, "0.05"), (100, "0.1"), (100, "0.5"),
        (1000, "0.0005"), (1000, "0.001"), (1000, "0.005"), (1000, "0.01"),
        (1000, "0.05"),
        (10000, "0.00005"), (10000, "0.0001"), (10000, "0.0005"),
    ]
    for n, p_str in directed_specs:
        G = nx.fast_gnp_random_graph(n, float(p_str), seed=42, directed=True)
        add("strongly_connected_components", G, f"Erdos Renyi ({n}, {p_str})")
    for n in (100, 1000, 10000):
        add(
            "strongly_connected_components",
            nx.empty_graph(n, create_using=nx.DiGraph),
            f"Empty ({n})",
        )
    for n in (100, 1000):
        add(
            "strongly_connected_components",
            nx.complete_graph(n, create_using=nx.DiGraph),
            f"Complete ({n})",
        )

    sp_kwargs = {"weight": "weight"}
    for n in (10, 100, 1000):
        G = _dijkstra_relaxation_worst_case(n)
        add(
            "shortest_path",
            G,
            f"dijkstra_relaxation_worst_case({n})",
            {**sp_kwargs, "source": 0, "target": n - 1},
        )
    for n in (100, 1000, 10000, 20000):
        G = _weighted(nx.path_graph, n)
        add(
            "shortest_path",
            G,
            f"weighted_graph(42, path_graph, {n})",
            {**sp_kwargs, "source": 0, "target": n - 1},
        )
    for n in (10, 100, 1000):
        for p in (0.1, 0.5, 0.9):
            G = _weighted(nx.fast_gnp_random_graph, n, p, seed=42)
            add(
                "shortest_path",
                G,
                f"weighted_graph(42, erdos_renyi_graph, {n}, {p}, seed=42)",
                {**sp_kwargs, "source": 0, "target": n - 1},
            )

    atlas_standin = nx.disjoint_union_all(
        [nx.gnm_random_graph(5, 6, seed=i) for i in range(142)]
    )
    add(
        "single_source_all_shortest_paths",
        atlas_standin,
        "atlas6 disjoint union (stand-in)",
        {"source": 0},
    )

    _common.write_json(out_dir / "dispatch-probe.json", rows)


def run_arm(bench_dir: Path, rev: str, env: dict, launch: list[str], timebox: float) -> int:
    cmd = [
        sys.executable, "-m", "asv", "run",
        "-E", "existing:same",
        "--set-commit-hash", rev,
        "--show-stderr",
        *launch,
    ]
    for pattern in BENCH_PATTERNS:
        cmd += ["-b", pattern]
    try:
        return _common.run(cmd, cwd=bench_dir, env=env, timeout=timebox, check=False).returncode
    except subprocess.TimeoutExpired:
        log(f"asv run hit the {timebox:.0f}s timebox; keeping partial results")
        return -1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, default=_common.DEFAULT_WORKDIR)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--rev", default=PIN, help="networkx commit to pin")
    parser.add_argument("--timebox", type=float, default=1200, help="seconds per arm")
    args = parser.parse_args()
    out = args.out or (args.workdir / "results-networkx")
    out.mkdir(parents=True, exist_ok=True)

    suite = _common.clone_at(UPSTREAM, args.rev, args.workdir, "networkx")
    bench_dir = suite / "benchmarks"

    drug_dropped = False
    if not drug_url_reachable():
        _common.patch_file(
            bench_dir / "benchmarks" / "benchmark_algorithms.py",
            DRUG_PATCHES,
            "drop offline drug-network param",
        )
        drug_dropped = True

    help_txt = subprocess.run(
        [sys.executable, "-m", "asv", "run", "--help"], capture_output=True, text=True
    ).stdout
    # forkserver imports the (expensive) benchmark modules once per arm
    # instead of once per benchmark process.
    launch = ["--launch-method", "forkserver"] if "--launch-method" in help_txt else []

    _common.run(
        [sys.executable, "-m", "asv", "machine", "--yes"],
        cwd=bench_dir,
        env=_common.clean_env(),
    )

    results_dir = bench_dir / "results"
    started = time.monotonic()
    rc_baseline = run_arm(bench_dir, args.rev, _common.clean_env(), launch, args.timebox)
    if results_dir.exists():
        _common.snapshot_tree(results_dir, out / "baseline")

    # asv keys results by machine+commit+env, so a second identical run would
    # merge into the same file; wipe between arms but keep the benchmark
    # discovery cache (module import there costs minutes).
    bjson = results_dir / "benchmarks.json"
    saved = bjson.read_bytes() if bjson.exists() else None
    if results_dir.exists():
        shutil.rmtree(results_dir)
    results_dir.mkdir(parents=True)
    if saved is not None:
        bjson.write_bytes(saved)

    rc_backend = run_arm(
        bench_dir,
        args.rev,
        _common.clean_env(NETWORKX_BACKEND_PRIORITY="rustworkx"),
        launch,
        args.timebox,
    )
    if results_dir.exists():
        _common.snapshot_tree(results_dir, out / "rustworkx")
    duration = time.monotonic() - started

    for arm in ("baseline", "rustworkx"):
        if not _common.asv_result_files(out / arm):
            log(f"ERROR: {arm} arm produced no asv result files")
            rc_baseline = rc_baseline or 1

    probe(out)

    _common.write_json(
        out / "meta.json",
        {
            "target": "networkx-asv",
            "upstream": UPSTREAM,
            "rev": args.rev,
            "bench_patterns": BENCH_PATTERNS,
            "drug_network_dropped": drug_dropped,
            "launch_method": launch[-1] if launch else "default",
            "returncodes": {"baseline": rc_baseline, "rustworkx": rc_backend},
            "duration_s": round(duration, 1),
            "machine": _common.machine_info(),
            "notes": [
                "zero benchmark-code changes; backend selected purely via "
                "NETWORKX_BACKEND_PRIORITY=rustworkx in the environment"
                + (" (except the offline drug-network drop)" if drug_dropped else ""),
                "auto-dispatch declines n<200 or m<400 graphs by design; see "
                "dispatch-probe.json for the per-graph verdicts",
                "NetworkX's conversion cache (default on since 3.4) amortizes "
                "nx->rustworkx conversion across samples within a cell",
            ],
        },
    )
    return 0 if rc_baseline in (0, -1) and rc_backend in (0, -1) else 1


if __name__ == "__main__":
    raise SystemExit(main())
