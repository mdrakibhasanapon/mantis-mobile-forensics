#!/usr/bin/env bash
# Mantis Mobile Forensics - Automated Test Runner
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================================="
echo "  Running Mantis Mobile Forensics Test Suite"
echo "=========================================================="

export PYTHONPATH="${ROOT_DIR}/packages/mmf_core/src:${ROOT_DIR}/apps/api/src:${PYTHONPATH:-}"

cd "${ROOT_DIR}"
python3 -m pytest tests/ -v --tb=short

echo "=========================================================="
echo "  All Forensic Engine Tests Passed Successfully!"
echo "=========================================================="
