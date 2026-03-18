#!/usr/bin/env bash
# Primera instalación en Linux (srv)
set -e
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
echo "Listo. Junto a SGC debe existir SGC_Base (Certificado.pdf + Excel)."
echo "Emitir: .venv/bin/python script/generar.py"
