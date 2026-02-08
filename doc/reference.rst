.. currentmodule:: gvdot

.. _reference-doc:

Reference
=========

Class Dot
---------

.. autoclass:: Dot

.. automethod:: Dot.use_theme


Graph Methods
~~~~~~~~~~~~~

.. automethod:: Dot.graph_default

.. automethod:: Dot.graph_role

.. automethod:: Dot.graph

Node Methods
~~~~~~~~~~~~

.. automethod:: Dot.node_default

.. automethod:: Dot.node_role

.. automethod:: Dot.node

.. automethod:: Dot.node_define

.. automethod:: Dot.node_update

.. automethod:: Dot.node_is_defined

Edge Methods
~~~~~~~~~~~~

.. automethod:: Dot.edge_default

.. automethod:: Dot.edge_role

.. automethod:: Dot.edge

.. automethod:: Dot.edge_define

.. automethod:: Dot.edge_update

.. automethod:: Dot.edge_is_defined

Subgraph Methods
~~~~~~~~~~~~~~~~

.. automethod:: Dot.subgraph

.. automethod:: Dot.subgraph_define

.. automethod:: Dot.subgraph_update

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

.. automethod:: Dot.all_default

.. automethod:: Dot.all_role

.. automethod:: Dot.is_multigraph

.. automethod:: Dot.parent

.. automethod:: Dot.copy


Supporting Types
----------------

.. autotype:: ID

.. autoclass:: Markup

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

