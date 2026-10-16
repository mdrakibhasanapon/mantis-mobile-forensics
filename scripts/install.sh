#!/usr/bin/env bash
# ==============================================================================
# Mantis Mobile Forensics (MMF) - Full Setup & Installer Engine
# Automatically installs all dependencies (System, Python, Node, Electron),
# compiles production web assets, installs high-res logos/icons,
# and registers launcher shortcuts in both the Application Menu and Desktop screen.
# ==============================================================================
set -e

# Resolve canonical script and repo directory
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ANSI Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
AMBER='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "=========================================================="
echo "    Mantis Mobile Forensics - Automated Installer         "
echo "=========================================================="
echo -e "${NC}"

# STEP 1: Verify & Install System Dependencies
echo -e "${BLUE}[STEP 1/6]${NC} Checking core system packages..."
MISSING_PKGS=()
for cmd in python3 pip3 node npm curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        case "$cmd" in
            pip3) MISSING_PKGS+=("python3-pip") ;;
            node|npm) MISSING_PKGS+=("nodejs" "npm") ;;
            *) MISSING_PKGS+=("$cmd") ;;
        esac
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo -e "${AMBER}  -> Missing packages detected: ${MISSING_PKGS[*]}${NC}"
    if [ "$(id -u)" -eq 0 ]; then
        apt-get update -y && apt-get install -y "${MISSING_PKGS[@]}"
    elif command -v sudo >/dev/null 2>&1; then
        echo "  -> Installing via sudo apt-get..."
        sudo apt-get update -y && sudo apt-get install -y "${MISSING_PKGS[@]}" || {
            echo -e "${AMBER}[WARN] Could not install system packages via sudo. Continuing with user environment...${NC}"
        }
    else
        echo -e "${AMBER}[WARN] Please install required packages: apt-get install ${MISSING_PKGS[*]}${NC}"
    fi
else
    echo -e "${GREEN}  -> Core system packages (python3, pip, node, npm, curl) are present.${NC}"
fi

# STEP 2: Verify & Install Python Dependencies
echo -e "${BLUE}[STEP 2/6]${NC} Installing Python forensic engine dependencies..."
if ! python3 -c "import fastapi, uvicorn, pydantic, pytest" >/dev/null 2>&1; then
    echo "  -> Installing Python requirements from requirements.txt..."
    pip3 install -q --no-input -r "${ROOT_DIR}/requirements.txt" --break-system-packages 2>/dev/null || \
    pip3 install -q --no-input -r "${ROOT_DIR}/requirements.txt" 2>/dev/null || {
        echo -e "${AMBER}  -> Note: Some Python dependencies may need system package installation.${NC}"
    }
fi
echo -e "${GREEN}  -> Python dependencies satisfied.${NC}"

# STEP 3: Install Web Dependencies & Build Production Bundle
echo -e "${BLUE}[STEP 3/6]${NC} Installing frontend dependencies & building production assets..."
cd "${ROOT_DIR}/apps/web"
if [ ! -d "node_modules" ]; then
    echo "  -> Running npm install in apps/web..."
    npm install --quiet
else
    echo -e "${GREEN}  -> Web node_modules verified.${NC}"
fi

if [ ! -f "dist/index.html" ]; then
    echo "  -> Compiling Vite production assets..."
    npm run build
else
    echo -e "${GREEN}  -> Web production bundle verified (dist/index.html).${NC}"
fi
cd "${ROOT_DIR}"

# STEP 4: Ensure Desktop Electron Runtime is Ready
echo -e "${BLUE}[STEP 4/6]${NC} Setting up desktop Electron runtime..."
mkdir -p "${ROOT_DIR}/electron_bin"
ELECTRON_READY=false

if [ -x "${ROOT_DIR}/electron_bin/dist/electron" ]; then
    ELECTRON_READY=true
elif [ -x "${HOME}/.gemini/antigravity/scratch/electron_bin/dist/electron" ]; then
    cp -r "${HOME}/.gemini/antigravity/scratch/electron_bin/dist" "${ROOT_DIR}/electron_bin/" 2>/dev/null || true
    chmod +x "${ROOT_DIR}/electron_bin/dist/electron" 2>/dev/null || true
    [ -x "${ROOT_DIR}/electron_bin/dist/electron" ] && ELECTRON_READY=true
fi

