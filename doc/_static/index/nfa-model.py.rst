.. code-block:: python

    @dataclass
    class NFA:
        alphabet : str
        delta    : dict[str, list[list[str]]]
        final    : list[str]
        start    : str
