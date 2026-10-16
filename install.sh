#!/usr/bin/env bash
# ==============================================================================
# Mantis Mobile Forensics - Universal Installation Launcher
# Supports:
#   1. Local execution: ./install.sh
#   2. Remote 1-liner: curl -sSL https://raw.githubusercontent.com/mdrakibhasanapon/mantis-mobile-forensics/main/install.sh | bash
# Automatically clones (if needed), installs all dependencies, and creates Desktop/Menu shortcuts!
# ==============================================================================
set -e

REPO_URL="https://github.com/mdrakibhasanapon/mantis-mobile-forensics.git"
TARGET_DIR="${HOME}/mantis-mobile-forensics"

# Case 1: Running inside the cloned repo
if [ -f "scripts/install.sh" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    exec "${SCRIPT_DIR}/scripts/install.sh" "$@"

# Case 2: Running via curl/pipe, but repo already cloned at ~/mantis-mobile-forensics
elif [ -f "${TARGET_DIR}/scripts/install.sh" ]; then
    echo "[INSTALL] Updating and setting up existing repository in ${TARGET_DIR}..."
    cd "${TARGET_DIR}"
    exec bash "${TARGET_DIR}/scripts/install.sh" "$@"

# Case 3: Running via curl/pipe on a fresh machine (auto-clone & setup)
else
    echo "=========================================================="
    echo "  Cloning Mantis Mobile Forensics from GitHub...          "
    echo "=========================================================="
    mkdir -p "${TARGET_DIR}"
    git clone "${REPO_URL}" "${TARGET_DIR}"
    cd "${TARGET_DIR}"
    exec bash "${TARGET_DIR}/scripts/install.sh" "$@"
fi
