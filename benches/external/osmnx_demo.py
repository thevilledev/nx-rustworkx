#!/usr/bin/env python3
"""Real-world demo: route and analyze a city street network, NX vs rustworkx.

OSMnx models cities as MultiDiGraphs, which this backend always rejects, so
the demo applies the one line the official NetworkX gallery example also uses:
``ox.convert.to_digraph(G, weight="travel_time")``. On that DiGraph it times
stock NetworkX (via each function's ``orig_func``) against forced
``backend="rustworkx"`` calls for:

- a batch of weighted point-to-point ``nx.shortest_path`` queries (the
  routing-engine workload; conversion is paid once and cached),
- weighted ``nx.closeness_centrality`` on a capped subgraph,
- unweighted ``nx.betweenness_centrality`` on the same subgraph,
- ``nx.pagerank`` on the full graph.

Every backend call is verified through a dispatch counter, and result parity
against NetworkX is reported per workload. Graph acquisition falls back:
--graphml file -> live Overpass download via osmnx -> --graphml-url ->
synthetic road-like graph (offline-safe, clearly labeled).

    uv run python benches/external/osmnx_demo.py --place "Helsinki, Finland"
    uv run python benches/external/osmnx_demo.py --synthetic
"""

from __future__ import annotations

import argparse
import gc
import math
import random
import time
import urllib.request
from collections import deque
from pathlib import Path

import _common
import _dispatch
import networkx as nx
from _common import log

nx.config.warnings_to_ignore.add("cache")


def time_once(fn):
    gc.collect()
    start = time.perf_counter()
    result = fn()
    return time.perf_counter() - start, result


def synthetic_city(n: int, seed: int) -> nx.DiGraph:
    """Road-network-like DiGraph: geometric layout, reciprocal weighted edges."""
    radius = math.sqrt(7 / (math.pi * n))  # ~7 expected neighbors
    G = nx.random_geometric_graph(n, radius, seed=seed)
    G = G.subgraph(max(nx.connected_components(G), key=len))
    pos = nx.get_node_attributes(G, "pos")
    rng = random.Random(seed)
    D = nx.DiGraph()
    for u, v in G.edges():
        meters = math.dist(pos[u], pos[v]) * 20_000  # ~20 km city extent
        speed_ms = rng.choice([30, 40, 50, 60, 80]) / 3.6
        seconds = meters / speed_ms
        D.add_edge(u, v, travel_time=seconds, length=meters)
        D.add_edge(v, u, travel_time=seconds, length=meters)
    return D


def multidigraph_to_digraph(G, weight: str) -> nx.DiGraph:
    """Collapse parallel edges keeping the minimum-weight one (osmnx-free)."""
    D = nx.DiGraph()
    D.add_nodes_from(G.nodes(data=True))
    for u, v, data in G.edges(data=True):
        w = float(data.get(weight, math.inf))
        if not D.has_edge(u, v) or w < float(D[u][v][weight]):
            D.add_edge(u, v, **{**data, weight: w})
    return D


def from_osmnx_graph(G) -> nx.DiGraph:
    import osmnx as ox

    G = ox.routing.add_edge_speeds(G)
    G = ox.routing.add_edge_travel_times(G)
    convert = getattr(ox, "convert", None)
    if convert is not None and hasattr(convert, "to_digraph"):
        return convert.to_digraph(G, weight="travel_time")
    return multidigraph_to_digraph(G, "travel_time")


def load_graphml(path: Path) -> nx.DiGraph:
    G = nx.read_graphml(path, force_multigraph=True)
    for _, _, data in G.edges(data=True):
        if "travel_time" in data:
            data["travel_time"] = float(data["travel_time"])
    return multidigraph_to_digraph(G, "travel_time")


def acquire(args) -> tuple[nx.DiGraph, dict]:
    if args.graphml:
        return load_graphml(Path(args.graphml)), {"source": "graphml", "path": args.graphml}
    if not args.synthetic:
        try:
            import osmnx as ox

            ox.settings.use_cache = True
            ox.settings.cache_folder = str(args.workdir / "osmnx-cache")
            ox.settings.requests_timeout = 60
            log(f"downloading {args.place!r} drive network via osmnx/Overpass ...")
            G = ox.graph_from_place(args.place, network_type="drive")
            return from_osmnx_graph(G), {"source": "overpass", "place": args.place}
        except Exception as exc:
            log(f"osmnx download unavailable ({exc!r}); trying fallbacks")
        if args.graphml_url:
            dest = args.workdir / "downloaded.graphml"
            log(f"fetching {args.graphml_url}")
            try:
                with urllib.request.urlopen(args.graphml_url, timeout=60) as resp:
                    dest.write_bytes(resp.read())
                return load_graphml(dest), {"source": "graphml-url", "url": args.graphml_url}
            except Exception as exc:
                log(f"graphml url failed ({exc!r}); falling back to synthetic")
    D = synthetic_city(args.synthetic_nodes, args.seed)
    return D, {"source": "synthetic", "nodes_requested": args.synthetic_nodes}


def bfs_ball(D: nx.DiGraph, start, cap: int) -> nx.DiGraph:
    U = D.to_undirected(as_view=True)
    seen = {start}
    queue = deque([start])
    while queue and len(seen) < cap:
        u = queue.popleft()
        for v in U.adj[u]:
            if v not in seen:
                seen.add(v)
                queue.append(v)
                if len(seen) >= cap:
                    break
    return D.subgraph(seen).copy()


