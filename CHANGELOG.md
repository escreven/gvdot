## Unreleased

## [1.3.1] - 2026-10-27

#### Changed
- The test harness probes the Graphviz installation before running tests.
- The first cells of the example notebooks probe the Graphviz installation.
- The Installation section of the doc plus `test/` and `examples/` READMEs have
  been updated to note the requirement to install `libgvplugin-neato-layout8`
  on Ubuntu 26.04 and later.

#### Fixed
- Included `ID` and `CompassPoint` descriptions in the Reference section of the
  doc.  This was broken by the move to a multi-module package.
- The Graphviz [install
  action](https://github.com/escreven/gvdot/blob/main/.github/actions/install-graphviz/action.yml)
  now installs `libgvplugin-neato-layout8` on Ubuntu. `apt-get install
  graphviz` on the most recent Ubuntu runner no longer installs the neato
  layout engine on its own.

## [1.3.0] - 2026-10-27

#### Added
- Function `impose_order()` which can improve the layout of undirected graphs
  rendered by program `dot`.
- `op.sh` now accepts a python interpreter specification option
  (`--python=PYTHON`).
- Custom style for the doc `:program:` role.

#### Changed
- Improved test harness DOT language analysis for testing impose_order().
- Restructured package from a single module to multiple files.

#### Fixed
- Catch `Exception` instead of `BaseException` in the test harness.
- Theme graph and and default attributes now inherited correctly if an
  application subclasses `Dot`.
- Description of default attribute inheritance for node `b` in the Discussion
  &Gt; Subgraphs section of the doc.

## [1.2.5] - 2026-10-08

#### Changed
- IPython kernel warnings during testing are suppressed.
- Verify PyPI workflow tests oldest dependencies as well as latest.
- Verify PyPI workflow uses canary jobs

#### Fixed
- Extraneous op.sh command line arguments are disallowed.
- Dependency Watch workflow now tests Python 3.15
- Underscore escaped `role_` attributes are no longer equivalent to `role`.

## [1.2.4] - 2026-09-16

#### Added
- Python 3.15 support.

#### Changed
- [Coverage](https://coverage.readthedocs.io/en/7.16.1/) option ``--branch`` is
  now used for the `op.sh` coverage reports and GitHub workflows, strengthening
  code coverage assurance.

## [1.2.3] - 2026-09-04

#### Added
- Type `CompassPoint` for the values allowed as the last component of a DOT
  language port specification.

## [1.2.2] - 2026-03-10

#### Added
- Methods `to_svg()`, `save()`, and `show()` accept path-like `program`
  argument values.

#### Fixed
- Non-lowercase forms of DOT reserved words such as `Graph` or `STRICT` are
  quoted.
- Attribute names are quoted when required.

## [1.2.1] - 2026-02-20

#### Changed
- Documentation updates.

## [1.2.0] - 2026-02-17

#### Added
- Added class `Nonce`.  Nonces are placeholders that class `Dot` resolves to
  unique DOT language IDs when generating DOT language representations.
  Applications can use Nonces to create identifiers that do not conflict with
  each other or with identifiers derived from input values.

#### Changed
- Type union `ID` now includes `Nonce`.
- Examples updated to use `Nonce`.

## [1.1.0] - 2026-02-13

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
  of Graphviz do not support TIFF.  Applications can still specify 'tiff' and
  any other format explicitly.

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
  the Dot object.
- Moved narrative docstring text from class Dot to Overview section of doc.
- Significantly revised docstrings throughout.
- Switched to using term "establish" instead of "specify" for first assignment
  to default and graph attributes; "specify" is too common.
- Harmonized the parameters of `to_rendered`, `to_svg`, and `show`
- All render methods now call `to_rendered` to do the real work.
- Render methods throw `ProcessException` and `TimeoutException` instead of the
  similar `subprocess` exceptions.
- The "show source" capability of `show()` is now separated out as
  `show_source()`.
- Method `show()` now catches Graphviz program execution related exceptions and
  displays HTML via `Markdown` objects describing the issue, then raises a
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
