.. currentmodule:: gvdot.markup

.. |br| raw:: html

   <br />

.. _markup_module:

Building HTML
=============

Module ``gvdot.markup`` builds Graphviz HTML strings. The module includes a
:class:`~gvdot.Markup` subclass for every element of `Graphviz HTML
<https://graphviz.org/doc/info/shapes.html#html>`_, plus additional supporting
types.  Applications assemble trees of Markup subclass instances then either
convert them to strings or pass them directly to the gvdot API, typically as
label attribute values.

Through the types defined and runtime checks, ``gvdot.markup`` ensures that the
HTML strings produced comply with the Graphviz HTML grammar, and it properly
escapes attribute values and content text.  Content model types and element
specific keyword arguments of Markup subclass initializers enable IDE hinting.

The Graphviz documentation includes an example of using Graphviz HTML to depict
records.  Here is that example transcribed to gvdot with Markup subclasses:

.. include:: _code/markup/records.py.rst

That dot object renders as

.. image:: _static/markup/records.*
    :align: center
    :alt: Records example using Markup subclasses

|br|
(The space embedded in ``mid dle`` is per the Graphviz example.)

While the Graphviz HTML grammar requires container elements such as ``FONT``
and ``TABLE`` to have content, ``gvdot.markup`` is more relaxed.  A
:class:`Container` is empty if it has no non-empty children.  Empty containers
are allowed, and are elided from any Graphviz HTML string produced.  Void
elements such as ``BR`` are never empty.  :class:`Text` elements are empty if
and only if they contain no printable characters.  :class:`TD` is a special
case: empty :class:`TD` instances are allowed but not elided.  Despite the
documented grammar, Graphviz programs accept ``<TD></TD>`` cells and give them
a different appearance than non-empty cells.

Applications can avoid ``gvdot.markup`` validation and escaping by using class
:class:`Raw`.  Raw HTML text is incorporated as-is into strings produced from
Markup object trees, with no checks or transformations.

While Graphviz HTML strings constructed through ``gvdot.markup`` are lexically
and syntactically correct (assuming correct use of :class:`Raw`), it's still
possible to create strings that Graphviz programs do not accept.
``gvdot.markup`` lexically validates entities, but does not determine if a
specific entity value is supported by Graphviz.  ``gvdot.markup`` does not
validate attribute values.

If Graphviz HTML is new to you, be aware that it differs from real HTML in ways
other than just being a subset --- whitespace does not collapse and is
non-breaking, it has grammar-driven element content constraints, and attributes
of same-named elements are similar but not identical.


Base Classes
------------

.. autoclass:: Managed
    :show-inheritance:
    :members:

.. autoclass:: Container
    :show-inheritance:
    :members:

.. autoclass:: ContainerElement
    :show-inheritance:

.. autoclass:: VoidElement
    :show-inheritance:


.. _markup_subclasses:

Markup Subclasses
-----------------

Non-Element Markup
~~~~~~~~~~~~~~~~~~

Four Markup subclasses do not correspond to Graphviz HTML elements.

.. autoclass:: Text
    :show-inheritance:

    Because :class:`Text` objects are created for Python strings, they are
    properly escaped.

    .. include:: _code/markup/escape.py.rst

    The Dot object above is rendered as

    .. image:: _static/markup/escape.*
        :align: center
        :alt: Escaping sensitive characters

.. autoclass:: Entity
    :show-inheritance:

    which is rendered as

    .. image:: _static/markup/entity.*
        :align: center
        :alt: Directed graph with Greek node names and an emoji title

    See also :func:`with_entities`.

.. autoclass:: Span
    :show-inheritance:

.. autoclass:: Raw
    :show-inheritance:

Element Markup
~~~~~~~~~~~~~~

The remaining fifteen Markup subclasses correspond to Graphviz HTML elements.

