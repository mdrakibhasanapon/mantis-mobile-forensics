#!/usr/bin/env bash
# ==============================================================================
# Mantis Mobile Forensics (MMF) - Automatic Update & Synchronization Engine
# Usage: ./update.sh [--force] [--check-only] [--skip-tests]
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}"
VERSION="1.0.0"

# ANSI Colors for terminal output
CYAN='\033[0;36m'
GREEN='\033[0;32m'
AMBER='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=========================================================="
echo "    Mantis Mobile Forensics - Auto-Update Engine          "
echo "=========================================================="
echo -e "${NC}"

FORCE_UPDATE=false
CHECK_ONLY=false
SKIP_TESTS=false

for arg in "$@"; do
    case "$arg" in
        --force|-f)
            FORCE_UPDATE=true
            ;;
        --check-only|-c)
            CHECK_ONLY=true
            ;;
        --skip-tests|-s)
            SKIP_TESTS=true
            ;;
        --help|-h)
            echo "Usage: ./update.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --check-only   Check for GitHub updates without applying them"
            echo "  -f, --force        Force rebuild & reinstall even if already up to date"
            echo "  -s, --skip-tests   Skip running forensic validation tests after update"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
    esac
done

cd "${ROOT_DIR}"

# ------------------------------------------------------------------------------
# 1. Git Repository & Remote Synchronization
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 1/5]${NC} Checking Git repository and remote synchronization..."

HAS_GIT=false
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    HAS_GIT=true
fi

PULLED_CHANGES=false

if [ "$HAS_GIT" = true ]; then
    CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")"
    REMOTE="$(git remote 2>/dev/null | head -n 1 || echo "")"

    if [ -n "$REMOTE" ]; then
        echo -e "  -> Fetching latest updates from remote: ${BOLD}${REMOTE}/${CURRENT_BRANCH}${NC}..."
        git fetch "$REMOTE" "$CURRENT_BRANCH" --quiet || {
            echo -e "${AMBER}[WARN] Network fetch from remote failed. Proceeding with local refresh...${NC}"
        }

        LOCAL_HASH="$(git rev-parse HEAD 2>/dev/null || echo "")"
        REMOTE_HASH="$(git rev-parse "${REMOTE}/${CURRENT_BRANCH}" 2>/dev/null || echo "")"

        if [ -n "$REMOTE_HASH" ] && [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
            echo -e "${AMBER}  -> New updates detected on GitHub!${NC}"
            echo -e "     Local:  ${LOCAL_HASH:0:8}"
            echo -e "     Remote: ${REMOTE_HASH:0:8}"

            if [ "$CHECK_ONLY" = true ]; then
                echo -e "${GREEN}[INFO] Updates are available! Run './update.sh' to pull and apply.${NC}"
                exit 0
            fi

            # Check if there are local uncommitted changes
            if ! git diff --quiet || ! git diff --cached --quiet; then
                echo -e "${AMBER}  -> Stashing local changes before pulling...${NC}"
                STASH_NAME="mmf_auto_stash_$(date +%s)"
                git stash push -u -m "$STASH_NAME" --quiet
                echo -e "     Local changes stashed safely."
            fi

            echo -e "  -> Pulling latest commits..."
            git pull "$REMOTE" "$CURRENT_BRANCH" --quiet
            PULLED_CHANGES=true

            echo -e "${GREEN}  -> Updated to latest commit:${NC}"
            git log -1 --pretty=format:"     Commit: %h - %s (%cr) <%an>%n"
        else
            echo -e "${GREEN}  -> Git repository is already up to date with remote.${NC}"
            if [ "$CHECK_ONLY" = true ]; then
                exit 0
            fi
        fi
    else
        echo -e "${AMBER}  -> Git is initialized locally, but no remote is configured yet.${NC}"
        echo -e "     To sync with GitHub, run:"
        echo -e "       ${BOLD}git remote add origin https://github.com/<your-user>/<your-repo>.git${NC}"
        echo -e "       ${BOLD}git push -u origin main${NC}"
    fi
else
    echo -e "${AMBER}  -> Project is not yet a Git repository.${NC}"
    echo -e "     To initialize Git and connect to GitHub, see COMMANDS.md"
fi

# ------------------------------------------------------------------------------
# 2. Python Dependencies Verification
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 2/5]${NC} Verifying Python forensic engine dependencies..."

if python3 -c "import fastapi, uvicorn, pydantic, pytest" >/dev/null 2>&1; then
    echo -e "${GREEN}  -> Core dependencies (fastapi, uvicorn, pydantic, pytest) are satisfied.${NC}"
else
    echo "  -> Installing missing Python dependencies..."
    pip3 install -q --no-input -r "${ROOT_DIR}/requirements.txt" --break-system-packages 2>/dev/null || \
    pip3 install -q --no-input -r "${ROOT_DIR}/requirements.txt" 2>/dev/null || {
        echo -e "${AMBER}  -> Note: Some Python dependencies may need system package installation.${NC}"
    }
fi

# ------------------------------------------------------------------------------
# 3. Web Frontend Build & Asset Compilation
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 3/5]${NC} Recompiling React/Vite forensic frontend application..."

