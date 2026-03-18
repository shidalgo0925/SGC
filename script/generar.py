#!/usr/bin/env python3
"""
SGC — Excel → overlay (nombre + CIP + QR obligatorio) → PDF base → PDFs locales.
1 fila = 1 PDF. Sin subida a servidores; el QR codifica datos de verificación en local (o URL si -u).
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False


# --- Ajustar según tu plantilla (origen ReportLab: abajo-izquierda) ---
CONFIG = {
    "nombre_x_center": None,  # None = centro horizontal de la página
    "nombre_y": 1050,
    "nombre_font": "Helvetica-Bold",
    "nombre_size": 52,
    "cip_y": 1015,
    "cip_font": "Helvetica",
    "cip_size": 24,
    "qr_x": 650,
    "qr_y": 65,
    "qr_size": 180,
    "nombre_max_chars": 45,
    "nombre_size_min": 14,
}


def slug_filename(nombre: str) -> str:
    """CERTIFICADO_NOMBRE_APELLIDO.pdf — seguro para disco."""
    s = re.sub(r"[^\w\s\-áéíóúñÁÉÍÓÚÑ]", "", str(nombre), flags=re.UNICODE)
    s = re.sub(r"\s+", "_", s.strip())[:120]
    if not s:
        s = "SIN_NOMBRE"
    return f"CERTIFICADO_{s}.pdf"


def resolve_base_pdf(root: str) -> str:
    """Plantilla: primero SGC/base/; si no, carpeta hermana SGC_Base (legacy)."""
    for name in ("Certificado.pdf", "certificado.pdf", "CERTIFICADO.PDF"):
        p = os.path.join(root, "base", name)
        if os.path.isfile(p):
            return p
    legacy = os.path.join(os.path.dirname(root), "SGC_Base")
    for name in ("Certificado.pdf", "certificado.pdf", "CERTIFICADO.PDF"):
        p = os.path.join(legacy, name)
        if os.path.isfile(p):
            return p
    return os.path.join(root, "base", "Certificado.pdf")


def _data_spreadsheets(data_dir: str) -> list[str]:
    """Archivos .xlsx / .xls en data/ (sin temporales Excel)."""
    if not os.path.isdir(data_dir):
        return []
    out = []
    for f in os.listdir(data_dir):
        if f.startswith("~$"):
            continue
        low = f.lower()
        if low.endswith((".xlsx", ".xls")):
            out.append(f)
    return out


def resolve_excel_path(root: str) -> str:
    """Excel: primero SGC/data/; si no, SGC_Base (legacy)."""
    data_dir = os.path.join(root, "data")
    for name in (
        "excel de datos peru.xlsx",
        "excel de datos peru.XLSX",
        "excel de datos peru.xls",
        "participantes.xlsx",
    ):
        p = os.path.join(data_dir, name)
        if os.path.isfile(p):
            return p
    files = _data_spreadsheets(data_dir)
    if files:
        xlsx = sorted(f for f in files if f.lower().endswith(".xlsx"))
        if xlsx:
            return os.path.join(data_dir, xlsx[0])
        return os.path.join(data_dir, sorted(files)[0])
    legacy = os.path.join(os.path.dirname(root), "SGC_Base")
    for name in ("excel de datos peru.xlsx", "excel de datos peru.XLSX", "excel de datos peru.xls"):
        p = os.path.join(legacy, name)
        if os.path.isfile(p):
            return p
    return os.path.join(data_dir, "excel de datos peru.xlsx")


def read_excel_any(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xls":
        return pd.read_excel(path, engine="xlrd")
    return pd.read_excel(path, engine="openpyxl")


def read_excel_raw_no_header(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    eng = "xlrd" if ext == ".xls" else "openpyxl"
    return pd.read_excel(path, engine=eng, header=None)


def _unique_col_names(row_vals: list) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for j, v in enumerate(row_vals):
        t = str(v).strip()
        if not t or t.lower() in ("nan", "none") or t == "NaT":
            base = f"_col{j}"
        else:
            base = t[:120]
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.append(base if n == 0 else f"{base}_{n}")
    return out


def read_excel_auto_header(path: str) -> pd.DataFrame:
    """
    Muchos Excels traen títulos o filas vacías arriba: busca la fila donde
    aparezcan columnas reconocibles (nombre + cip/dni).
    """
    raw = read_excel_raw_no_header(path)
    if raw.empty:
        raise ValueError("Excel vacío.")
    last_err: Exception | None = None
    max_h = min(80, len(raw))
    for h in range(max_h):
        row = raw.iloc[h]
        vals = [row.iloc[j] if j < len(row) else "" for j in range(raw.shape[1])]
        cols = _unique_col_names(vals)
        data = raw.iloc[h + 1 :].copy()
        if data.empty or len(cols) != data.shape[1]:
            if len(cols) < data.shape[1]:
                cols = cols + [f"_col{i}" for i in range(len(cols), data.shape[1])]
            elif len(cols) > data.shape[1]:
                cols = cols[: data.shape[1]]
        data.columns = cols
        data = data.dropna(how="all")
        if data.empty:
            continue
        try:
            return normalize_columns(data)
        except ValueError as e:
            last_err = e
            continue
    try:
        return normalize_columns(read_excel_any(path))
    except ValueError:
        msg = "No se encontró fila de encabezados con nombre y CIP/DNI."
        if last_err:
            msg += f" Detalle: {last_err}"
        raise ValueError(msg) from last_err


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Mapea columnas típicas Perú / variantes → id, nombre, cip."""
    def norm(c):
        return re.sub(r"\s+", " ", str(c).strip().lower())

    col_by_norm = {norm(c): c for c in df.columns}

    def pick(aliases):
        for a in aliases:
            if a in col_by_norm:
                return col_by_norm[a]
        return None

    id_c = pick(
        [
            "id",
            "#",
            "nro",
            "n°",
            "nº",
            "num",
            "número",
            "numero",
            "no",
            "cod",
            "código participante",
            "número de orden",
        ]
    )
    nom_c = pick(
        [
            "nombre",
            "nombre completo",
            "nombres y apellidos",
            "apellidos y nombres",
            "participante",
            "alumno",
            "estudiante",
        ]
    )
    cip_c = pick(
        [
            "cip",
            "dni",
            "documento",
            "documento de identidad",
            "cédula",
            "cedula",
            "código",
            "codigo",
            "n° documento",
            "nro documento",
            "doc. identidad",
            "doc identidad",
            "n° dni",
            "ndocumento",
        ]
    )
    # Coincidencia por texto en el encabezado (Excels con nombres raros)
    def col_norm_name(c):
        s = re.sub(r"\s+", " ", str(c).strip().lower())
        s = re.sub(r"^@+", "", s)
        return s

    if not nom_c:
        for c in df.columns:
            cn = col_norm_name(c)
            if "dropdown" in cn or cn.startswith("_col"):
                continue
            if any(
                k in cn
                for k in (
                    "nombre",
                    "apellido",
                    "nombres",
                    "participante",
                    "alumno",
                    "estudiante",
                    "trabajador",
                    "asistente",
                )
            ):
                nom_c = c
                break
    if not cip_c:
        for c in df.columns:
            cn = col_norm_name(c)
            if c == nom_c or "dropdown" in cn:
                continue
            if any(
                k in cn
                for k in (
                    "cip",
                    "dni",
                    "documento",
                    "cedula",
                    "cédula",
                    "doc.",
                    "identidad",
                    "ruc",
                )
            ):
                cip_c = c
                break
    missing = []
    if not nom_c:
        missing.append("nombre (o nombre completo, participante, etc.)")
    if not cip_c:
        missing.append("cip (o dni, documento, cédula, etc.)")
    if missing:
        raise ValueError(
            "Faltan columnas.\n"
            f"  Columnas en el Excel: {list(df.columns)}\n"
            f"  Faltante: {', '.join(missing)}"
        )
    email_c = pick(
        ["email", "correo", "correo electrónico", "correo electronico", "e-mail", "mail"]
    )
    orcid_c = pick(["orcid", "id orcid"])
    if not email_c:
        for c in df.columns:
            if c in (id_c, nom_c, cip_c):
                continue
            cn = col_norm_name(c)
            if any(k in cn for k in ("correo", "email", "e-mail", "mail")):
                email_c = c
                break
    if not orcid_c:
        for c in df.columns:
            if c in (id_c, nom_c, cip_c):
                continue
            if "orcid" in col_norm_name(c):
                orcid_c = c
                break

    if id_c:
        out = df[[id_c, nom_c, cip_c]].copy()
        out.columns = ["id", "nombre", "cip"]
    else:
        out = df[[nom_c, cip_c]].copy()
        out.insert(0, "id", range(1, len(out) + 1))
        out.columns = ["id", "nombre", "cip"]
    if email_c:
        out["email"] = df.loc[out.index, email_c].astype(str).replace("nan", "").replace("None", "")
    else:
        out["email"] = ""
    if orcid_c:
        out["orcid"] = df.loc[out.index, orcid_c].astype(str).replace("nan", "").replace("None", "")
    else:
        out["orcid"] = ""
    return out


