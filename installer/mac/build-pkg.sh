#!/bin/bash
# Build the Narrative.Rx macOS .pkg installer.
# Assembles a payload directory, then runs `pkgbuild` + `productbuild`.
#
# Usage (invoked by .github/workflows/build-installer-mac.yml):
#   ./installer/mac/build-pkg.sh <version>
# Output:
#   installer/dist/NarrativeRx-Setup-<version>.pkg

set -euo pipefail

VERSION="${1:-0.0.0-dev}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_ROOT="$REPO_ROOT/installer/mac/_build"
PKGROOT="$BUILD_ROOT/pkgroot"
SCRIPTS_DIR="$BUILD_ROOT/scripts"
DIST_DIR="$REPO_ROOT/installer/dist"
APP_PATH="/Library/Application Support/NarrativeRx"
IDENTIFIER="com.narrativerx.app"

echo "[build-pkg] version=$VERSION"
rm -rf "$BUILD_ROOT"
mkdir -p "$PKGROOT$APP_PATH" "$SCRIPTS_DIR" "$DIST_DIR"

# --- 1. Copy backend source ---
echo "[build-pkg] Copying backend..."
mkdir -p "$PKGROOT$APP_PATH/backend"
rsync -a \
    --exclude='.env' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='tests' \
    "$REPO_ROOT/backend/" "$PKGROOT$APP_PATH/backend/"

# --- 2. Copy pre-built frontend ---
echo "[build-pkg] Copying frontend build..."
mkdir -p "$PKGROOT$APP_PATH/frontend/build"
rsync -a "$REPO_ROOT/frontend/build/" "$PKGROOT$APP_PATH/frontend/build/"

# --- 3. Copy mac helper files (launchd plists, setup wizard, updater) ---
mkdir -p "$PKGROOT$APP_PATH/mac"
cp -R "$REPO_ROOT/installer/mac/launchd" "$PKGROOT$APP_PATH/mac/"
cp "$REPO_ROOT/installer/mac/setup.command" "$PKGROOT$APP_PATH/mac/"
cp "$REPO_ROOT/installer/mac/updater.sh" "$PKGROOT$APP_PATH/mac/" 2>/dev/null || true
chmod +x "$PKGROOT$APP_PATH/mac/setup.command"
[ -f "$PKGROOT$APP_PATH/mac/updater.sh" ] && chmod +x "$PKGROOT$APP_PATH/mac/updater.sh"

# --- 4. VERSION marker (read by /api/system/version) ---
echo -n "$VERSION" > "$PKGROOT$APP_PATH/VERSION"

# --- 5. Postinstall script ---
cp "$REPO_ROOT/installer/mac/scripts/postinstall" "$SCRIPTS_DIR/postinstall"
chmod +x "$SCRIPTS_DIR/postinstall"

# --- 6. Build component package ---
echo "[build-pkg] Building component pkg..."
COMPONENT_PKG="$BUILD_ROOT/component.pkg"
pkgbuild \
    --root "$PKGROOT" \
    --scripts "$SCRIPTS_DIR" \
    --identifier "$IDENTIFIER" \
    --version "$VERSION" \
    --install-location "/" \
    "$COMPONENT_PKG"

# --- 7. Build distribution (product) package ---
echo "[build-pkg] Building distribution pkg..."
DIST_XML="$BUILD_ROOT/distribution.xml"
cat > "$DIST_XML" <<XMLEOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>Narrative.Rx $VERSION</title>
    <organization>com.narrativerx</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" hostArchitectures="arm64"/>
    <volume-check>
        <allowed-os-versions>
            <os-version min="12.0"/>
        </allowed-os-versions>
    </volume-check>
    <welcome file="welcome.txt" mime-type="text/plain"/>
    <license file="LICENSE.txt" mime-type="text/plain"/>
    <conclusion file="conclusion.txt" mime-type="text/plain"/>
    <choices-outline>
        <line choice="default">
            <line choice="$IDENTIFIER"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="$IDENTIFIER" visible="false">
        <pkg-ref id="$IDENTIFIER"/>
    </choice>
    <pkg-ref id="$IDENTIFIER" version="$VERSION" onConclusion="none">component.pkg</pkg-ref>
</installer-gui-script>
XMLEOF

# Welcome / License / Conclusion (shown by the installer GUI)
RES_DIR="$BUILD_ROOT/resources"
mkdir -p "$RES_DIR"
cat > "$RES_DIR/welcome.txt" <<'W'
Welcome to Narrative.Rx.

This installer copies the app to your Mac. When it finishes, a
Terminal window will pop up to walk you through the one-time
setup (Homebrew, Python 3.12, MongoDB) — you'll be asked for
your Mac password once so the setup can install services.

If the Terminal window doesn't open automatically, double-click:
  /Library/Application Support/NarrativeRx/mac/setup.command

For Apple Silicon (M1/M2/M3/M4) Macs, macOS 12+.
W
cat > "$RES_DIR/conclusion.txt" <<'C'
Narrative.Rx files have been copied to your Mac.

A Terminal window has opened to complete the interactive setup.
Please follow the prompts in that window — it will install
Homebrew, Python, and MongoDB (about 5 minutes), then open the
app at http://localhost:8080.

If you closed the Terminal window by accident, re-run:
  /Library/Application Support/NarrativeRx/mac/setup.command
C
if [ -f "$REPO_ROOT/installer/EULA.txt" ]; then
    cp "$REPO_ROOT/installer/EULA.txt" "$RES_DIR/LICENSE.txt"
else
    echo "See https://github.com/sb-witzy/Narrative-2 for license terms." > "$RES_DIR/LICENSE.txt"
fi

FINAL_PKG="$DIST_DIR/NarrativeRx-Setup-$VERSION.pkg"
productbuild \
    --distribution "$DIST_XML" \
    --resources "$RES_DIR" \
    --package-path "$BUILD_ROOT" \
    "$FINAL_PKG"

echo "[build-pkg] Done: $FINAL_PKG"
ls -lh "$FINAL_PKG"
