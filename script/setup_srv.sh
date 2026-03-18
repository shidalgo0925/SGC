#!/usr/bin/env bash
# Primera instalación en Linux (srv)
set -e
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
echo "Listo. Plantilla en SGC/base/, Excel en SGC/data/ (o clonaste ya con esos archivos)."
echo "Emitir: .venv/bin/python script/generar.py"
