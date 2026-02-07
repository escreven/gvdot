.. code-block:: python

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
    
