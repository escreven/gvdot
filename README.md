
Generate and render optionally themed GraphViz diagrams with simple, easy to
maintain code.

The heart of gvdot is class `Dot`, a DOT language graph expression.
Applications create diagrams using dot object methods, then either convert the
object to a DOT language string or render it as SVG or an image.  Users can
also interactively display dot objects in notebooks.

### Example

Suppose we want to generate diagrams of non-deterministic finite automata
like this

![Example
NFA](https://raw.githubusercontent.com/escreven/gvdot/main/readme-example.svg)

represented as instances of

```python
@dataclass
class NFA:
    alphabet : str
    delta    : dict[str, list[list[str]]]
    final    : list[str]
    start    : str
```

where `delta["q"][i]` is the list of states reached from $q$ by the
$i^\text{th}$ input alphabet symbol.

We start by defining a theme, a normal dot object from which other dot objects
can inherit graph attributes, default attributes, and roles.

```python
nfa_theme = (Dot()
    .all_default(fontsize=12)
    .node_default(shape="circle", style="filled", fillcolor="khaki")
    .node_role("init", label="", shape="none", width=0, height=0)
    .node_role("final", shape="doublecircle", penwidth=1.25)
    .graph(rankdir="LR", labelloc="t", fontsize=16))
```

A gvdot role is a collection Graphviz attribute values applications can assign
to diagram elements by name.

Having isolated presentation attributes in a theme, our generation code is
clean and easy to maintain.

```python
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
```

We can render and save the diagram above with

```python
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

with open("example.svg","w") as f:
    print(nfa_diagram(example,"Example NFA").to_svg(), file=f)
```

In a notebook, we can directly show the diagram from a cell containing

```python
nfa_diagram(example,"Example NFA").show()
```

You can find this [NFA
example](https://github.com/escreven/gvdot/blob/main/examples/nfa.ipynb) and
others in the [examples](https://github.com/escreven/gvdot/tree/main/examples)
directory.