def page_size_points(reader: PdfReader, page_index: int = 0):
    p = reader.pages[page_index]
    mb = p.mediabox
    return float(mb.width), float(mb.height)


def nombre_font_size(nombre: str, base_size: int, min_size: int, max_chars: int) -> int:
    n = len(nombre)
    if n <= max_chars:
        return base_size
    return max(min_size, int(base_size * max_chars / max(n, 1)))


def qr_payload(row_id, nombre: str, cip: str, qr_url_base: str | None) -> str:
    if qr_url_base and qr_url_base.strip():
        return qr_url_base.strip().rstrip("/") + f"/{row_id}"
    n = str(nombre).replace("|", " ").strip()[:120]
    return f"SGC-CERT|id={row_id}|cip={cip}|n={n}"


def build_overlay(
    width: float,
    height: float,
    nombre: str,
    cip: str,
    row_id,
    qr_url_base: str | None,
    cfg: dict,
    sin_qr: bool = False,
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    cx = cfg["nombre_x_center"] if cfg["nombre_x_center"] is not None else width / 2
    fs = nombre_font_size(nombre, cfg["nombre_size"], cfg["nombre_size_min"], cfg["nombre_max_chars"])
    c.setFont(cfg["nombre_font"], fs)
    c.drawCentredString(cx, cfg["nombre_y"], nombre)
    c.setFont(cfg["cip_font"], cfg["cip_size"])
    c.drawCentredString(cx, cfg["cip_y"], f"CIP: {cip}")

    if not sin_qr:
        payload = qr_payload(row_id, nombre, cip, qr_url_base)
        img = qrcode.make(payload, box_size=3)
        qbuf = io.BytesIO()
        img.save(qbuf, format="PNG")
        qbuf.seek(0)
        c.drawImage(
            ImageReader(qbuf),
            cfg["qr_x"],
            cfg["qr_y"],
            width=cfg["qr_size"],
            height=cfg["qr_size"],
            mask="auto",
        )
    c.save()
    buf.seek(0)
    return buf.read()


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ap = argparse.ArgumentParser(description="SGC: Excel + PDF base → PDFs individuales")
    ap.add_argument("-e", "--excel", default="", help="Ruta Excel (vacío = auto)")
    ap.add_argument("-b", "--base", default="", help="Ruta PDF plantilla (vacío = auto)")
    ap.add_argument("-o", "--output", default=os.path.join(root, "output", "certificados_generados"))
    ap.add_argument(
        "-u",
        "--qr-base-url",
        default="",
        dest="qr_base_url",
        help="Opcional: URL base; si no, el QR lleva texto local SGC-CERT|id=…|cip=…|n=…",
    )
    ap.add_argument(
        "-n",
        "--limite",
        type=int,
        default=0,
        help="Solo las primeras N filas (0 = todas). Útil para calibrar posición.",
    )
    ap.add_argument(
        "--sin-qr",
        action="store_true",
        help="Solo nombre + CIP (calibrar texto; lote final sin este flag lleva QR).",
    )
    ap.add_argument(
        "--cert1",
        action="store_true",
        help="Primera fila → output/cert1.pdf, sin QR.",
    )
    args = ap.parse_args()

    if args.cert1:
        args.limite = 1
    sin_qr = args.sin_qr or args.cert1

    base_pdf = args.base.strip() or resolve_base_pdf(root)
    excel_path = args.excel.strip() or resolve_excel_path(root)

    if not os.path.isfile(base_pdf):
        print(f"ERROR: No existe PDF base: {base_pdf}", file=sys.stderr)
        print("Esperado: SGC/base/Certificado.pdf (o -b ruta)", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(excel_path):
        print(f"ERROR: No existe Excel: {excel_path}", file=sys.stderr)
        print("Esperado: SGC/data/excel de datos peru.xlsx (o -e ruta)", file=sys.stderr)
        sys.exit(1)
    if not sin_qr and not HAS_QR:
        print("ERROR: Sin --sin-qr hace falta QR. pip install 'qrcode[pil]' Pillow", file=sys.stderr)
        sys.exit(1)

    try:
        df = read_excel_auto_header(excel_path)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.limite and args.limite > 0:
        df = df.head(args.limite).copy()
        print(f"Modo prueba: solo {len(df)} fila(s).", file=sys.stderr)

    os.makedirs(args.output, exist_ok=True)
    with open(base_pdf, "rb") as f:
        base_pdf_bytes = f.read()
    base_reader = PdfReader(io.BytesIO(base_pdf_bytes))
    w, h = page_size_points(base_reader, 0)
    qr_base = args.qr_base_url.strip() or None

    ok = 0
    errs = []
    for idx, row in df.iterrows():
        try:
            rid = row["id"]
            nombre = str(row["nombre"]).strip()
            cip = str(row["cip"]).strip()
            if not nombre:
                errs.append((idx, "nombre vacío"))
                continue
            overlay_pdf = build_overlay(w, h, nombre, cip, rid, qr_base, CONFIG, sin_qr=sin_qr)
            overlay_reader = PdfReader(io.BytesIO(overlay_pdf))
            # Nuevo lector por fila: merge_page muta la página; no reutilizar la misma.
            row_reader = PdfReader(io.BytesIO(base_pdf_bytes))
            page = row_reader.pages[0]
            page.merge_page(overlay_reader.pages[0])
            writer = PdfWriter()
            writer.add_page(page)
            if args.cert1:
                out_dir = os.path.join(root, "output")
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, "cert1.pdf")
            else:
                out_name = slug_filename(nombre)
                out_path = os.path.join(args.output, out_name)
                if os.path.isfile(out_path):
                    stem, ext = os.path.splitext(out_name)
                    out_path = os.path.join(args.output, f"{stem}_id{rid}{ext}")
            with open(out_path, "wb") as f:
                writer.write(f)
            ok += 1
        except Exception as e:
            errs.append((idx, str(e)))

    print(f"Base: {base_pdf}")
    print(f"Excel: {excel_path}")
    if args.cert1 and ok:
        print(f"Certificado de prueba: {os.path.join(root, 'output', 'cert1.pdf')}")
    else:
        print(f"Generados: {ok} PDF(s) en {args.output}")
    if errs:
        print(f"Errores: {len(errs)}", file=sys.stderr)
        for i, msg in errs[:20]:
            print(f"  fila {i}: {msg}", file=sys.stderr)
        if len(errs) > 20:
            print(f"  ... y {len(errs) - 20} más", file=sys.stderr)


if __name__ == "__main__":
    main()
