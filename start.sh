#!/usr/bin/env bash
# 0x Cookies — one-shot launcher for localhost & VPS.
#
# Usage:
#   ./start.sh                 # panel on http://0.0.0.0:8080
#   ./start.sh --port 9000     # custom port
#   HOST=127.0.0.1 ./start.sh  # bind to localhost only
#
# It will:
#   1. create/prepare a local Chromium browser (Playwright)
#   2. install missing system libraries for headless Chromium when possible
#      (apt on Debian/Ubuntu, dnf on RHEL/Fedora, apk on Alpine)
#   3. auto-add ./third_party/lib (if you dropped extracted .so files there)
#      to LD_LIBRARY_PATH
#   4. start the control panel
set -euo pipefail
cd "$(dirname "$0")"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

echo "[0x Cookies] python: $(python3 --version 2>&1)"

# --- 1. make sure playwright + chromium are present ---------------------------
if ! python3 -c "import playwright" 2>/dev/null; then
  echo "[0x Cookies] installing playwright (pip)…"
  python3 -m pip install --quiet --upgrade playwright || {
    echo "[0x Cookies] pip install failed — install 'playwright' manually."; }
fi

if ! python3 -m playwright install chromium >/dev/null 2>&1; then
  echo "[0x Cookies] downloading Chromium for Playwright…"
  python3 -m playwright install chromium || true
fi

# --- 2. system libs for headless Chromium ------------------------------------
missing_lib() { ! ldconfig -p 2>/dev/null | grep -q "$1"; }

if missing_lib "libglib-2.0.so.0" || missing_lib "libnss3.so"; then
  echo "[0x Cookies] installing Chromium system libraries…"
  if command -v apt-get >/dev/null; then
    if [ "$(id -u)" = "0" ]; then APT="apt-get"; else APT="sudo apt-get"; fi
    $APT update -y >/dev/null 2>&1 || true
    $APT install -y libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
      libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 \
      libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
      libatspi2.0-0 libxshmfence1 >/dev/null 2>&1 || \
      python3 -m playwright install-deps chromium || true
  elif command -v dnf >/dev/null; then
    sudo dnf install -y glib2 nss nspr atk at-spi2-atk cups-libs libdrm \
      libxkbcommon libXcomposite libXdamage libXfixes libXrandr mesa-libgbm \
      alsa-lib pango cairo >/dev/null 2>&1 || true
  elif command -v apk >/dev/null; then
    sudo apk add --no-cache glib nss nspr atk at-spi2-atk cups-libs libdrm \
      libxkbcommon libxcomposite libxdamage libxfixes libxrandr mesa-gbm \
      alsa-lib pango cairo >/dev/null 2>&1 || true
  fi
fi

# --- 3. optional local third-party libs --------------------------------------
LIBDIRS=""
for d in ./third_party/lib ./third_party/lib/x86_64-linux-gnu ./third_party/lib/aarch64-linux-gnu; do
  [ -d "$d" ] && LIBDIRS="${LIBDIRS:+$LIBDIRS:}$d"
done
if [ -n "$LIBDIRS" ]; then
  export LD_LIBRARY_PATH="$LIBDIRS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  echo "[0x Cookies] LD_LIBRARY_PATH += $LIBDIRS"
fi

# --- 4. run ------------------------------------------------------------------
export OXC_HOST="$HOST" OXC_PORT="$PORT"
python3 - <<'PY'
import os
print(f"[0x Cookies] starting panel on http://{os.environ.get('OXC_HOST')}:{os.environ.get('OXC_PORT')}")
PY
exec python3 server.py --host "$HOST" --port "$PORT"
