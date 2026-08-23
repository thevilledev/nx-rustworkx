# Design note: native graph generators

Status: accepted (2026-08-23). The seeded-RNG policy is settled on the safe
default described below; no code yet.

All measurements and dispatch-machinery claims below were verified against
networkx 3.6.1 and rustworkx 0.18.1 (CPython 3.12, Linux, best-of timings).
Where the NetworkX 3.4 floor behaves differently, the difference is called out.

## Summary

Grow `nx_rustworkx/generators.py` from the four shipped constructors
(`graph__new__`, `digraph__new__`, `empty_graph`, `from_edgelist`) to a set of
generators backed by rustworkx kernels, so `nx.path_graph`, `nx.gnp_random_graph`
and friends return a `RustworkxGraph` directly and whole pipelines never pay
graph conversion.

Two tiers, one policy decision:

- **Deterministic generators** (path, cycle, star, complete, …) map to
  `rx.generators.*` kernels and produce *byte-identical* graphs to NetworkX.
  Pure win; ship without ceremony.
- **Random generators** (`gnp_random_graph`, `gnm_random_graph`, …) map to
  rustworkx's samplers, which draw from a different RNG than NetworkX. The same
  seed produces a different — equally valid — graph. **Decision:** run
  them natively for unseeded calls; for seeded calls, fall back to NetworkX's
  sampling by default (which still lands in a native graph, see "the accidental
  Route A" below) and offer one config switch,
  `nx.config.backends.rustworkx.native_seeded_generators = True`, for users who
  accept backend-specific seeded streams in exchange for the full speedup.

Measured stakes: `rx.undirected_gnp_random_graph(20_000, 0.001)` runs in
5.4 ms where `nx.gnp_random_graph` takes 13.4 s and `nx.fast_gnp_random_graph`
takes 275 ms. Deterministic generators win 5–50× after wrapper overhead.

## Background: what already exists

`RustworkxGraph` carries `__networkx_backend__ = "rustworkx"`, so any graph the
backend returns keeps every later dispatchable call on rustworkx with zero
conversion. The four shipped constructors already exploit this for
`nx.Graph(..., backend="rustworkx")` and for generator-priority dispatch of
`empty_graph` / `from_edgelist`.

### The accidental Route A

Setting `nx.config.backend_priority.generators = ["rustworkx"]` today does more
than dispatch those four names. Most classic NetworkX generators build their
result by calling `nx.empty_graph(...)` internally, and dispatchable functions
dispatch on *every* call, including calls made from inside NetworkX. So with
generator priority set, `nx.path_graph(10)`, `nx.complete_graph(5)` and even
`nx.gnp_random_graph(30, 0.2, seed=42)` **already return a `RustworkxGraph`**:
NetworkX's own Python code runs, gets a rustworkx-backed empty graph from us,
and mutates it through the `add_edge` API.

Verified properties of Route A:

- **Exact parity, including seeded streams.** NetworkX's sampling code runs
  with NetworkX's RNG; only the container is ours. `gnp_random_graph(30, 0.2,
  seed=42)` under generator priority has the identical edge set to vanilla
  NetworkX.
- **No generation speedup.** The Python loop still dominates: gnp at n=2000 is
  146 ms via Route A vs 154 ms vanilla. Its value is that the *pipeline* skips
  conversion afterwards.
- **Partial coverage.** Generators that build via bare `nx.Graph()` instead of
  `empty_graph` (e.g. `karate_club_graph`) do not engage it.

Route A is the safety net this design leans on: any generator we decline still
comes back as a native graph whenever its NetworkX implementation builds on
`empty_graph`.

### What native kernels add on top

| call | NetworkX | Route A | rx kernel | wrapper build |
|---|---|---|---|---|
| `gnp_random_graph(2_000, 0.01)` | 154 ms | 146 ms | 0.5 ms | ~0.5 ms |
| `gnp_random_graph(20_000, 0.001)` | 13 384 ms | 13 087 ms | 5.4 ms | ~4.5 ms |
| `fast_gnp_random_graph(20_000, 0.001)` | 275 ms | — | 5.3 ms | ~4.5 ms |
| `path_graph(10_000)` | 9.0 ms | 10.7 ms | 0.2 ms | ~2 ms |
| `path_graph(100_000)` | 127 ms | 110 ms | 2.1 ms | 22 ms |

"Wrapper build" is constructing `RustworkxGraph`'s `node_to_index` dict and
`index_to_node` list, O(n) in Python; it is the dominant cost of the native
route and still leaves a 5× win in the worst row. (A follow-up, not required
for v1: these kernels all label nodes `0..n-1`, so a lazy identity-map
representation could make wrapping O(1).)

Native kernels also fix an ergonomic hole: today
`nx.path_graph(n, backend="rustworkx")` raises `NotImplementedError`, because
explicit backend dispatch requires the named function, not its `empty_graph`
substrate.

## Dispatch mechanics that constrain the design

These were verified by experiment and by reading `networkx/utils/backends.py`;
they shape everything below.

1. **`should_run` is never consulted for generators.** The dispatcher calls
   `should_run` only on the conversion path; for functions with no graph
   arguments it checks `can_run` alone. Consequences: the `min_nodes` /
   `min_edges` cutoffs and the `NO_AUTO_DISPATCH` mechanism do not apply to
   generators (correctly — there is no conversion cost to amortize), and any
   gating we need must live in `can_run` or in the implementation.

2. **`can_run` cannot distinguish priority dispatch from explicit
   `backend="rustworkx"`.** Both paths call it with identical arguments. There
   is therefore *no way* to express "skip under priority, run when explicit"
   for a generator — the lever the backend uses elsewhere (`should_run`) does
   not exist here. An opt-in for divergent behavior must be a config knob, not
   a dispatch-mode distinction.

3. **`seed` reaches the backend as a `random.Random` instance, never the raw
   int.** `@py_random_state` is applied outside `@nx._dispatchable`, so
   NetworkX normalizes the seed before dispatch: `seed=42` arrives as
   `Random(42)`, and `seed=None` arrives as the module-global instance
   (`nx.utils.create_py_random_state(None)` returns that same object, giving a
   private-API-free way to detect "no explicit seed"). rustworkx kernels take a
   `u64`; derive it as `seed.getrandbits(64)` — deterministic for a given user
   seed, stable across platforms and CPython versions (Mersenne Twister's
   stream is specified), and it draws from the global RNG in the unseeded case
   exactly as NetworkX itself would.

4. **The parity harness strictly compares every generator the backend claims.**
   Under `NETWORKX_TEST_BACKEND=rustworkx`, NetworkX's conftest sets *both*
   `backend_priority.algos` and `backend_priority.generators` and flips
   `_dispatchable._is_testing`. For each graph-returning call it runs the
   backend *and* NetworkX with copied RNG state and asserts full equality —
   `G.graph`, node attrs, adjacency. Deterministic kernels pass this and get
   free, continuous verification across the whole algorithm suite. Divergent
   random kernels would fail it in every test that builds a seeded graph, far
   beyond what `on_start_tests` xfails can reasonably cover. The escape is
   clean: when `can_run` returns a reason for a no-graph-args function, the
   test machinery silently runs the NetworkX original (no xfail, no failure).
   So random generators must decline in `can_run` while
   `getattr(_dispatchable, "_is_testing", False)` is set. This is a documented
   coupling to a private-but-stable testing flag; if it ever disappears,
   `can_run` degrades to claiming the call and CI fails loudly rather than
   silently.

5. **A raised `NotImplementedError` behaves differently per path.** Under
   priority dispatch it falls through to NetworkX's implementation (landing in
   Route A); under explicit `backend=` it propagates to the user, wrapped, with
   our message preserved as the chained cause. This gives the seeded-by-default
   decline an actionable error text where `can_run` reason strings would be
   swallowed by NetworkX's generic "not implemented for the given arguments"
   message.

6. **Floor compatibility is clean, but the env var story is not.** The
   dispatch surface this design needs was verified present at the 3.4 floor:
   `backend_priority.generators`, `_dispatchable._is_testing`, and
   `create_using=None` on the random generators' signatures all exist in
   3.4.2 as in 3.6.1 (v1 accepts `create_using` and falls back whenever it is
   not `None`). The gap is documentation: the env var the README advertises
   (`NETWORKX_BACKEND_PRIORITY`) sets *algorithm* priority only; generator
   priority needs `NETWORKX_BACKEND_PRIORITY_GENERATORS` or
   `nx.config.backend_priority.generators` — a docs gap this feature must
   close.

7. **`fallback_to_nx` defaults to `False`.** A native graph hitting a
   dispatchable function the backend does not implement raises rather than
   converting back. This is already true for `nx.Graph(backend="rustworkx")`
   users, but generator priority widens exposure to every pipeline. The usage
   docs must pair generator priority with a recommendation to set
   `nx.config.fallback_to_nx = True` (or explain the failure mode).

## The decision: seeded random generators

A rustworkx sampler cannot reproduce NetworkX's sample for the same seed: the
RNGs differ (Pcg64 vs Mersenne Twister) and so does the sampling order. Any
G(n, p) sample is a *valid* return for `gnp_random_graph` — the backend already
embraces exactly this doctrine for tie-breaking (`topological_sort`,
`greedy_color`, `minimum_spanning_tree` all document "a different equally valid
answer"). But a seed is the one argument whose entire purpose is
reproducibility, and the failure mode is quiet: a researcher flips on an env
var and every "reproducible" figure in their pipeline changes.

Options considered:

- **A. Always native, document loudly.** Maximum speed. Rejected as the
  default: it makes a global env var silently change seeded results, and the
  parity harness excludes these functions from comparison anyway (fact 4), so
  "documented as a valid difference" would be the *only* guardrail.
- **B. Never native for random generators.** Rejected: it forfeits the
  headline win (three orders of magnitude on gnp) for everyone, including
  users who never seed and users happy to opt in.
- **C. Config-gated (decided).**
  - Unseeded calls (`seed` is the global RNG instance): run the rustworkx
    kernel. Nobody can observe which valid sample they got; this is the same
    contract NetworkX itself offers for `seed=None`.
  - Seeded calls with `native_seeded_generators = False` (default): raise
    `NotImplementedError` from the implementation with a message naming the
    config switch. Under priority dispatch this falls through to NetworkX's
    sampler and — via Route A — still returns a conversion-free native graph
    with NetworkX's exact seeded stream. Under explicit `backend="rustworkx"`
    the user sees the actionable message (fact 5).
  - Seeded calls with `native_seeded_generators = True`: run the kernel.
    Guarantee: same seed ⇒ same graph, for a pinned rustworkx version, on any
    platform (fact 3). No promise across rustworkx upgrades — rustworkx does
    not pin its sampling streams — and never the same graph as NetworkX's for
    that seed. Both facts go in the docs verbatim.
  - Regardless of the knob: `can_run` declines while the parity harness is
    active (fact 4).

C with the safe default is the accepted design: it costs almost nothing —
seeded pipelines keep NetworkX-speed *generation* (which they have today)
while still gaining conversion-free *execution* — and the full speedup is one
documented config line away. It also matches the project's established
posture: measured, conservative defaults with explicit opt-ins (`min_nodes`,
`astar_heuristic_check`, `NO_AUTO_DISPATCH`).

A per-call opt-in via NetworkX's `**backend_kwargs` passthrough (e.g.
`nx.gnp_random_graph(..., backend="rustworkx", native_seed=True)`) was
considered and rejected: it is unreachable under priority dispatch, invisible
in docs tooling, and encourages call sites that break without the backend
installed.

One deliberate consequence to document: on this backend
`fast_gnp_random_graph` and `gnp_random_graph` share one kernel, so (when
seeded natively) they produce the *same* graph for the same seed — NetworkX
produces different graphs for the two names. Same "equally valid sample"
doctrine, stated explicitly.

## Scope

### Tier 1 — deterministic, exact parity (v1)

Each maps to an `rx.generators` kernel (plus `directed_*` variant where
NetworkX accepts a directed `create_using`) and must pass the parity harness's
strict equality, which the CI suite then enforces forever. Verified mappings:

| NetworkX | rustworkx kernel | notes |
|---|---|---|
| `path_graph(n)` | `path_graph` / `directed_path_graph` | edge directions match; `n` may be an iterable of node labels — wrap via `index_to_node` |
| `cycle_graph(n)` | `cycle_graph` / `directed_cycle_graph` | |
| `star_graph(n)` | `star_graph(n + 1)` / `directed_star_graph` | NetworkX's `n` counts leaves; rustworkx counts nodes |
| `complete_graph(n)` | `complete_graph` / `directed_complete_graph` | |
| `barbell_graph(m1, m2)` | `barbell_graph` | undirected only, as in NetworkX |
| `lollipop_graph(m, n)` | `lollipop_graph` | undirected only |
| `binomial_tree(n)` | `binomial_tree_graph` / `directed_binomial_tree_graph` | |
| `full_rary_tree(r, n)` | `full_rary_tree` | |
| `karate_club_graph()` | `karate_club_graph` | map node payloads to the `club` attr, edge floats to `weight`, set `G.graph["name"]` |
| `grid_2d_graph(m, n)` | `grid_graph` | relabel flat indices to NetworkX's `(i, j)` tuples via `index_to_node`; `periodic=True` falls back |

Counts and edge sets for every row above were checked against NetworkX 3.6.1;
exact attribute-level parity is the implementation's acceptance test.
`create_using` follows shipped `empty_graph` semantics: class or instance
selects directedness, multigraphs are rejected in `can_run`, and the return is
always a `RustworkxGraph` (never the passed-in instance).

Generators with no rustworkx kernel need no action in v1. Those that build on
`empty_graph` (`wheel_graph`, `ladder_graph`, `circular_ladder_graph`, … —
verified) already return native graphs through Route A under generator
priority; the rest (`turan_graph`, `hypercube_graph`, which assemble via other
dispatchables — verified) simply stay on NetworkX.

### Tier 2 — random, distribution-equivalent (v1, behind the policy above)

| NetworkX | rustworkx kernel |
|---|---|
| `gnp_random_graph` (+ aliases `erdos_renyi_graph`, `binomial_graph` — same function object, one dispatch name) | `undirected_gnp_random_graph` / `directed_gnp_random_graph` |
| `fast_gnp_random_graph` | same kernels as above |
| `gnm_random_graph` | `undirected_gnm_random_graph` / `directed_gnm_random_graph` (exact `m` edges, all `n` nodes — verified) |
| `dense_gnm_random_graph` | `undirected_gnm_random_graph` |

### Tier 3 — reviewed after v1; four shipped, the rest parked

The distribution-semantics reviews were carried out after v1 landed, with
these outcomes:

- **`barabasi_albert_graph` — shipped.** rustworkx's default initial condition
  differs from NetworkX's star seed (measured 37 vs 36 edges for n=20, m=2),
  but its `initial_graph` parameter accepts NetworkX's `star_graph(m)` seed
  explicitly. With that bridge the growth process is the same model — verified
  by matching edge counts across an (n, m) grid including corner cases — and
  only the RNG differs. A user-supplied `initial_graph` falls back.
- **`random_regular_graph` — shipped.** rustworkx's kernel documents itself as
  based on NetworkX's implementation of the pairing model, so the distribution
  is the same by construction.
- **`stochastic_block_model` — shipped.** Same model; NetworkX's validations,
  `partition`/`name` graph attributes, and per-node `block` attributes are
  replicated. `sparse` only selects NetworkX's sampling algorithm and is
  ignored.
- **`random_geometric_graph` — shipped.** Same model; positions land under
  `pos_name` as NetworkX stores them. An explicit `pos` makes the output
  deterministic and floating-point-boundary-sensitive, so it falls back.
- **`hyperbolic_random_graph` — dropped.** NetworkX has no dispatchable
  function of that name; there is nothing to implement.
- **`watts_strogatz_graph` and rewiring models — parked**: no rustworkx kernel.
- **`hexagonal_lattice_graph` — parked**: kernel exists but NetworkX's tuple
  labeling and embedding attrs make the mapping fiddly.
- **bipartite `random_graph` / `gnmk_random_graph` — parked**: rustworkx has a
  p-based bipartite kernel only, and the NetworkX versions set `bipartite`
  node attributes; needs its own pass.

## Deliverables

1. `nx_rustworkx/generators.py`: Tier 1 + Tier 2 implementations, the
   `native_seeded_generators` config default (`False`) added to
   `_info.py::get_info()["default_config"]`, seeded detection via
   `create_py_random_state(None)` identity, `_is_testing` decline in the random
   generators' `can_run`.
2. `_info.py`: `additional_docs` for every new name; random ones carry the RNG
   divergence sentence and the within-version determinism guarantee.
3. Docs: README "Limits" bullet for seeded divergence (opt-in only); website
   usage page gains a Generators section covering
   `NETWORKX_BACKEND_PRIORITY_GENERATORS`, the `fallback_to_nx` pairing, and
   the seeded policy; algorithms page gains a generators table.
4. Tests: `tests/test_generators.py` — strict parity vs `orig_func` for Tier 1
   (labels, attrs, `G.graph`, directed variants, iterable `n`, multigraph
   rejection); Tier 2 same-seed-twice determinism, unseeded dispatch,
   seeded-default fallthrough (priority) and raise (explicit), knob opt-in,
   `_is_testing` decline; a floors-leg check that NetworkX 3.4 signatures
   dispatch cleanly.
5. CI: add `--pyargs networkx.generators` to the backend suite job — it
   strict-verifies Tier 1 on every run; random generators sit out via the
   `_is_testing` decline. Expect to grow the divergent-xfail list in
   `on_start_tests` if specific generator tests probe behaviors the wrapper
   does not honor.
6. `benches/bench_generators.py`: native-vs-NetworkX timings including wrapper
   cost, same materiality method as `bench_parity.py`. (Generators cannot use
   `NO_AUTO_DISPATCH` — fact 1 — so if any case ever measures slower, the
   remedy is dropping the kernel, not a should_run entry.)

Suggested rollout: two PRs — Tier 1 + CI leg first (no policy content), then
Tier 2 + the config knob + policy docs, so the seeded decision gets its own
review.

## Non-goals

Recorded here so the scope stays honest; each is parked on its own merits, not
forgotten:

- **Eccentricity / diameter family**: needs an O(n²)-memory guard before any
  all-pairs-based implementation is safe to auto-dispatch.
- **Multigraph support**: a real scope decision — the README currently sells
  its absence as a feature — not a generator concern.
- **`lexicographical_topological_sort`**: rustworkx's string-key requirement
  makes it semantically unsafe to claim.

## Settled and remaining items

1. **Settled:** `native_seeded_generators` defaults to `False` (maintainer
   decision, 2026-08-23). Seeded calls reproduce NetworkX's exact graph by
   default; flipping to `True` remains a one-line change plus README wording
   should the valid-difference doctrine ever be extended to seeds.
2. Implementation-time details, revisitable in PR review without reopening
   this note: the env-var story lives on the website with the README kept
   minimal (matching the existing README-points-to-website pattern), and the
   parity harness is detected via `_dispatchable._is_testing` rather than
   excluding random generators by path in the workflow (the flag is narrower
   and fails loudly if NetworkX ever removes it).
