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

# --- 4b. Build Narrative.Rx.app bundle into /Applications ---
echo "[build-pkg] Assembling Narrative.Rx.app..."
APP_BUNDLE="$PKGROOT/Applications/Narrative.Rx.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
cp "$REPO_ROOT/installer/mac/app/Info.plist" "$APP_BUNDLE/Contents/Info.plist"
# Substitute the version so the About panel shows the right number
sed -i '' "s|>1.0.0<|>$VERSION<|g" "$APP_BUNDLE/Contents/Info.plist"
cp "$REPO_ROOT/installer/mac/app/NarrativeRx" "$APP_BUNDLE/Contents/MacOS/NarrativeRx"
chmod +x "$APP_BUNDLE/Contents/MacOS/NarrativeRx"

# Convert the 512x512 PNG source into a multi-resolution .icns
if command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
    ICONSET="$BUILD_ROOT/AppIcon.iconset"
    mkdir -p "$ICONSET"
    SRC_PNG="$REPO_ROOT/frontend/public/logo512.png"
    for size in 16 32 128 256 512; do
        sips -z "$size" "$size"     "$SRC_PNG" --out "$ICONSET/icon_${size}x${size}.png"    >/dev/null
        sips -z $((size*2)) $((size*2)) "$SRC_PNG" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
    done
    iconutil -c icns -o "$APP_BUNDLE/Contents/Resources/AppIcon.icns" "$ICONSET"
    echo "[build-pkg] Icon generated."
else
    echo "[build-pkg] WARN: sips/iconutil not found — the .app will use a generic icon."
fi

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
Narrative.Rx has been installed.

A Terminal window will now open to complete the interactive
setup (Homebrew, Python, MongoDB — about 5 minutes).

Once setup finishes, open the app any time from:
   * Applications > Narrative.Rx
   * Spotlight (Cmd+Space) - type "Narrative"
   * http://localhost:8080

If the Terminal window doesn't appear, double-click:
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
