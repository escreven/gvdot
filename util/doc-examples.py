from pathlib import PurePath
from gvdot import Dot, Markup, Port

#
# We expect to be in project/util/doc-examples.py.  Return the path to
# directory project/doc/_static.
#

def _get_static_dir():
    return PurePath(__file__).parent.parent.joinpath("doc","_static")

#
# Generate doc examples.
#

def generate_rollback(static_dir:PurePath):

    dot = Dot(directed=True)
    dot.graph(rankdir="LR", labelloc="t", label="Rolling Back")
    dot.node("old", color="green", label=Markup("d<sub>k</sub>"))
    dot.node("new", color="red", label=Markup("d<sub>k+1</sub>"))
    dot.edge("old", "new", label="apply")
    dot.edge(Port("new",cp="s"), Port("old",cp="s"), label="undo")

    print("DOT for rollback:")
    print()
    print(dot)
    print()

    with open(static_dir / "rollback.svg", "w") as f:
        print(dot.to_svg(), file=f)


def generate_change_mind(static_dir:PurePath):

    dot = Dot(directed=True)
    dot.graph(rankdir="LR")
    dot.all_default(color="limegreen")
    dot.edge("a", "b", color="blue", style="dashed")

    with open(static_dir / "change-mind-1.svg", "w") as f:
        print(dot.to_svg(), file=f)

    # That edge looks terrible.  Let's just use the default.
    dot.edge("a", "b", color=None)
    with open(static_dir / "change-mind-2.svg", "w") as f:
        print(dot.to_svg(), file=f)


def generate_tasks(static_dir:PurePath):

    dot = Dot(directed=True)



if __name__ == "__main__":
    static_dir = _get_static_dir()
    generate_rollback(static_dir)
    generate_change_mind(static_dir)
