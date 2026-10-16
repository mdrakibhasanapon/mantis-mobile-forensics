# Mantis Mobile Forensics (MMF)
## Professional Cross-Platform Mobile Digital Forensics Desktop Workstation for Kali Linux x86_64

[![Platform](https://img.shields.io/badge/Platform-Kali%20Linux%20x86__64-blue.svg)](https://www.kali.org)
[![Engine](https://img.shields.io/badge/Engine-Python%20FastAPI%20%2B%20Electron-cyan.svg)]()
[![Forensics](https://img.shields.io/badge/DFIR-Offline--First%20Audit--Chained-emerald.svg)]()
[![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg)](LICENSE)

**Mantis Mobile Forensics (MMF)** is a desktop-first mobile digital forensics platform designed for digital forensics laboratories, incident responders, law enforcement examiners, and digital forensics education.

MMF couples an **Electron desktop shell** with a local **Python FastAPI forensic engine** running strictly on loopback (`127.0.0.1`) with session token protections, isolated case boundaries, immutable cryptographic audit logging, and offline operation.

---

## Key Forensic Capabilities

1. **Android & Mobile Artefact Engines**:
   - Contacts parsing (`contacts2.db` raw contacts and structured data)
   - SMS and MMS text messaging (`mmssms.db`)
   - Telephony call logs with duration and direction (`calllog.db`)
   - Chrome / WebKit browser history and visits (`History`)
   - WhatsApp message store decryption & parsing (`msgstore.db`)
   - Telegram mobile / desktop store (`cache4.db`, users, dialogs, messages)
   - Signal encrypted local message store (`signal.db`, threads, recipients)
   - Facebook Messenger database (`threads_db2`, participants, messages, attachments)
   - IMO Messenger chat & contacts (`imofriends.db`, `account.db`)
   - Instagram Direct messages (`direct_v2.db`)
   - Discord mobile message repository (`messages.db`, channels)
   - Android user dictionary & keyboard input (`user_dict.db`)
   - Android application package inspection & permissions (`AndroidManifest.xml`, `packages.xml`, `packages.list`)
   - Android Wi-Fi network configurations & credentials (`WifiConfigStore.xml`, `wpa_supplicant.conf`)
   - Android Bluetooth paired device database & link keys (`bt_config.conf`, `bt_config.xml`)

2. **iOS & iPadOS Backup Analysis**:
   - Unencrypted & password-authorized iTunes / Finder backup imports
   - Device and backup state inspection (`Info.plist`, `Status.plist`, `Manifest.db`)
   - iMessage & SMS conversation extraction (`sms.db`, handles, timestamps)
   - iOS Call History logs (`CallHistory.storedata`, `ZCALLRECORD`)
   - Safari mobile web browsing history (`History.db`)
   - Normalization of WebKit / Cocoa timestamps to standard UTC ISO-8601

3. **Live Mobile USB Extraction Wizard**:
   - Real-time Android Debug Bridge (ADB) device detection and hardware discovery
   - Live root privilege verification (`su -c id`, `whoami`)
   - System diagnostics: live battery level, hardware health, storage utilization
   - One-click logical extraction modes: Quick Triage (properties, packages, logcat buffer), Media (`/sdcard/DCIM`), and App databases

4. **Geolocation & EXIF Photo Intelligence**:
   - EXIF metadata parser extracting GPS Latitude, Longitude, Altitude, Camera Make/Model, and Timestamps from JPEG, PNG, TIFF, HEIC
   - Automatic DMS rational conversion to precision decimal degrees
   - Interactive Geo-Map viewer with coordinate pins, camera metadata, and direct OpenStreetMap / Google Maps pivots

5. **Communication Link Analysis & Network Graph**:
   - Visual nodal relationship graph mapping target suspect against frequent contacts
   - Channel breakdown: voice calls, WhatsApp, Telegram, Signal, Messenger, SMS
   - 24-Hour activity distribution (Pattern of Life heatmap) identifying sleep/wake activity cycles

6. **Automated Deep IOC & Malware Triage Scanner**:
   - Cryptocurrency wallet scanner: Bitcoin (BTC), Ethereum (ETH), Monero (XMR)
   - Payment card detection with standard Luhn algorithm validation (Visa, MasterCard, Amex)
   - Cryptographic private keys, AWS access keys, JWT tokens, and seed phrase indicators
   - Dark Web (.onion) and suspicious C2 marker detection
   - Configurable high-risk investigation keyword scanner

7. **Evidence Vault & Cryptographic Chain of Custody**:
   - Original evidence stored in read-only vault (`chmod 0444`)
   - Streaming chunked SHA-256 and MD5 cryptographic integrity verification
   - Append-only, cryptographically chained SHA-256 audit trail with tamper detection
   - Complete isolation: case data stored in `~/.local/share/mantis-forensics`, **never** inside the app directory

8. **SQLite Freelist Carving & Deleted-Data Recovery**:
   - Header inspection: page size, total pages, freelist page count, change counter, WAL/SHM status
   - Safe read-only SQL queries with forbidden DDL/DML rejection
   - Regex-based and freelist byte carving with confidence ratings

9. **Professional Forensic Case Reporting**:
   - Official, print-ready PDF case dossiers rendered via WeasyPrint with A4 pagination and header/footer stamps
   - Interactive HTML investigation reports with dark DFIR workstation styling
   - Cryptographic JSON case manifests and CSV timeline exports

---

## Desktop Application Architecture

```
mantis-mobile-forensics/
├── apps/
│   ├── api/          # FastAPI Python forensic engine
│   ├── desktop/      # Electron desktop shell & process supervisor
│   └── web/          # React + TypeScript DFIR workstation UI
├── packages/
│   └── mmf_core/     # Pure forensic parsing, hashing, and recovery core
├── assets/           # Icons, SVG vectors, and Kali .desktop launcher
├── scripts/
│   ├── mantis-forensics  # Main terminal launcher binary
│   ├── dev.sh            # Development mode runner
│   ├── build_deb.sh      # Debian (.deb) package compiler
│   ├── install.sh        # Kali system installer
│   └── test.sh           # Automated test suite
└── tests/            # Unit, integration, security, and API tests
```

---

## Quick Start & Installation

### ⚡ Option 1: 1-Line Instant Installer (Zero manual steps)
Simply paste this single command in terminal and press Enter:

```bash
curl -sSL https://raw.githubusercontent.com/mdrakibhasanapon/mantis-mobile-forensics/main/install.sh | bash
```
*This automatically clones the repository, installs all dependencies (Python, Node, Electron), builds the UI, and creates the Desktop and Application Menu shortcuts without any manual commands.*

---

### 💻 Option 2: 1-Line Git Clone & Install
```bash
git clone https://github.com/mdrakibhasanapon/mantis-mobile-forensics.git && cd mantis-mobile-forensics && ./install.sh
```

### What `./install.sh` Does Automatically:
1. **Installs System Packages**: Checks and ensures `python3`, `pip3`, `nodejs`, `npm`, `curl`, and `adb` are present.
2. **Installs Python Dependencies**: Installs `fastapi`, `uvicorn`, `pydantic`, `pytest`, and forensic modules from `requirements.txt`.
3. **Installs Web Packages & Builds UI**: Runs `npm install` and compiles the React/Tailwind production bundle (`apps/web/dist`).
4. **Bundles Electron Desktop Runtime**: Configures the standalone Electron workstation runtime for offline execution.
5. **Registers Desktop & Application Menu Icons**:
   - **Desktop Screen**: Double-clickable shortcut created directly on your desktop (`~/Desktop/mantis-mobile-forensics.desktop`).
   - **Application Menu**: Registered in Kali Linux menu (`Forensics` and `Security` categories).
   - **Terminal Launcher**: Global command `mantis-forensics` symlinked in `~/.local/bin/`.
6. **Rebuilds Caches**: Updates the GTK icon theme cache and desktop database for instant rendering with the custom Mantis logo.

---

### Alternative: Build Debian (`.deb`) Package

```bash
# Build the .deb package
./scripts/build_deb.sh

# Install system-wide via dpkg (requires root/sudo)
sudo dpkg -i mantis-mobile-forensics_1.0.0_amd64.deb
```

---

## Launching the Application

- **From Kali Application Menu**:
  Open `Applications` -> `Forensics` -> `Mantis Mobile Forensics`
- **From Terminal**:
  ```bash
  mantis-forensics
  ```
- **CLI Options**:
  ```bash
  mantis-forensics --demo              # Launch with synthetic lab extraction
  mantis-forensics --data-dir /path    # Custom evidence vault storage directory
  mantis-forensics --headless-api      # Headless API server mode
  mantis-forensics --test              # Run automated forensic validation tests
  ```

---

## Development Mode

Run the frontend and backend concurrently in separate processes:

```bash
./scripts/dev.sh
```

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8765`
- Interactive OpenAPI Docs: `http://127.0.0.1:8765/docs`

---

## Forensic Validation Tests

Execute the comprehensive test suite verifying hashing, audit chaining, parsing, and security protections:

```bash
./scripts/test.sh
```
