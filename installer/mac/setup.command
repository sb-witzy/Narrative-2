#!/bin/bash
# Narrative.Rx — macOS interactive setup.
# Opened automatically by the .pkg postinstall in Terminal.app.
# Can also be re-run manually if the initial install had trouble:
#    /Library/Application Support/NarrativeRx/mac/setup.command
#
# This script assumes it's being run as a normal user in a real Terminal
# window — so it CAN prompt for `sudo` passwords and Homebrew's own
# interactive install works. Any step that fails is visible and the user
# can re-run.

set -u
APP_DIR="/Library/Application Support/NarrativeRx"
ENV_FILE="$APP_DIR/.env"
LOG_DIR="/Library/Logs/NarrativeRx"
LAUNCHD_APP="/Library/LaunchDaemons/com.narrativerx.app.plist"
LAUNCHD_MONGO="/Library/LaunchDaemons/com.narrativerx.mongodb.plist"
STAMP=$(date +%Y%m%d-%H%M%S)

sudo mkdir -p "$LOG_DIR" 2>/dev/null
SETUP_LOG="$LOG_DIR/setup-$STAMP.log"

# Duplicate everything to a log file for later debugging
exec > >(tee "$SETUP_LOG") 2>&1

clear
cat <<HEADER

============================================================
     Narrative.Rx — First time setup
============================================================

I'll install a few things your Mac needs (Homebrew, Python 3.12,
MongoDB) and configure Narrative.Rx to launch automatically at
boot.

You'll be asked for your Mac password once or twice — that's
normal, macOS needs it to install services.

Log for this run:  $SETUP_LOG

Press Enter to continue, or Ctrl+C to bail.
HEADER
read -r

step() {
    echo
    echo "-----------------------------------------------------------"
    echo ">>> $*"
    echo "-----------------------------------------------------------"
}

fail() {
    echo
    echo "!!! $*"
    echo "!!! Setup stopped. Fix the above, then re-run:"
    echo "!!!   $APP_DIR/mac/setup.command"
    echo
    read -p "Press Enter to close..." _
    exit 1
}

# --- 1. Xcode Command Line Tools ---
step "Checking for Xcode Command Line Tools"
if ! xcode-select -p >/dev/null 2>&1; then
    echo "Not installed. Requesting install (a dialog will appear)..."
    xcode-select --install
    echo "Please click 'Install' in the popup and wait for it to finish."
    echo "This can take 5-10 minutes."
    read -p "When Xcode CLT is done installing, press Enter to continue..." _
fi
if ! xcode-select -p >/dev/null 2>&1; then
    fail "Xcode CLT still not detected. Run 'xcode-select --install' manually and re-run this setup."
fi
echo "OK."

# --- 2. Homebrew ---
step "Checking for Homebrew"
BREW_BIN=""
if [ -x /opt/homebrew/bin/brew ]; then BREW_BIN="/opt/homebrew/bin/brew"; fi
if [ -z "$BREW_BIN" ] && [ -x /usr/local/bin/brew ]; then BREW_BIN="/usr/local/bin/brew"; fi
if [ -z "$BREW_BIN" ]; then
    echo "Not installed. Installing Homebrew (this can take a few minutes)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
        || fail "Homebrew installation failed."
    if [ -x /opt/homebrew/bin/brew ]; then BREW_BIN="/opt/homebrew/bin/brew"; fi
    if [ -z "$BREW_BIN" ] && [ -x /usr/local/bin/brew ]; then BREW_BIN="/usr/local/bin/brew"; fi
fi
[ -z "$BREW_BIN" ] && fail "Homebrew still not found on PATH after install."
echo "Homebrew: $BREW_BIN"
BREW_PREFIX=$("$BREW_BIN" --prefix)

# --- 3. Python 3.12 ---
step "Installing Python 3.12"
if ! "$BREW_BIN" list python@3.12 >/dev/null 2>&1; then
    "$BREW_BIN" install python@3.12 || fail "brew install python@3.12 failed."
fi
PYTHON_BIN="$BREW_PREFIX/opt/python@3.12/bin/python3.12"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$BREW_PREFIX/bin/python3"
[ -x "$PYTHON_BIN" ] || fail "Python 3.12 not found after brew install."
echo "Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# --- 4. MongoDB Community ---
step "Installing MongoDB Community"
# Step 4a: tap under HOMEBREW_NO_INSTALL_FROM_API so third-party tap load works.
if ! "$BREW_BIN" tap | grep -q '^mongodb/brew$'; then
    HOMEBREW_NO_INSTALL_FROM_API=1 "$BREW_BIN" tap mongodb/brew \
        || fail "brew tap mongodb/brew failed."
fi
"$BREW_BIN" tap --repair 2>/dev/null || true

# Step 4b: trust the tap (Homebrew 4.4+ requires this before any formula load).
if "$BREW_BIN" trust --help >/dev/null 2>&1; then
    echo "Trusting mongodb/brew tap..."
    "$BREW_BIN" trust mongodb/brew 2>/dev/null || \
        "$BREW_BIN" trust --formula mongodb/brew/mongodb-community 2>/dev/null || \
        echo "(brew trust step is a no-op on this Homebrew version)"
fi

# Step 4c: install WITH the API enabled so 'mongosh' (migrated to
# homebrew/core) resolves correctly as a transitive dependency.
if ! "$BREW_BIN" list mongodb-community >/dev/null 2>&1; then
    "$BREW_BIN" install mongodb/brew/mongodb-community \
        || fail "brew install mongodb/brew/mongodb-community failed. Try 'brew doctor' and re-launch this setup."
