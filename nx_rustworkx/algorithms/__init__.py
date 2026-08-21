"""Algorithm implementations attached to BackendInterface by name.

Each submodule lists the NetworkX function names it implements in ``__all__``.
``ALGORITHMS`` is the union of those lists and drives both the backend
interface and the metadata in :mod:`nx_rustworkx._info`.
"""

from nx_rustworkx.algorithms import (
    centrality,
    community,
    connectivity,
    dag,
    isomorphism,
    link_analysis,
    shortest_paths,
    traversal,
)
from nx_rustworkx.algorithms.centrality import *  # noqa: F401,F403
from nx_rustworkx.algorithms.community import *  # noqa: F401,F403
from nx_rustworkx.algorithms.connectivity import *  # noqa: F401,F403
from nx_rustworkx.algorithms.dag import *  # noqa: F401,F403
from nx_rustworkx.algorithms.isomorphism import *  # noqa: F401,F403
from nx_rustworkx.algorithms.link_analysis import *  # noqa: F401,F403
from nx_rustworkx.algorithms.shortest_paths import *  # noqa: F401,F403
from nx_rustworkx.algorithms.traversal import *  # noqa: F401,F403

_MODULES = (
    centrality,
    community,
    connectivity,
    dag,
    isomorphism,
    link_analysis,
    shortest_paths,
    traversal,
)

ALGORITHMS = sorted({name for module in _MODULES for name in module.__all__})

__all__ = ALGORITHMS + ["ALGORITHMS"]
