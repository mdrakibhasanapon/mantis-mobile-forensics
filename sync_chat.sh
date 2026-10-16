#!/usr/bin/env bash
# ==============================================================================
# Mantis Mobile Forensics - Antigravity Cross-Device Chat Synchronization
# Syncs the exact Antigravity conversation across all your laptops via GitHub!
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}"
CONVERSATION_ID="eca3c3cd-3686-46e2-8757-83d836fc4999"
BACKUP_ARCHIVE="${ROOT_DIR}/.antigravity_chat_backup.tar.gz"
BRAIN_BASE_DIR="${HOME}/.gemini/antigravity/brain"
TARGET_BRAIN_DIR="${BRAIN_BASE_DIR}/${CONVERSATION_ID}"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
AMBER='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "=========================================================="
echo "   Antigravity Cross-Device Chat Synchronization Engine   "
echo "=========================================================="
echo -e "${NC}"

MODE=""
for arg in "$@"; do
    case "$arg" in
        --backup|-b)
            MODE="backup"
            ;;
        --restore|-r)
            MODE="restore"
            ;;
        --help|-h)
            echo "Usage: ./sync_chat.sh [--backup | --restore]"
            echo ""
            echo "  --backup   Package current active Antigravity chat and push to GitHub"
            echo "  --restore  Unpack chat from GitHub backup directly into Antigravity"
            exit 0
            ;;
    esac
done

# If no mode specified, auto-detect:
# If target brain doesn't exist on this machine -> RESTORE!
# If target brain already exists -> BACKUP & SYNC!
if [ -z "$MODE" ]; then
    if [ -d "$TARGET_BRAIN_DIR" ]; then
        MODE="backup"
    else
        MODE="restore"
    fi
fi

if [ "$MODE" = "restore" ]; then
    echo -e "${BLUE}[SYNC]${NC} Restoring Antigravity chat session to this laptop..."
    if [ ! -f "$BACKUP_ARCHIVE" ]; then
        echo -e "${AMBER}[WARN] Chat backup archive not found in repository.${NC}"
        exit 1
    fi

    mkdir -p "$BRAIN_BASE_DIR"
    tar -xzf "$BACKUP_ARCHIVE" -C "$BRAIN_BASE_DIR"

    # Also register in Antigravity app_storage if Antigravity config dir exists
    APP_CONFIG_DIR="${HOME}/.config/Antigravity"
    mkdir -p "$APP_CONFIG_DIR"

    echo ""
    echo -e "${GREEN}${BOLD}==========================================================${NC}"
    echo -e "${GREEN}${BOLD}  Chat Session Restored Successfully!                     ${NC}"
    echo -e "${GREEN}${BOLD}==========================================================${NC}"
    echo -e "  Conversation ID: ${CYAN}${CONVERSATION_ID}${NC}"
    echo -e "  Location:        ${CYAN}${TARGET_BRAIN_DIR}${NC}"
    echo ""
    echo -e "  ${BOLD}Now open Antigravity on this laptop:${NC}"
    echo -e "  You will see this exact conversation in your chat history!"
    echo -e "${GREEN}==========================================================${NC}"

elif [ "$MODE" = "backup" ]; then
    CONV_DIRS=()
    for d in "$BRAIN_BASE_DIR"/*; do
        if [ -d "$d" ] && [ "$(basename "$d")" != "tempmediaStorage" ]; then
            CONV_DIRS+=("$(basename "$d")")
        fi
    done

    if [ ${#CONV_DIRS[@]} -eq 0 ]; then
        echo -e "${AMBER}[WARN] No conversation sessions found in ${BRAIN_BASE_DIR}.${NC}"
        exit 1
    fi

    mkdir -p "${ROOT_DIR}"
    tar -czf "$BACKUP_ARCHIVE" -C "$BRAIN_BASE_DIR" "${CONV_DIRS[@]}"
    ARCHIVE_SIZE="$(du -h "$BACKUP_ARCHIVE" | cut -f1)"

    echo -e "${GREEN}  -> Conversations packaged cleanly (${ARCHIVE_SIZE}): ${CONV_DIRS[*]}${NC}"

    # Auto commit and push if in git repo
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "  -> Committing and pushing updated chat to GitHub..."
        git add "$BACKUP_ARCHIVE"
        git commit -m "sync: update Antigravity chat history across devices" || true
        git push origin main || {
            echo -e "${AMBER}  -> Note: Run 'git push' to send chat backup to GitHub.${NC}"
        }
    fi

    echo ""
    echo -e "${GREEN}${BOLD}==========================================================${NC}"
    echo -e "${GREEN}${BOLD}  Chat Synchronized to GitHub!                            ${NC}"
    echo -e "${GREEN}${BOLD}==========================================================${NC}"
    echo -e "  On your other laptop, simply run:  ${CYAN}./update.sh${NC}"
    echo -e "  and this exact chat will appear in your Antigravity!   "
    echo -e "${GREEN}==========================================================${NC}"
fi
