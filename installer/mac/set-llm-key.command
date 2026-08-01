#!/bin/bash
# Narrative.Rx — LLM key entry wizard (macOS).
# Opened on first click of the Narrative.Rx.app icon when the .env has no
# EMERGENT_LLM_KEY. Also re-runnable any time from:
#   /Library/Application Support/NarrativeRx/mac/set-llm-key.command
# to rotate the key.

set -u
APP_DIR="/Library/Application Support/NarrativeRx"
ENV_FILE="$APP_DIR/.env"
LAUNCHD_APP="/Library/LaunchDaemons/com.narrativerx.app.plist"

clear
cat <<HEADER

============================================================
     Narrative.Rx — Enter your Emergent LLM key
============================================================

Narrative.Rx uses your Emergent LLM key to generate insurance
narratives with Claude AI. You'll only need to paste it once.

Get your key at:
   https://app.emergent.sh -> Profile -> Universal Key

Press Ctrl+C to cancel.
------------------------------------------------------------
HEADER

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found."
    echo "Please run setup.command first:"
    echo "  $APP_DIR/mac/setup.command"
    read -p "Press Enter to close..." _
    exit 1
fi

read -p "Paste your Emergent LLM key: " LLM_KEY
if [ -z "$LLM_KEY" ]; then
    echo
    echo "No key entered. Aborting."
    read -p "Press Enter to close..." _
    exit 1
fi

echo
echo "Saving key and restarting service (you may be asked for your Mac password)..."
sudo sed -i '' "s|^EMERGENT_LLM_KEY=.*|EMERGENT_LLM_KEY=$LLM_KEY|" "$ENV_FILE"
# Drop a world-readable marker so the Narrative.Rx.app launcher (running
# as the console user, without sudo) can tell the key has been set without
# needing to read the root-only .env file.
sudo touch "$APP_DIR/.llm-key-set"
sudo chmod 644 "$APP_DIR/.llm-key-set"
sudo launchctl unload "$LAUNCHD_APP" 2>/dev/null
sudo launchctl load "$LAUNCHD_APP"

echo
echo "Waiting for the service to come back up..."
for _ in $(seq 1 15); do
    if curl -fsS -m 1 http://localhost:8080/api/ >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

cat <<DONE

============================================================
     Done — Narrative.Rx is ready to use
============================================================

Opening http://localhost:8080 in your browser...

Log in with:
   Email:    admin@dental.com
   Password: admin123

Change your password in Settings once you're in.
============================================================

DONE
sleep 1
open "http://localhost:8080" 2>/dev/null || true
read -p "Press Enter to close this window..." _
