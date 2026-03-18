#!/usr/bin/env bash
cd "$(dirname "$0")"
if [[ -f .venv/Scripts/python.exe ]]; then
  exec .venv/Scripts/python.exe script/generar.py "$@"
fi
if command -v py >/dev/null 2>&1; then
  exec py -3 script/generar.py "$@"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 script/generar.py "$@"
fi
echo "Sin Python: py -3 -m venv .venv  luego ./emitir_peru.sh" >&2
exit 1
