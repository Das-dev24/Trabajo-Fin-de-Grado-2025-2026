#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="/tmp/.build_venv"
DIST_DIR="$SCRIPT_DIR/dist"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q
pip install pyinstaller -q

echo "Ejecutando PyInstaller..."
pyinstaller "$SCRIPT_DIR/HIVES.spec" --clean --noconfirm

echo ""
echo "Ejecutable en: $DIST_DIR/HIVES/"
