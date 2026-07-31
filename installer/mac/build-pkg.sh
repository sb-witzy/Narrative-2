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

# --- 3. Copy mac helper files (launchd plists, firstrun) ---
mkdir -p "$PKGROOT$APP_PATH/mac"
cp -R "$REPO_ROOT/installer/mac/launchd" "$PKGROOT$APP_PATH/mac/"
cp "$REPO_ROOT/installer/mac/firstrun.command" "$PKGROOT$APP_PATH/mac/"
cp "$REPO_ROOT/installer/mac/updater.sh" "$PKGROOT$APP_PATH/mac/" 2>/dev/null || true
chmod +x "$PKGROOT$APP_PATH/mac/firstrun.command"
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

This installer will:
  1. Install Homebrew (if not present)
  2. Install python@3.12 and mongodb-community
  3. Set up Narrative.Rx as a launchd service
  4. Open the app at http://localhost:8080

You'll need administrator credentials.

For Apple Silicon (M1/M2/M3) Macs, macOS 12+.
W
cat > "$RES_DIR/conclusion.txt" <<'C'
Narrative.Rx is installed.

A Terminal window has opened so you can paste your Emergent
LLM key. Log into the app at http://localhost:8080 once setup
finishes.

You can re-run the wizard from:
   /Library/Application Support/NarrativeRx/mac/firstrun.command
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
