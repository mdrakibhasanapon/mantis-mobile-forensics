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
    # Verify Python dependencies
    if ! python3 -c "import fastapi, uvicorn, pydantic" >/dev/null 2>&1; then
        echo "[INSTALL] Installing missing Python dependencies..."
        pip3 install -q --no-input -r "${ROOT_DIR}/requirements.txt" --break-system-packages 2>/dev/null || \
        pip3 install -q --no-input -r "${ROOT_DIR}/requirements.txt" 2>/dev/null || true
    fi

    echo "[INSTALL] Setting up user-level desktop integration in ~/.local..."
    mkdir -p "${HOME}/.local/bin"
    mkdir -p "${HOME}/.local/share/applications"
    mkdir -p "${HOME}/.local/share/icons/hicolor/scalable/apps"
    mkdir -p "${HOME}/.local/share/pixmaps"

    # Symlink launcher
    ln -sf "${ROOT_DIR}/scripts/mantis-forensics" "${HOME}/.local/bin/mantis-forensics"

    # Copy icons to standard resolutions
    mkdir -p "${HOME}/.local/share/icons/hicolor/256x256/apps"
    mkdir -p "${HOME}/.local/share/icons/hicolor/512x512/apps"
    cp "${ROOT_DIR}/assets/mantis.png" "${HOME}/.local/share/icons/hicolor/256x256/apps/mantis.png"
    cp "${ROOT_DIR}/assets/icon.png" "${HOME}/.local/share/icons/hicolor/512x512/apps/mantis.png"
    cp "${ROOT_DIR}/assets/icon.svg" "${HOME}/.local/share/icons/hicolor/scalable/apps/mantis.svg"
    cp "${ROOT_DIR}/assets/mantis.png" "${HOME}/.local/share/pixmaps/mantis.png"

    # Also install into custom user themes if present (e.g. Flat-Remix)
    for theme_dir in "${HOME}/.local/share/icons"/*; do
        if [ -d "${theme_dir}" ] && [ "$(basename "${theme_dir}")" != "hicolor" ]; then
            mkdir -p "${theme_dir}/48x48/apps" "${theme_dir}/256x256/apps" 2>/dev/null || true
            cp "${ROOT_DIR}/assets/mantis.png" "${theme_dir}/48x48/apps/mantis.png" 2>/dev/null || true
            cp "${ROOT_DIR}/assets/mantis.png" "${theme_dir}/256x256/apps/mantis.png" 2>/dev/null || true
            if command -v gtk-update-icon-cache >/dev/null 2>&1; then
                gtk-update-icon-cache -f -t "${theme_dir}" >/dev/null 2>&1 || true
            fi
        fi
    done

    # Adapt and install desktop file with absolute user path and absolute icon path
    sed -e "s|Exec=mantis-forensics|Exec=${HOME}/.local/bin/mantis-forensics|g" \
        -e "s|Icon=mantis|Icon=${HOME}/.local/share/icons/hicolor/256x256/apps/mantis.png|g" \
        "${ROOT_DIR}/assets/mantis-mobile-forensics.desktop" > "${HOME}/.local/share/applications/mantis-mobile-forensics.desktop"

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${HOME}/.local/share/applications" || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
    fi

    echo "[INSTALL] User desktop entry and launcher installed successfully!"
fi

# Auto-restore Antigravity chat session if backup exists
if [ -f "${ROOT_DIR}/sync_chat.sh" ] && [ -f "${ROOT_DIR}/.antigravity_chat_backup.tar.gz" ]; then
    "${ROOT_DIR}/sync_chat.sh" --restore >/dev/null 2>&1 || true
    echo "[INSTALL] Antigravity chat session restored for this machine!"
fi


echo "=========================================================="
echo "  Installation Complete!"
echo "  You can now launch Mantis Mobile Forensics:"
echo "  1. From Application Menu: Kali Menu -> Forensics -> Mantis Mobile Forensics"
echo "  2. From Terminal: mantis-forensics"
echo "=========================================================="
