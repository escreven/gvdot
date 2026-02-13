## Unreleased

#### Added
- Class `Dot` now has a base class `Block` which implements most of `Dot`'s DOT
  language building methods, but not role definition, theme assignment,
  rendering, or conversion to DOT language text.

#### Changed
- Methods `subgraph()` and `subgraph_define()` now return `Block` instances
  instead of `Dot` instances.  This change enforces through types what were
  previously runtime facts: the objects returned by `subgraph()` and
  `subgraph_define()` could not have themes assigned, and could not be usefully
  copied, rendered, or converted to DOT language text.

## [1.0.0] - 2026-02-11

#### Changed
- `save()` no longer infers the TIFF format from the filename.  Older versions
  of Graphviz (including the one currently installed by apt-get on Ubuntu) do
  not support TIFF.  Applications can still specify 'tiff' and any other format
  explicitly.

## [0.9.2] - 2026-02-09

#### Added
- `dpi`, `size`, and `ratio` are now arguments to all render methods.
- `ProcessException` and `TimeoutException` raised by render methods.  These
  exceptions are similar to the `subprocess` module `CalledProcessError` and
  `TimeoutExpired` exceptions but they guarantee the `stderr` text is a string.
- `ShowException` raised by `show()` as a catch-all sanitized exception.
- Render method `program` arguments can now be `PathLike` objects.

#### Changed
- Themes are now dynamic.  Instead of merging attribute assignments when
  `use_theme()` is called, themes are resolved at render time without affecting
  the dot object.
- Moved narrative docstring text from class Dot to Overview section of doc.
- Significantly revised docstrings throughout.
- Switched to using term "establish" instead of "specify" for first assignment
  to default and graph attributes; "specify" is too common.
- Harmonized the parameters of the `to_rendered`, `to_svg`, and `show`
- All render methods now call `to_rendered` to do the real work.
- Render methods throw `ProcessException` and `TimeoutException` instead of the
  similar `subprocess` exceptions.
- The "show source" capability of `show()` is now separated out as
  `show_source()`.
- Method `show()` now catches Graphviz program execution related exceptions and
  displays HTML via `Markdown` objects decribing the issue, then raises a
  sanitized `ShowException`.

#### Fixed
- Clarified that amending endpoint order for non-multigraphs is supported;
  fixed error in endpoint order amending.
- `role` argument to `node_role()` type corrected to `str`.

#### Removed
- Ability to specify arbitrary -G, -N, -E command line attributes.  The most
  useful, and perhaps only useful capability enabled by these is to set output
  resolution, size, and aspect ratio, and these were added as direct
  parameters.

## [0.9.1] - 2026-02-03

First release.
