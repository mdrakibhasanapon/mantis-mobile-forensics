#!/usr/bin/env bash
# Mantis Mobile Forensics - Debian (.deb) Package Builder for Kali Linux x86_64
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
STAGING="${BUILD_DIR}/deb_staging"
DEB_NAME="mantis-mobile-forensics_1.0.0_amd64.deb"

echo "=========================================================="
echo "  Building Mantis Mobile Forensics .deb Package"
echo "=========================================================="

# 1. Ensure web frontend is built
echo "[BUILD] Verifying web production assets..."
cd "${ROOT_DIR}/apps/web"
if [ ! -d "node_modules" ]; then
    echo "[BUILD] Installing web frontend dependencies (npm install)..."
    npm install
fi
if [ ! -f "dist/index.html" ]; then
    echo "[BUILD] Building Vite frontend..."
    npm run build
fi


# 2. Prepare staging directory
rm -rf "${STAGING}"
mkdir -p "${STAGING}/DEBIAN"
mkdir -p "${STAGING}/opt/mantis-mobile-forensics"
mkdir -p "${STAGING}/usr/bin"
mkdir -p "${STAGING}/usr/share/applications"
mkdir -p "${STAGING}/usr/share/pixmaps"
mkdir -p "${STAGING}/usr/share/icons/hicolor/scalable/apps"

# 3. Create DEBIAN/control
cat << 'EOF' > "${STAGING}/DEBIAN/control"
Package: mantis-mobile-forensics
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Mantis DFIR Team <dfir@mantis-forensics.org>
Depends: python3 (>= 3.10), python3-fastapi, python3-uvicorn, python3-pydantic, python3-sqlalchemy, sqlite3
Recommends: adb, libimobiledevice-utils, yara
Description: Professional Mobile Digital Forensics Desktop Workstation
 Mantis Mobile Forensics (MMF) is a modular desktop workstation built for Kali
 Linux x86_64. Features include Android/iOS acquisition & backup import,
 SQLite WAL and freelist carving, cross-source deterministic correlation,
 local malware triage, audit trail verification, and professional reporting.
EOF

# 4. Create DEBIAN/postinst
cat << 'EOF' > "${STAGING}/DEBIAN/postinst"
#!/bin/sh
set -e
chmod +x /opt/mantis-mobile-forensics/scripts/mantis-forensics
chmod +x /usr/bin/mantis-forensics

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "${STAGING}/DEBIAN/postinst"

# 5. Create DEBIAN/prerm
cat << 'EOF' > "${STAGING}/DEBIAN/prerm"
#!/bin/sh
set -e
exit 0
EOF
chmod 755 "${STAGING}/DEBIAN/prerm"

# 6. Copy application files into /opt/mantis-mobile-forensics
echo "[BUILD] Staging application tree..."
cp -r "${ROOT_DIR}/apps" "${STAGING}/opt/mantis-mobile-forensics/"
cp -r "${ROOT_DIR}/packages" "${STAGING}/opt/mantis-mobile-forensics/"
cp -r "${ROOT_DIR}/assets" "${STAGING}/opt/mantis-mobile-forensics/"
cp -r "${ROOT_DIR}/scripts" "${STAGING}/opt/mantis-mobile-forensics/"
cp "${ROOT_DIR}/README.md" "${STAGING}/opt/mantis-mobile-forensics/"
cp "${ROOT_DIR}/LICENSE" "${STAGING}/opt/mantis-mobile-forensics/"

# Include Electron binary if cached
if [ -d "${HOME}/.gemini/antigravity/scratch/electron_bin/dist" ]; then
    echo "[BUILD] Bundling Electron binary..."
    mkdir -p "${STAGING}/opt/mantis-mobile-forensics/electron_bin"
    cp -r "${HOME}/.gemini/antigravity/scratch/electron_bin/dist" "${STAGING}/opt/mantis-mobile-forensics/electron_bin/"
elif [ -d "/home/kali/.gemini/antigravity/scratch/electron_bin/dist" ]; then
    echo "[BUILD] Bundling Electron binary..."
    mkdir -p "${STAGING}/opt/mantis-mobile-forensics/electron_bin"
    cp -r "/home/kali/.gemini/antigravity/scratch/electron_bin/dist" "${STAGING}/opt/mantis-mobile-forensics/electron_bin/"
fi

# 7. Create /usr/bin launcher
cat << 'EOF' > "${STAGING}/usr/bin/mantis-forensics"
#!/usr/bin/env bash
exec /opt/mantis-mobile-forensics/scripts/mantis-forensics "$@"
EOF
chmod 755 "${STAGING}/usr/bin/mantis-forensics"

# 8. Desktop entry and icons
cp "${ROOT_DIR}/assets/mantis-mobile-forensics.desktop" "${STAGING}/usr/share/applications/"
cp "${ROOT_DIR}/assets/icon.png" "${STAGING}/usr/share/pixmaps/mantis.png"
mkdir -p "${STAGING}/usr/share/icons/hicolor/256x256/apps"
cp "${ROOT_DIR}/assets/mantis.png" "${STAGING}/usr/share/icons/hicolor/256x256/apps/mantis.png"
cp "${ROOT_DIR}/assets/mantis.png" "${STAGING}/usr/share/icons/hicolor/scalable/apps/mantis.png"
cp "${ROOT_DIR}/assets/icon.svg" "${STAGING}/usr/share/icons/hicolor/scalable/apps/mantis.svg"

# Ensure standard Debian package permissions
chmod 755 "${STAGING}/DEBIAN"
chmod 755 "${STAGING}/DEBIAN/postinst"
chmod 755 "${STAGING}/DEBIAN/prerm"
chmod 644 "${STAGING}/DEBIAN/control"

# 9. Build Debian package with dpkg-deb using gzip compression
echo "[BUILD] Assembling .deb package with dpkg-deb..."
dpkg-deb -Zgzip --build --root-owner-group "${STAGING}" "${ROOT_DIR}/${DEB_NAME}"

echo "=========================================================="
echo "  Debian Package Created Successfully:"
echo "  ${ROOT_DIR}/${DEB_NAME}"
echo "=========================================================="
ls -lh "${ROOT_DIR}/${DEB_NAME}"