.. list-table::
    :header-rows: 1
    :align: center

    * - Class
      - Element
      - Content
      - Alias

    * - :class:`Font`
      - ``FONT``
      - :type:`~gvdot.markup.TextOrTableContent`
      - ---

    * - :class:`Bold`
      - ``B``
      - :type:`~gvdot.markup.TextOrTableContent`
      - ``B``

    * - :class:`Italic`
      - ``I``
      - :type:`~gvdot.markup.TextOrTableContent`
      - ``I``

    * - :class:`Underline`
      - ``U``
      - :type:`~gvdot.markup.TextOrTableContent`
      - ``U``

    * - :class:`Overline`
      - ``O``
      - :type:`~gvdot.markup.TextOrTableContent`
      - ``O``

    * - :class:`Strike`
      - ``S``
      - :type:`~gvdot.markup.TextContent`
      - ``S``

    * - :class:`Sub`
      - ``SUB``
      - :type:`~gvdot.markup.TextContent`
      - ---

    * - :class:`Sup`
      - ``SUP``
      - :type:`~gvdot.markup.TextContent`
      - ---

    * - :class:`BR`
      - ``BR``
      - ---
      - ---

    * - :class:`Table`
      - ``TABLE``
      - :type:`~gvdot.markup.RowContent`
      - ---

    * - :class:`TR`
      - ``TR``
      - :type:`~gvdot.markup.CellContent`
      - ---

    * - :class:`TD`
      - ``TD``
      - :type:`~gvdot.markup.GeneralContent`
      - ---

    * - :class:`HR`
      - ``HR``
      - ---
      - ---

    * - :class:`VR`
      - ``VR``
      - ---
      - ---

    * - :class:`Img`
      - ``IMG``
      - ---
      - ---

The classes for single letter elements have descriptive names so they stand out
in code.  For those who prefer the single letter names, ``gvdot.markup``
includes single capital letter aliases so that one can write

    .. code-block:: python

        from gvdot.markup import I
        dot = Dot().graph(label=I("Emphasized"))

The element Markup subclasses are not documented individually.  Instead, see
`HTML-like Labels <https://graphviz.org/doc/info/shapes.html#html>`_, in the
Graphviz documentation.  The keyword arguments of each class initializer
correspond directly to the element attributes described there, except for
element attribute ``POINT-SIZE`` which has keyword ``point_size``.

Also see :class:`Container` for a description of the ``*content`` initializer
parameter, method :meth:`~Container.add()`, and the exceptions they may raise.

.. autoclass:: Font
    :show-inheritance:

.. autoclass:: Bold
    :show-inheritance:

.. autoclass:: Italic
    :show-inheritance:

.. autoclass:: Underline
    :show-inheritance:

.. autoclass:: Overline
    :show-inheritance:

.. autoclass:: Strike
    :show-inheritance:

.. autoclass:: Sub
    :show-inheritance:

.. autoclass:: Sup
    :show-inheritance:

.. autoclass:: BR
    :show-inheritance:

.. autoclass:: Table
    :show-inheritance:

.. autoclass:: TR
    :show-inheritance:

.. autoclass:: TD
    :show-inheritance:

.. autoclass:: HR
    :show-inheritance:

.. autoclass:: VR
    :show-inheritance:

.. autoclass:: Img
    :show-inheritance:


Supporting Types
----------------

.. _markup-content-types:

Content Types
~~~~~~~~~~~~~

Content types constrain the allowed content values for Markup subclasses based
on the Graphviz HTML grammar.  They are intended as an aid to coding in an IDE;
at runtime :class:`Managed` enforces the constraints implied by these types and
more.

.. autotype:: gvdot.markup.GeneralContent
.. autotype:: gvdot.markup.TextContent
.. autotype:: gvdot.markup.TextOrTableContent
.. autotype:: gvdot.markup.RowContent
.. autotype:: gvdot.markup.CellContent

Attribute Value Types
~~~~~~~~~~~~~~~~~~~~~

The types below are used for Markup subclass attributes that are choices.

.. autotype:: gvdot.markup.Align
.. autotype:: gvdot.markup.TDAlign
.. autotype:: gvdot.markup.VAlign
.. autotype:: gvdot.markup.ImageScale


Functions
---------

.. autofunction:: with_entities

    Compare a :class:`Text` label with a label created by
    :func:`with_entities`:

    .. include:: _code/markup/with-entities.py.rst

    The DOT language representation of the Dot object is

    .. include:: _code/markup/with-entities.dot.rst

    which is rendered as

    .. image:: _static/markup/with-entities.*
        :align: center
        :alt: Comparison of escaped text with converted character entities
