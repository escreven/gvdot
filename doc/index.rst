.. currentmodule:: gvdot

gvdot
=====

Package gvdot makes it easy to generate and render Graphviz diagrams with
clear, maintainable code by separating presentation from structure.

The heart of gvdot is class :class:`Dot`, a DOT language builder.  Applications
create diagrams using :class:`Dot` methods, then either convert the instance to
DOT language text or render it as SVG or an image.  Users can also
interactively display Dot objects in notebooks.

.. _landing-page-example:

Example
~~~~~~~

Suppose we want to generate diagrams of nondeterministic finite automata
like this:

.. image:: _static/index/nfa.*
    :align: center
    :width: 90%
    :alt: Example NFA diagram

represented by instances of

.. include:: _code/index/nfa-model.py.rst

where ``delta["q"][0]`` is the list of states reached from state :math:`q` by
epsilon transitions, and ``delta["q"][i]`` is the list of states reached from
:math:`q` by symbol ``alphabet[i-1]``.

We start by defining a theme, a normal :class:`Dot` object from which other dot
objects can inherit graph attributes, default attributes, and roles.

.. include:: _code/index/nfa-theme.py.rst

The theme defines two gvdot roles, collections of Graphviz attribute values
that applications can assign to diagram elements by name.

Having isolated presentation attributes in a theme, our generation code is
straightforward.

.. include:: _code/index/nfa-diagram.py.rst

We can render and save the diagram above with

.. include:: _code/index/nfa-generate.py.rst

In a notebook, we can directly display the diagram from a cell containing

.. code:: python

    nfa_diagram(example,"Example NFA").show()


.. toctree::
    :maxdepth: 2
    :hidden:
    :caption: Contents:

    quicktour
    discussion
    reference
    examples
    installation
    resources
