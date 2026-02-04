import os
import shutil
from subprocess import CalledProcessError, TimeoutExpired
from gvdot import Dot, InvocationException
from utility import expect_ex, image_format, likely_full_svg, likely_svg
from utility import tmpdir


def test_to_svg():
    """
    Method to_svg() should invoke the specified graphviz program to render the
    dot object as SVG.  If the program isn't found, it should raise an
    InvocationError.  If the program exits with a non-zero status, it should
    raise a CalledProcessError.  If a timeout is specified, and the program
    times out, it should raise a TimeoutExpired exception.
    """
    dot = Dot().edge("a","b")

    svg = dot.to_svg()
    assert likely_full_svg(svg)
    svg_len = len(svg)

    svg = dot.to_svg(inline=True)
    assert likely_svg(svg) and not likely_full_svg(svg)

    svg = dot.to_svg("neato")
    assert likely_full_svg(svg)

    ex = expect_ex(InvocationException, lambda: dot.to_svg("doesnotexist"))
    assert "doesnotexist" in str(ex)

    path = shutil.which('dot')

    if path is None:
        raise RuntimeError("Could not find path to dot program")

    pathdir = os.path.dirname(path)

    svg = dot.to_svg(program="dot",directory=pathdir)
    assert likely_full_svg(svg)

    expect_ex(TimeoutExpired,lambda: dot.to_svg(
        directory=tmpdir(), program="dotsleep", timeout=0.1))

    ex = expect_ex(CalledProcessError,lambda: dot.to_svg(
        directory=tmpdir(), program="doterror"))

    assert ex.returncode == 1 and "ErrorText" in ex.stderr

    #
    # The rendered output should be smaller after applying the attributes below
    # on the command line since the title is gone and the nodes and edges are
    # invisible.
    #

    graph_attrs = { 'label': ''}
    node_attrs  = { 'style': 'invisible'}
    edge_attrs  = { 'style': 'invisible'}

    data = dot.to_svg(graph_attrs=graph_attrs,
                      node_attrs=node_attrs,
                      edge_attrs=edge_attrs)

    assert likely_full_svg(data)
    assert len(data) < svg_len

    bad_attrs = { 'not legal': 42 }
    ex = expect_ex(ValueError, lambda:dot.to_svg(graph_attrs=bad_attrs))


def test_to_rendered():
    """
    Method to_rendered() should invoke the specified graphviz program to render
    the dot object as bytes.  If the program isn't found, it should raise an
    InvocationError.  If the program exits with a non-zero status, it should
    raise a CalledProcessError.  If a timeout is specified, and the program
    times out, it should raise a TimeoutExpired exception.
    """
    dot = Dot().edge("a","b").graph(label="Title")

    data = dot.to_rendered()
    assert image_format(data) == 'PNG'
    png_len = len(data)

    data = dot.to_rendered(format='jpeg')
    assert image_format(data) == 'JPEG'

    data = dot.to_rendered("neato")
    assert image_format(data) == 'PNG'

    ex = expect_ex(InvocationException, lambda: dot.to_rendered("doesnotexist"))
    assert "doesnotexist" in str(ex)

    path = shutil.which('dot')

    if path is None:
        raise RuntimeError("Could not find path to dot program")

    pathdir = os.path.dirname(path)

    data = dot.to_rendered(program="dot",directory=pathdir)
    assert image_format(data) == 'PNG'

    expect_ex(TimeoutExpired,lambda: dot.to_rendered(
        directory=tmpdir(), program="dotsleep", timeout=0.1))

    ex = expect_ex(CalledProcessError,lambda: dot.to_rendered(
        directory=tmpdir(), program="doterror"))

    assert ex.returncode == 1 and b"ErrorText" in ex.stderr

    #
    # The rendered output should be smaller after applying the attributes below
    # on the command line (since everything is white).
    #

    graph_attrs = { 'label': ''}
    node_attrs  = { 'style': 'invisible'}
    edge_attrs  = { 'style': 'invisible'}

    data = dot.to_rendered(graph_attrs=graph_attrs,
                           node_attrs=node_attrs,
                           edge_attrs=edge_attrs)

    assert image_format(data) == 'PNG'
    assert len(data) < png_len

    bad_attrs = { 'not legal': 42 }
    ex = expect_ex(ValueError, lambda:dot.to_rendered(graph_attrs=bad_attrs))
