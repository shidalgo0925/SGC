#!/usr/bin/env bash
# Git Bash: "python" suele ser el alias de la Microsoft Store (no sirve).
cd "$(dirname "$0")"

if [[ -f .venv/Scripts/python.exe ]]; then
  exec .venv/Scripts/python.exe script/generar.py --cert1 "$@"
fi
if command -v py >/dev/null 2>&1; then
  exec py -3 script/generar.py --cert1 "$@"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 script/generar.py --cert1 "$@"
fi

echo "No se encontró Python usable en este Bash." >&2
echo "" >&2
echo "Haz UNA de estas:" >&2
echo "  1) Crear venv (recomendado):" >&2
echo "       py -3 -m venv .venv" >&2
echo "       .venv/Scripts/python.exe -m pip install -r requirements.txt" >&2
echo "       ./emitir_cert1.sh" >&2
echo "  2) Quitar alias Store: Configuración → Aplicaciones → Alias ejecución → desactivar python.exe" >&2
echo "  3) Usar CMD: emitir_cert1.bat" >&2
exit 1
