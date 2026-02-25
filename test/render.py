import os
import shutil
from gvdot import Dot, InvocationException, ProcessException, TimeoutException
from utility import dotecho, doterror, dotsleep, tmpdir
from utility import expect_ex, image_format, likely_full_svg, likely_svg
from utility import image_file_format


def test_to_rendered():
    """
    Method to_rendered() should invoke the specified graphviz program to render
    the dot object as bytes.  If the program isn't found, it should raise an
    InvocationException.  If the program exits with a non-zero status, it
    should raise a ProcessException.  If a timeout is specified, and the
    program times out, it should raise a TimeoutException exception.  The dpi,
    size, and ratio arguments should be passed as -G options to the program.
    """
    dot = Dot().edge("a","b").graph(label="Title")

    data = dot.to_rendered()
    assert image_format(data) == 'PNG'
    base_png_len = len(data)

    data = dot.to_rendered(format='jpeg')
    assert image_format(data) == 'JPEG'

    data = dot.to_rendered("neato")
    assert image_format(data) == 'PNG'

    ex = expect_ex(InvocationException, lambda: dot.to_rendered("doesnotexist"))
    assert "doesnotexist" in str(ex)
    assert ex.program == "doesnotexist"

    path = shutil.which('dot')

    if path is None:
        raise RuntimeError("Could not find path to dot program")

    pathdir = os.path.dirname(path)

    data = dot.to_rendered(program="dot",directory=pathdir)
    assert image_format(data) == 'PNG'

    ex = expect_ex(TimeoutException,lambda: dot.to_rendered(
        directory=tmpdir(), program=dotsleep(), timeout=0.01))

    assert "timed out" in str(ex)
    assert ex.program.endswith(dotsleep())
    assert ex.timeout == 0.01
    assert type(ex.stderr) is str

    ex = expect_ex(ProcessException,lambda: dot.to_rendered(
        directory=tmpdir(), program=doterror()))

    assert "exited with status" in str(ex)
    assert ex.program.endswith(doterror())
    assert ex.status == 1 and "ErrorText" in ex.stderr
    assert type(ex.stderr) is str

    #
    # The rendered output should be smaller if we use a coarse resolution.
    #

    data = dot.to_rendered(dpi=30)
    coarse_png_len = len(data)
    assert image_format(data) == 'PNG'
    assert coarse_png_len < base_png_len

    #
    # And it should be larger again with an extreme extreme aspect ratio.
    #

    data = dot.to_rendered(dpi=30, ratio=20)
    tall_png_len = len(data)
    assert image_format(data) == 'PNG'
    assert tall_png_len > coarse_png_len

    #
    # And finally it should be very small with a tiny maximum size.
    #

    data = dot.to_rendered(dpi=30, ratio=20, size="1,1")
    tiny_png_len = len(data)
    assert image_format(data) == 'PNG'
    assert tiny_png_len < tall_png_len

    #
    # Check the command line too.
    #

    # Returned date is the echoed command line
    data = dot.to_rendered(
        dpi=30, ratio=20, size="1,1",
        directory=tmpdir(), program=dotecho()).decode()

    assert "-Gdpi=30" in data
    assert "-Gratio=20" in data
    assert "-Gsize=1,1" in data


def test_to_rendered_downcase():
    """
    to_rendered() should downcase the format before forming the -T argument.
    """
    dot = Dot().edge("a", "b")
    text = dot.to_rendered(
        format="PnG", directory=tmpdir(), program=dotecho()).decode()
    assert "-Tpng" in text
    assert "-TPnG" not in text