if [ "$ELECTRON_READY" = false ]; then
    # Search npx cache or download via npx
    if command -v npx >/dev/null 2>&1; then
        CACHED_ELECTRON="$(find "${HOME}/.npm/_npx" -name "electron" -type f -perm /111 2>/dev/null | grep "/electron/dist/electron" | head -n 1 || true)"
        if [ -n "$CACHED_ELECTRON" ] && [ -x "$CACHED_ELECTRON" ]; then
            ELECTRON_DIR="$(dirname "$CACHED_ELECTRON")"
            cp -r "$ELECTRON_DIR" "${ROOT_DIR}/electron_bin/" 2>/dev/null || true
            chmod +x "${ROOT_DIR}/electron_bin/dist/electron" 2>/dev/null || true
            [ -x "${ROOT_DIR}/electron_bin/dist/electron" ] && ELECTRON_READY=true
        else
            echo "  -> Fetching Electron runtime for desktop workstation..."
            npx --yes electron --version >/dev/null 2>&1 || true
            CACHED_ELECTRON="$(find "${HOME}/.npm/_npx" -name "electron" -type f -perm /111 2>/dev/null | grep "/electron/dist/electron" | head -n 1 || true)"
            if [ -n "$CACHED_ELECTRON" ] && [ -x "$CACHED_ELECTRON" ]; then
                ELECTRON_DIR="$(dirname "$CACHED_ELECTRON")"
                cp -r "$ELECTRON_DIR" "${ROOT_DIR}/electron_bin/" 2>/dev/null || true
                chmod +x "${ROOT_DIR}/electron_bin/dist/electron" 2>/dev/null || true
                [ -x "${ROOT_DIR}/electron_bin/dist/electron" ] && ELECTRON_READY=true
            fi
        fi
    fi
fi

if [ "$ELECTRON_READY" = true ]; then
    echo -e "${GREEN}  -> Standalone Electron runtime bundled in electron_bin/dist (offline-ready).${NC}"
else
    echo -e "${AMBER}  -> Electron will launch via system/npx runtime.${NC}"
fi

# STEP 5: Install Icons & Desktop Entry for Application Menu and Desktop Screen
echo -e "${BLUE}[STEP 5/6]${NC} Installing icons & desktop shortcuts..."
chmod +x "${ROOT_DIR}/scripts/mantis-forensics"

# 5a. Create user directories
mkdir -p "${HOME}/.local/bin"
mkdir -p "${HOME}/.local/share/applications"
mkdir -p "${HOME}/.local/share/icons/hicolor/scalable/apps"
mkdir -p "${HOME}/.local/share/icons/hicolor/256x256/apps"
mkdir -p "${HOME}/.local/share/icons/hicolor/512x512/apps"
mkdir -p "${HOME}/.local/share/pixmaps"

# 5b. Symlink launcher
ln -sf "${ROOT_DIR}/scripts/mantis-forensics" "${HOME}/.local/bin/mantis-forensics"

# If root, also symlink to /usr/local/bin
if [ "$(id -u)" -eq 0 ]; then
    ln -sf "${ROOT_DIR}/scripts/mantis-forensics" "/usr/local/bin/mantis-forensics" 2>/dev/null || true
fi

# 5c. Copy icons across standard sizes
cp -f "${ROOT_DIR}/assets/icon.svg" "${HOME}/.local/share/icons/hicolor/scalable/apps/mantis.svg"
cp -f "${ROOT_DIR}/assets/mantis.png" "${HOME}/.local/share/icons/hicolor/256x256/apps/mantis.png"
cp -f "${ROOT_DIR}/assets/icon.png" "${HOME}/.local/share/icons/hicolor/512x512/apps/mantis.png"
cp -f "${ROOT_DIR}/assets/mantis.png" "${HOME}/.local/share/pixmaps/mantis.png"

