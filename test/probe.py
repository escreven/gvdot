import os
import shutil
from contextlib import chdir, contextmanager
from collections.abc import Callable
from pathlib import Path
from gvdot import InvocationException, ProcessException, TimeoutException
from gvdot import Dot, probe, ProbeException
from utility import EmptyPathLike, expect_ex, tempdir, program


def _require_probe_ex(cause:type[Exception|None], issues:tuple[str,...],
                      **kwargs) -> ProbeException:

    program   = kwargs.get('program','dot')
    layout    = kwargs.get('layout',None)
    format    = kwargs.get('format','png')
    timeout   = kwargs.get('timeout',None)
    directory = kwargs.get('directory',None)

    ex = expect_ex(ProbeException,lambda: probe(**kwargs))

    assert ex.program == program
    assert ex.layout == layout
    assert ex.format == format
    assert ex.timeout == timeout
    assert ex.directory == directory
    assert len(issues) == len(ex.issues)
    assert all(issue in ex.issues for issue in issues)
    assert isinstance(ex.__cause__,cause)

    s = str(ex)
    assert program == "." or str(program) in s
    assert directory is None or str(directory) in s

    if cause is ProcessException:
        assert ex.__cause__.status != 0 #type:ignore
    elif cause is TimeoutException:
        assert ex.__cause__.timeout == timeout #type:ignore

    return ex


def test_exception():
    """
    ProbeException should retain its arguments and use them in its string
    representation.
    """
    program = Path("dot")
    directory = Path("graphviz/bin")

    ex = ProbeException(program,"neato","SVG",None,
                        directory,("format",))
    assert ex.program is program
    assert ex.layout == "neato"
    assert ex.format == "SVG"
    assert ex.directory is directory
    assert ex.issues == ("format",)
    s = str(ex)
    assert "SVG" in s
    assert str(directory / program) in s

    ex = ProbeException(program,"neato","SVG",None,
                        directory,("layout",))
    assert ex.program is program
    assert ex.layout == "neato"
    assert ex.format == "SVG"
    assert ex.directory is directory
    assert ex.issues == ("layout",)
    s = str(ex)
    assert "neato" in s
    assert str(directory / program) in s

    ex = ProbeException(program,"neato","SVG",None,
                        directory,("layout","format"))
    assert ex.program is program
    assert ex.layout == "neato"
    assert ex.format == "SVG"
    assert ex.directory is directory
    assert ex.issues == ("layout","format")
    s = str(ex)
    assert "SVG" in s
    assert "neato" in s
    assert str(directory / program) in s


def test_available():
    """
    Available combinations using real Graphviz programs should return a
    version.  The layout can be chosen independently of the program, and format
    names are case insensitive.
    """
    assert probe()
    assert probe("neato",format="svg")
    assert probe("dot",layout="neato",format="PnG")
    assert probe("neato",layout="dot",format="SVG")


def test_pathlike():
    """
    The program and directory arguments can be strings or path-like objects.
    """
    pathstr = shutil.which('dot')
    assert pathstr
    path = Path(pathstr)

    assert probe(path)
    assert probe(str(path))
    assert probe(path.name,directory=path.parent)
    assert probe(Path(path.name),directory=str(path.parent))


def test_bad_invocation():
    """
    Probes with problematic program specifications should result in
    "invocation" issues with descriptive messages and InvocationException
    causes.
    """
    for layout, format in zip((None,"neato","nosuchlayout"),
                              ("png","SVG","nosuchformat")):

        def bad_invocation(program, directory=None):
            ex = _require_probe_ex(
                program=program, layout=layout, format=format,
                directory=directory, issues=("invocation",),
                cause=InvocationException)
            return str(ex)

        assert "PATH" in bad_invocation("doesnotexist")
        assert "PATH" in bad_invocation(".")

        assert "executable" in bad_invocation("./doesnotexist")
        assert "executable" in bad_invocation(tempdir())

        assert "executable" in bad_invocation("doesnotexist", tempdir())
        assert "executable" in bad_invocation(".", tempdir())

        if os.name != 'nt':
            assert "executable" in bad_invocation(
                os.path.join(tempdir(),'dotnoexec'))

        assert "invalid.exe" in bad_invocation(
            os.path.join(tempdir(),"invalid.exe"))


def test_bad_generation():
    """
    Probes with unsupported explicit layouts and formats should result in
    combinations of "layout" and "format" issues with descriptive messages and
    ProcessException causes.
    """
    wrongdot = tempdir() + "/" + 'doterror'

    for program, issues, layout, format in (
        ("dot",    ("layout",),         "noSUCHlayout", "PnG"),
        ("dot",    ("format",),         "neato",        "noSUCHformat"),
        ("dot",    ("layout","format"), "noSUCHlayout", "noSUCHformat"),
    ):
        ex = _require_probe_ex(program=program, layout=layout, format=format,
                               issues=issues, cause=ProcessException)
        s = str(ex)
        if 'layout' in issues:
            assert layout is not None
            assert layout in s
        if 'format' in issues:
            assert format in s


