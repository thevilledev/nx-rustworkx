# rustworkx API gap analysis

Status: complete (2026-08-23), run against rustworkx 0.18.1 and NetworkX 3.6.1.

The question: after the generator batches and the eccentricity family, does
rustworkx offer kernels the backend still leaves unclaimed? The sweep
enumerated every public rustworkx callable (297, top level plus
`rx.generators`), subtracted the ones the backend's source already consumes
(113), and triaged the remainder against NetworkX's dispatchable registry.

**Outcome: one new function shipped (`bipartite.color`), and the backend has
otherwise saturated rustworkx's kernel surface.** Every other unclaimed
callable falls into a bucket below, recorded so future contributors do not
re-litigate them. Growth from here comes from upstream rustworkx kernels, not
from unclaimed ones.

## Shipped from this sweep

- **`bipartite.color`** ← `rx.two_color`. rustworkx's traversal happens to
  produce NetworkX's exact assignment on every case probed (paths, stars,
  trees, lattices, grids, directed graphs treated weakly, disconnected
  components); isolates are recolored 0 afterward, as NetworkX assigns, and
  `None` maps to NetworkX's "Graph is not bipartite." error. A two-coloring is
  unique per component only up to swapping the colors, so the metadata records
  the possibility of an opposite-but-valid choice.

## No NetworkX counterpart

Nothing dispatchable exists for these, so there is nothing to implement:
`bfs_search` / `dfs_search` / `dijkstra_search` (visitor APIs),
`graph_token_swapper`, `maximum_bisimulation`, `connected_subgraphs`,
`local_complement`, `longest_simple_path`, `all_pairs_all_simple_paths`,
`num_shortest_paths_unweighted`, `collect_runs` / `collect_bicolor_runs`,
`is_subgraph_isomorphic` / `vf2_mapping` (NetworkX's subgraph isomorphism
lives on `GraphMatcher`, which does not dispatch), `hyperbolic_random_graph`
and the hyperbolic routing helpers, and the quantum-layout generators
(`heavy_hex_graph`, `heavy_square_graph`, `mesh_graph` — an alias of
`complete_graph` — and `directed_grid_graph`, whose one-way orientation is not
NetworkX's directed-grid semantics).

## Semantic mismatch — kernel exists, answers a different question

- **`bfs_successors` / `bfs_predecessors`**: NetworkX yields the BFS forest
  (each node once, under its discovery parent). rustworkx's digraph-only API
  reports successors per node including the traversal parent, so
  reconstructing NetworkX's answer means re-doing the BFS bookkeeping in
  Python — which erases the kernel.
- **`k_shortest_path_lengths`**: returns lengths; NetworkX's
  `shortest_simple_paths` yields the paths themselves.
- **`generators.dorogovtsev_goltsev_mendes_graph`**: node counts match but the
  subdivision is labeled differently from n=3 up — isomorphic, not
  label-identical, and a deterministic generator must be exact.
- **`adjacency_matrix`**: rustworkx builds a dense n×n array; NetworkX's
  contract is a SciPy sparse array, and densifying defeats both the memory
  and the point.
- **`lexicographical_topological_sort`**: still parked from the original
  design note — rustworkx requires string keys, and coercing NetworkX's
  arbitrary comparable keys through strings reorders them (10 sorts before 9).
- **`is_isomorphic_node_match`**: matches on node payloads, but the backend's
  payloads are node IDs (or None), not attribute dicts; serving NetworkX's
  `node_match` would need a bespoke conversion path.

## Result-construction-bound — no expected win

`union` / `graph_union` could serve NetworkX's `union` / `disjoint_union` /
`compose`, but those return graphs assembled in Python either way — the same
reason `complement` and the products sit in `NO_AUTO_DISPATCH` — and the
payload-equality merge `rx.union` offers is unsound for kernel-built graphs,
whose payloads are not node IDs. The small classic graphs
(`generalized_petersen_graph(5, 2)` is Petersen under a fixed relabeling, and
NetworkX's `small` module has twenty more) would only wrap static edge lists:
generation cost is microseconds either way, and a wrapper would measure as a
materiality failure in the generator bench while winning nothing.

## Upstream wishlist

The parked items that need kernels rustworkx does not have, roughly by value:
a Watts–Strogatz / rewiring sampler, an edge-count bipartite sampler
(`gnmk`), a BFS-forest API (successors/predecessors as NetworkX defines
them), sparse adjacency output, and multigraph support (a scope decision for
this backend regardless).
