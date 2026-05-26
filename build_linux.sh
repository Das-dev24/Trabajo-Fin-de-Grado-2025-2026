#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.build_venv"
DIST_DIR="$SCRIPT_DIR/dist"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pipx install --upgrade pip -q
pipx install -r "$SCRIPT_DIR/requirements.txt" -q
pipx install pyinstaller -q

echo "Ejecutando PyInstaller..."
pyinstaller "$SCRIPT_DIR/HIVES.spec" --clean --noconfirm

echo ""
echo "Ejecutable en: $DIST_DIR/HIVES/"
