"""
Generate and render Graphviz diagrams with clear, maintainable code by separating presentation from structure.
"""

__all__ = (
    "Markup", "Nonce", "Port", "Dot", "InvocationException",
    "ProcessException", "TimeoutException", "ShowException",
    "Block", "ID", "CompassPoint",
    "impose_order",
)

from ._core import (
    __version__, Markup, Nonce, Port, Dot, InvocationException,
    ProcessException, TimeoutException, ShowException,
    Block, ID, CompassPoint,
)

from ._impose import impose_order

#
# Pull up for debugging and testing
#

from ._core import _NormPort, _Edge, _RoleRef
from ._impose import _Digraph, _AVAILABLE_VERSIONS
