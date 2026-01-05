#!/usr/bin/env bash
set -euo pipefail

# Simple local deploy script for Salehi
# Runs a pull + venv deps + service restart from the repo root.

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[deploy] Updating source in ${APP_DIR}"
cd "${APP_DIR}"

# Track current branch to pull the matching remote branch (per-env configs)
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
SERVICE_NAME="${BRANCH}.service"
git fetch --all --prune
git reset --hard "origin/${BRANCH}"

# Ensure asterisk user can write audio outputs and sounds dirs (run after pull so new files are covered)
if id asterisk >/dev/null 2>&1; then
  CHOWN_BIN="chown"
  CHMOD_BIN="chmod"
  if command -v sudo >/dev/null 2>&1; then
    CHOWN_BIN="sudo chown"
    CHMOD_BIN="sudo chmod"
  fi

  ${CHOWN_BIN} -R asterisk:asterisk "${APP_DIR}/assets/audio" || true
  ${CHMOD_BIN} -R 775 "${APP_DIR}/assets/audio" || true

  for path in /usr/share/asterisk/sounds/custom /usr/share/asterisk/sounds/en/custom /var/lib/asterisk/sounds/custom /var/lib/asterisk/sounds/en/custom; do
    ${CHOWN_BIN} -R asterisk:asterisk "$path" || true
    ${CHMOD_BIN} -R 775 "$path" || true
  done
fi

python3 -m venv "${APP_DIR}/venv" || true
source "${APP_DIR}/venv/bin/activate"
pip install --upgrade pip
pip install --upgrade -r "${APP_DIR}/requirements.txt"

if command -v systemctl >/dev/null 2>&1; then
  echo "[deploy] Restarting ${SERVICE_NAME}"
  if sudo -n true 2>/dev/null; then
    sudo systemctl restart "${SERVICE_NAME}"
  else
    systemctl restart "${SERVICE_NAME}"
  fi
else
  echo "[deploy] systemctl not found; skipping service restart"
fi

echo "[deploy] Update complete"