fi
MONGOD_BIN="$BREW_PREFIX/opt/mongodb-community/bin/mongod"
MONGOD_CONF="$BREW_PREFIX/etc/mongod.conf"
[ -x "$MONGOD_BIN" ] || fail "mongod binary not found after brew install."
echo "MongoDB: $MONGOD_BIN"

# --- 5. Python venv + backend deps ---
step "Creating Python virtual environment and installing backend deps"
# /Library/Application Support/NarrativeRx/ was extracted by the .pkg as
# root:wheel, so the current user can't write inside it. Run venv + pip
# via sudo — the resulting venv is root-owned which matches the launchd
# daemon (also root) that will exec python from it.
if [ ! -x "$APP_DIR/backend/.venv/bin/python" ]; then
    sudo "$PYTHON_BIN" -m venv "$APP_DIR/backend/.venv" \
        || fail "python -m venv failed."
fi
sudo "$APP_DIR/backend/.venv/bin/python" -m pip install --upgrade pip \
    || fail "pip upgrade failed."
sudo "$APP_DIR/backend/.venv/bin/python" -m pip install \
    -r "$APP_DIR/backend/requirements.txt" \
    --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
    || fail "pip install requirements failed."
echo "Backend deps installed."

# --- 6. Seed .env if missing (LLM key stays empty — filled by firstrun.command) ---
step "Preparing configuration file"
if [ ! -f "$ENV_FILE" ]; then
    JWT=$("$APP_DIR/backend/.venv/bin/python" -c 'import secrets; print(secrets.token_hex(32))')
    ACT=$(cat "$APP_DIR/activation-key.txt" 2>/dev/null || echo "NRX-TEMP-KEY-0001")
    sudo tee "$ENV_FILE" >/dev/null <<ENVEOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=narrative_rx
CORS_ORIGINS=http://localhost:8080
JWT_SECRET=$JWT
EMERGENT_LLM_KEY=
ADMIN_EMAIL=admin@dental.com
ADMIN_PASSWORD=admin123
SERVE_FRONTEND=1
MAX_CONCURRENT_LLM=3
ACTIVATION_KEY=$ACT
PRACTICE_NAME=
ENVEOF
    sudo chmod 600 "$ENV_FILE"
    echo "Wrote $ENV_FILE"
    echo "Activation key: $ACT"
else
    echo ".env already exists — leaving as-is."
fi

# --- 7. Install and load launchd services ---
step "Installing background services"
# Patch the plist templates so they point at the actual brew prefix
sudo bash -c "sed 's|/opt/homebrew|$BREW_PREFIX|g' '$APP_DIR/mac/launchd/com.narrativerx.mongodb.plist' > '$LAUNCHD_MONGO'"
sudo bash -c "sed 's|/opt/homebrew|$BREW_PREFIX|g' '$APP_DIR/mac/launchd/com.narrativerx.app.plist' > '$LAUNCHD_APP'"
sudo chown root:wheel "$LAUNCHD_APP" "$LAUNCHD_MONGO"
sudo chmod 644 "$LAUNCHD_APP" "$LAUNCHD_MONGO"

sudo launchctl unload "$LAUNCHD_MONGO" 2>/dev/null || true
sudo launchctl load "$LAUNCHD_MONGO" || fail "Could not load MongoDB launchd service."
sudo launchctl unload "$LAUNCHD_APP" 2>/dev/null || true
sudo launchctl load "$LAUNCHD_APP" || fail "Could not load Narrative.Rx launchd service."

step "Waiting for backend to bind port 8080"
for i in $(seq 1 30); do
    if curl -fsS http://localhost:8080/api/ >/dev/null 2>&1; then
        echo "Backend is up."
        break
    fi
    printf "."
    sleep 1
done
echo

# --- 8. Prompt for Emergent LLM key ---
step "Emergent LLM key"
echo "Narrative.Rx needs an Emergent LLM key to generate narratives."
echo "Get yours at https://app.emergent.sh (Profile -> Universal Key)."
echo
read -p "Paste your Emergent LLM key (or press Enter to skip): " LLM_KEY
if [ -n "$LLM_KEY" ]; then
    sudo sed -i '' "s|^EMERGENT_LLM_KEY=.*|EMERGENT_LLM_KEY=$LLM_KEY|" "$ENV_FILE"
    sudo launchctl unload "$LAUNCHD_APP" 2>/dev/null
    sudo launchctl load "$LAUNCHD_APP"
    echo "Saved. Service restarted."
fi

# --- 9. Done ---
cat <<DONE

============================================================
     Setup complete
============================================================

Narrative.Rx is now running in the background.

To open the app any time:
   * Open Applications > Narrative.Rx
   * Or search Spotlight (Cmd+Space) for "Narrative"
   * Or visit http://localhost:8080 in your browser

Log in with:
   Email:    admin@dental.com
   Password: admin123

Change your password in Settings once logged in.

To re-run this setup or update your LLM key later:
   $APP_DIR/mac/setup.command

Your practice activation key:
   $(cat "$APP_DIR/activation-key.txt" 2>/dev/null || echo "NRX-XXXX-XXXX-XXXX")
============================================================

DONE
sleep 2
open "http://localhost:8080" 2>/dev/null || true
read -p "Press Enter to close this window..." _
