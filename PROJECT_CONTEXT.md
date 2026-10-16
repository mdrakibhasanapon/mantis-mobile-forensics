# 🧠 Mantis Mobile Forensics - Antigravity AI Project Context & Session Memory

> **Notice for Antigravity AI**: This document serves as the persistent cross-device memory for the Mantis Mobile Forensics project. When a new Antigravity session is started on any laptop, reading this file brings the agent up to speed with the complete architecture, recent changes, decisions, and workflow.

---

## 📌 Project Overview
- **Name**: Mantis Mobile Forensics (MMF)
- **Author/Owner**: `@mdrakibhasanapon`
- **Repository**: `https://github.com/mdrakibhasanapon/mantis-mobile-forensics.git`
- **Target OS**: Kali Linux x86_64 / Debian Linux
- **Architecture**:
  - **Backend Engine**: Python 3.10+ FastAPI on `127.0.0.1:8765` (`apps/api`), forensic core in `packages/mmf_core`.
  - **Frontend UI**: React 18 + TypeScript + Vite + TailwindCSS on `127.0.0.1:5173` (`apps/web`).
  - **Desktop App**: Electron workstation launcher (`apps/desktop`).
  - **Package**: Debian `.deb` installer (`scripts/build_deb.sh`, `install.sh`).

---

## 🛠️ Key Commands Cheat Sheet
| Action | Command | Purpose |
| :--- | :--- | :--- |
| **Auto-Update from GitHub** | `./update.sh` | Pulls latest code, builds frontend, refreshes desktop integration, runs tests. |
| **Development Server** | `./dev.sh` | Concurrently launches backend (`:8765`) and frontend (`:5173`). |
| **Launch Desktop Workstation** | `mantis-forensics` | Opens the installed desktop application. |
| **Run Regression Test Suite** | `./scripts/test.sh` | Runs all 32 pytest forensic tests (must pass 100%). |
| **Install / Re-link** | `./install.sh` | Installs desktop shortcuts, icons, and local launcher. |
| **Build Debian Package** | `./scripts/build_deb.sh` | Builds `mantis-mobile-forensics_1.0.0_amd64.deb`. |

---

## 🚀 Recent Implementations & Problem Solutions

### 1. Evidence Explorer - Human-Readable Database Inspector (`wpndatabase.db` fix)
- **Issue**: Selecting a binary database file (e.g. `Notifications/wpndatabase.db`) in Evidence Explorer displayed raw chunk bytes (`errors="replace"`) with SQLite B-tree pointers, null bytes, and unreadable binary garbage.
- **Solution**:
  - Backend `read_file_preview` in `vault.py` automatically detects SQLite files using `SqliteForensicExplorer.is_sqlite_database()` and extracts clean text preview (ASCII `>= 4` chars) and SQLite schema/tables with row counts.
  - Added `@router.post("/{evidence_id}/query-db")` to query any table in an evidence database on demand.
  - Added dedicated **"Database Inspector"** tab in Evidence Explorer that defaults to active when a `.db`/`.sqlite` file is clicked.
  - Supports table switching pills (`Notification (22)`, `NotificationHandler (158)`, `HandlerSettings (3762)`, etc.), search filter, and CSV export.
  - Integrated `forensicFormatter.ts` to decode timestamps:
    - **Windows FileTime (100ns intervals since 1601)**: e.g. `133336161230286775` -> `2023-07-12 06:15:23 UTC`.
    - **Unix timestamps** (seconds, milliseconds, microseconds, nanoseconds).
    - **Mac Cocoa / Apple Absolute Time**.
    - **WebKit / Chrome epochs**.
    - **Toast notification XML payloads** (`<toast scenario='reminder'>...`) formatted cleanly.
  - **Text Preview Tab**: Added toggle for `[ Clean Readable Strings ]` vs `[ Raw Chunk ]` to filter out binary null bytes.
  - **Forensic Cell Inspector Modal**: One-click deep inspection for any table cell showing Decoded, Hex Dump, and Raw DB Value with copy buttons.

### 2. Auto-Update Engine (`./update.sh`)
- Created root `update.sh` that pulls from `origin/main`, compiles Vite assets, updates Python/Node dependencies, updates desktop launcher symlinks, and runs verification tests.

### 3. Git & Multi-Laptop Sync
- Configured Git remote `git@github.com:mdrakibhasanapon/mantis-mobile-forensics.git` with SSH authentication.
- Added comprehensive `.gitignore` preventing 137MB `.deb` builds, `node_modules/`, and cache from bloating the repository.
- Root convenience scripts: `./install.sh`, `./dev.sh`, `./update.sh`, `sync_chat.sh`, `requirements.txt`, `requirements-system.txt`.

