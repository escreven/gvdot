from __future__ import annotations
from contextlib import contextmanager
import io
import os
import re
import shutil
import tempfile
from typing import Callable
from PIL import Image
from gvdot import Dot

#
# Most tests compare produced DOT language with expected DOT language.  To
# avoid having to specify the expected DOT language exactly, we normalize DOT
# text by stripping blank lines, separating tokens by a single space, and
# sorting entity attribute lists alphabetically. While nowhere close to
# actually parsing the DOT text, this is enough to verify expected output.
# There are significant lexical and other restrictions:
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

_COMMENT_RE = re.compile(r"\s*(//.*)")

_TOKEN_RE = re.compile(r"\s*(" + "|".join((
    # Simple IDs
    r"[a-zA-Z_][a-zA-Z0-9_]*",
    r"-?(?:[.][0-9]+|[0-9]+(?:[.][0-9]*)?)",
    # Quoted string IDs
    r'"(?:[^"]|\")*"',
    # Markup IDs
    r"<[^>]*>",
    # Edge connectors
    r"--|->",
    # Syntax significant characters
    r"[\[\]{},;=:]",
)) + r")")

def _parse_attrs(tokens:list[str]) -> dict[str,str]:
    result = dict()
    while tokens:
        if len(tokens) < 3 or tokens[1] != '=':
            raise ValueError("Malformed attributes: " + " ".join(tokens))
        result[tokens[0]] = tokens[2]
        tokens = tokens[3:]
    return result

def _normalize_line(line:str) -> str:
    line = line.rstrip()
    if match := _COMMENT_RE.fullmatch(line):
        return match[1]
    tokens = []
    pos = 0
    end = len(line)
    while pos < end:
        if match := _TOKEN_RE.match(line,pos):
            tokens.append(match[1])
            pos = match.end()
        else:
            raise ValueError("Unrecognized token: " + line[pos:])
    if "[" in tokens:
        if tokens[-1] != "]":
            raise ValueError("No closing bracket: " + line)
        index = tokens.index("[")
        attrs = _parse_attrs(tokens[index+1:-1])
        del tokens[index+1:]
        for name in sorted(attrs):
            tokens.extend([name,'=',attrs[name]])
        tokens.append("]")
    return " ".join(tokens)

def _normalize_text(text:str) -> list[tuple[int,str]]:
    lines = []
    for lineno, line in enumerate(text.splitlines()):
        line = _normalize_line(line)
        if line: lines.append((lineno,line))
    return lines

#
# Raised by expect_str() when actual DOT text doens't match expected text.
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
    expect_lines = _normalize_text(expect_str)

    actual_str = str(dot)
    actual_lines = _normalize_text(actual_str)

    n = max(len(expect_lines),len(actual_lines))

    for i in range(n):

        expect_lineno, expect_line = (expect_lines[i]
            if i < len(expect_lines) else (-1, None))

        actual_lineno, actual_line = (actual_lines[i]
            if i < len(actual_lines) else (-1, None))

        if expect_line != actual_line:
            raise DotMismatch(expect_str, actual_str,
                              expect_lineno, actual_lineno)

#
# Raise an AssertionError iff fn() does not raise the given exeption type.
# expect_ex() returns the exception raised.
#

def expect_ex[T:BaseException](extype:type[T], fn:Callable) -> T:
    try:
        fn()
    except BaseException as ex:
        if not isinstance(ex,extype):
            raise AssertionError(f"Caught {ex.__class__.__name__}; "
                                 f"expected {extype.__name__}") from ex
        return ex

    raise AssertionError(f"No exception; expected {extype.__name__}")

#
# Data validation for to_svg and to_rendered test helpers.
#

def likely_full_svg(text:str):
    return (re.fullmatch(r"<\?xml.*<svg.*</svg>.*",text,re.DOTALL) is not None)

def likely_svg(text:str):
    return (re.fullmatch(r".*<svg.*</svg>.*",text,re.DOTALL) is not None)

def image_format(data:bytes):
    return Image.open(io.BytesIO(data)).format

def image_file_format(filename:str):
    return Image.open(filename).format

#
# Create fake Graphviz programs for testing timeouts and non-zero exit status.
# The context value is the temporary directory of the fakes.
#
# On Windows, the fakes are implemented as .cmd batch files.  Unfortunately,
# because Windows doesn't have a notion of process tree, subprocess.run() of
# dotsleep.cmd with a timeout doesn't actually return until after the
# powershell sleep completes.
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
