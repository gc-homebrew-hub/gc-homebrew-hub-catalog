#!/bin/sh
# Serves this folder on the LAN so a GameCube can use it as a source before a
# change is merged: on the console, Sources, X, http://<address>:8765/index.json
# It also serves a test source (scripts/make-test-source.py) at test/index.json;
# give a version to serve that version of the test app: serve.sh 8765 2
cd "$(dirname "$0")/.." || exit 1
port=${1:-8765}
addr=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | cut -d' ' -f1)
python3 scripts/make-test-source.py "${addr:-127.0.0.1}" "$port" "${2:-1}" || exit 1
echo "Add this source on the console: http://${addr:-<this computer's address>}:$port/index.json"
echo "Test source (copytest ${2:-1}): http://${addr:-<this computer's address>}:$port/test/index.json"
exec python3 -m http.server "$port"
