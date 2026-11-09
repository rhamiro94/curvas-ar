"""Indicadores de cabecera: riesgo país, MEP implícito, A3500 y TAMAR (hoy y hace N días)."""
from datetime import date, timedelta

from . import bcra, motor, ust
from .config import DIAS_ATRAS, RIESGO_PAIS


def _par(actual, previo, fecha_a=None, fecha_p=None, **extra):
    if actual is None:
        return None
    d = {"valor": actual, "fecha": fecha_a.isoformat() if fecha_a else None,
         "valor_7d": previo, "fecha_7d": fecha_p.isoformat() if fecha_p else None}
    d.update(extra)
    return d


def riesgo_pais(df_hd, cache_ust: dict):
    """Agrega spread_pb / spread_7d_pb a df_hd y devuelve el KPI."""
    if df_hd is None or df_hd.empty:
        return None
    f_hoy = df_hd["fecha"].max()
    f_ref = df_hd["fecha_7d"].dropna().max() if df_hd["fecha_7d"].notna().any() else None
    fu, curva = ust.curva_en(f_hoy, cache_ust)
    fu7, curva7 = ust.curva_en(f_ref, cache_ust) if f_ref else (None, None)
    if not curva:
        return None
    df_hd["spread_pb"] = [motor.spread_ust(r.tir, r.duration, curva) for r in df_hd.itertuples()]
    df_hd["spread_7d_pb"] = [motor.spread_ust(r.tir_7d, r.duration_7d, curva7)
                             if curva7 and r.tir_7d == r.tir_7d and r.tir_7d is not None else None
                             for r in df_hd.itertuples()]
    base = df_hd["ticker"].str[:-1]
    sel = df_hd[base.isin(RIESGO_PAIS)]
    hoy = motor.riesgo_pais([(r.spread_pb, RIESGO_PAIS[r.ticker[:-1]], r.precio) for r in sel.itertuples()])
    ref = motor.riesgo_pais([(r.spread_7d_pb, RIESGO_PAIS[r.ticker[:-1]], r.precio_7d)
                             for r in sel.itertuples() if r.spread_7d_pb == r.spread_7d_pb])
    return _par(hoy, ref, f_hoy, f_ref, fecha_ust=fu.isoformat(), bonos=len(sel),
                metodo="Spread sobre el Tesoro de EE.UU. a la duration, ponderado por valor de mercado (Globales y Bonares del canje 2020)")


def mep(precios, hoy: date):
    """MEP implícito con AL30 / AL30D (precio en pesos / precio en dólares)."""
    try:
        p_ars, f = precios.actual("AL30", "BONOS")
        p_usd, _ = precios.actual("AL30D", "BONOS")
        ref = hoy - timedelta(days=DIAS_ATRAS)
        r_ars, f7 = precios.cierre_en("AL30", "BONOS", ref)
        r_usd, _ = precios.cierre_en("AL30D", "BONOS", ref)
    except Exception as e:
        print(f"⚠️ MEP: {e}")
        return None
    if not p_ars or not p_usd:
        return None
    return _par(p_ars / p_usd, r_ars / r_usd if r_ars and r_usd else None, f, f7, metodo="AL30 / AL30D")


def canje(precios, hoy: date):
    """Canje MEP vs cable: AL30D / AL30C - 1."""
    try:
        p_mep, f = precios.actual("AL30D", "BONOS")
        p_ccl, _ = precios.actual("AL30C", "BONOS")
        ref = hoy - timedelta(days=DIAS_ATRAS)
        r_mep, f7 = precios.cierre_en("AL30D", "BONOS", ref)
        r_ccl, _ = precios.cierre_en("AL30C", "BONOS", ref)
    except Exception as e:
        print(f"⚠️ Canje: {e}")
        return None
    if not p_mep or not p_ccl:
        return None
    return _par(p_mep / p_ccl - 1, (r_mep / r_ccl - 1) if r_mep and r_ccl else None, f, f7,
                metodo="AL30D / AL30C - 1")


def bcra_kpi(id_variable: int, hoy: date, metodo: str, escala: float = 1.0):
    try:
        ult, prev = bcra.ultimo_y_previo(id_variable, hoy, DIAS_ATRAS)
    except Exception as e:
        print(f"⚠️ BCRA {id_variable}: {e}")
        return None
    if not ult:
        return None
    return _par(ult[1] * escala, prev[1] * escala if prev else None, ult[0], prev[0] if prev else None, metodo=metodo)


def calcular(precios, df_hd, hoy: date, cache_ust: dict | None = None) -> dict:
    cache_ust = {} if cache_ust is None else cache_ust
    out = {
        "riesgo_pais": riesgo_pais(df_hd, cache_ust),
        "mep": mep(precios, hoy),
        "canje": canje(precios, hoy),
        "a3500": bcra_kpi(bcra.ID_A3500, hoy, "Tipo de cambio mayorista de referencia (BCRA, Com. A 3500)"),
        "tamar": bcra_kpi(bcra.ID_TAMAR, hoy, "TAMAR bancos privados, TNA (BCRA)", escala=0.01),
    }
    return {k: v for k, v in out.items() if v}
