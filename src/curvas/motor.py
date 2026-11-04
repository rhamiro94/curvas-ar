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


def metricas_cer(precio: float, cer_emision: float, cer_t10: float, vto: date, liq: date):
    """CER cupón cero. VR = 100 x CER(T-10 de la liquidación) / CER de emisión.
    TIR real = (VR / precio)^(365/días) - 1 (rendimiento sobre el CER, sin proyectar inflación)."""
    dias = (vto - liq).days
    if dias <= 0 or not precio or precio <= 0 or not cer_emision or not cer_t10:
        return None
    vr = 100 * cer_t10 / cer_emision
    tir = (vr / precio) ** (365 / dias) - 1
    return {"dias": dias, "vr": vr, "tir": tir, "md": dias / 365 / (1 + tir)}


def ajuste_log(xs, ys):
    """Línea de tendencia logarítmica y = a + b·ln(x) por mínimos cuadrados.
    Devuelve {a, b, r2, n} o None si hay menos de 3 puntos válidos."""
    import math
    pares = [(math.log(x), y) for x, y in zip(xs, ys)
             if x is not None and y is not None and x > 0 and y == y]
    n = len(pares)
    if n < 3:
        return None
    mx = sum(p[0] for p in pares) / n
    my = sum(p[1] for p in pares) / n
    sxx = sum((p[0] - mx) ** 2 for p in pares)
    if sxx == 0:
        return None
    b = sum((p[0] - mx) * (p[1] - my) for p in pares) / sxx
    a = my - b * mx
    ss_tot = sum((p[1] - my) ** 2 for p in pares)
    ss_res = sum((p[1] - (a + b * p[0])) ** 2 for p in pares)
    return {"a": a, "b": b, "r2": 1 - ss_res / ss_tot if ss_tot else None, "n": n}