# Also install into custom user themes if present (e.g. Flat-Remix)
for theme_dir in "${HOME}/.local/share/icons"/*; do
    if [ -d "${theme_dir}" ] && [ "$(basename "${theme_dir}")" != "hicolor" ]; then
        mkdir -p "${theme_dir}/48x48/apps" "${theme_dir}/256x256/apps" 2>/dev/null || true
        cp -f "${ROOT_DIR}/assets/mantis.png" "${theme_dir}/48x48/apps/mantis.png" 2>/dev/null || true
        cp -f "${ROOT_DIR}/assets/mantis.png" "${theme_dir}/256x256/apps/mantis.png" 2>/dev/null || true
        if command -v gtk-update-icon-cache >/dev/null 2>&1; then
            gtk-update-icon-cache -f -t "${theme_dir}" >/dev/null 2>&1 || true
        fi
    fi
done

# 5d. Prepare desktop file with absolute executable and absolute icon path
DESKTOP_TEMPLATE="${ROOT_DIR}/assets/mantis-mobile-forensics.desktop"
INSTALLED_APP_DESKTOP="${HOME}/.local/share/applications/mantis-mobile-forensics.desktop"
ICON_PATH="${HOME}/.local/share/icons/hicolor/256x256/apps/mantis.png"
LAUNCHER_PATH="${HOME}/.local/bin/mantis-forensics"

sed -e "s|Exec=mantis-forensics|Exec=${LAUNCHER_PATH}|g" \
    -e "s|Icon=mantis|Icon=${ICON_PATH}|g" \
    "${DESKTOP_TEMPLATE}" > "${INSTALLED_APP_DESKTOP}"
chmod +x "${INSTALLED_APP_DESKTOP}"

# 5e. Install directly onto Desktop screen if Desktop folder exists
DESKTOP_DIR=""
if command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
fi
if [ -z "$DESKTOP_DIR" ] || [ ! -d "$DESKTOP_DIR" ]; then
    DESKTOP_DIR="${HOME}/Desktop"
fi

if [ -d "$DESKTOP_DIR" ]; then
    DESKTOP_FILE="${DESKTOP_DIR}/mantis-mobile-forensics.desktop"
    cp -f "${INSTALLED_APP_DESKTOP}" "${DESKTOP_FILE}"
    chmod +x "${DESKTOP_FILE}"
    if command -v gio >/dev/null 2>&1; then
        gio set "${DESKTOP_FILE}" metadata::trusted true 2>/dev/null || true
    fi
    echo -e "${GREEN}  -> Desktop screen shortcut installed at: ${DESKTOP_FILE}${NC}"
fi

# 5f. Update desktop database and icon caches
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo -e "${GREEN}  -> Application Menu and Desktop shortcuts configured with custom Mantis logo.${NC}"

# STEP 6: Build Debian Package (if missing)
echo -e "${BLUE}[STEP 6/6]${NC} Finalizing installation..."
if [ ! -f "${ROOT_DIR}/mantis-mobile-forensics_1.0.0_amd64.deb" ]; then
    if [ -f "${ROOT_DIR}/scripts/build_deb.sh" ]; then
        echo "  -> Assembling Debian package..."
        "${ROOT_DIR}/scripts/build_deb.sh" >/dev/null 2>&1 || true
    fi
fi

# If root, install .deb package via dpkg
if [ "$(id -u)" -eq 0 ] && [ -f "${ROOT_DIR}/mantis-mobile-forensics_1.0.0_amd64.deb" ]; then
    dpkg -i "${ROOT_DIR}/mantis-mobile-forensics_1.0.0_amd64.deb" || apt-get install -f -y
    echo -e "${GREEN}  -> Successfully installed system-wide in /opt/mantis-mobile-forensics!${NC}"
fi

# Auto-restore Antigravity chat session if backup exists
if [ -f "${ROOT_DIR}/sync_chat.sh" ] && [ -f "${ROOT_DIR}/.antigravity_chat_backup.tar.gz" ]; then
    "${ROOT_DIR}/sync_chat.sh" --restore >/dev/null 2>&1 || true
fi

# Ensure ~/.local/bin is in PATH for current user
if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
    export PATH="${HOME}/.local/bin:${PATH}"
fi

echo ""
echo -e "${GREEN}${BOLD}==========================================================${NC}"
echo -e "${GREEN}${BOLD}  Mantis Mobile Forensics - Setup Complete!               ${NC}"
echo -e "${GREEN}${BOLD}==========================================================${NC}"
echo -e "  You can launch the workstation from anywhere:"
if [ -d "$DESKTOP_DIR" ]; then
    echo -e "  1. ${CYAN}Desktop Screen${NC}:      Double-click the 'Mantis Mobile Forensics' icon"
fi
echo -e "  2. ${CYAN}Application Menu${NC}:    Kali Menu -> Forensics -> Mantis Mobile Forensics"
echo -e "  3. ${CYAN}Terminal Command${NC}:    Run: mantis-forensics"
echo -e "${GREEN}==========================================================${NC}"
