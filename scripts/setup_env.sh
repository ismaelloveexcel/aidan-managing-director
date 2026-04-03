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

VENV_DIR=".venv"
VENV_PYTHON="${VENV_DIR}/bin/python"

echo "[INFO] Python found: $(python3 --version)"

if [ ! -x "${VENV_PYTHON}" ]; then
  echo "[INFO] Creating project virtual environment in ${VENV_DIR}..."
  python3 -m venv "${VENV_DIR}"
fi

echo "[INFO] Installing dependencies from requirements.txt into ${VENV_DIR}..."
"${VENV_PYTHON}" -m pip install -r requirements.txt

echo "[INFO] Verifying imports..."
"${VENV_PYTHON}" -c "import fastapi, streamlit, pydantic; print('Dependency check passed.')"

echo
echo "[SUCCESS] Environment setup completed."
echo "You can now run:"
echo "  source ${VENV_DIR}/bin/activate"
echo "  ./scripts/start_local.sh"
