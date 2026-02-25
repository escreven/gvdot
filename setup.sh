#!/bin/bash

#
# Setup local filters referenced by .gitattributes.
#

set -euo pipefail

git config --local filter.ipynb-exec-null.clean \
  "sed -E 's/^([[:space:]]*\"execution_count\":[[:space:]]*)[^[:space:],]+,/\\1null,/'"

git config --local filter.ipynb-exec-null.smudge cat
