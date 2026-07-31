#!/bin/bash
# Narrative.Rx macOS self-update runner.
# Spawned DETACHED by POST /api/system/update when the app is installed
# via NarrativeRx-Setup-<version>.pkg.
#
# Args:
#   $1 = download URL for the new .pkg from GitHub Releases

set -u
DOWNLOAD_URL="${1:-}"
if [ -z "$DOWNLOAD_URL" ]; then
    echo "usage: $0 <pkg-url>" >&2
    exit 2
fi

LOG_DIR="/Library/Logs/NarrativeRx"
mkdir -p "$LOG_DIR"
STAMP=$(date +%Y%m%d-%H%M%S)
LOG="$LOG_DIR/update-$STAMP.log"
PKG="/tmp/NarrativeRx-Setup-latest.pkg"

exec > "$LOG" 2>&1
echo "=== macOS self-update @ $(date) ==="
echo "URL: $DOWNLOAD_URL"

# Give the HTTP 202 time to flush to the browser
sleep 3

echo "Downloading $PKG ..."
if ! curl -fL --retry 3 --retry-delay 2 --max-time 900 -o "$PKG" "$DOWNLOAD_URL"; then
    echo "Download failed"
    exit 1
fi
SIZE=$(stat -f '%z' "$PKG")
echo "Downloaded $SIZE bytes"
if [ "$SIZE" -lt 10000000 ]; then
    echo "Download too small — probably an error page. Aborting."
    rm -f "$PKG"
    exit 1
fi

echo "Stopping backend service..."
launchctl unload /Library/LaunchDaemons/com.narrativerx.app.plist 2>/dev/null || true

echo "Running installer -pkg ..."
if ! sudo -n installer -pkg "$PKG" -target / >> "$LOG" 2>&1; then
    # -n (non-interactive) will fail without a passwordless sudoers entry.
    # Fall back to interactive so the pkg still installs when triggered from
    # a Terminal session; if the backend service triggered this (launchd
    # root context), the first attempt should already have succeeded.
    installer -pkg "$PKG" -target / >> "$LOG" 2>&1 || {
        echo "installer failed — restarting old version"
        launchctl load /Library/LaunchDaemons/com.narrativerx.app.plist
        exit 1
    }
fi

echo "Restarting backend..."
launchctl load /Library/LaunchDaemons/com.narrativerx.app.plist

rm -f "$PKG"
echo "=== update done @ $(date) ==="
