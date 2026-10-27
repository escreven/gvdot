from __future__ import annotations
from contextlib import contextmanager
import io
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET  # How ugly
from re import Pattern, Match
from dataclasses import dataclass, field
from typing import Callable, ClassVar, Protocol
from PIL import Image
from gvdot import Dot

#
# Most tests compare produced DOT language with expected DOT language.  To
# avoid having to specify the expected DOT language exactly, we parse DOT text
# into line-oriented DOT forms implemented as DotLine classes.
#
# While this is sufficient to recognize and compare DOT language emitted by
# Dot, it is far from actually parsing the DOT language.  Besides being limited
# to line-oriented forms and having no notion of structural relationships, the
# significant restrictions include
#
#    - Only // comments supported, and only on their own line
#    - Only ASCII characters
#    - No markup contains any right angle bracket (!)
#    - Square bracketed attribute lists can only appear at the end of a line
#    - No more than one attribute list per line
#    - Strings (including markup) cannot span lines
#    - No string appending via +
#    - No # preprocessor line indicators
#

#
# Regular subexpressions incorporated further down.
#

_ID = ("(?:" + "|".join((
    # Simple IDs
    r"[a-zA-Z_][a-zA-Z0-9_]*",
    r"-?(?:[.][0-9]+|[0-9]+(?:[.][0-9]*)?)",
    # Quoted string IDs
    r'"(?:[^\"]|\\")*"',
    # Markup IDs
    r"<[^>]*>")) + ")")

_ATTRS = rf"\[(\s*{_ID}\s*=\s*{_ID})*\s*\]"

_COMPASS_PT = r"(?:n|ne|e|se|s|sw|w|nw|c|_)"

_PORT = rf":{_ID}(?::{_COMPASS_PT})?"

_POINT = rf"{_ID}(?:{_PORT})?"

#
# Parse an attribute list like '[a=12 b="hello there"]' into a dict.  The text
# can be None, in which case _parse_attrs() returns an empty dict.  The dict
# values are the text as it appears in the DOT language text, including
# surrounding quotes if present.
#

_RE_ATTRS_BODY = re.compile(r"\[\s*(.*)\]")
_RE_ATTRS_PAIR = re.compile(rf"\s*({_ID})\s*=\s*({_ID})")

def _parse_attrs(text:str|None) -> dict[str,str]:
    if text is None: return {}
    assert (match := _RE_ATTRS_BODY.fullmatch(text))
    body = match[1].rstrip()
    bodypos = 0
    result = dict()
    while (match := _RE_ATTRS_PAIR.match(body,pos=bodypos)):
        result[match[1]] = match[2]
        bodypos = match.end()
    if bodypos < len(body):
        raise ValueError(f"Malformed attributes: {text}")
    return result

#
# The line-oriented DOT language forms.  DotLine members:
#
#   lineno  - the corresponding line number in the source text
#   _RE     - a compiled regular expression recognizing the form
#   build() - creates an instance given an _RE match.
#

class DotLine(Protocol):
    lineno : int = field(init=False, default=-1)
    _RE : ClassVar[Pattern]
    @staticmethod
    def build(match:Match) -> DotLine:
        ...

@dataclass
class CommentLine(DotLine):
    text : str
    _RE = re.compile(r"//\s*(.*)")
    @staticmethod
    def build(match:Match):
        return CommentLine(
            text=match[1])

@dataclass
class GraphLine(DotLine):
    strict : bool
    directed : bool
    graphid : str | None
    _RE = re.compile(rf"(strict\s+)?(graph|digraph)\s+({_ID})?\s*{{")
    @staticmethod
    def build(match:Match):
        return GraphLine(
            strict=match[1] is not None,
            directed=match[2] == "digraph",
            graphid=match[3])

@dataclass
class GraphDAttrLine(DotLine):
    attrs : dict[str,str]
    _RE = re.compile(rf"graph\s*({_ATTRS})")
    @staticmethod
    def build(match:Match):
        return GraphDAttrLine(
            attrs=_parse_attrs(match[1]))

