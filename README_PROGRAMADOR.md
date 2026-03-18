# SGC — Certificados masivos (resumen técnico)

## Qué es

Proyecto **independiente** de NodeOne/Odoo: **1 PDF por fila** de Excel, superponiendo **nombre + CIP** (y opcionalmente **QR**) sobre un **PDF plantilla fija**.

## Flujo

`Excel → pandas → overlay (ReportLab) → merge (PyPDF2) con PDF base → output/certificados_generados/`

**Regla:** 1 fila = 1 certificado.

## Stack

- Python 3 · `pandas` + `openpyxl` · `reportlab` · `PyPDF2` · opcional `qrcode[pil]`

## Estructura

| Ruta | Uso |
|------|-----|
| `base/Certificado.pdf` | Plantilla (o `certificado.pdf`) |
| `data/excel de datos peru.xlsx` | Datos (o primer `.xlsx` en `data/`) |
| `script/generar.py` | Motor |
| `output/certificados_generados/` | Salida |
| `emitir_peru.bat` | Atajo Windows |

## Excel — columnas (`normalize_columns` en `generar.py`)

- **id:** `id`, `#`, `nro`, `número`, … — si no hay, se usa 1, 2, 3…
- **nombre:** `nombre`, `nombre completo`, `participante`, `apellidos y nombres`, …
- **cip:** `cip`, `dni`, `documento`, `cédula`, `código`, …

## Calibración visual

En `CONFIG` (origen ReportLab **abajo-izquierda**): `nombre_y`, `cip_y`, fuentes, `qr_x`, `qr_y`, `qr_size` según tamaño real de la página del PDF base.

## Ejecución

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
emitir_peru.bat
```

O: `python script/generar.py`

### Argumentos

| Corto | Largo | Descripción |
|-------|-------|-------------|
| `-b` | `--base` | PDF plantilla |
| `-e` | `--excel` | Excel |
| `-o` | `--output` | Carpeta salida |
| `-u` | `--qr-base-url` | URL base del QR (`/{id}`) |
| | `--no-qr` | Sin QR |

## Checklist

1. venv + `requirements.txt`
2. PDF en `base/` + Excel en `data/`
3. Ajustar `CONFIG` en `generar.py`
4. Lote de prueba (p. ej. 100+ filas &lt; 2 min)
5. Documentar coordenadas finales si el cliente las fija

## Fuera de alcance (v1)

HTML dinámico, NodeOne, un solo PDF con todos los certificados.

## Portable

Empaquetar sin `.venv` y sin PDFs de prueba en `output/`. Ver `COMO_INSTALAR_PC.txt`.