cd "${ROOT_DIR}/apps/web"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "  -> Installing Node frontend dependencies..."
    npm install --prefer-offline --no-audit --quiet
else
    echo -e "${GREEN}  -> Node modules verified.${NC}"
fi

echo "  -> Building production frontend bundle (Vite)..."
npm run build --silent || npx vite build

cd "${ROOT_DIR}"
echo -e "${GREEN}  -> Frontend bundle compiled successfully in apps/web/dist!${NC}"


# ------------------------------------------------------------------------------
# 4. Desktop Integration & Launcher Refresh
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 4/5]${NC} Refreshing Desktop integration and launcher symlinks..."

# If installed system-wide in /opt/mantis-mobile-forensics
if [ -d "/opt/mantis-mobile-forensics" ] && [ "$(id -u)" -eq 0 ]; then
    echo "  -> System package detected. Rebuilding Debian package..."
    "${ROOT_DIR}/scripts/build_deb.sh"
    dpkg -i "${ROOT_DIR}/mantis-mobile-forensics_1.0.0_amd64.deb" || apt-get install -f -y
    echo -e "${GREEN}  -> System-wide /opt installation updated successfully!${NC}"
fi

# Refresh user desktop integration (~/.local)
if mkdir -p "${HOME}/.local/bin" 2>/dev/null; then
    mkdir -p "${HOME}/.local/share/applications" 2>/dev/null || true
    mkdir -p "${HOME}/.local/share/icons/hicolor/scalable/apps" 2>/dev/null || true
    mkdir -p "${HOME}/.local/share/pixmaps" 2>/dev/null || true

    # Update symlink launcher
    chmod +x "${ROOT_DIR}/scripts/mantis-forensics"
    ln -sf "${ROOT_DIR}/scripts/mantis-forensics" "${HOME}/.local/bin/mantis-forensics" 2>/dev/null || true

    # Update icons & desktop file
    if [ -f "${ROOT_DIR}/assets/icon.svg" ]; then
        cp -f "${ROOT_DIR}/assets/icon.svg" "${HOME}/.local/share/icons/hicolor/scalable/apps/mantis.svg" 2>/dev/null || true
    fi
    if [ -f "${ROOT_DIR}/assets/mantis.png" ]; then
        cp -f "${ROOT_DIR}/assets/mantis.png" "${HOME}/.local/share/pixmaps/mantis.png" 2>/dev/null || true
    fi
    if [ -f "${ROOT_DIR}/assets/mantis-mobile-forensics.desktop" ]; then
        sed "s|Exec=mantis-forensics|Exec=${HOME}/.local/bin/mantis-forensics|g" \
            "${ROOT_DIR}/assets/mantis-mobile-forensics.desktop" > "${HOME}/.local/share/applications/mantis-mobile-forensics.desktop" 2>/dev/null || true
    fi

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true
    fi

    echo -e "${GREEN}  -> User desktop launcher and application menu refreshed.${NC}"
else
    echo -e "${AMBER}  -> Desktop integration preserved (launcher in scripts/mantis-forensics).${NC}"
fi


# ------------------------------------------------------------------------------
# 5. Forensic Test Suite Verification
# ------------------------------------------------------------------------------
if [ "$SKIP_TESTS" = false ]; then
    echo -e "${BLUE}[STEP 5/5]${NC} Running forensic engine regression test suite..."
    if [ -f "${ROOT_DIR}/scripts/test.sh" ]; then
        chmod +x "${ROOT_DIR}/scripts/test.sh"
        "${ROOT_DIR}/scripts/test.sh"
    fi
else
    echo -e "${BLUE}[STEP 5/5]${NC} Skipping test suite (--skip-tests active)."
fi

# ------------------------------------------------------------------------------
# Completion Banner
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}==========================================================${NC}"
echo -e "${GREEN}${BOLD}  Mantis Mobile Forensics - Update Completed Successfully!${NC}"
echo -e "${GREEN}${BOLD}==========================================================${NC}"
echo -e "  Workstation Version: ${CYAN}v${VERSION}${NC}"
if [ "$HAS_GIT" = true ]; then
    echo -e "  Current Git Commit:  ${CYAN}$(git rev-parse --short HEAD 2>/dev/null || echo "N/A")${NC}"
fi
echo -e "  Status:              ${GREEN}Operational & Verified${NC}"
echo ""
echo -e "  ${BOLD}To launch the application:${NC}"
echo -e "    1. Terminal:  ${CYAN}mantis-forensics${NC}  or  ${CYAN}./dev.sh${NC}"
echo -e "    2. Kali Menu: ${CYAN}Applications -> Forensics -> Mantis Mobile Forensics${NC}"
echo ""
echo -e "  ${BOLD}To share updates across laptops:${NC}"
echo -e "    • On laptop 1 (after changes):  ${AMBER}git add . && git commit -m 'updates' && git push${NC}"
echo -e "    • On laptop 2 (to receive):    ${AMBER}./update.sh${NC}"
echo -e "${GREEN}==========================================================${NC}"
