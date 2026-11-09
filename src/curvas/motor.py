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


def a_bey(tir_efectiva: float) -> float:
    """Tasa efectiva anual -> rendimiento semestral equivalente (convención del Tesoro de EE.UU.)."""
    return 2 * ((1 + tir_efectiva) ** 0.5 - 1)


def spread_ust(tir: float, duration_macaulay: float, curva_ust) -> float:
    """Spread en puntos básicos sobre el Tesoro de EE.UU. al plazo de la duration."""
    from .ust import interpolar
    return (a_bey(tir) - interpolar(curva_ust, duration_macaulay)) * 1e4


def riesgo_pais(bonos) -> float | None:
    """Promedio de spreads ponderado por valor de mercado. bonos: [(spread_pb, monto_emitido, precio)]."""
    validos = [(s, m * p / 100) for s, m, p in bonos if s is not None and m and p]
    total = sum(v for _, v in validos)
    return sum(s * v for s, v in validos) / total if total else None


def breakeven_mensual(tea_fija: float, tir_real: float) -> float:
    """Inflación mensual implícita entre una tasa fija y una CER del mismo plazo."""
    return ((1 + tea_fija) / (1 + tir_real)) ** (1 / 12) - 1


def monto_tamar(emision: date, vto: date, margen: float, serie: dict, hoy: date, tasa_futura: float) -> float:
    """Monto al vencimiento por VN 100 de un bono TAMAR capitalizable.
    Capitaliza en cada mes (mismo día que el vencimiento) a (TAMAR promedio del período + margen) x días/365.
    Días ya transcurridos: TAMAR publicada (BCRA). Días futuros: tasa_futura.
    Validado contra el monto proyectado del informe BYMA/IAMC 05-Oct-26 (diferencias de 0,0% a 0,2%)."""
    import calendar
    cortes = [vto]
    d = vto
    while True:
        y, m = (d.year - 1, 12) if d.month == 1 else (d.year, d.month - 1)
        d = date(y, m, min(vto.day, calendar.monthrange(y, m)[1]))
        if d <= emision:
            break
        cortes.append(d)
    cortes = [emision] + sorted(cortes)
    fechas = sorted(serie)
    factor = 1.0
    for a, b in zip(cortes, cortes[1:]):
        conocidos = [serie[f] for f in fechas if a <= f < b and f <= hoy]
        n_dias = (b - a).days
        dias_futuros = max(0, (b - max(a, hoy + timedelta(days=1))).days) if b > hoy else 0
        if conocidos and dias_futuros:
            peso = (n_dias - dias_futuros) / n_dias
            tasa = peso * (sum(conocidos) / len(conocidos)) + (1 - peso) * tasa_futura
        elif conocidos:
            tasa = sum(conocidos) / len(conocidos)
        else:
            tasa = tasa_futura
        factor *= 1 + (tasa + margen) * n_dias / 365
    return 100 * factor


def metricas_tamar(precio: float, monto: float, vto: date, liq: date, tamar_hoy: float):
    m = metricas_lecap(precio, monto, vto, liq)
    if m:
        m["margen_implicito"] = m["tna"] - tamar_hoy
    return m
