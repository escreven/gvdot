from argparse import ArgumentParser
from collections import defaultdict
from dataclasses import dataclass
import nbformat
from pathlib import Path
import re
from types import FunctionType
from typing import Any
from gvdot import Dot, Markup, Port, Nonce
from artifacts import Artifact, Image, PythonCode, DotCode, save_artifacts


#
# pyright: reportInvalidTypeForm=false
#
# Needed because sometimes we create classes nested functions and return them
# as values, then use them in example code as types.
#

# ============================================================================
#                            INDEX.RST ARTIFACTS
# ============================================================================

def nfa_example() -> list[Artifact]:

    def model():
        @dataclass
        class NFA:
            alphabet : str
            delta    : dict[str, list[list[str]]]
            final    : list[str]
            start    : str
        return NFA

    NFA = model()

    def theme():
         nfa_theme = (Dot()
            .all_default(fontsize=12)
            .node_default(shape="circle", style="filled", fillcolor="khaki")
            .node_role("init", label="", shape="none", width=0, height=0)
            .node_role("final", shape="doublecircle", penwidth=1.25)
            .graph(rankdir="LR", labelloc="t", fontsize=16))
         return nfa_theme

    nfa_theme = theme()

    def diagram():
        def nfa_diagram(nfa:NFA, title:str):

            dot = Dot(directed=True).use_theme(nfa_theme)
            dot.graph(label=Markup(f"<b>{title}</b>"))

            init_id = Nonce()
            dot.node(init_id, role="init")
            dot.edge(init_id, nfa.start)

            for state in nfa.final:
                dot.node(state, role="final")

            for state, transitions in nfa.delta.items():
                merged = defaultdict(list)
                for index, targets in enumerate(transitions):
                    for target in targets:
                        merged[target].append(
                            nfa.alphabet[index-1] if index > 0 else '&epsilon;')
                for target, symbols in merged.items():
                    dot.edge(state, target, label=", ".join(symbols))

            return dot
        return nfa_diagram

    nfa_diagram = diagram()

    def generate():
        example = NFA("01", {
            "s0": [["q0", "r0"], [], []],
            "q0": [[], ["q1"], ["q0"]],
            "q1": [[], ["q1"], ["q2"]],
            "q2": [[], ["q3"], ["q0"]],
            "q3": [[], ["q1"], ["q4"]],
            "q4": [[], ["q4"], ["q4"]],
            "r0": [[], ["r0"], ["r1"]],
            "r1": [[], ["r0"], ["r2"]],
            "r2": [[], ["r3"], ["r1"]],
            "r3": [[], ["r3"], ["r3"]],
        }, ["q4","r0","r1","r2"], "s0")

        #+ nfa_diagram(example,"Example NFA").save("example.svg")

        return example

    example = generate()

    dot = nfa_diagram(example,"Example NFA")

    result = [
        Image("index/nfa", dot),
        PythonCode("index/nfa-model", model),
        PythonCode("index/nfa-theme", theme),
        PythonCode("index/nfa-diagram", diagram),
        PythonCode("index/nfa-generate", generate),
    ]

    #
    # What follows is init -> start fragment that appears in the overview.
    #

    fragment_theme = (Dot().use_theme(nfa_theme)
    .node_role("...", label="...", style="", shape="plaintext",
               margin=0.03, width=0))

    nonce = Nonce()
    dot = Dot(directed=True).use_theme(fragment_theme)
    dot.node(nonce,role="init")
    dot.node("s0")
    dot.node("r0",role="...")
    dot.node("q0",role="...")
    dot.edge(nonce,"s0")
    dot.edge("s0","r0")
    dot.edge("s0","q0")

    result.append(Image("discussion/nfa-init",dot))

    return result


# ============================================================================
#                          DISCUSSION.RST ARTIFACTS
# ============================================================================


def rollback_example() -> list[Artifact]:

    def code():
        dot = Dot(directed=True)
        dot.graph(rankdir="LR", labelloc="t", label="Rolling Back")
        dot.node("old", color="green", label=Markup("d<sub>k</sub>"))
        dot.node("new", color="red", label=Markup("d<sub>k+1</sub>"))
        dot.edge("old", "new", label="apply")
        dot.edge(Port("new",cp="s"), Port("old",cp="s"), label="undo")
        #+ print(dot)
        return dot

    return [
        PythonCode("discussion/rollback", code),
        DotCode("discussion/rollback", dot := code()),
        Image("discussion/rollback", dot),
    ]


