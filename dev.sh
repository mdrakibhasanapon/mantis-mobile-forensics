#!/usr/bin/env bash
# Mantis Mobile Forensics - Root Development Launcher
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/scripts/dev.sh" "$@"
