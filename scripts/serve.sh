#!/bin/sh
# Serves this folder on the LAN so a GameCube can use it as a source before a
# change is merged: on the console, Sources, X, http://<address>:8765/index.json
cd "$(dirname "$0")/.." || exit 1
port=${1:-8765}
addr=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | cut -d' ' -f1)
echo "Add this source on the console: http://${addr:-<this computer's address>}:$port/index.json"
exec python3 -m http.server "$port"