def route_cost(D: nx.DiGraph, path: list) -> float:
    return sum(D[u][v]["travel_time"] for u, v in zip(path, path[1:]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--place", default="Helsinki, Finland")
    parser.add_argument("--graphml", default=None, help="local .graphml to use")
    parser.add_argument("--graphml-url", default=None, help="fallback .graphml URL")
    parser.add_argument("--synthetic", action="store_true", help="skip downloads")
    parser.add_argument("--synthetic-nodes", type=int, default=12000)
    parser.add_argument("--routes", type=int, default=200)
    parser.add_argument("--cap", type=int, default=6000, help="centrality subgraph size")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workdir", type=Path, default=_common.DEFAULT_WORKDIR)
    parser.add_argument("--out", type=Path, default=None, help="output JSON path")
    args = parser.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    out_path = args.out or (args.workdir / "results-osmnx" / "osmnx.json")

    D, provenance = acquire(args)
    # Route within the largest strongly connected component so every seeded
    # origin/destination pair is reachable.
    D = D.subgraph(max(nx.strongly_connected_components.orig_func(D), key=len)).copy()
    provenance.update(nodes=D.number_of_nodes(), edges=D.number_of_edges())
    log(f"graph ready: {provenance}")

    rng = random.Random(args.seed)
    nodes = sorted(D.nodes)
    pairs = [(rng.choice(nodes), rng.choice(nodes)) for _ in range(args.routes)]
    hub = max(nodes, key=lambda n: D.degree(n))
    C = bfs_ball(D, hub, args.cap)
    log(f"centrality subgraph: n={C.number_of_nodes()}, m={C.number_of_edges()}")

    workloads: list[dict] = []

    # (a) batch routing: N weighted single-pair shortest paths on the full graph
    sp = nx.shortest_path
    t_stock, stock_routes = time_once(
        lambda: [sp.orig_func(D, o, d, weight="travel_time") for o, d in pairs]
    )
    with _dispatch.count_dispatch() as counts:
        t_first, first_route = time_once(
            lambda: sp(D, *pairs[0], weight="travel_time", backend="rustworkx")
        )
        t_rest, rest_routes = time_once(
            lambda: [
                sp(D, o, d, weight="travel_time", backend="rustworkx")
                for o, d in pairs[1:]
            ]
        )
    assert counts.get("shortest_path") == len(pairs), counts
    backend_routes = [first_route, *rest_routes]
    cost_mismatch = sum(
        1
        for a, b in zip(stock_routes, backend_routes)
        if not math.isclose(route_cost(D, a), route_cost(D, b), rel_tol=1e-9)
    )
    workloads.append(
        {
            "name": f"shortest_path x{args.routes} (weight=travel_time)",
            "function": "shortest_path",
            "stock_s": t_stock,
            "backend_s": t_first + t_rest,
            "backend_first_call_s": t_first,
            "backend_steady_s_per_call": t_rest / max(1, len(pairs) - 1),
            "stock_s_per_call": t_stock / len(pairs),
            "dispatch_count": counts.get("shortest_path"),
            "parity": f"{cost_mismatch} of {args.routes} route costs differ",
        }
    )

    # (b)-(d): whole-result algorithms with numeric parity checks
    specs = [
        (
            "closeness_centrality (distance=travel_time)",
            nx.closeness_centrality,
            C,
            {"distance": "travel_time"},
        ),
        ("betweenness_centrality (unweighted)", nx.betweenness_centrality, C, {}),
        ("pagerank", nx.pagerank, D, {}),
    ]
    for name, func, G, kwargs in specs:
        fname = func.__name__
        log(f"running {name} ...")
        t_stock, expected = time_once(lambda: func.orig_func(G, **kwargs))
        with _dispatch.count_dispatch() as counts:
            t_backend, got = time_once(lambda: func(G, **kwargs, backend="rustworkx"))
        assert counts.get(fname) == 1, counts
        diff = max(abs(expected[k] - got[k]) for k in expected)
        workloads.append(
            {
                "name": name,
                "function": fname,
                "graph": "subgraph" if G is C else "full",
                "stock_s": t_stock,
                "backend_s": t_backend,
                "dispatch_count": 1,
                "parity": f"max abs diff {diff:.2e}",
            }
        )

    for w in workloads:
        w["speedup"] = round(w["stock_s"] / w["backend_s"], 2)
        w["stock_s"] = round(w["stock_s"], 4)
        w["backend_s"] = round(w["backend_s"], 4)

    report = {
        "target": "osmnx-demo",
        "provenance": provenance,
        "routes": args.routes,
        "centrality_subgraph": {
            "nodes": C.number_of_nodes(),
            "edges": C.number_of_edges(),
            "cap": args.cap,
        },
        "machine": _common.machine_info(),
        "workloads": workloads,
        "notes": [
            "OSMnx MultiDiGraphs never dispatch; the one required line is "
            "ox.convert.to_digraph(G, weight='travel_time')",
            "backend arm uses explicit backend='rustworkx'; the stock arm "
            "calls each function's orig_func",
            "first shortest_path call includes nx->rustworkx conversion; "
            "NetworkX's graph cache covers the remaining calls",
        ],
    }
    _common.write_json(out_path, report)

    print()
    print(f"{'workload':52} {'NetworkX':>10} {'rustworkx':>10} {'speedup':>8}")
    for w in workloads:
        print(
            f"{w['name']:52} {w['stock_s']:>9.3f}s {w['backend_s']:>9.3f}s "
            f"{w['speedup']:>7.1f}x"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
