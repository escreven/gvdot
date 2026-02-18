.. currentmodule:: gvdot

.. _reference-doc:

Reference
=========

Dot and Block
-------------

.. autoclass:: Dot
    :show-inheritance:

.. autoclass:: Block

.. container:: custom-box

    **NOTE**: The methods of :class:`Dot` and :class:`Block` described below
    are organized by category, not by class.  Keep in mind that each
    :class:`Block` method is also a method of :class:`Dot`.


Theme Methods
~~~~~~~~~~~~~

.. automethod:: Dot.use_theme

Graph Methods
~~~~~~~~~~~~~

.. automethod:: Dot.graph_role
.. automethod:: Block.graph_default
.. automethod:: Block.graph

Node Methods
~~~~~~~~~~~~

.. automethod:: Dot.node_role
.. automethod:: Block.node_default
.. automethod:: Block.node
.. automethod:: Block.node_define
.. automethod:: Block.node_update
.. automethod:: Block.node_is_defined

Edge Methods
~~~~~~~~~~~~

.. automethod:: Dot.edge_role
.. automethod:: Block.edge_default
.. automethod:: Block.edge
.. automethod:: Block.edge_define
.. automethod:: Block.edge_update
.. automethod:: Block.edge_is_defined

Subgraph Methods
~~~~~~~~~~~~~~~~

.. automethod:: Block.subgraph
.. automethod:: Block.subgraph_define
.. automethod:: Block.subgraph_update

Render Methods
~~~~~~~~~~~~~~

.. automethod:: Dot.__str__
.. automethod:: Dot.to_rendered
.. automethod:: Dot.to_svg
.. automethod:: Dot.save
.. automethod:: Dot.show
.. automethod:: Dot.show_source


Other Methods
~~~~~~~~~~~~~

.. automethod:: Dot.is_multigraph
.. automethod:: Dot.copy
.. automethod:: Dot.all_role
.. automethod:: Block.all_default
.. automethod:: Block.parent
.. automethod:: Block.dot


Supporting Types
----------------

.. autotype:: ID
.. autoclass:: Markup
.. autoclass:: Nonce
.. autoclass:: Port


Exceptions
----------

.. autoexception:: InvocationException
    :members:

.. autoexception:: ProcessException
    :members:

.. autoexception:: TimeoutException
    :members:

.. autoexception:: ShowException
    :members:

