"""Cálculos de renta fija. Validado contra el informe BYMA/IAMC del 05-Oct-26 (±5 pb).

Convenciones:
  TIR  : efectiva anual, base actual/365, desde la liquidación (T+1 hábil).
  LECAP: TEA = (pago_final/precio)^(365/días) - 1 ; TEM = (1+TEA)^(1/12) - 1 ; TNA = TEM*12
"""
from datetime import date, timedelta


def liquidacion(fecha_operacion: date, feriados=frozenset(), dias_habiles: int = 1) -> date:
    d = fecha_operacion
    while dias_habiles:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in feriados:
            dias_habiles -= 1
    return d


def _futuros(flujos, liq):
    return [(d, m) for d, m in flujos if d > liq]


def tir(precio: float, flujos, liq: date):
    """TIR efectiva anual por bisección. None si no hay flujos futuros o precio."""
    fut = _futuros(flujos, liq)
    if not fut or not precio or precio <= 0:
        return None

    def vp(r):
        return sum(m / (1 + r) ** ((d - liq).days / 365) for d, m in fut)

    lo, hi = -0.99, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if vp(mid) > precio:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def metricas_bono(precio: float, flujos, liq: date):
    r = tir(precio, flujos, liq)
    if r is None:
        return None
    pv = [((d - liq).days / 365, m / (1 + r) ** ((d - liq).days / 365)) for d, m in _futuros(flujos, liq)]
    total = sum(v for _, v in pv)
    macaulay = sum(t * v for t, v in pv) / total
    return {"tir": r, "duration": macaulay, "md": macaulay / (1 + r)}


def metricas_lecap(precio: float, pago_final: float, vto: date, liq: date):
    dias = (vto - liq).days
    if dias <= 0 or not precio or precio <= 0:
        return None
    tea = (pago_final / precio) ** (365 / dias) - 1
    tem = (1 + tea) ** (1 / 12) - 1
    return {"dias": dias, "tna": tem * 12, "tea": tea, "tem": tem, "dm": dias / (1 + tea)}
