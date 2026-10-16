#!/usr/bin/env bash
# Mantis Mobile Forensics - Automated Test Runner
set -e

# Resolve symlinks to find real script and root directory
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================================="
echo "  Running Mantis Mobile Forensics Test Suite"
echo "=========================================================="

export PYTHONPATH="${ROOT_DIR}/packages/mmf_core/src:${ROOT_DIR}/apps/api/src:${PYTHONPATH:-}"
export MMF_DATA_DIR="${MMF_DATA_DIR:-/tmp/mantis-forensics-test}"

cd "${ROOT_DIR}"
python3 -m pytest tests/ -v --tb=short

echo "=========================================================="
echo "  All Forensic Engine Tests Passed Successfully!"
echo "=========================================================="
