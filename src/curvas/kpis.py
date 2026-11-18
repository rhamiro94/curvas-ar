"""Indicadores de cabecera: riesgo país, MEP implícito, canje, A3500 y TAMAR (hoy y hace N días)."""
from datetime import date, timedelta

from . import bcra, motor, referencias, ust
from .config import DIAS_ATRAS, MONTOS_EMITIDOS, RIESGO_PAIS, SUFIJO_RIESGO_PAIS
from .flujos import flujos_soberano


def _par(actual, previo, fecha_a=None, fecha_p=None, **extra):
    if actual is None:
        return None
    d = {"valor": actual, "fecha": fecha_a.isoformat() if fecha_a else None,
         "valor_7d": previo, "fecha_7d": fecha_p.isoformat() if fecha_p else None}
    d.update(extra)
    return d


def spreads_hard_dollar(df_hd, cache_ust: dict):
    """Agrega spread_pb / spread_7d_pb (sobre el Tesoro de EE.UU.) a cada bono de la tabla hard dollar (precio MEP)."""
    if df_hd is None or df_hd.empty:
        return
    f_hoy = df_hd["fecha"].max()
    f_ref = df_hd["fecha_7d"].dropna().max() if df_hd["fecha_7d"].notna().any() else None
    _, curva = ust.curva_en(f_hoy, cache_ust)
    _, curva7 = ust.curva_en(f_ref, cache_ust) if f_ref else (None, None)
    if not curva:
        return
    df_hd["spread_pb"] = [motor.spread_ust(r.tir, r.duration, curva) for r in df_hd.itertuples()]
    df_hd["spread_7d_pb"] = [motor.spread_ust(r.tir_7d, r.duration_7d, curva7)
                             if curva7 and r.tir_7d == r.tir_7d and r.tir_7d is not None else None
                             for r in df_hd.itertuples()]


def riesgo_pais_en(precios_bonos: dict, cfg: dict, feriados, cache_ust: dict):
    """Riesgo país con {base: (precio cable, fecha)}. Devuelve (pb, fecha precios, fecha curva UST, n bonos)."""
    if not precios_bonos:
        return None, None, None, 0
    fecha = max(f for _, f in precios_bonos.values())
    fu, curva = ust.curva_en(fecha, cache_ust)
    if not curva:
        return None, fecha, None, 0
    liq = motor.liquidacion(fecha, feriados)
    bonos = []
    for base, (p, _) in precios_bonos.items():
        m = motor.metricas_bono(p, flujos_soberano(cfg, base) or [], liq)
        if m:
            bonos.append((motor.spread_ust(m["tir"], m["duration"], curva), MONTOS_EMITIDOS[base], p))
    return motor.riesgo_pais(bonos), fecha, fu, len(bonos)


def riesgo_pais(precios, cfg: dict, feriados, hoy: date, cache_ust: dict):
    """KPI de riesgo país: Globales en dólar cable, spread sobre el Tesoro a la duration, ponderado por valor de mercado."""
    ref = hoy - timedelta(days=DIAS_ATRAS)
    hoy_p, ref_p = {}, {}
    for base in RIESGO_PAIS:
        tk = base + SUFIJO_RIESGO_PAIS
        try:
            p, f = precios.actual(tk, "BONOS")
            r, f7 = precios.cierre_en(tk, "BONOS", ref)
        except Exception as e:
            print(f"⚠️ Riesgo país {tk}: {e}")
            continue
        if p:
            hoy_p[base] = (p, f)
        if r:
            ref_p[base] = (r, f7)
    valor, f_hoy, fu, n = riesgo_pais_en(hoy_p, cfg, feriados, cache_ust)
    valor_7d, f_ref, _, _ = riesgo_pais_en(ref_p, cfg, feriados, cache_ust)
    if valor is None:
        return None
    out = _par(valor, valor_7d, f_hoy, f_ref, fecha_ust=fu.isoformat() if fu else None, bonos=n,
               metodo="Globales en dólar cable: spread sobre el Tesoro de EE.UU. a la duration, ponderado por valor de mercado")
    pub = referencias.riesgo_pais_publicado()
    if pub:
        f_pub = max(pub)
        out["publicado"] = {"valor": pub[f_pub], "fecha": f_pub.isoformat(),
                            "fuente": "JP Morgan EMBI (vía ArgentinaDatos)"}
        mismo = pub.get(f_hoy)
        if mismo is not None:
            out["publicado"]["diferencia_pb"] = valor - mismo
    return out


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


def calcular(precios, df_hd, hoy: date, cfg: dict, feriados, cache_ust: dict | None = None) -> dict:
    cache_ust = {} if cache_ust is None else cache_ust
    spreads_hard_dollar(df_hd, cache_ust)
    out = {
        "riesgo_pais": riesgo_pais(precios, cfg, feriados, hoy, cache_ust),
        "mep": mep(precios, hoy),
        "canje": canje(precios, hoy),
        "a3500": bcra_kpi(bcra.ID_A3500, hoy, "Tipo de cambio mayorista de referencia (BCRA, Com. A 3500)"),
        "tamar": bcra_kpi(bcra.ID_TAMAR, hoy, "TAMAR bancos privados, TNA (BCRA)", escala=0.01),
    }
    return {k: v for k, v in out.items() if v}
