.. currentmodule:: gvdot


.. |br| raw:: html

   <br />


Examples
========

.. grid:: 2
    :gutter: 3
    :class-container: examples-toc

    .. grid-item-card:: Entity Relationship Diagram
        :link: er-diagram
        :link-type: doc
        :class-title: sd-text-center sd-mb-3

        .. image:: _static/examples/er-generated-color.svg
            :align: center
            :class: sd-mb-3

        Reproduces the Chen-style entity relationship diagram from the Graphviz
        documentation, showing how to use themes and roles to separate
        presentation from structure.

    .. grid-item-card:: Red-Black Trees
        :link: rb-trees
        :link-type: doc
        :class-title: sd-text-center sd-mb-3

        .. image:: _static/examples/rb-auto-18.svg
            :align: center
            :class: sd-mb-3

        Creates illustrations for students learning about red-black trees.  It
        uses nonces to identify phantom nodes inserted to create good layouts.

    .. grid-item-card:: SQLite Schema Diagrammer
        :link: sqlite-schema
        :link-type: doc
        :class-title: sd-text-center sd-mb-3
        :columns: 12

        .. image:: _static/examples/sqlite-schema.svg
            :align: center
            :class: sd-mb-3

        Depicts tables, columns, and foreign keys loaded from a SQLite database
        connection.  It uses ``gvdot.markup`` to create Graphviz HTML node
        labels and uses multiple edge roles to portray the varying
        characteristics of foreign keys.

.. toctree::
    :hidden:
    :maxdepth: 1

    er-diagram
    rb-trees
    sqlite-schema
