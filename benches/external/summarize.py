#!/usr/bin/env python3
"""Merge the external-benchmark outputs into a single RESULTS.md.

    uv run python benches/external/summarize.py \
        --t1 <dir from run_nx_parallel_asv> \
        --t2 <dir from run_networkx_asv> \
        --t3 <json from osmnx_demo> \
        --out benches/external/RESULTS.md
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import time
from pathlib import Path

# asv benchmark name suffix -> the dispatched NetworkX function it times.
T2_FUNCTIONS = {
    "time_betweenness_centrality": "betweenness_centrality",
    "time_pagerank": "pagerank",
    "time_connected_components": "connected_components",
    "time_tarjan_scc": "strongly_connected_components",
    "time_shortest_path": "shortest_path",
    "time_single_source_all_shortest_paths": "single_source_all_shortest_paths",
}


def load_asv_dir(snapshot_dir: Path) -> dict[str, tuple[list, list]]:
    """Return {benchmark_name: (values, params)} from an asv results snapshot."""
    out: dict[str, tuple[list, list]] = {}
    if not snapshot_dir.exists():
        return out
    for f in sorted(snapshot_dir.rglob("*.json")):
        if f.name in ("benchmarks.json", "machine.json"):
            continue
        data = json.loads(f.read_text())
        if "results" not in data or "commit_hash" not in data:
            continue
        cols = data.get("result_columns") or ["result", "params"]
        for name, row in data["results"].items():
            m = dict(zip(cols, row if isinstance(row, list) else [row]))
            out[name] = (m.get("result") or [], m.get("params") or [])
    return out


def combo_values(values: list, params: list) -> dict[tuple, float | None]:
    combos = list(itertools.product(*params)) if params else [()]
    return dict(zip(combos, values))


def unquote(s: str) -> str:
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"" else s


def fmt_s(v: float | None) -> str:
    if v is None:
        return "failed"
    return f"{v:.4g} s"


def fmt_speedup(nx_t: float | None, rw_t: float | None) -> str:
    if nx_t is None or rw_t is None or rw_t == 0:
        return "—"
    return f"**{nx_t / rw_t:.1f}x**"


def short_name(name: str) -> str:
    parts = name.split(".")
    return parts[-1].removeprefix("time_") + f" ({parts[0].removeprefix('bench_')})"


def load_json(path: Path | None) -> dict | list | None:
    if path is None or not Path(path).exists():
        return None
    return json.loads(Path(path).read_text())


def t1_section(t1_dir: Path | None, warnings: list[str]) -> list[str]:
    lines = ["## Target 1 — `networkx/nx-parallel` asv suite (forced dispatch)", ""]
    meta = load_json(t1_dir / "meta.json") if t1_dir else None
    results = load_asv_dir(t1_dir / "asv-results") if t1_dir else {}
    if not results:
        return [*lines, "_no results captured_", ""]
    lines += [
        f"Upstream `{meta['rev'][:12]}`, one-line backend patch "
        '(`backends = ["rustworkx", None]`); `repeat = number = 1`, so every '
        "rustworkx cell is a **cold call including nx→rustworkx conversion**.",
        "",
        "| benchmark | params | NetworkX | rustworkx (incl. convert) | speedup |",
        "|---|---|---|---|---|",
    ]
    for name, (values, params) in sorted(results.items()):
        if not params:
            continue
        vals = combo_values(values, params)
        for combo in itertools.product(*params[1:]):
            nx_t = vals.get(("None", *combo))
            rw_t = vals.get(("'rustworkx'", *combo))
            label = ", ".join(unquote(c) for c in combo)
            lines.append(
                f"| {short_name(name)} | {label} | {fmt_s(nx_t)} | {fmt_s(rw_t)} "
                f"| {fmt_speedup(nx_t, rw_t)} |"
            )
            if nx_t is not None and rw_t is not None and nx_t / rw_t < 0.9:
                warnings.append(
                    f"T1 {short_name(name)} [{label}]: rustworkx slower ({nx_t / rw_t:.2f}x)"
                )
    return [*lines, ""]


def t2_section(t2_dir: Path | None, warnings: list[str]) -> list[str]:
    lines = [
        "## Target 2 — NetworkX's bundled asv suite (zero-change, env-var A/B)",
        "",
    ]
    meta = load_json(t2_dir / "meta.json") if t2_dir else None
    base = load_asv_dir(t2_dir / "baseline") if t2_dir else {}
    back = load_asv_dir(t2_dir / "rustworkx") if t2_dir else {}
    probe = load_json(t2_dir / "dispatch-probe.json") if t2_dir else None
    if not base or not back:
        return [*lines, "_no results captured_", ""]

    verdicts: dict[tuple[str, str], dict] = {}
    for row in probe or []:
        verdicts[(row["function"], row.get("params", ""))] = row

    def dispatch_cell(bench: str, label: str) -> str:
        func = T2_FUNCTIONS.get(bench.rsplit(".", 1)[-1])
        row = verdicts.get((func, label))
        if row is None:
            matches = [v for (f, _), v in verdicts.items() if f == func]
            row = matches[0] if len(matches) == 1 else None
        if row is None:
            return "?"
        return "yes" if row["auto_dispatch"] else f"no — {row['reason']}"

    drug_note = (
        " The offline container dropped the drug-interaction-network parameter."
        if meta and meta.get("drug_network_dropped")
        else ""
    )
    lines += [
        f"NetworkX `{meta['rev'][:12]}` (tag networkx-3.6.1), **no benchmark-code "
        "changes**: the second arm only sets `NETWORKX_BACKEND_PRIORITY=rustworkx`."
        f'{drug_note} Rows marked "no" are the backend\'s own honest declines '
        "(auto-dispatch floor n<200 / m<400, or a NO_AUTO_DISPATCH function) and "
        "are expected to tie.",
        "",
        "| benchmark | graph | NetworkX | rustworkx | speedup | auto-dispatch |",
        "|---|---|---|---|---|---|",
    ]
    for name in sorted(base):
        values_b, params = base[name]
        vals_nx = combo_values(values_b, params)
        vals_rw = combo_values(*back.get(name, ([], params)))
        for combo in itertools.product(*params) if params else [()]:
            nx_t = vals_nx.get(combo)
            rw_t = vals_rw.get(combo)
            label = ", ".join(unquote(c) for c in combo)
            disp = dispatch_cell(name, label)
            lines.append(
                f"| {short_name(name)} | {label or '—'} | {fmt_s(nx_t)} "
                f"| {fmt_s(rw_t)} | {fmt_speedup(nx_t, rw_t)} | {disp} |"
            )
            if nx_t and rw_t:
                ratio = nx_t / rw_t
                # Sub-millisecond cells are timer noise; don't flag their ratios.
                audible = nx_t > 1e-3 and rw_t > 1e-3
                if disp == "yes" and audible and 0.9 < ratio < 1.15:
                    warnings.append(
                        f"T2 {short_name(name)} [{label}]: expected dispatch but "
                        f"~no delta ({ratio:.2f}x) — verify"
                    )
                if disp == "yes" and ratio < 0.8 and rw_t > 5e-4:
                    warnings.append(
                        f"T2 {short_name(name)} [{label}]: backend dispatched and "
                        f"LOST ({ratio:.2f}x) — should_run tuning candidate"
                    )
                if disp.startswith("no") and audible and (ratio > 1.3 or ratio < 0.7):
                    warnings.append(
                        f"T2 {short_name(name)} [{label}]: expected tie (declined) "
                        f"but {ratio:.2f}x — verify"
                    )
    return [*lines, ""]


def t3_section(t3_json: Path | None) -> list[str]:
    lines = ["## Target 3 — OSMnx-style city routing demo (forced dispatch)", ""]
    data = load_json(t3_json)
    if not data:
        return [*lines, "_no results captured_", ""]
    prov = data["provenance"]
    lines += [
        f"Graph: **{prov['source']}** {prov.get('graph_type', 'DiGraph')} "
        f"({prov['nodes']:,} nodes / {prov['edges']:,} edges"
        + (
            f", {prov['parallel_bundles']:,} parallel-way bundles"
            if prov.get("parallel_bundles")
            else ""
        )
        + ", largest SCC); "
        f"centrality subgraph n={data['centrality_subgraph']['nodes']:,}. "
        'Stock arm = `orig_func`, backend arm = `backend="rustworkx"` with a '
        "dispatch counter asserting every call.",
        "",
        "| workload | NetworkX | rustworkx | speedup | parity |",
        "|---|---|---|---|---|",
    ]
    for w in data["workloads"]:
        lines.append(
            f"| {w['name']} | {fmt_s(w['stock_s'])} | {fmt_s(w['backend_s'])} "
            f"| **{w['speedup']}x** | {w['parity']} |"
        )
    first = next((w for w in data["workloads"] if "backend_first_call_s" in w), None)
    if first:
        lines += [
            "",
            f"Routing detail: first backend call (includes graph conversion) "
            f"{first['backend_first_call_s'] * 1000:.1f} ms; steady state "
            f"{first['backend_steady_s_per_call'] * 1000:.3f} ms/route vs NetworkX "
            f"{first['stock_s_per_call'] * 1000:.2f} ms/route.",
        ]
    return [*lines, ""]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1", type=Path, default=None)
    parser.add_argument("--t2", type=Path, default=None)
    parser.add_argument("--t3", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "RESULTS.md")
    args = parser.parse_args()

    machine = None
    for src in (args.t1, args.t2):
        meta = load_json(src / "meta.json") if src else None
        if meta:
            machine = meta["machine"]
            break
    if machine is None:
        data = load_json(args.t3)
        machine = data["machine"] if data else {}
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent,
    ).stdout.strip()

    warnings: list[str] = []
    lines = [
        "# External benchmark results",
        "",
        f"Generated {time.strftime('%Y-%m-%d')} by the runners in this directory, "
        f"at nx-rustworkx `{sha}`.",
        "",
        f"Machine: {machine.get('platform', '?')}, {machine.get('cpu_count', '?')} "
        f"CPUs, Python {machine.get('python', '?')}, networkx "
        f"{machine.get('networkx', '?')}, rustworkx {machine.get('rustworkx', '?')}, "
        f"nx-rustworkx {machine.get('nx-rustworkx', '?')}.",
        "",
        "Three complementary measurements: **T1** forces dispatch per call on the "
        "NetworkX org's own backend benchmark suite (cold, conversion included); "
        "**T2** changes zero benchmark code and lets auto-dispatch decide via "
        "`NETWORKX_BACKEND_PRIORITY`; **T3** is a real-world street-network "
        "routing/centrality workload.",
        "",
    ]
    lines += t1_section(args.t1, warnings)
    lines += t2_section(args.t2, warnings)
    lines += t3_section(args.t3)
    lines += [
        "## Reading the numbers",
        "",
        "- Auto-dispatch declines graphs with n<200 or m<400 "
        "(`nx.config.backends.rustworkx.min_nodes/min_edges`) and 22 functions are "
        'never auto-selected; an explicit `backend="rustworkx"` bypasses only '
        "the size floor. Weighted betweenness always falls back to NetworkX; "
        "MultiGraph/MultiDiGraph dispatch with NetworkX's parallel-edge rules "
        "except for the functions NetworkX itself refuses on them.",
        "- T1 cells time a single cold call (conversion included); T2 cells are "
        "asv medians where NetworkX's conversion cache (default on since 3.4) "
        "amortizes conversion; T3 reports both cold and steady-state routing.",
        "- **Cold-call economics**: T1's sub-1x rows are all near-linear "
        "functions (component counts, isolates, unweighted BFS all-pairs on "
        "dense low-diameter graphs) where a single cold call cannot amortize "
        "the O(m) conversion. Superlinear kernels (betweenness, weighted "
        "all-pairs) win 5-50x even cold; repeat-call workloads amortize "
        "conversion through the cache either way.",
        "- **Gap found by T2, now fixed**: weighted single-pair "
        "`shortest_path` used to auto-dispatch and lose badly (0.02-0.4x on "
        "path-shaped and dense graphs) — NetworkX answers a weighted pair "
        "with bidirectional Dijkstra, while the backend's single-source paths "
        "kernel materializes a path for every visited node. `should_run` now "
        "declines single pairs (`benches/bench_single_pair.py` holds the "
        "measurements); the goal-stopped `*_length` variants win 1.2-9x "
        "everywhere and keep dispatching, and forced `backend=` still runs "
        "the paths kernels, which road-network shapes reward (T3: 1.5x).",
        "- `single_source_all_shortest_paths` keeps dispatching deliberately: "
        "it wins 6.9x/1.3x on connected path/dense shapes; the "
        "many-components row flags a sub-millisecond loss because only the "
        "source's 5-node component is reachable while conversion covers the "
        "whole graph.",
        "- Same machine, same process pattern for both arms in every target; "
        "still: single-machine numbers, expect variance.",
        "",
    ]
    if warnings:
        lines += ["## Sanity flags", ""]
        lines += [f"- {w}" for w in warnings]
        lines += [""]
        print("SANITY FLAGS:")
        for w in warnings:
            print(" -", w)

    args.out.write_text("\n".join(lines))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
