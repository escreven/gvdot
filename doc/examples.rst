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

        Reproduces a Graphviz gallery entity relationship diagram, then shows
        how to use themes and roles to separate presentation from structure
        when generating diagrams from models.

    .. grid-item-card:: Red-Black Trees
        :link: rb-trees
        :link-type: doc
        :class-title: sd-text-center sd-mb-3

        .. image:: _static/examples/rb-auto-18.svg
            :align: center
            :class: sd-mb-3

        Creates illustrations for students learning about red-black trees.  The
        generator uses nonces to identify phantom nodes steering Graphviz
        toward better tree layouts.

    .. grid-item-card:: SQLite Schema Diagrammer
        :link: sqlite-schema
        :link-type: doc
        :class-title: sd-text-center sd-mb-3
        :columns: 12

        .. image:: _static/examples/sqlite-schema.svg
            :align: center
            :class: sd-mb-3

        Generates schema diagrams from SQLite databases. It uses
        ``gvdot.markup`` to build Graphviz HTML node labels depicting tables
        and their columns, and assigns multiple edge roles to portray the
        varying characteristics of foreign keys.

.. toctree::
    :hidden:
    :maxdepth: 1

    er-diagram
    rb-trees
    sqlite-schema
