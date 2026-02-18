#
# Verify PYPI.md is a deployable state.
#
# PyPI incorporates PYPI.md into the pypi.org gvdot package description page
# as-is.  It doesn't correct relative GitHub links, so links in PYPI.md must
# be absolute.  PyPI also doesn't support LaTeX in markdown.
#
# Because PYPI.md is based on README.md, the script further requires PYPI.md to
# have the same or later modification time as README.md.
#
# op.sh runs this script before declaring a release or deploying to [Test]PyPI.
#

import re
import sys
from pathlib import Path

link_re = re.compile(r"]\(\s*([^\s]+)\s*\)")
math_re = re.compile(r"\s\$([^\s][^$]*[^\s]|[^\s])\$|\$\$")

with open("PYPI.md") as f:
    pypi_md = f.read()

for link in link_re.findall(pypi_md):
    if not link.startswith("https://"):
        print(f"PYPI.md may contain link {link}",file=sys.stderr)
        print("Only absolute https:// links should be used",file=sys.stderr)
        sys.exit(1)

if match := math_re.search(pypi_md):
    print(f"PYPI.md may contain LaTex {match[0].strip()}",file=sys.stderr)
    print("PyPI does not support embedded LaTex.",file=sys.stderr)
    sys.exit(1)

if Path("README.md").stat().st_mtime > Path("PYPI.md").stat().st_mtime:
    print("README.md modified after PYPI.md",file=sys.stderr)
    print("Verify PYPI.md is up to date; touch if necessary",file=sys.stderr)
    sys.exit(1)
