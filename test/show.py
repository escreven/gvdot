import re
from typing import Any
from gvdot import Dot, ShowException
import gvdot
from utility import doterror, dotsleep, expect_ex, image_format
from utility import likely_full_svg, tmpdir


class _MockIPython:

    displayed : list[tuple[str,Any]]

    def __init__(self):
        self.displayed = []

    def take(self):
        result = self.displayed
        self.displayed = []
        return result

    def display(self, content:tuple[str,Any]):
        assert type(content) is tuple
        self.displayed.append(content)

    def Markdown(self, data:str):
        assert type(data) is str
        return "Markdown", data

    def SVG(self, data:str|bytes):
        if type(data) is bytes:
            data = data.decode()
        return "SVG", data

    def Image(self, data:bytes):
        assert type(data) is bytes
        return "Image", data

    def Code(self, data:bytes, language:str):
        assert type(data) is str
        assert language == "graphviz"
        return "Code", data

    def __enter__(self):
        self.old_display = gvdot.display
        self.old_Markdown = gvdot.Markdown
        self.old_SVG = gvdot.SVG
        self.old_Image = gvdot.Image
        self.old_Code = gvdot.Code
        gvdot.display = self.display
        gvdot.Markdown = self.Markdown
        gvdot.SVG = self.SVG
        gvdot.Image = self.Image
        gvdot.Code = self.Code
        return self

    def __exit__(self, exc_type, exc, tb):
        gvdot.display = self.old_display
        gvdot.Markdown = self.old_Markdown
        gvdot.SVG = self.old_SVG
        gvdot.Image = self.old_Image
        gvdot.Code = self.old_Code
        return False


class _NoIPython:

    def __enter__(self):
        self.old_display = gvdot.display
        self.old_Markdown = gvdot.Markdown
        self.old_SVG = gvdot.SVG
        self.old_Image = gvdot.Image
        self.old_Code = gvdot.Code
        gvdot.display = None
        gvdot.Markdown = None
        gvdot.SVG = None
        gvdot.Image = None
        gvdot.Code = None
        return self

    def __exit__(self, exc_type, exc, tb):
        gvdot.display = self.old_display
        gvdot.Markdown = self.old_Markdown
        gvdot.SVG = self.old_SVG
        gvdot.Image = self.old_Image
        gvdot.Code = self.old_Code
        return False


def test_show():
    """
    When IPython is installed, method show() should display Markdown, SVG, and
    Image objects.  It should pass through program names and timeouts to the
    underlying to_svg() and to_rendered() methods.  It should set the size
    graph attribute through the command line if requested.

    When IPython is not installed, method show() should raise an explanatory
    exception.
    """
    with _MockIPython() as mock:

        #
        # We want a tall graph for the size= check at the end.
        #
        dot = Dot().graph(fontsize=32)
        dot.edge("a","b").edge("b","c").edge("c","d")

        dot.show_source()
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "Code"
        assert "graph" in displayed[0][1]

        dot.show(format="svG")
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "SVG"
        assert likely_full_svg(displayed[0][1])

        dot.show(format="png")
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "Image"
        assert image_format(displayed[0][1]) == "PNG"

        ex = expect_ex(ShowException, lambda: dot.show(
            program="doesnotexist", format="svg"))
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "Markdown"
        assert "could not be invoked" in displayed[0][1]
        assert "could not complete" in str(ex)

        expect_ex(ShowException, lambda: dot.show(
            program="doesnotexist", format="png"))
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "Markdown"
        assert "could not be invoked" in displayed[0][1]

        expect_ex(ShowException,lambda: dot.show(
            format="svg", directory=tmpdir(),
            program=dotsleep(), timeout=0.01))
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "Markdown"
        assert "timed out" in displayed[0][1]

        expect_ex(ShowException,lambda: dot.show(
            format="png", directory=tmpdir(),
            program=dotsleep(), timeout=0.01))
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "Markdown"
        assert "timed out" in displayed[0][1]

        expect_ex(ShowException,lambda: dot.show(
            format="svg", directory=tmpdir(),
            program=doterror()))
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "Markdown"
        assert "exited with status" in displayed[0][1]

        expect_ex(ShowException,lambda: dot.show(
            format="png", directory=tmpdir(),
            program=doterror()))
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "Markdown"
        assert "exited with status" in displayed[0][1]

        expect_ex(RuntimeError, lambda: Dot().subgraph().show())
        expect_ex(RuntimeError, lambda: Dot().subgraph().show_source())

        dot.show(format="SVG", size="1, 1")
        displayed = mock.take()
        assert len(displayed) == 1
        assert displayed[0][0] == "SVG"
        assert 'height="72pt"' in displayed[0][1]

    with _NoIPython():
        try:
            Dot().show()
            assert False
        except RuntimeError as ex:
            assert re.search("IPython.*install", str(ex))
        try:
            Dot().show_source()
            assert False
        except RuntimeError as ex:
            assert re.search("IPython.*install", str(ex))
