import os
import re
import subprocess
from subprocess import CalledProcessError, TimeoutExpired
from pathlib import Path
from os import PathLike
from ._core import Dot, InvocationException, ProcessException, TimeoutException
from ._core import _invocation_str

__all__ = ()


class ProbeException(Exception):
    """
    A Graphviz installation probe failed.

    .. attribute:: program
        :type: str|PathLike

        The :func:`probe` ``program`` argument.

    .. attribute:: layout
        :type: str|None

        The :func:`probe` ``layout`` argument.

    .. attribute:: format
        :type: str

        The :func:`probe` ``format`` argument.

    .. attribute:: timeout
        :type: float|None

        The :func:`probe` ``timeout`` argument.

    .. attribute:: directory
        :type: str|PathLike|None

        The :func:`probe` ``directory`` argument.

    .. attribute:: issues
        :type: tuple[str,...]

        One or more short strings identifying the nature of the problem.  See
        :func:`probe` for the possible strings and their meaning.

    The string representation of a :class:`ProbeException` is a description of
    the problem incorporating the attributes above.
    """
    program   : str|PathLike
    layout    : str|None
    format    : str
    timeout   : float|None
    directory : str|PathLike|None
    issues    : tuple[str,...]

    def __init__(self, program:str|PathLike, layout:str|None, format:str,
                 timeout:float|None, directory:str|PathLike|None,
                 issues:tuple[str,...]):
        self.program     = program
        self.layout      = layout
        self.format      = format
        self.timeout     = timeout
        self.directory   = directory
        self.issues      = issues

    def __str__(self):

        cause = self.__cause__
        if (isinstance(cause, InvocationException) or
            isinstance(cause, TimeoutException)
        ):
            return str(cause)

        if self.directory is None:
            progname = str(self.program)
        else:
            progname = str(Path(self.directory,self.program))

        program_str = f"program '{progname}'"
        format_str = f"format '{self.format}'"
        layout_str = ("default layout" if self.layout is None
                      else f"layout '{self.layout}'")

        def C(s:str):
            return s[0].title() + s[1:]

        if 'identity' in self.issues:
            return (f"{C(program_str)} may not be a Graphviz program"
                    "; check option -V output")

        if 'layout' in self.issues or 'format' in self.issues:
            if 'format' not in self.issues:
                return f"{C(layout_str)} is unavailable for {program_str}"
            if 'layout' not in self.issues:
                return f"{C(format_str)} is not supported by {program_str}"
            return (f"{C(layout_str)} and {format_str} "
                    f"are not supported by {program_str}")

        return (f"{C(program_str)} could not render with "
                f"{layout_str} and {format_str}")


def _dash_V(program:str|PathLike, directory:str|PathLike|None,
            timeout:float|None) -> tuple[int,...] | None:

    program = _invocation_str(program,directory)
    command = [ program, "-V" ]

    try:
        completed = subprocess.run(
            command, input="", capture_output=True,
            text=False, check=True, timeout=timeout)
    except CalledProcessError as ex:
        raise ProcessException(
            program, ex.returncode, ex.stderr) from None
    except TimeoutExpired as ex:
        assert timeout is not None
        raise TimeoutException(
            program, timeout, "" if ex.stderr is None
            else ex.stderr) from None
    except Exception as ex:
        raise InvocationException(program) from ex

    output = completed.stderr.decode(errors="replace").lower()

    if "graphviz" not in output:
        return None

    if not (match := re.search(r"version\s+([0-9]+(\.[0-9]+)*)", output)):
        return (0,)

    return tuple(map(int,match[1].split('.')))  #type:ignore


