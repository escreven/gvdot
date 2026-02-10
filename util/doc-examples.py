from abc import abstractmethod
from argparse import ArgumentParser
from collections import defaultdict
from dataclasses import dataclass
import inspect
from pathlib import PurePath
import re
import sys
import textwrap
from types import FunctionType
from gvdot import Dot, Markup, Port

#
# pyright: reportInvalidTypeForm=false
#
# Needed because sometimes we create classes nested functions and return them
# as values, then use them in example code as types.
#

#
# Generate a rst code block string for the given text in the specified
# language.  The input lines are dedented, and any blank lines at the beginning
# or end are deleted.
#
# If language is "python", lines that look like
#
#   <whitespace>#+<anything>
#
# are included as
#
#   <whitespace><anything>
#
# and lines that end with #-<whitespace> as well as a last line like
# <whitespace>return<anything> are excluded.
#

def _code_block(language:str, text:str):

    text  = textwrap.dedent(text)
    lines = text.splitlines()

    while lines and re.fullmatch(r"\s*", lines[0]):
        del lines[0]

    while lines and re.fullmatch(r"\s*", lines[-1]):
        del lines[-1]

    if language == 'python':
        if lines and re.fullmatch(r"\s*return.*",lines[-1]):
            del lines[-1]
        transformed = []
        for line in lines:
            if match := re.fullmatch(r"(\s*)#\+\s*(.*)", line):
                transformed.append(match[1] + match[2])
            elif not re.fullmatch(r".*#-\s*", line):
                transformed.append(line)
        lines = transformed

    assert lines

    return f".. code-block:: {language}\n\n" + "".join(
        "    " + line + "\n" for line in lines)


#
# Examples can have images, python source code, and dot source code, all of
# which is optional.  _save_examples() generates these artifacts and stores
# them in doc/_static.
#
# NOTE: This module must be in directory util/ relative to repo root.
#

@dataclass
class _Artifact:
    name : str

    @abstractmethod
    def save(self, dir:PurePath):
        ...

@dataclass
class _Image(_Artifact):
    dot : Dot

    def save(self, dir:PurePath):
        name = self.name
        dot = self.dot
        dot.save(dir / f"_static/{name}.svg")
        dot.save(dir / f"_static/{name}.png", dpi=300)

@dataclass
class _DotCode(_Artifact):
    dot : Dot

    def save(self, dir:PurePath):
        with open(dir / f"_code/{self.name}.dot.rst", "w") as f:
            print(_code_block("graphviz",str(self.dot)), file=f, end="")

@dataclass
class _PythonCode(_Artifact):
    code : FunctionType

    def save(self, dir:PurePath):

        source = inspect.getsource(self.code)

        match = re.fullmatch(r"[ \t]*def [^\n]*\):[^\n]*\n(.*)",
                             source, re.DOTALL)

        if not match:
            print(f"Unexpected source for {self.code}")
            sys.exit(1)

        with open(dir / f"_code/{self.name}.py.rst", "w") as f:
            print(_code_block("python",match[1]), file=f, end="")


def _save_artifacts(artifacts:list[_Artifact]):

    dir = PurePath(__file__).parent.parent.joinpath("doc")

    for artifact in artifacts:
        artifact.save(dir)


# ============================================================================
#                            INDEX.RST ARTIFACTS
# ============================================================================

def nfa_example() -> list[_Artifact]:

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
            dot.graph(label=Markup(f"<b>{title}<br/></b>"))

            dot.node("_init_", role="init")
            dot.edge("_init_", nfa.start)

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

    return [
        _Image("index/nfa", dot),
        _PythonCode("index/nfa-model", model),
        _PythonCode("index/nfa-theme", theme),
        _PythonCode("index/nfa-diagram", diagram),
        _PythonCode("index/nfa-generate", generate),
    ]


# ============================================================================
#                          OVERVIEW.RST ARTIFACTS
# ============================================================================


def rollback_example() -> list[_Artifact]:

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
        _PythonCode("overview/rollback", code),
        _DotCode("overview/rollback", dot := code()),
        _Image("overview/rollback", dot),
    ]


def attrs_example() -> list[_Artifact]:

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
        subdot = dot.subgraph("cluster_1")
        subdot.graph_default(fontsize=12, fontname="sans-serif")
        subdot.node_default(shape="box")
        subdot.edge_default(arrowhead="diamond")
        subdot.graph(labelloc="t", label="Clustered", role="focus")
        subdot.node("c",role="important", label="C")
        subdot.edge("c","last")
        return dot

    return [
        _PythonCode("overview/attrs", code),
        _DotCode("overview/attrs", dot := code()),
        _Image("overview/attrs", dot),
    ]


def change_mind_example() -> list[_Artifact]:

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
        _PythonCode("overview/change-mind",code),
        _Image("overview/change-mind-1", dot1),
        _Image("overview/change-mind-2", dot2),
    ]


#
# Generates artifacts used in both Roles and Themes.
#

def project_example() -> list[_Artifact]:

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
        _PythonCode("overview/project-model", model),
        _PythonCode("overview/project-roles-code", roles_code),
        _Image(     "overview/project-roles-image", roles_code()),
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
        _PythonCode("overview/project-themes-theme1", theme1),
        _PythonCode("overview/project-themes-code1", themes_code1),
        _Image(     "overview/project-themes-image1", dot1),
        _PythonCode("overview/project-themes-theme2", theme2),
        _PythonCode("overview/project-themes-code2", themes_code2),
        _Image(     "overview/project-themes-image2", dot2),
    ])

    return artifacts


def multigraph_example() -> list[_Artifact]:

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
        _PythonCode("overview/multigraph-stage1", code1),
        _PythonCode("overview/multigraph-stage2", code2),
        _PythonCode("overview/multigraph-stage3", code3),
        _DotCode(   "overview/multigraph-stage1", code1()),
        _DotCode(   "overview/multigraph-stage2", code2()),
        _DotCode(   "overview/multigraph-stage3", code3()),
        _Image(     "overview/multigraph-stage1", code1()),
        _Image(     "overview/multigraph-stage2", code2()),
        _Image(     "overview/multigraph-stage3", code3()),
    ]


# ============================================================================
#                                  MAIN
# ============================================================================

def _main():

    parser = ArgumentParser(
        description="Generate example code and images for documentation.")

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
        _save_artifacts(artifacts)

if __name__ == "__main__":

    _main()
#
#    artifacts = [
#        *nfa_example(),
#        *rollback_example(),
#        *change_mind_example(),
#        *project_example(),
#        *attrs_example(),
#    ]
#
#    _save_artifacts(artifacts)
