"""
Gunicorn:  cd /var/www/certificados && venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 app.app:app
"""
import os
import sqlite3

from flask import Flask, render_template

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB = os.environ.get("CERTIFICADOS_DB", os.path.join(BASE, "data", "certificados.db"))

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


def get_cert(cert_id: int):
    if not os.path.isfile(DB):
        return None
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT id, nombre, cip, correo, orcid FROM certificados WHERE id = ?",
            (cert_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


@app.route("/v/<int:cert_id>")
def verificacion(cert_id):
    row = get_cert(cert_id)
    if not row:
        return render_template("no_valido.html"), 404

    actividad = os.environ.get(
        "ACTIVIDAD_TXT",
        "Actividad académica certificada por Relatic Panamá.",
    )
    data = {
        "id": row["id"],
        "nombre": row["nombre"] or "",
        "cip": row["cip"] or "",
        "correo": (row["correo"] or "").strip() or "—",
        "orcid": (row["orcid"] or "").strip() or "—",
    }
    return render_template("verificacion.html", data=data, actividad=actividad)


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