### 4. Cross-Platform Desktop & Multi-Device Hardening (Latest)
- **Automatic Frontend Build in Installer**: Updated `scripts/build_deb.sh` to automatically install `node_modules` via `npm install` before building Vite assets, preventing `ERR_MODULE_NOT_FOUND`.
- **Symlink Canonical Resolution**: Fixed launcher scripts (`scripts/mantis-forensics`, `scripts/dev.sh`, `scripts/test.sh`) using a `readlink` resolution loop so `BASH_SOURCE[0]` correctly resolves to the true project root when executed via symlinks in `~/.local/bin/` or `/usr/bin/`, preventing `ModuleNotFoundError: No module named 'mmf_api'`.
- **Offline Electron Bundling**: Embedded standalone Electron runtime in `electron_bin/dist/` with fallback to `npx electron` for zero-configuration desktop workstation launching.
- **GNOME Multi-Theme Desktop Icon System**: Resolved desktop menu gear icon fallback by generating full-spectrum PNG resolutions (16x16 to 512x512) and installing them across `hicolor` and active custom themes (e.g. `Flat-Remix-Orange-Dark`), setting an absolute `Icon=` path in the `.desktop` file and updating icon caches.
### 5. Next-Gen Mobile Artefact Parsers & Cross-Case Search Engine (Latest)
- **Telegram Forensic Parser** (`packages/mmf_core/.../apps/telegram.py`):
  - Extracts users, dialogs, contacts, messages (`cache4.db`), handles outgoing/incoming flags, Unix epoch normalization.
- **Signal Encrypted Store Parser** (`packages/mmf_core/.../apps/signal.py`):
  - Extracts conversations, recipients, messages (`signal.db`), timestamp normalization from milliseconds.
- **Android Wi-Fi Configurations** (`packages/mmf_core/.../android/wifi.py`):
  - Parses `WifiConfigStore.xml` and legacy `wpa_supplicant.conf`. Extracts SSIDs, PSKs/PreSharedKeys, security suites (WPA_PSK, SAE, etc.), and creation timestamps.
- **Android Bluetooth Pairings** (`packages/mmf_core/.../android/bluetooth.py`):
  - Parses `bt_config.conf` / `bt_config.xml`. Extracts paired MAC addresses, device names, device class (CoD), and Link Keys.
- **Android Package Inventory & Dangerous Permissions** (`packages/mmf_core/.../android/packages.py`):
  - Parses `packages.xml` / `packages.list`. Audits installed apps, install/update timestamps, APK paths, and flags dangerous surveillance permissions (SMS, audio recording, camera, location, contacts).
- **iOS iMessage & SMS Parser** (`packages/mmf_core/.../ios/sms.py`):
  - Parses iOS `sms.db`. Extracts chat handles, text, service type (`iMessage` vs `SMS`), and converts Apple Cocoa nanoseconds to UTC ISO-8601.
- **iOS Call History** (`packages/mmf_core/.../ios/callhistory.py`):
  - Parses iOS `CallHistory.storedata` (`ZCALLRECORD`). Extracts caller/callee, duration, origination, answer state, and converts Cocoa timestamps.
- **iOS Safari Mobile History** (`packages/mmf_core/.../ios/safari.py`):
  - Parses iOS `History.db`. Extracts visited URLs, page titles, visit counts, redirect attributes, and converts Cocoa epochs.
- **Global Cross-Case Search API** (`apps/api/.../forensics.py`):
  - Added `@router.get("/search")` endpoint supporting regex and keyword queries across all ingested case artifacts and timeline events.
- **Frontend & Test Coverage**:
  - Added `wireless` category filter tab & badges to `ArtifactsPage.tsx`.
  - Added comprehensive unit tests in `tests/unit/test_parsers.py` (32/32 tests passing 100%).

---

## 📂 Storage & Data Privacy
- **Local Data Directory**: Case databases and evidence vaults are stored strictly at `~/.local/share/mantis-forensics` (or configurable via `MMF_DATA_DIR`), never inside the codebase repository.
- **Security**: Local loopback binding (`127.0.0.1:8765`) protected with `X-MMF-Session-Token`.

---

## 💡 How to Prompt Antigravity on a New Laptop
To resume work in a new Antigravity session on any other laptop:
```text
@PROJECT_CONTEXT.md continue from here. I want to [your next request]
```
Antigravity will instantly read this context and continue with full understanding!