def test_to_svg():
    """
    Method to_svg() should invoke the specified graphviz program to render the
    dot object as SVG.  If the program isn't found, it should raise an
    InvocationError.  If the program exits with a non-zero status, it should
    raise a ProcessException.  If a timeout is specified, and the program times
    out, it should raise a TimeoutException exception.  The dpi, size, and
    ratio arguments should be passed as -G options to the program.
    """
    dot = Dot().edge("a","b")

    svg = dot.to_svg()
    assert likely_full_svg(svg)

    #
    # Older versions of Graphviz do not support the -Tsvg_inline option.
    # Therefore, we accept either the correct line SVG result or a
    # ProcessException mentioning svg_inline.
    #

    try:
        svg = dot.to_svg(inline=True)
        assert likely_svg(svg) and not likely_full_svg(svg)
    except ProcessException as ex:
        assert "svg_inline" in ex.stderr

    svg = dot.to_svg("neato")
    assert likely_full_svg(svg)

    ex = expect_ex(InvocationException, lambda: dot.to_svg("doesnotexist"))
    assert "doesnotexist" in str(ex)
    assert ex.program == "doesnotexist"

    path = shutil.which('dot')

    if path is None:
        raise RuntimeError("Could not find path to dot program")

    pathdir = os.path.dirname(path)

    svg = dot.to_svg(program="dot",directory=pathdir)
    assert likely_full_svg(svg)

    ex = expect_ex(TimeoutException,lambda: dot.to_svg(
        directory=tmpdir(), program=dotsleep(), timeout=0.01))

    assert ex.program.endswith(dotsleep())
    assert ex.timeout == 0.01
    assert type(ex.stderr) is str

    ex = expect_ex(ProcessException,lambda: dot.to_svg(
        directory=tmpdir(), program=doterror()))

    assert ex.program.endswith(doterror())
    assert ex.status == 1 and "ErrorText" in ex.stderr
    assert type(ex.stderr) is str

    # Returned string is the echoed command line
    svg = dot.to_svg(
        dpi=30, ratio=20, size="1,1",
        directory=tmpdir(), program=dotecho())

    assert "-Gdpi=30" in svg
    assert "-Gratio=20" in svg
    assert "-Gsize=1,1" in svg


def test_save():
    """
    Method save() should invoke the specified graphviz program to save the dot
    object as bytes.  It should infer the format from the file extension if not
    given, if given the format should take precedence over the extension.  If
    the program isn't found, it should raise an InvocationError.  If the
    program exits with a non-zero status, it should raise a ProcessException.
    If a timeout is specified, and the program times out, it should raise a
    TimeoutException exception.
    """
    dir = tmpdir()

    test_png = f"{dir}/test.png"
    test_jpg = f"{dir}/test.jpg"

    dot = Dot().edge("a","b").graph(label="Title")

    dot.save(test_png)
    assert image_file_format(test_png) == 'PNG'
    png_len = os.path.getsize(test_png)

    dot.save(test_jpg)
    assert image_file_format(test_jpg) == 'JPEG'

    dot.save(test_png, format='jpg')
    assert image_file_format(test_png) == 'JPEG'

    expect_ex(ValueError, lambda: dot.save(f"{dir}/test.unknown"))
    expect_ex(ValueError, lambda: dot.save(f"{dir}/test"))
    expect_ex(FileExistsError, lambda: dot.save(test_png,exclusive=True))

    dot.save(test_png,"neato")
    assert image_file_format(test_png) == 'PNG'

    ex = expect_ex(InvocationException, lambda:
                   dot.save(test_png,"doesnotexist"))
    assert "doesnotexist" in str(ex)
    assert ex.program == "doesnotexist"

    path = shutil.which('dot')

    if path is None:
        raise RuntimeError("Could not find path to dot program")

    pathdir = os.path.dirname(path)

    dot.save(test_png, program="dot", directory=pathdir)
    assert image_file_format(test_png) == 'PNG'

    ex = expect_ex(TimeoutException,lambda: dot.save(test_png,
        directory=tmpdir(), program=dotsleep(), timeout=0.01))

    assert ex.program.endswith(dotsleep())
    assert ex.timeout == 0.01
    assert type(ex.stderr) is str

    ex = expect_ex(ProcessException,lambda: dot.save(test_png,
        directory=tmpdir(), program=doterror()))

    assert ex.program.endswith(doterror())
    assert ex.status == 1 and "ErrorText" in ex.stderr
    assert type(ex.stderr) is str

    # Written data is the echoed command line
    dot.save(test_png,
        dpi=30, ratio=20, size="1,1",
        directory=tmpdir(), program=dotecho())

    with open(test_png, "rb") as f:
        data = f.read().decode()
        assert "-Gdpi=30" in data
        assert "-Gratio=20" in data
        assert "-Gsize=1,1" in data


def test_inferred_formats():
    """
    Make sure all inferred save formats are supported.
    """
    dot = Dot().node("Yes")
    dir = tmpdir()
    for extension in ('svg','png','jpg','jpeg','gif','pdf'):
        dot.save(f"{dir}/supported.{extension}")


def test_inferred_case_insensitive():
    """
    save() should infer format from file extension by case-insensitive
    comparison.
    """
    dot = Dot().edge("a", "b")
    svg_file = f"{tmpdir()}/casecheck.SvG"
    jpg_file = f"{tmpdir()}/casecheck.JPeG"

    dot.save(svg_file, directory=tmpdir(), program=dotecho())
    dot.save(jpg_file, directory=tmpdir(), program=dotecho())

    with open(svg_file, "rb") as f:
        text = f.read().decode()
        assert "-Tsvg" in text

    with open(jpg_file, "rb") as f:
        text = f.read().decode()
        assert "-Tjpeg" in text
