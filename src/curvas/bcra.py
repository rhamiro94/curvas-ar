"""Índices del BCRA (API pública de estadísticas v4)."""
import json
import urllib.request
from datetime import date, timedelta

URL = "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id}?desde={d}&hasta={h}&limit=3000"
ID_CER = 30


def serie(id_variable: int, desde: date, hasta: date) -> dict:
    """{fecha: valor} de una variable del BCRA."""
    url = URL.format(id=id_variable, d=desde.isoformat(), h=hasta.isoformat())
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "curvas-ar"})
    with urllib.request.urlopen(req, timeout=30) as r:
        datos = json.load(r)
    return {date.fromisoformat(x["fecha"]): float(x["valor"]) for x in datos["results"][0]["detalle"]}


def habil_menos(d: date, n: int, feriados=frozenset()) -> date:
    """La fecha n días hábiles antes de d."""
    while n:
        d -= timedelta(days=1)
        if d.weekday() < 5 and d not in feriados:
            n -= 1
    return d


def cer_t10(liquidacion: date, feriados=frozenset()):
    """(fecha, valor) del CER de 10 días hábiles antes de la liquidación."""
    f = habil_menos(liquidacion, 10, feriados)
    s = serie(ID_CER, f - timedelta(days=10), f)
    if f not in s:
        raise RuntimeError(f"El BCRA no publicó el CER del {f}")
    return f, s[f]
