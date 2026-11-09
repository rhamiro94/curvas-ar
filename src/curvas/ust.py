"""Curva de rendimientos del Tesoro de EE.UU. (par yield curve diaria, treasury.gov)."""
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime

URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
       "?data=daily_treasury_yield_curve&field_tdr_date_value_month={ym}")
PLAZOS = {"BC_1MONTH": 1 / 12, "BC_3MONTH": 0.25, "BC_6MONTH": 0.5, "BC_1YEAR": 1, "BC_2YEAR": 2,
          "BC_3YEAR": 3, "BC_5YEAR": 5, "BC_7YEAR": 7, "BC_10YEAR": 10, "BC_20YEAR": 20, "BC_30YEAR": 30}


def curvas_mes(anio: int, mes: int) -> dict:
    """{fecha: [(plazo_años, rendimiento_decimal), ...]} de un mes."""
    req = urllib.request.Request(URL.format(ym=f"{anio}{mes:02d}"), headers={"User-Agent": "curvas-ar"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raiz = ET.fromstring(r.read())
    out = {}
    for props in raiz.iter():
        if not props.tag.endswith("properties"):
            continue
        campos = {c.tag.split("}")[-1]: (c.text or "") for c in props}
        f = datetime.fromisoformat(campos["NEW_DATE"][:19]).date()
        puntos = [(t, float(campos[k]) / 100) for k, t in PLAZOS.items() if campos.get(k)]
        if puntos:
            out[f] = sorted(puntos)
    return out


def curva_en(fecha: date, cache: dict | None = None):
    """Última curva publicada en o antes de 'fecha' (mira el mes y el anterior)."""
    cache = {} if cache is None else cache
    meses = {(fecha.year, fecha.month), ((fecha.year - 1, 12) if fecha.month == 1 else (fecha.year, fecha.month - 1))}
    for ym in meses:
        if ym not in cache:
            try:
                cache[ym] = curvas_mes(*ym)
            except Exception:
                cache[ym] = {}
    todas = {f: c for ym in meses for f, c in cache[ym].items() if f <= fecha}
    if not todas:
        return None, None
    f = max(todas)
    return f, todas[f]


def interpolar(curva, plazo: float) -> float:
    """Rendimiento lineal en el plazo pedido (extremos planos)."""
    if plazo <= curva[0][0]:
        return curva[0][1]
    for (t0, y0), (t1, y1) in zip(curva, curva[1:]):
        if plazo <= t1:
            return y0 + (y1 - y0) * (plazo - t0) / (t1 - t0)
    return curva[-1][1]
