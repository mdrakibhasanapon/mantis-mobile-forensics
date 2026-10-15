#!/usr/bin/env bash
# Mantis Mobile Forensics - Root Installation Launcher
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/scripts/install.sh" "$@"