def attrs_example() -> list[Artifact]:

    def code():
        dot = Dot(directed=True)
        dot.graph_default(bgcolor="antiquewhite")
        dot.node_default(shape="circle")
        dot.edge_default(style="dashed")
        dot.graph_role("focus", bgcolor="bisque4")
        dot.node_role("important", style="filled", fillcolor="khaki")
        dot.edge_role("important", color="red")
        dot.graph(rankdir="LR", label="Many ways to set attributes")
        dot.node("a", label="A")
        dot.node("b", label="B", fontcolor="green")
        dot.edge("a","b")
        dot.edge("b","c",role="important")
        cluster = dot.subgraph("cluster_1")
        cluster.graph_default(fontsize=12, fontname="sans-serif")
        cluster.node_default(shape="box")
        cluster.edge_default(arrowhead="diamond")
        cluster.graph(labelloc="t", label="Clustered", role="focus")
        cluster.node("c",role="important", label="C")
        cluster.edge("c","last")
        return dot

    return [
        PythonCode("discussion/attrs", code),
        DotCode("discussion/attrs", dot := code()),
        Image("discussion/attrs", dot),
    ]


def change_mind_example() -> list[Artifact]:

    dot1 : Dot

    def code():
        nonlocal dot1 #-
        dot = Dot(directed=True)
        dot.graph(rankdir="LR")
        dot.all_default(color="limegreen")
        dot.edge("a", "b", color="blue", style="dashed")
        #+ dot.show()
        dot1 = dot.copy() #-

        # That edge looks terrible.  Let's just use the default.
        dot.edge("a", "b", color=None)
        #+ dot.show()
        return dot

    dot2 = code()
    assert dot1  #type:ignore

    return [
        PythonCode("discussion/change-mind",code),
        Image("discussion/change-mind-1", dot1),
        Image("discussion/change-mind-2", dot2),
    ]


#
# Generates artifacts used in both Roles and Themes.
#

def project_example() -> list[Artifact]:

    def model():
        @dataclass
        class Task:
            id       : str
            name     : str
            requires : tuple[str, ...] = ()
            status   : str = "normal"

        @dataclass
        class Project:
            tasks: dict[str,Task]
            def __init__(self, tasklist:list[Task]):
                self.tasks = { task.id: task for task in tasklist }

        return Task, Project

    Task, Project = model()

    example = Project([
        Task("T3", "Build dev env", ()),
        Task("T4", "Implement core", ("T3",)),
        Task("T5", "Implement UI", ("T3",), 'atrisk'),
        Task("T6", "Write system tests", ("T4",)),
        Task("T7", "Integrate", ("T4", "T5"), 'atrisk'),
        Task("T8", "Run system tests", ("T6", "T7"), 'critical'),
    ])

    #
    # Use in Roles section.
    #

    def roles_code():
        def task_diagram(project:Project):
            dot = Dot(directed=True)
            dot.node_default(shape="box", margin=0.1, style="filled",
                             fontsize=10, fontname="sans-serif",
                             width=0, height=0)
            dot.node_role("normal", color="#10a010")
            dot.node_role("atrisk", color="#ffbf00")
            dot.node_role("critical", color="#c00000", fontcolor="#e8e8e8")
            for id, task in project.tasks.items():
                dot.node(id, label=task.name,
                        role=task.status)
                for other in task.requires:
                    dot.edge(other, id)
            return dot
        return task_diagram(example)

    artifacts = [
        PythonCode("discussion/project-model", model),
        PythonCode("discussion/project-roles-code", roles_code),
        Image(     "discussion/project-roles-image", roles_code()),
    ]

    #
    # Use in Themes section.
    #

    def theme1():
        project_theme = (Dot()
            .node_default(shape="box", margin=0.1, style="filled",
                          fontsize=10, fontname="sans-serif",
                          width=0, height=0)
            .node_role("normal", color="#10a010")
            .node_role("atrisk", color="#ffbf00")
            .node_role("critical", color="#c00000", fontcolor="#e8e8e8"))
        return project_theme

    project_theme = theme1()

    def themes_code1():
        def task_diagram(project:Project, theme:Dot=project_theme):
            dot = Dot(directed=True).use_theme(theme)
            for id, task in project.tasks.items():
                dot.node(id, label=task.name,
                         role=task.status)
                for other in task.requires:
                    dot.edge(other, id)
            return dot
        return task_diagram

    task_diagram = themes_code1()

    dot1 = task_diagram(example)

    def theme2():
        compact_project_theme = (Dot()
            .use_theme(project_theme)
            .graph(rankdir="LR", ranksep=0.25)
            .node_default(margin=0.05)
            .edge_default(arrowsize=0.75))
        return compact_project_theme

    compact_project_theme = theme2()

    def themes_code2():
        #+ task_diagram(example, compact_project_theme).show()
        return task_diagram(example, compact_project_theme)

    dot2 = themes_code2()

    artifacts.extend([
        PythonCode("discussion/project-themes-theme1", theme1),
        PythonCode("discussion/project-themes-code1", themes_code1),
        Image(     "discussion/project-themes-image1", dot1),
        PythonCode("discussion/project-themes-theme2", theme2),
        PythonCode("discussion/project-themes-code2", themes_code2),
        Image(     "discussion/project-themes-image2", dot2),
    ])

    return artifacts


