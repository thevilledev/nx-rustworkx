"""NetworkX backend interface for rustworkx."""

from __future__ import annotations

from nx_rustworkx import algorithms
from nx_rustworkx.algorithms._utils import (
    NO_AUTO_DISPATCH,
    NO_AUTO_DISPATCH_REASON,
    default_can_run,
    default_should_run,
)
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
        if name in NO_AUTO_DISPATCH:
            return NO_AUTO_DISPATCH_REASON
        checker = getattr(func, "should_run", None)
        if checker is not None:
            return checker(*args, **kwargs)
        return default_should_run(args, kwargs)

    @staticmethod
    def on_start_tests(items):
        """Xfail the NetworkX tests this backend cannot honor.

        NetworkX already xfails anything ``can_run`` refuses, so this list only
        needs the cases where the backend runs but answers differently.
        """
        try:
            import pytest
        except ModuleNotFoundError:
            return

        divergent = {
            "test_topological_sort6": (
                "the backend sorts a converted snapshot, so it cannot detect "
                "mutation of the NetworkX graph during iteration"
            ),
            "test_steiner_tree": (
                "steiner_tree calls minimum_spanning_edges internally, and a "
                "minimum spanning forest is not unique when weights tie, so the "
                "intermediate result differs even though the tree matches"
            ),
        }
        for item in items:
            # Parameterized items arrive as "name[param]".
            reason = divergent.get(item.name.partition("[")[0])
            if reason is not None:
                item.add_marker(pytest.mark.xfail(reason=reason, strict=False))


for _name in algorithms.ALGORITHMS:
    setattr(BackendInterface, _name, getattr(algorithms, _name))
