"""Prove that dispatch actually fired instead of silently falling back.

Two mechanisms:

- ``count_dispatch()`` wraps every registered backend function with a call
  counter, so a timed run can assert that the backend really handled a call.
- ``auto_dispatch_verdict()`` asks the backend's own ``can_run``/``should_run``
  whether a call on a given graph would auto-dispatch under backend priority,
  and reports the refusal reason when it would not. NetworkX treats a string
  return from either hook as "no, and here is why".
"""

from __future__ import annotations

import functools
from contextlib import contextmanager

from nx_rustworkx.algorithms import ALGORITHMS
from nx_rustworkx.interface import BackendInterface


@contextmanager
def count_dispatch():
    """Count calls that reach the backend, keyed by function name."""
    counts: dict[str, int] = {}
    originals = {name: getattr(BackendInterface, name) for name in ALGORITHMS}

    def counting(name, func):
        # functools.wraps copies __dict__, keeping the attached can_run /
        # should_run attributes that BackendInterface.can_run() looks up.
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            counts[name] = counts.get(name, 0) + 1
            return func(*args, **kwargs)

        return wrapper

    for name, func in originals.items():
        setattr(BackendInterface, name, counting(name, func))
    try:
        yield counts
    finally:
        for name, func in originals.items():
            setattr(BackendInterface, name, func)


def _refusal(verdict) -> str | None:
    """None when the hook allows the call, else a human-readable reason."""
    if verdict is True or (bool(verdict) and not isinstance(verdict, str)):
        return None
    return verdict if isinstance(verdict, str) and verdict else "declined"


def auto_dispatch_verdict(name: str, G, kwargs: dict | None = None) -> dict:
    """Would ``nx.<name>(G, **kwargs)`` auto-dispatch under backend priority?"""
    kwargs = dict(kwargs or {})
    if getattr(BackendInterface, name, None) is None:
        return {"function": name, "auto_dispatch": False, "reason": "not implemented"}
    can = _refusal(BackendInterface.can_run(name, (G,), kwargs))
    should = _refusal(BackendInterface.should_run(name, (G,), kwargs))
    reason = can if can is not None else should
    return {
        "function": name,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "auto_dispatch": reason is None,
        "reason": reason,
    }