def multigraph_example() -> list[Artifact]:

    def code1():
        dot = Dot().graph(rankdir="LR")
        dot.edge("a", "b", color="red", label="first")
        dot.edge("a", "b", color="green", label="second")
        dot.edge("a", "b", color="blue", label="third")
        return dot

    def code2():
        dot = Dot(multigraph=True).graph(rankdir="LR")
        dot.edge("a", "b", color="red", label="first")
        dot.edge("a", "b", color="green", label="second")
        dot.edge("a", "b", color="blue", label="third")
        return dot

    def code3():
        dot = Dot(multigraph=True).graph(rankdir="LR")
        dot.edge("a", "b", 1, color="red", label="first")
        dot.edge("a", "b", 2, color="green", label="second")
        dot.edge("a", "b", 3, color="blue", label="third")

        # Amend the green edge
        dot.edge("a", "b", 2, style="dashed")
        return dot

    return [
        PythonCode("discussion/multigraph-stage1", code1),
        PythonCode("discussion/multigraph-stage2", code2),
        PythonCode("discussion/multigraph-stage3", code3),
        DotCode(   "discussion/multigraph-stage1", code1()),
        DotCode(   "discussion/multigraph-stage2", code2()),
        DotCode(   "discussion/multigraph-stage3", code3()),
        Image(     "discussion/multigraph-stage1", code1()),
        Image(     "discussion/multigraph-stage2", code2()),
        Image(     "discussion/multigraph-stage3", code3()),
    ]


# ============================================================================
#                                QUICK TOUR
# ============================================================================

def _example_cell_code(cell:dict[str,Any]) -> str|None:
    if not cell['cell_type'] == 'code':
        return None
    source:str = cell['source']
    if "dot = Dot(" not in source:
        return None
    lines = source.splitlines()
    while lines and lines[-1].strip() in (
            "dot.show()", "dot.show_source()", ""):
        lines.pop()
    return "\n".join(lines)

def _example_section_tag(cell:dict[str,Any]) -> str|None:
    if not cell['cell_type'] == 'markdown':
        return None
    source:str = cell['source']
    match = re.match(r"##\s+([a-zA-Z0-9 ]+)$", source, re.MULTILINE)
    if not match:
        return None
    section = match[1]
    return section.lower().replace(' ','-')

def quicktour_example() -> list[Artifact]:

    artifacts = []

    #
    # Read the Quick Tour notebook
    #

    path  = Path(__file__).parent.parent.joinpath("examples")
    nb    = nbformat.read(path / "quicktour.ipynb",4)
    cells = nb.cells

    section_tag = None
    section_use = 0

    for cell in cells:

        if (tag := _example_section_tag(cell)) is not None:
            section_tag = tag
            section_use = 0
            continue

        if not (source := _example_cell_code(cell)):
            continue

        if section_tag is None:
            raise RuntimeError("Section tag is None")

        section_use += 1

        env = dict(Dot=Dot, Markup=Markup, Port=Port, Nonce=Nonce)
        exec(source,env)
        dot = env['dot']
        assert isinstance(dot,Dot)

        name = f"quicktour/{section_tag}"

        if section_use > 1:
            name += f"_{section_use}"

        artifacts.extend([
            PythonCode(name,source),
            DotCode(name,dot),
            Image(name,dot)
        ])

    return artifacts


# ============================================================================
#                                  MAIN
# ============================================================================

def _main():

    parser = ArgumentParser(
        description="Generate code snippets and images for documentation.")

    parser.add_argument("pattern", nargs="?", default=None,
        help="Only generate artifacts for examples matching this pattern")

    args      = parser.parse_args()
    pattern   = args.pattern
    artifacts = []

    for name, value in globals().items():
        if (type(value) is FunctionType and
            getattr(value,'__module__',None) == '__main__' and
            (match := re.fullmatch(r"([a-z].*)_example", name))):
                example = match[1]
                if pattern is None or re.search(pattern,example):
                    print(f"Will generate artifacts for {example}")
                    artifacts.extend(value())

    if not artifacts:
        print("No examples matched pattern")
    else:
        save_artifacts(artifacts)

if __name__ == "__main__":

    _main()
