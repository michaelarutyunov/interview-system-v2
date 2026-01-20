#!/bin/bash
# fix-specs.sh - Update specs to use python3 instead of python

cd "$(dirname "$0")/../specs/phase-1"

for spec in *.md; do
  sed -i 's/python -c/python3 -c/g' "$spec"
  echo "Updated $spec"
done

echo "All specs updated to use python3"