@dataclass
class NodeDAttrLine(DotLine):
    attrs : dict[str,str]
    _RE = re.compile(rf"node\s*({_ATTRS})")
    @staticmethod
    def build(match:Match):
        return NodeDAttrLine(
            attrs=_parse_attrs(match[1]))

@dataclass
class EdgeDAttrLine(DotLine):
    attrs : dict[str,str]
    _RE = re.compile(rf"edge\s*({_ATTRS})")
    @staticmethod
    def build(match:Match):
        return EdgeDAttrLine(
            attrs=_parse_attrs(match[1]))

@dataclass
class GraphAttrLine(DotLine):
    name : str
    value : str
    _RE = re.compile(rf"({_ID})\s*=\s*({_ID})")
    @staticmethod
    def build(match:Match):
        return GraphAttrLine(
            name=match[1],
            value=match[2])

@dataclass
class NodeLine(DotLine):
    nodeid : str
    attrs : dict[str,str]
    _RE = re.compile(rf"({_ID})\s*({_ATTRS})?")
    @staticmethod
    def build(match:Match):
        return NodeLine(
            nodeid=match[1],
            attrs=_parse_attrs(match[2]))

@dataclass
class EdgeLine(DotLine):
    endpoint1 : str
    endpoint2 : str
    directed : bool
    attrs : dict[str,str]
    _RE = re.compile(rf"({_POINT})\s*(--|->)\s*({_POINT})\s*({_ATTRS})?")
    @staticmethod
    def build(match:Match):
        return EdgeLine(
            endpoint1=match[1],
            endpoint2=match[3],
            directed=match[2] == "->",
            attrs=_parse_attrs(match[4]))

@dataclass
class SubgraphLine(DotLine):
    graphid : str | None
    _RE = re.compile(rf"subgraph\s+({_ID})?\s*{{")
    @staticmethod
    def build(match:Match):
        return SubgraphLine(
            graphid=match[1])

@dataclass
class EndLine(DotLine):
    _RE = re.compile(r"}")
    @staticmethod
    def build(match:Match):
        return EndLine()

#
# NOTE: Order matters because default graph, node, and edge attribute lines
# look like node lines.
#

_DOT_LINE_CLASSES:list[type[DotLine]] = [
    CommentLine,
    GraphLine,
    GraphDAttrLine,
    NodeDAttrLine,
    EdgeDAttrLine,
    GraphAttrLine,
    NodeLine,
    EdgeLine,
    SubgraphLine,
    EndLine,
]

#
# Parse DOT language text into a DotLine list.  Raises ValueError if the DOT
# language text is not recognized.
#

def parse(text:str) -> list[DotLine]:
    lines = text.splitlines()
    dotlines = list[DotLine]()
    for lineno, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        for cl in _DOT_LINE_CLASSES:
            if (match := cl._RE.fullmatch(line)):
                dotlines.append(dotline := cl.build(match))
                dotline.lineno = lineno
                break
        else:
            raise ValueError("Don't recognize DOT line: " + line)
    return dotlines

#
# Raised by expect_str() when actual DOT text doesn't match expected text.
# Properties expected and actual are the unnormalized text, and the
# corresponding line numbers are zero based.  If expected or actual is a prefix
# of the other, the corresponding line number is -1.
#

class DotMismatch(AssertionError):

    def __init__(self, expected:str, actual:str,
                 expected_lineno:int, actual_lineno:int):
        self.expected        = expected
        self.actual          = actual
        self.expected_lineno = expected_lineno
        self.actual_lineno   = actual_lineno

#
# Raise an AssertionError iff str(dot) does not match the given text.
#

def expect_str(dot:Dot, text:str):

    expect_str = text
    expect_lines = parse(expect_str)

    actual_str = str(dot)
    actual_lines = parse(actual_str)

    n = max(len(expect_lines),len(actual_lines))

    for i in range(n):
        expect_lineno, expect_line = (
            (expect_lines[i].lineno, expect_lines[i])
            if i < len(expect_lines) else (-1, None))

        actual_lineno, actual_line = (
            (actual_lines[i].lineno, actual_lines[i])
            if i < len(actual_lines) else (-1, None))

        if expect_line != actual_line:
            raise DotMismatch(expect_str, actual_str,
                              expect_lineno, actual_lineno)