def test_version():
    """
    Probe parses and returns the program's version as a tuple.  If a program's
    version is missing or can't be parsed, the version tuple should be (0,).
    """
    assert probe() > (0,0,0)
    assert probe(program=program("dotdvg10")) == (1,)
    assert probe(program=program("dotdvg20")) == (1,2)
    assert probe(program=program("dotdvg30")) == (1,2,3)
    assert probe(program=program("dotdvg40")) == (1,2,3,4)
    assert probe(program=program("dotdvgd0")) == (11,22)
    assert probe(program=program("dotdvgq0")) == (11,22,33)
    assert probe(program=program("dotdvgx0")) == (0,)


def test_identity():
    """
    To be recognized as a Graphviz program, a program needs to respond to the
    -V option by writing "graphviz" and exit with status zero.  The version
    identified is allowed to be missing.
    """
    assert probe(program=program("dotdvgx0"))
    assert probe(program=program("dotdvg10"))
    assert probe(program=program("dotdvg30"))

    _require_probe_ex(program=program("dotdvg31"),
                      issues=("identity",), cause=ProcessException)

    _require_probe_ex(program=program("dotdvx30"),
                      issues=("identity",), cause=type(None))

    _require_probe_ex(program=program("doterror"),
                      issues=("other",), cause=ProcessException)


def test_timeout():
    """
    Callers can timeout probes.
    """
    _require_probe_ex(program=program("dotsleep"), timeout=1.0,
                      issues=("timeout",), cause=TimeoutException)

    _require_probe_ex(program=program("dotdvsleep"), timeout=0.01,
                      issues=("timeout",), cause=TimeoutException)


def test_dot_relative():
    """
    Directory "." should cause program to be interpreted relative to ".".
    """
    dotecho = Path(program("dotecho")).name
    with chdir(tempdir()):
        probe(dotecho,directory=".")
        probe(Path(dotecho),directory=Path("."))
        expect_ex(ProbeException, lambda: (
            probe("neato",directory=".")))
        expect_ex(ProbeException, lambda: (
            probe(Path("neato"),directory=Path("."))))


def test_empty_segments():
    """
    Program and directory must both be non-empty.
    """
    for program, directory in (
        ("",tempdir()),
        ("dot",""),
        (EmptyPathLike(),tempdir()),
        ("dot",EmptyPathLike()),
    ):
        expect_ex(ValueError, lambda: probe(
            program=program, directory=directory),
            moreinfo=lambda: repr((program,directory)))


#
# Monkey patch Dot.to_rendered to enable the remaining tests.  This depends on
# the implementation approach of probe(), but making the tests below work in a
# black-box way would be substantially more complex.
#

@contextmanager
def _mock_to_rendered(fn:Callable):
    save_to_rendered = Dot.to_rendered
    Dot.to_rendered = fn
    try:
        yield
    finally:
        Dot.to_rendered = save_to_rendered


def test_default_layout_unavailable():
    """
    A program's default layout can be unavailable.
    """
    def to_rendered(self, program, **kwargs):
        s = str(self)
        if 'layout=' not in s:
            raise ProcessException(program,1,"mock says hello")
        return b'Good to go'

    with _mock_to_rendered(to_rendered):
        ex = _require_probe_ex(program="dot", format="svg",
                               issues=("layout",), cause=ProcessException)

    s = str(ex)
    assert "default layout" in s.lower()
    assert "mock" in ex.__cause__.stderr  #type:ignore


def test_first_failure_wins():
    """
    Subsequent process errors shouldn't obscure the first as the cause.
    """
    neato_png_ex = ProcessException("dot",1,"mock says neato png")
    neato_png_used = False

    def to_rendered(self, program, *, format, **kwargs):
        nonlocal neato_png_used
        s = str(self)
        if 'layout=neato' in s and format == 'png':
            assert not neato_png_used
            neato_png_used = True
            raise neato_png_ex
        else:
            raise ProcessException(program,1,"mock says something else")

    with _mock_to_rendered(to_rendered):
        ex = _require_probe_ex(
            program="dot", layout="neato", format="png",
            issues=("other",), cause=ProcessException)

    assert ex.__cause__ is neato_png_ex


def test_combination_failure():
    """
    If the layout and format work separately but not together, report an
    undiagnosed issue without claiming that the baseline also failed.
    """
    def to_rendered(self, program, *, format, **kwargs):
        s = str(self)
        if 'layout=neato' in s and format == 'png':
            raise ProcessException(program,1,"mock says bad combo")
        return b'Good to go'

    with _mock_to_rendered(to_rendered):
        ex = _require_probe_ex(
            program="dot", layout="neato", format="png",
            issues=("other",), cause=ProcessException)

    s = str(ex)
    assert "neato" in s
    assert "png" in s


def test_diagnostic_invocation_failure():
    """
    An invocation failure during diagnosis should retain the originally
    requested arguments and use the invocation exception as its cause.
    """
    pathstr = shutil.which('dot')
    assert pathstr
    path = Path(pathstr)
    program = Path(path.name)
    directory = path.parent

    def to_rendered(self, program, *, format, directory, **kwargs):
        progname = directory / program
        s = str(self)
        if 'layout=neato' in s and format == 'png':
            raise ProcessException(progname,1,"mock says neato png")
        if 'layout=dot' in s and format == 'dot':
            raise InvocationException(progname)
        return b'Good to go'

    with _mock_to_rendered(to_rendered):
        ex = _require_probe_ex(
            program=program, layout="neato", format="png",
            directory=directory, issues=("invocation",),
            cause=InvocationException)

    assert ex.program is program
    assert ex.directory is directory
