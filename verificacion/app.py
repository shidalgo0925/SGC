"""
Página de verificación al escanear el QR: /v/<id>
Ejecutar: desde carpeta SGC → .venv/Scripts/python.exe verificacion/app.py
En producción: gunicorn -w 2 -b 0.0.0.0:8000 verificacion.app:app
"""
import os
import sys

import yaml
from flask import Flask, render_template

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "script"))

from generar import read_excel_auto_header, resolve_excel_path

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

_PARTICIPANTES: dict[str, dict] | None = None


def _cfg():
    p = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_participantes():
    global _PARTICIPANTES
    if _PARTICIPANTES is not None:
        return _PARTICIPANTES
    cfg = _cfg()
    excel = (cfg.get("excel_path") or "").strip()
    path = excel if excel and os.path.isfile(excel) else resolve_excel_path(ROOT)
    df = read_excel_auto_header(path)
    m: dict[str, dict] = {}
    for _, row in df.iterrows():
        rid = str(row["id"]).strip()
        if not rid:
            continue
        m[rid] = {
            "nombre": str(row["nombre"]).strip(),
            "dni": str(row["cip"]).strip(),
            "email": str(row.get("email", "") or "").strip(),
            "orcid": str(row.get("orcid", "") or "").strip(),
        }
    _PARTICIPANTES = m
    return m


@app.route("/v/<pid>")
def verificar(pid):
    cfg = _cfg()
    actividad = cfg.get("actividad", "").strip()
    p = cargar_participantes().get(str(pid).strip())
    if not p or not p.get("nombre"):
        return render_template("no_encontrado.html"), 404
    return render_template(
        "verificado.html",
        actividad=actividad,
        nombre=p["nombre"],
        dni=p["dni"],
        email=p.get("email") or "—",
        orcid=p.get("orcid") or "—",
    )


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG") == "1")
