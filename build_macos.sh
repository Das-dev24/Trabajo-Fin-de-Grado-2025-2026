#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${TMPDIR:-/tmp}/.hives_build_venv"
DIST_DIR="$SCRIPT_DIR/dist"

PYTHON="${PYTHON:-}"

# Si se especificó PYTHON, lo usamos directamente
if [ -n "$PYTHON" ]; then
    if [ ! -x "$PYTHON" ]; then
        echo "ERROR: \$PYTHON ($PYTHON) no es un ejecutable válido." >&2
        exit 1
    fi
else
    for cand in python3 python; do
        p="$(command -v "$cand" 2>/dev/null || true)"
        if [ -n "$p" ]; then
            PYTHON="$p"
            break
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo "No se encontró un intérprete de Python."
    if ! command -v uv >/dev/null 2>&1; then
        echo "Instalando uv para provisionar Python..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
        export PATH="$HOME/.local/bin:$PATH"
    fi
    echo "Descargando Python 3 con uv..."
    uv python install 3
    PYTHON="$(uv python find 3)"
fi

echo "Usando intérprete: $PYTHON ($("$PYTHON" --version 2>&1))"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q
pip install pyinstaller -q

echo "Ejecutando PyInstaller..."
pyinstaller "$SCRIPT_DIR/HIVES.spec" --clean --noconfirm

echo ""
echo "Aplicación en: $DIST_DIR/HIVES.app"
