"""Every backend function must accept NetworkX's positional arguments.

The dispatcher forwards NetworkX's own parameters positionally, so a renamed
or reordered parameter silently breaks ``can_run`` and the call itself.
"""

from __future__ import annotations

import inspect

import networkx as nx
import pytest

from nx_rustworkx import algorithms
from nx_rustworkx.interface import BackendInterface

POSITIONAL = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)


# NetworkX exposes a few of these only under a submodule, and stoer_wagner's
# public name is the decorated wrapper rather than the dispatchable.
_LOOKUP_MODULES = (
    nx.algorithms.connectivity.stoerwagner,
    nx.approximation,
)


def _networkx_function(name):
    func = getattr(nx, name, None)
    if func is not None and hasattr(func, "orig_func"):
        return func.orig_func
    for module in _LOOKUP_MODULES:
        candidate = getattr(module, name, None)
        if candidate is not None and hasattr(candidate, "orig_func"):
            return candidate.orig_func
    return func


def _positional_names(func):
    parameters = inspect.signature(func).parameters.values()
    return [p.name for p in parameters if p.kind in POSITIONAL]


@pytest.mark.parametrize("name", algorithms.ALGORITHMS)
def test_backend_signature_matches_networkx(name):
    reference = _networkx_function(name)
    assert reference is not None, f"{name} is not a NetworkX function"
    expected = _positional_names(reference)
    got = _positional_names(getattr(BackendInterface, name))
    assert got[: len(expected)] == expected, (
        f"{name}: backend takes {got}, NetworkX passes {expected}"
    )


@pytest.mark.parametrize("name", algorithms.ALGORITHMS)
def test_backend_defaults_match_networkx(name):
    """A different default silently changes behavior for unspecified arguments."""
    reference = _networkx_function(name)
    expected = inspect.signature(reference).parameters
    got = inspect.signature(getattr(BackendInterface, name)).parameters
    for pname, param in expected.items():
        if param.kind not in POSITIONAL or param.default is inspect.Parameter.empty:
            continue
        if pname not in got:
            continue
        ours = got[pname].default
        if ours is inspect.Parameter.empty:
            continue
        assert ours == param.default or (ours is None and param.default is not None), (
            f"{name}.{pname} defaults to {ours!r}, NetworkX uses {param.default!r}"
        )


REQUIRED_STANDINS = {
    "source": 0,
    "target": 3,
    "start": 0,
    "n": 0,
    "distance": 1,
    "C": [0, 1],
    "S": [0, 1],
    "sources": [0],
    "G2": nx.path_graph(4, create_using=nx.DiGraph),
    "H": nx.path_graph(3, create_using=nx.DiGraph),
    "matching": {(0, 1)},
    "terminal_nodes": [0, 2],
}


@pytest.mark.parametrize("name", algorithms.ALGORITHMS)
def test_can_run_accepts_networkx_defaults(name):
    """can_run is called with NetworkX's resolved arguments, defaults included."""
    reference = _networkx_function(name)
    parameters = list(inspect.signature(reference).parameters.values())
    args = []
    for param in parameters[1:]:
        if param.kind not in POSITIONAL:
            continue
        if param.default is inspect.Parameter.empty:
            assert param.name in REQUIRED_STANDINS, (
                f"{name} needs a stand-in for required argument {param.name!r}"
            )
            args.append(REQUIRED_STANDINS[param.name])
        else:
            args.append(param.default)
    G = nx.path_graph(4, create_using=nx.DiGraph)
    result = BackendInterface.can_run(name, (G, *args), {})
    assert result is True or isinstance(result, str)


TRUTHY_FLAGS = [
    ("betweenness_centrality", {"normalized": 1, "endpoints": 0}),
    ("edge_betweenness_centrality", {"normalized": 1}),
    ("closeness_centrality", {"wf_improved": 1}),
    ("max_weight_matching", {"maxcardinality": 1}),
    ("group_betweenness_centrality", {"normalized": 1}),
]


@pytest.mark.parametrize(("name", "flags"), TRUTHY_FLAGS)
def test_non_bool_flags_are_accepted(name, flags):
    """NetworkX takes any truthy value; rustworkx's kernels need a real bool."""
    G = nx.gnp_random_graph(20, 0.3, seed=0)
    for u, v in G.edges():
        G[u][v]["weight"] = 1 + ((u + v) % 4)
    extra = ([0, 1],) if name == "group_betweenness_centrality" else ()
    result = getattr(nx, name)(G, *extra, backend="rustworkx", **flags)
    assert result is not None
