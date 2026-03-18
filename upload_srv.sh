#!/usr/bin/env bash
# En TU PC (Git Bash). Necesitás SSH al servidor (clave o agente).

USR="relaticpanama2025"
HOST="34.66.214.83"
REMOTE_DIR="~/SGC_deploy_certificados"

ssh "${USR}@${HOST}" "mkdir -p ${REMOTE_DIR}/data"
echo ">>> Subiendo carpeta deploy/certificados..."
scp -r deploy/certificados/* "${USR}@${HOST}:${REMOTE_DIR}/"

echo ">>> Guía..."
scp GUIA_SERVIDOR.txt "${USR}@${HOST}:~/"

DB="deploy/certificados/data/certificados.db"
if [[ -f "$DB" ]]; then
  echo ">>> Subiendo certificados.db..."
  ssh "${USR}@${HOST}" "mkdir -p ${REMOTE_DIR}/data"
  scp "$DB" "${USR}@${HOST}:${REMOTE_DIR}/data/"
else
  echo ">>> No hay certificados.db local. Creala con import_excel_to_db.py y subila:"
  echo "    scp deploy/certificados/data/certificados.db ${USR}@${HOST}:${REMOTE_DIR}/data/"
fi

echo "Hecho. En el srv: ls ${REMOTE_DIR}"
