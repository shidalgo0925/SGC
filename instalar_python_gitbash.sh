#!/usr/bin/env bash
# Instalar Python 3 desde Git Bash (Windows).
set -e
echo "=== Instalar Python para SGC ==="

if command -v py >/dev/null 2>&1; then
  echo "Ya tienes el launcher 'py'. Versión:"
  py -3 --version || true
  echo "Siguiente: py -3 -m venv .venv"
  exit 0
fi

if command -v winget >/dev/null 2>&1; then
  echo "Instalando con winget (Python 3.12)..."
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo ""
  echo "Listo. CIERRA esta ventana de Git Bash y abre una NUEVA."
  echo "Luego en SGC:"
  echo "  py -3 -m venv .venv"
  echo "  .venv/Scripts/python.exe -m pip install -r requirements.txt"
  echo "  ./emitir_cert1.sh"
  exit 0
fi

PY_VER="3.12.7"
URL="https://www.python.org/ftp/python/${PY_VER}/python-${PY_VER}-amd64.exe"
OUT="$HOME/Downloads/python_sgc_installer.exe"
mkdir -p "$(dirname "$OUT")"
echo "winget no encontrado. Descargando Python ${PY_VER}..."
curl -fSL -o "$OUT" "$URL"
WIN_OUT=$(cygpath -w "$OUT")
echo "Ejecutando instalador (silencioso, usuario actual, PATH + py)..."
cmd.exe //c "\"${WIN_OUT}\" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0"
echo ""
echo "Listo. CIERRA Git Bash y abre una NUEVA terminal."
echo "Luego: cd .../SGC && py -3 -m venv .venv"
exit 0
