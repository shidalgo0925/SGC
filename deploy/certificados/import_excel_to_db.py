#!/usr/bin/env python3
"""
Una sola vez (o al actualizar lista): Excel → SQLite.
Uso:
  cd /var/www/certificados
  venv/bin/python import_excel_to_db.py data/participantes.xlsx

Columnas reconocidas (insensible a mayúsculas):
  id | # | nro | número …  (si falta: 1,2,3…)
  nombre | apellidos y nombres | participante …
  cip | dni | documento …
  correo | email | mail …
  orcid
"""
import argparse
import os
import re
import sqlite3

import pandas as pd


def norm(c):
    return re.sub(r"\s+", " ", str(c).strip().lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("excel", help="Ruta al .xlsx")
    ap.add_argument(
        "-o",
        "--db",
        default=os.path.join(os.path.dirname(__file__), "data", "certificados.db"),
    )
    args = ap.parse_args()

    df = pd.read_excel(args.excel, engine="openpyxl", header=None)
    # Buscar fila de encabezados (misma idea que generar.py)
    best = None
    for h in range(min(80, len(df))):
        row = [str(df.iloc[h, j]).strip() for j in range(df.shape[1])]
        cols = [norm(x) if x and x != "nan" else f"_c{i}" for i, x in enumerate(row)]
        sub = df.iloc[h + 1 :].copy()
        if sub.empty:
            continue
        sub.columns = cols[: sub.shape[1]]
        sub = sub.dropna(how="all")
        if sub.empty:
            continue
        by = {norm(c): c for c in sub.columns}

        def pick(keys):
            for k in keys:
                if k in by:
                    return by[k]
            return None

        nom = pick(
            [
                "nombre",
                "nombre completo",
                "apellidos y nombres",
                "nombres y apellidos",
                "participante",
            ]
        )
        doc = pick(["cip", "dni", "documento", "cédula", "cedula"])
        if not nom or not doc:
            for c in sub.columns:
                n = norm(c)
                if not nom and any(
                    x in n for x in ("nombre", "apellido", "participante")
                ):
                    nom = c
                if (
                    not doc
                    and nom != c
                    and any(x in n for x in ("cip", "dni", "documento", "cedula"))
                ):
                    doc = c
        if not nom or not doc:
            continue
        idcol = pick(
            ["id", "#", "nro", "número", "numero", "no", "num"]
        )
        mail = pick(["email", "correo", "correo electrónico", "e-mail", "mail"])
        if not mail:
            for c in sub.columns:
                n = norm(c)
                if any(x in n for x in ("correo", "email", "mail")):
                    mail = c
                    break
        orch = pick(["orcid"])
        if not orch:
            for c in sub.columns:
                if "orcid" in norm(c):
                    orch = c
                    break

        rows = []
        for i, r in sub.iterrows():
            nombre = str(r[nom]).strip()
            cip = str(r[doc]).strip()
            if not nombre or nombre.lower() == "nan":
                continue
            if idcol and str(r[idcol]).strip() not in ("", "nan", "None"):
                try:
                    cid = int(float(str(r[idcol]).replace(",", ".").split(".")[0]))
                except (ValueError, TypeError):
                    cid = len(rows) + 1
            else:
                cid = len(rows) + 1
            co = (
                str(r[mail]).strip()
                if mail and str(r.get(mail, "")).strip() not in ("", "nan")
                else ""
            )
            orc = (
                str(r[orch]).strip()
                if orch and str(r.get(orch, "")).strip() not in ("", "nan")
                else ""
            )
            rows.append((cid, nombre, cip, co, orc))
        if rows:
            best = rows
            break

    if not best:
        raise SystemExit("No se pudo detectar columnas nombre + documento en el Excel.")

    # IDs duplicados en Excel → reasignar para no romper PRIMARY KEY
    by_id = {}
    for cid, nombre, cip, co, orc in best:
        while cid in by_id:
            cid = max(by_id.keys(), default=0) + 1
        by_id[cid] = (nombre, cip, co, orc)
    best = [(i, by_id[i][0], by_id[i][1], by_id[i][2], by_id[i][3]) for i in sorted(by_id.keys())]

    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS certificados (
        id INTEGER PRIMARY KEY,
        nombre TEXT,
        cip TEXT,
        correo TEXT,
        orcid TEXT
    )"""
    )
    conn.execute("DELETE FROM certificados")
    conn.executemany(
        "INSERT INTO certificados (id, nombre, cip, correo, orcid) VALUES (?,?,?,?,?)",
        best,
    )
    conn.commit()
    conn.close()
    print(f"OK: {len(best)} filas -> {args.db}")


if __name__ == "__main__":
    main()