#
# Raise an AssertionError iff fn() does not raise the given exception type.
# expect_ex() returns the exception raised.
#

def expect_ex[T:Exception](extype:type[T], fn:Callable) -> T:
    try:
        fn()
    except Exception as ex:
        if not isinstance(ex,extype):
            raise AssertionError(f"Caught {ex.__class__.__name__}; "
                                 f"expected {extype.__name__}") from ex
        return ex

    raise AssertionError(f"No exception; expected {extype.__name__}")

#
# Data validation for to_svg, to_rendered, and impose_order tests.
#

_LENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)([a-z]+)")

def _parse_length(s:str) -> tuple[float, str]:
    if (match := _LENGTH_RE.fullmatch(s)):
        return float(match[1]), match[2]
    else:
        raise ValueError(f"Bad length: {s}")

def svg_parse(text:str) -> ET.Element[str]:
    if ((svg := ET.fromstring(text)) is None
            or svg.tag.lower().split('}',1)[-1] != 'svg'):
        raise ValueError("Text is not SVG")
    return svg

def svg_dimensions(svg:ET.Element) -> tuple[float,float,str]:
    width = svg.get('width')
    height = svg.get('height')
    if width is None or height is None:
        raise RuntimeError("SVG does not have width and height attributes")
    width, width_unit = _parse_length(width)
    height, height_unit = _parse_length(height)
    if width_unit != height_unit:
        raise ValueError(f"Inconsistent units, {width_unit} and {height_unit}")
    return width, height, width_unit

def likely_full_svg(text:str):
    return (re.fullmatch(r"<\?xml.*<svg.*</svg>.*",text,re.DOTALL) is not None)

def image_format(data:bytes):
    return Image.open(io.BytesIO(data)).format

def image_file_format(filename:str):
    return Image.open(filename).format

#
# Create fake Graphviz programs for testing timeouts and non-zero exit status.
#
# On Windows, the fakes are implemented as .cmd batch files.  Unfortunately, on
# Windows subprocess.run() of dotsleep.cmd with a timeout doesn't actually
# return until after the powershell sleep completes.
#

_tmpdir:str|None = None

def tmpdir() -> str:
    if _tmpdir is None:
        raise RuntimeError("tmpdir is None")
    return _tmpdir

if os.name == 'nt':
    def dotsleep(): return "dotsleep.cmd"
    def doterror(): return "doterror.cmd"
    def dotecho(): return "dotecho.cmd"
else:
    def dotsleep(): return "dotsleep"
    def doterror(): return "doterror"
    def dotecho(): return "dotecho"

@contextmanager
def fakedots():
    global _tmpdir
    _tmpdir = tempfile.mkdtemp()
    try:
        dotsleep = os.path.join(_tmpdir, "dotsleep")
        doterror = os.path.join(_tmpdir, "doterror")
        dotecho = os.path.join(_tmpdir, "dotecho")

        def script(path, commands):
            if os.name == 'nt':
                path += '.cmd'
            with open(path, "w") as f:
                f.write(commands)

        if os.name == 'nt':
            script(dotsleep, 'powershell -Command "Start-Sleep -s 5"\n')
            script(doterror, '@echo ErrorText 1>&2\nexit /b 1\n')
            script(dotecho,  '@echo %*\n')
        else:
            script(dotsleep, '#!/bin/sh\nsleep 10\n')
            script(doterror, '#!/bin/sh\necho ErrorText >&2\nexit 1\n')
            script(dotecho,  '#!/bin/sh\necho "$@"\n')
            os.chmod(dotsleep, 0o755)
            os.chmod(doterror, 0o755)
            os.chmod(dotecho, 0o755)

        yield

    finally:
        shutil.rmtree(_tmpdir)
        _tmpdir = None