def probe(program:str|PathLike='dot',*,
          layout:str|None=None, format:str='png', timeout:float|None=None,
          directory:str|PathLike|None=None) -> tuple[int,...]:
    """
    Verify the capabilities of a Graphviz installation.

    :param program: Which Graphviz program to investigate (:program:`dot` by
        default).  ``program`` should either be the name of the program or
        a path to the program.

    :param layout: A Graphviz layout engine such as ``'circo'`` or ``'dot'``.
        If None, :func:`probe()` uses the default layout engine for
        ``program``.

    :param format: The output format desired (png by default).

    :param timeout: Limit program execution time to this many seconds.  The
        limit applies to each program :func:`probe()` may run individually; it
        is not a cumulative limit.

    :param directory: If specified, ``program`` is interpreted as a path
        relative to ``directory``.

    :return: The Graphviz program version number found.  If the program reports
        version 16.1.0, the returned tuple will be ``(16, 1, 0)``.  If no
        version number is found, the returned tuple will be ``(0,)``.

    :raises ValueError: A specified program or directory value is empty.

    :raises ProbeException: Any attempt to render a graph using the specified
        program, layout engine, and output format is likely to fail.  The
        string representation of :class:`ProbeException` describes why.

    Parameters ``program``, ``format``, ``timeout``, and ``directory`` have the
    same meaning as the identically named parameters of
    :meth:`Dot.to_rendered`.  Parameter ``layout`` corresponds to the eponymous
    Graphviz graph attribute.

    :func:`probe` first invokes the specified program with option ``-V`` to
    confirm its identity, then attempts to render a small test graph with the
    required layout and output format.  If that fails, it takes further steps
    to diagnose the problem, sometimes rendering the test graph using other
    layouts and output formats.

    If verification fails, :func:`probe` raises :class:`ProbeException` which
    includes attribute ``issues``, a non-empty tuple of strings from the table
    below.

        .. list-table::
            :header-rows: 1

            * - Issue
              - Meaning
            * - invocation
              - The program could not be run
            * - timeout
              - The program took longer than ``timeout`` seconds to run
            * - identity
              - The program ran but -V output did not identify it as a Graphviz
                program
            * - layout
              - The layout engine is not available
            * - format
              - The output format is not supported
            * - other
              - The program ran and failed, but the cause could not be
                determined

    Examples:

    .. code-block:: python

        #
        # Make sure we can render neato graphs to SVG.
        #

        try:
            probe(layout="neato", format="svg")
        except ProbeException as ex:
            print(ex)
            print("Generator requires Graphviz with neato and SVG support")
            sys.exit(1)

    .. code-block:: python

        #
        # Fallback to PNG if SVG not supported.
        #

        format = "svg"
        try:
            probe(format=format)
        except ProbeException as ex:
            if "format" in ex.issues:
                format = "png"
            else:
                raise

    .. code-block:: python

        #
        # We need at least version 14.1.0.
        #

        if probe() < (14,1):
            raise RuntimeError("Need Graphviz 14.1.0 or better")
    """
    #
    # Run the program with option -V to verify that it is a Graphviz program
    # and get its reported version.  Failing to see "graphviz" (any case) in
    # the output means the probe fails; failing to find the version number does
    # not, just in case the reported format changes.
    #

    try:
        version = _dash_V(program, directory, timeout)
        dash_V_ex = None
    except InvocationException as ex:
        raise ProbeException(program, layout, format, timeout,
                             directory, ("invocation",)) from ex
    except TimeoutException as ex:
        raise ProbeException(program, layout, format, timeout,
                             directory, ("timeout",)) from ex
    except ProcessException as ex:
        dash_V_ex = ex

    if dash_V_ex is not None or version is None:
        raise ProbeException(program, layout, format, timeout,
                             directory, ("identity",)) from dash_V_ex

    #
    # Try to use program to render a trivial graph with the specified layout
    # and format.
    #

    def attempt(attempt_layout:str|None,
                attempt_format:str) -> ProcessException | None:

        dot = Dot()
        if attempt_layout is not None:
            dot.graph(layout=attempt_layout)
        dot.edge("a","b")

        try:
            dot.to_rendered(program=program,format=attempt_format,
                            timeout=timeout,directory=directory)
        except InvocationException as ex:
            raise ProbeException(program, layout, format,
                                 timeout, directory,
                                 ("invocation",)) from ex
        except TimeoutException as ex:
            raise ProbeException(program, layout, format,
                                 timeout, directory,
                                 ("timeout",)) from ex
        except ProcessException as ex:
            return ex

        return None

    if (failure := attempt(layout,format)) is None:
        return version

    #
    # Diagnose the failure.
    #

    baseline_ok = attempt("dot","dot")  is None
    layout_ok   = attempt(layout,"dot") is None
    format_ok   = attempt("dot",format) is None
    issues      = []

    if not layout_ok and (format_ok or baseline_ok):
        issues.append("layout")

    if not format_ok and (layout_ok or baseline_ok):
        issues.append("format")

    if not issues:
        #
        # There are two ways to reach here:
        #  1. not layout_ok and not format_ok and not baseline_ok
        #  2. layout_ok and format_ok
        #
        # (1) means something is very wrong, since the baseline should always
        # be available. (2) is also strange since layout and format are both ok
        # independently, but just not together.
        #
        issues.append("other")

    raise ProbeException(program,layout,format,
                         timeout, directory,
                         tuple(issues)) from failure
