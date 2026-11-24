"""
Generate and render Graphviz diagrams with clear, maintainable code by separating presentation from structure.
"""

__version__ = "1.6.0"

__all__ = (
    "Markup", "Nonce", "Port", "Dot", "InvocationException",
    "ProcessException", "TimeoutException", "ShowException",
    "Block", "ID", "AttrSpec", "CompassPoint",
    "impose_order", "probe", "ProbeException",
)

from ._core import (
    Markup, Nonce, Port, Dot, InvocationException,
    ProcessException, TimeoutException, ShowException,
    Block, ID, AttrSpec, CompassPoint,
)
from ._probe import probe, ProbeException
from ._impose import impose_order

#
# Pull up for debugging and testing
#

from ._impose import _Digraph, _AVAILABLE_VERSIONS
from ._core import _NormPort, _Edge
