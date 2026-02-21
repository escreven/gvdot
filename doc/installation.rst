.. currentmodule:: gvdot

Installation
------------

You can install gvdot from PyPI with

.. code:: console

    $ pip install gvdot

To ensure the optional notebook support is enabled, use

.. code:: console

    $ pip install gvdot[ipython]

You can also clone the repo and install it directly.

.. code:: console

    $ git clone https://github.com/escreven/gvdot.git
    $ cd gvdot
    $ pip install .


Package gvdot requires Python 3.12 or greater.

`Rendering <https://gvdot.readthedocs.io/en/latest/discussion.html#rendering>`_
requires a Graphviz installation.  You can determine if one is in your ``PATH``
with

.. code:: console

    $ dot -V

To install Graphviz, see `<https://graphviz.org/download>`_.

