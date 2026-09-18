#!/bin/bash
set -e

REPO="masterkoco/GreedyMedia"
INSTALL_DIR="/opt/greedy-media-utility"
DESKTOP_FILE="/usr/share/applications/greedy-media-utility.desktop"
TAR_URL="https://github.com/${REPO}/releases/latest/download/GreedyMediaUtility-Linux.tar.gz"

if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run this installer with sudo: sudo bash install.sh"
  exit 1
fi

echo "[+] Downloading latest release of Greedy Media Utility from GitHub..."
TMP_DIR=$(mktemp -d)
curl -L -o "${TMP_DIR}/greedy-media.tar.gz" "$TAR_URL"

echo "[+] Installing application files to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
tar -xzf "${TMP_DIR}/greedy-media.tar.gz" -C "$INSTALL_DIR" --strip-components=1

echo "[+] Creating desktop application shortcut..."
cat << EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Name=Greedy Media Utility
Exec=${INSTALL_DIR}/greedy-media-utility
Icon=${INSTALL_DIR}/icon.jpeg
Terminal=false
Categories=AudioVideo;Video;
EOF

chmod +x "${INSTALL_DIR}/greedy-media-utility"
update-desktop-database 2>/dev/null || true

rm -rf "$TMP_DIR"
echo "[✅] Greedy Media Utility installed successfully! You can now launch it from your system application menu."
