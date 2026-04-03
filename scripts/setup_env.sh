#!/usr/bin/env bash
set -euo pipefail

echo "============================================"
echo " AI-DAN Local Setup"
echo "============================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 was not found on your system."
  echo "Install Python 3.11+ and rerun this script."
  exit 1
fi

if ! command -v pip3 >/dev/null 2>&1; then
  echo "[ERROR] pip3 was not found on your system."
  echo "Install pip for Python 3 and rerun this script."
  exit 1
fi

echo "[INFO] Python found: $(python3 --version)"
echo "[INFO] Installing dependencies from requirements.txt..."
python3 -m pip install --upgrade -r requirements.txt

echo "[INFO] Verifying imports..."
python3 -c "import fastapi, streamlit, pydantic; print('Dependency check passed.')"

echo
echo "[SUCCESS] Environment setup completed."
echo "You can now run:"
echo "  ./scripts/start_local.sh"
