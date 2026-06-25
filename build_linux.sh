#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="/tmp/.build_venv"
DIST_DIR="$SCRIPT_DIR/dist"

#Versiones de python compatibles con TensorFlow
TF_MAX_MINOR=12
TF_MIN_MINOR=9

py_minor() { "$1" -c 'import sys; print(sys.version_info[1])' 2>/dev/null; }

is_compatible() {
    local py="$1" minor
    minor="$(py_minor "$py")" || return 1
    [ -n "$minor" ] || return 1
    [ "$minor" -ge "$TF_MIN_MINOR" ] && [ "$minor" -le "$TF_MAX_MINOR" ]
}

PYTHON="${PYTHON:-}"

#Comprobamos si el python instalado es compatible
if [ -n "$PYTHON" ]; then
    if ! is_compatible "$PYTHON"; then
        echo "ERROR: \$PYTHON ($PYTHON) no es compatible con TensorFlow (requiere 3.${TF_MIN_MINOR}–3.${TF_MAX_MINOR})." >&2
        exit 1
    fi
# 2) Otherwise probe common interpreter names on PATH.
else
    for cand in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python; do
        p="$(command -v "$cand" 2>/dev/null || true)"
        if [ -n "$p" ] && is_compatible "$p"; then
            PYTHON="$p"
            break
        fi
    done
fi

#Si no encuentra python contabile lo instala con uv
if [ -z "$PYTHON" ]; then
    echo "No se encontró un Python compatible con TensorFlow (3.${TF_MIN_MINOR}–3.${TF_MAX_MINOR})."
    if ! command -v uv >/dev/null 2>&1; then
        echo "Instalando uv para provisionar Python 3.${TF_MAX_MINOR}..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # shellcheck disable=SC1090
        [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
        export PATH="$HOME/.local/bin:$PATH"
    fi
    echo "Descargando Python 3.${TF_MAX_MINOR} con uv..."
    uv python install "3.${TF_MAX_MINOR}"
    PYTHON="$(uv python find "3.${TF_MAX_MINOR}")" || true
    if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
        echo "ERROR: uv no pudo encontrar Python 3.${TF_MAX_MINOR} tras instalarlo." >&2
        exit 1
    fi
fi

echo "Usando intérprete: $PYTHON ($("$PYTHON" --version 2>&1))"

if [ -d "$VENV_DIR" ] && ! is_compatible "$VENV_DIR/bin/python"; then
    echo "El venv existente usa un Python incompatible; recreándolo..."
    rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q
pip install pyinstaller -q

echo "Limpiando directorios de salida previos..."
rm -rf "$DIST_DIR" "$SCRIPT_DIR/build"

echo "Ejecutando PyInstaller..."
"$VENV_DIR/bin/pyinstaller" "$SCRIPT_DIR/HIVES.spec" --clean --noconfirm

echo ""
echo "Ejecutable en: $DIST_DIR/HIVES/"
