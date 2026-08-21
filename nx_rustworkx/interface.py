"""NetworkX backend interface for rustworkx."""

from __future__ import annotations

from nx_rustworkx import algorithms, generators
from nx_rustworkx.algorithms._utils import default_can_run, default_should_run
from nx_rustworkx.convert import convert_from_nx, convert_to_nx

__all__ = ["BackendInterface"]


class BackendInterface:
    """Dispatch object registered as the ``rustworkx`` NetworkX backend."""

    convert_from_nx = staticmethod(convert_from_nx)
    convert_to_nx = staticmethod(convert_to_nx)

    @classmethod
    def can_run(cls, name, args, kwargs):
        func = getattr(cls, name, None)
        if func is None:
            return False
        checker = getattr(func, "can_run", None)
        if checker is None:
            return default_can_run(*args, **kwargs)
        return checker(*args, **kwargs)

    @classmethod
    def should_run(cls, name, args, kwargs):
        func = getattr(cls, name, None)
        if func is None:
            return False
        checker = getattr(func, "should_run", None)
        if checker is not None:
            return checker(*args, **kwargs)
        return default_should_run(args, kwargs)

    @staticmethod
    def on_start_tests(items):
        """Xfail NetworkX tests this backend cannot honor yet."""
        try:
            import pytest
        except ModuleNotFoundError:
            return

        reasons = [
            ("k=", "k-sampling is not implemented by rustworkx betweenness"),
            ("sample", "k-sampling is not implemented by rustworkx betweenness"),
            ("weighted", "weighted betweenness is not implemented"),
            ("MultiGraph", "MultiGraph is not supported"),
            ("multigraph", "MultiGraph is not supported"),
            ("node_match", "node_match / edge_match are not supported"),
            ("edge_match", "node_match / edge_match are not supported"),
        ]
        for item in items:
            label = f"{item.name} {item.fspath}"
            for needle, reason in reasons:
                if needle.lower() in label.lower():
                    item.add_marker(pytest.mark.xfail(reason=reason, strict=False))
                    break


for _name in algorithms.ALGORITHMS:
    setattr(BackendInterface, _name, getattr(algorithms, _name))

for _name in generators.GENERATORS:
    setattr(BackendInterface, _name, getattr(generators, _name))
