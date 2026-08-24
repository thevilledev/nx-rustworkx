"""NetworkX backend powered by rustworkx.

Keep ``import networkx as nx`` as the primary UX. Enable this backend with
``NETWORKX_BACKEND_PRIORITY=rustworkx`` or ``backend="rustworkx"``.
"""

from __future__ import annotations

__all__ = [
    "BackendInterface",
    "RustworkxGraph",
    "__version__",
    "convert_from_nx",
    "convert_to_nx",
]


def __getattr__(name: str):
    if name == "__version__":
        # Resolve from the installed distribution so the two can never drift.
        from importlib.metadata import version

        value = globals()["__version__"] = version("nx-rustworkx")
        return value
    if name == "BackendInterface":
        from nx_rustworkx.interface import BackendInterface

        return BackendInterface
    if name == "RustworkxGraph":
        from nx_rustworkx.graph import RustworkxGraph

        return RustworkxGraph
    if name == "convert_from_nx":
        from nx_rustworkx.convert import convert_from_nx

        return convert_from_nx
    if name == "convert_to_nx":
        from nx_rustworkx.convert import convert_to_nx

        return convert_to_nx
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
