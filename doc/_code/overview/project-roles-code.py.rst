.. code-block:: python

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
