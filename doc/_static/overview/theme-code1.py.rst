.. code-block:: python

    def task_diagram(project:Project, theme:Dot=project_theme):
        dot = Dot(directed=True).use_theme(theme)
        for id, task in project.tasks.items():
            dot.node(id, label=task.name,
                    role=task.status)
            for other in task.requires:
                dot.edge(other, id)
        return dot
