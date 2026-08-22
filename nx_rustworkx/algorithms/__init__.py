"""Algorithm implementations attached to BackendInterface by name.

Each submodule lists the NetworkX function names it implements in ``__all__``.
``ALGORITHMS`` is the union of those lists and drives both the backend
interface and the metadata in :mod:`nx_rustworkx._info`.
"""

from nx_rustworkx.algorithms import (
    centrality,
    coloring,
    connectivity,
    core,
    cycles,
    dag,
    isomorphism,
    link_analysis,
    matching,
    operators,
    shortest_paths,
    simple_paths,
    structure,
    traversal,
    trees,
)
from nx_rustworkx.algorithms.centrality import *  # noqa: F401,F403
from nx_rustworkx.algorithms.coloring import *  # noqa: F401,F403
from nx_rustworkx.algorithms.connectivity import *  # noqa: F401,F403
from nx_rustworkx.algorithms.core import *  # noqa: F401,F403
from nx_rustworkx.algorithms.cycles import *  # noqa: F401,F403
from nx_rustworkx.algorithms.dag import *  # noqa: F401,F403
from nx_rustworkx.algorithms.isomorphism import *  # noqa: F401,F403
from nx_rustworkx.algorithms.link_analysis import *  # noqa: F401,F403
from nx_rustworkx.algorithms.matching import *  # noqa: F401,F403
from nx_rustworkx.algorithms.operators import *  # noqa: F401,F403
from nx_rustworkx.algorithms.shortest_paths import *  # noqa: F401,F403
from nx_rustworkx.algorithms.simple_paths import *  # noqa: F401,F403
from nx_rustworkx.algorithms.structure import *  # noqa: F401,F403
from nx_rustworkx.algorithms.traversal import *  # noqa: F401,F403
from nx_rustworkx.algorithms.trees import *  # noqa: F401,F403

_MODULES = (
    centrality,
    coloring,
    connectivity,
    core,
    cycles,
    dag,
    isomorphism,
    link_analysis,
    matching,
    operators,
    shortest_paths,
    simple_paths,
    structure,
    traversal,
    trees,
)

ALGORITHMS = sorted({name for module in _MODULES for name in module.__all__})

__all__ = ALGORITHMS + ["ALGORITHMS"]
