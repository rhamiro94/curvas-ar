"""Carga diaria de la pestaña "renta fija" del Google Sheet.

Escribe SOLO las columnas A:U (datos de mercado y del maestro). Las columnas
de la U en adelante son tuyas: fórmulas o cálculos manuales que no se tocan.
"""
import json
import os
from datetime import date, timedelta

from .config import SETTLEMENT, DIAS_ATRAS
from .universo import grupos

LIBRO = os.environ.get("SHEET_LIBRO", "IOL pro")
HOJA = os.environ.get("SHEET_HOJA", "renta fija")

ENCABEZADOS = [
    "Símbolo", "Categoría", "Moneda", "Tipo", "Plazo de Liquidación",
    "Precio", "Vencimiento", "Monto Vto", "Monto Vto CER", "Monto Vto TAMAR + Margen",
    f"Precio {DIAS_ATRAS}d", f"Fecha {DIAS_ATRAS}d", f"Var {DIAS_ATRAS}d (%)",
    "Variación (%)", "Apertura", "Máximo", "Mínimo",
    "Último Cierre", "Volumen", "Fecha", "CER emisión / VR USD (DL)",
]
ULTIMA_COL = "U"  # 21 columnas: A..U


HOJA_INDICES = "indices"


def conectar_sheet():
    """Libro de Google con la cuenta de servicio de GOOGLE_SA_JSON (contenido) o GOOGLE_SA_FILE (ruta)."""
    import gspread
    contenido = os.environ.get("GOOGLE_SA_JSON")
    if contenido:
        gc = gspread.service_account_from_dict(json.loads(contenido))
    elif os.environ.get("GOOGLE_SA_FILE"):
        gc = gspread.service_account(filename=os.environ["GOOGLE_SA_FILE"])
    else:
        return None
    return gc.open(LIBRO)


def _var(a, b):
    try:
        a, b = float(a), float(b)
        return round((a / b - 1) * 100, 2) if a > 0 and b > 0 else ""
    except (TypeError, ValueError):
        return ""


def armar_filas(precios, hoy: date):
    """Precio actual y de hace DIAS_ATRAS días para todo el universo."""
    ref = hoy - timedelta(days=DIAS_ATRAS)
    filas, errores = [], []
    for categoria, lista in grupos.items():
        for ins in lista:
            tk, tipo = ins["ticker"], ins["type"]
            vto = ins.get("vto", "")
            if vto and date.fromisoformat(vto) < hoy:
                continue  # ya venció
            try:
                d = _reintentar_actual(precios, tk, tipo)
            except Exception as e:
                errores.append((tk, f"precio actual: {e}")); continue
            if not d or not d.get("price"):
                errores.append((tk, "sin precio")); continue
            try:
                p7, f7 = precios.cierre_en(tk, tipo, ref)
            except Exception:
                p7, f7 = None, None
            filas.append([
                tk, categoria, ins.get("moneda", "ARS"), tipo, SETTLEMENT,
                d.get("price", ""), vto, ins.get("monto_vto", ""),
                ins.get("monto_cer", ""), ins.get("monto_tamar", ""),
                p7 or "", f7.isoformat() if f7 else "", _var(d.get("price"), p7),
                d.get("marketChangePercent", ""), d.get("openingPrice", ""),
                d.get("max", ""), d.get("min", ""), d.get("previousClose", ""),
                d.get("volume", ""), d.get("date", ""), ins.get("cer_emision", ins.get("vr", "") if categoria == "DOLLAR LINKED" else ""),
            ])
    return filas, errores


def _reintentar_actual(precios, tk, tipo):
    from .precios import _reintentar
    import time
    from .config import PAUSA_PPI
    d = _reintentar(precios.ppi.marketdata.current, tk, tipo, SETTLEMENT)
    time.sleep(PAUSA_PPI)
    return d


def escribir(libro, filas):
    """Reemplaza A:U de "renta fija" sin tocar las columnas V en adelante."""
    ws = libro.worksheet(HOJA)
    valores = [ENCABEZADOS] + [["" if v is None else v for v in f] for f in filas]
    ws.batch_clear([f"A2:{ULTIMA_COL}{max(ws.row_count, len(valores))}"])
    ws.update(range_name=f"A1:{ULTIMA_COL}{len(valores)}", values=valores,
              value_input_option="USER_ENTERED")


def escribir_indices(libro, filas):
    """Pestaña "indices": una fila por índice (CER T-10, etc.). La crea si no existe."""
    import gspread
    try:
        ws = libro.worksheet(HOJA_INDICES)
    except gspread.WorksheetNotFound:
        ws = libro.add_worksheet(title=HOJA_INDICES, rows=20, cols=6)
    valores = [["Índice", "Fecha del dato", "Valor", "Para liquidación", "Actualizado"]] + filas
    ws.batch_clear(["A1:E20"])
    ws.update(range_name=f"A1:E{len(valores)}", values=valores, value_input_option="USER_ENTERED")


def _reemplazar_hoja(libro, titulo, valores, columnas=20):
    import gspread
    try:
        ws = libro.worksheet(titulo)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = libro.add_worksheet(title=titulo, rows=max(len(valores) + 20, 50), cols=columnas)
    ws.update(range_name="A1", values=[["" if v is None else v for v in f] for f in valores],
              value_input_option="USER_ENTERED")


def escribir_control(libro, tabla_curvas, tabla_ajustes):
    """Pestañas generadas (se reescriben enteras): lo mismo que muestra la terminal web,
    para controlarlo contra tus cálculos manuales."""
    _reemplazar_hoja(libro, "control curvas", tabla_curvas)
    _reemplazar_hoja(libro, "control ajustes", tabla_ajustes)
