#!/usr/bin/env bash
# No owner files, credentials or network access required.
set -euo pipefail
if [[ $# != 1 ]]; then
  echo "Usage: bash $0 /path/to/ghidra/support/analyzeHeadless" >&2
  exit 2
fi
headless="$(realpath "$1")"
scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT
mkdir "$scratch/projects"
python3 "$scripts/synthetic_reference_pe.py" make "$scratch/fixture.exe"
sha="$(sha256sum "$scratch/fixture.exe" | cut -d' ' -f1)"
"$headless" "$scratch/projects" synthetic-reference \
  -import "$scratch/fixture.exe" -overwrite \
  -scriptPath "$scripts" \
  -postScript DX2BoundedReferenceCollector.java "$scratch/evidence.json" "$sha" \
  -analysisTimeoutPerFile 120 -deleteProject
test -s "$scratch/evidence.json"
python3 "$scripts/synthetic_reference_pe.py" check "$scratch/fixture.exe" "$scratch/evidence.json"
