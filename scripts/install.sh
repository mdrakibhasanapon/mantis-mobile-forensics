#!/usr/bin/env bash
# Mantis Mobile Forensics - Kali Linux Installation Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================================="
echo "  Installing Mantis Mobile Forensics on Kali Linux"
echo "=========================================================="

# Check if .deb package exists, build if missing
if [ ! -f "${ROOT_DIR}/mantis-mobile-forensics_1.0.0_amd64.deb" ]; then
    echo "[INSTALL] Building .deb package first..."
    "${ROOT_DIR}/scripts/build_deb.sh"
fi

# If running as root or with sudo available
if [ "$(id -u)" -eq 0 ]; then
    echo "[INSTALL] Installing deb package via dpkg..."
    dpkg -i "${ROOT_DIR}/mantis-mobile-forensics_1.0.0_amd64.deb" || apt-get install -f -y
    echo "[INSTALL] Successfully installed system-wide in /opt/mantis-mobile-forensics!"
else
    # Non-root / user-level installation
    echo "[INSTALL] Setting up user-level desktop integration in ~/.local..."
    mkdir -p "${HOME}/.local/bin"
    mkdir -p "${HOME}/.local/share/applications"
    mkdir -p "${HOME}/.local/share/icons/hicolor/scalable/apps"
    mkdir -p "${HOME}/.local/share/pixmaps"

    # Symlink launcher
    ln -sf "${ROOT_DIR}/scripts/mantis-forensics" "${HOME}/.local/bin/mantis-forensics"

    # Copy icons
    cp "${ROOT_DIR}/assets/icon.svg" "${HOME}/.local/share/icons/hicolor/scalable/apps/mantis.svg"
    cp "${ROOT_DIR}/assets/mantis.png" "${HOME}/.local/share/pixmaps/mantis.png"

    # Adapt and install desktop file with absolute user path
    sed "s|Exec=mantis-forensics|Exec=${HOME}/.local/bin/mantis-forensics|g" \
        "${ROOT_DIR}/assets/mantis-mobile-forensics.desktop" > "${HOME}/.local/share/applications/mantis-mobile-forensics.desktop"

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${HOME}/.local/share/applications" || true
    fi

    echo "[INSTALL] User desktop entry and launcher installed successfully!"
fi

echo "=========================================================="
echo "  Installation Complete!"
echo "  You can now launch Mantis Mobile Forensics:"
echo "  1. From Application Menu: Kali Menu -> Forensics -> Mantis Mobile Forensics"
echo "  2. From Terminal: mantis-forensics"
echo "=========================================================="
