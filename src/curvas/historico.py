"""Series históricas para la pestaña "Histórico": A3500, MEP implícito, CER, TAMAR, Merval
(en pesos y en USD), retorno total de Bonares y Globales, y riesgo país diario.

Se reconstruye entero en cada corrida (son ~15 consultas). La curva del Tesoro de EE.UU. de
los meses ya cerrados se guarda en data/historico/ust_cache.json para no volver a pedirla.
"""
import json
from datetime import date, timedelta

from . import bcra, motor, referencias, ust
from .config import HISTORICO_DESDE, MERVAL_CANDIDATOS, MONTOS_EMITIDOS, RAIZ, RIESGO_PAIS, SUFIJO_RIESGO_PAIS
from .flujos import flujos_completos

DIR = RAIZ / "data" / "historico"
BONARES = ["AL29D", "AL30D", "AL35D", "AE38D", "AL41D"]
GLOBALES = ["GD29D", "GD30D", "GD35D", "GD38D", "GD41D", "GD46D"]


def _cache_ust():
    ruta = DIR / "ust_cache.json"
    try:
        crudo = json.loads(ruta.read_text())
        return {tuple(map(int, k.split("-"))): {date.fromisoformat(f): [tuple(p) for p in c] for f, c in v.items()}
                for k, v in crudo.items()}
    except Exception:
        return {}


def _guardar_cache_ust(cache, hoy):
    # solo meses cerrados (los del mes en curso cambian)
    cerrados = {k: v for k, v in cache.items() if (k[0], k[1]) < (hoy.year, hoy.month) and v}
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / "ust_cache.json").write_text(json.dumps(
        {f"{a}-{m}": {f.isoformat(): c for f, c in v.items()} for (a, m), v in cerrados.items()}))


def _retorno_total(precios: dict, flujos: list) -> dict:
    """Índice de retorno total (base 1) de un bono: (precio + pagos del período) / precio anterior."""
    fechas = sorted(precios)
    idx, nivel = {}, 1.0
    for a, b in zip(fechas, fechas[1:]):
        pagos = sum(m for d, m in flujos if a < d <= b)
        nivel *= (precios[b] + pagos) / precios[a]
        idx[b] = nivel
    if fechas:
        idx[fechas[0]] = 1.0
    return idx


def _indice_grupo(series: dict, pesos: dict, precios: dict) -> dict:
    """Promedio de retornos diarios ponderado por valor de mercado del día anterior (monto emitido x precio)."""
    fechas = sorted(set().union(*[set(s) for s in series.values()])) if series else []
    nivel, out, previo = 100.0, {}, None
    for f in fechas:
        if previo is not None:
            num = den = 0.0
            for tk, s in series.items():
                if f in s and previo in s and previo in precios.get(tk, {}):
                    w = pesos.get(tk, 1) * precios[tk][previo]
                    num += w * (s[f] / s[previo] - 1)
                    den += w
            if den:
                nivel *= 1 + num / den
        out[f] = nivel
        previo = f
    return out


def construir(precios, flujos_cfg: dict, feriados, hoy: date) -> dict:
    desde = date.fromisoformat(HISTORICO_DESDE)
    series, avisos = {}, []

    def bcra_serie(nombre, id_var, escala=1.0):
        try:
            series[nombre] = {f: v * escala for f, v in bcra.serie(id_var, desde, hoy).items()}
        except Exception as e:
            avisos.append(f"{nombre}: {e}")

    bcra_serie("a3500", bcra.ID_A3500)
    bcra_serie("cer", bcra.ID_CER)
    bcra_serie("tamar", bcra.ID_TAMAR, 0.01)

    def ppi(tk, tipo="BONOS"):
        try:
            return precios.historico(tk, tipo, desde, hoy)
        except Exception as e:
            avisos.append(f"{tk}: {e}")
            return {}

    al30, al30d = ppi("AL30"), ppi("AL30D")
    series["mep"] = {f: al30[f] / al30d[f] for f in al30 if f in al30d}
    al30c = ppi("AL30C")
    series["canje"] = {f: al30d[f] / al30c[f] - 1 for f in al30d if f in al30c}

    for tk, tipo in MERVAL_CANDIDATOS:
        mv = ppi(tk, tipo)
        if mv:
            series["merval"] = mv
            series["merval_usd"] = {f: v / series["mep"][f] for f, v in mv.items() if f in series["mep"]}
            break
    else:
        avisos.append("Merval: ningún ticker candidato devolvió datos en PPI")

    precios_usd, rt = {}, {}
    for tk in BONARES + GLOBALES:
        p = ppi(tk)
        if p:
            precios_usd[tk] = p
            rt[tk] = _retorno_total(p, flujos_completos(flujos_cfg, tk[:-1]))
    pesos = {tk: MONTOS_EMITIDOS.get(tk[:-1], 1) for tk in rt}
    if any(tk in rt for tk in BONARES):
        series["bonares_rt"] = _indice_grupo({tk: rt[tk] for tk in BONARES if tk in rt}, pesos, precios_usd)
    if any(tk in rt for tk in GLOBALES):
        series["globales_rt"] = _indice_grupo({tk: rt[tk] for tk in GLOBALES if tk in rt}, pesos, precios_usd)

    # riesgo país diario: Globales en dólar cable (misma cuenta que el KPI de cabecera)
    cable = {}
    for base in RIESGO_PAIS:
        p = ppi(base + SUFIJO_RIESGO_PAIS)
        if p:
            cable[base] = p
    cache = _cache_ust()
    rp = {}
    fechas = sorted(set().union(*[set(p) for p in cable.values()])) if cable else []
    for f in fechas:
        fu, curva = ust.curva_en(f, cache)
        if not curva or (f - fu).days > 7:
            continue
        liq = motor.liquidacion(f, feriados)
        bonos = []
        for base, p in cable.items():
            if f not in p:
                continue
            m = motor.metricas_bono(p[f], flujos_completos(flujos_cfg, base), liq)
            if m:
                bonos.append((motor.spread_ust(m["tir"], m["duration"], curva), MONTOS_EMITIDOS[base], p[f]))
        if len(bonos) >= len(RIESGO_PAIS) - 1:
            rp[f] = motor.riesgo_pais(bonos)
    series["riesgo_pais"] = rp
    pub = referencias.riesgo_pais_publicado()
    if pub:
        series["riesgo_pais_publicado"] = {f: v for f, v in pub.items() if f >= desde}
    else:
        avisos.append("riesgo país publicado: ArgentinaDatos no respondió")
    _guardar_cache_ust(cache, hoy)

    return {"desde": HISTORICO_DESDE, "avisos": avisos,
            "series": {k: sorted([[f.isoformat(), round(v, 6)] for f, v in s.items()]) for k, s in series.items() if s}}


def guardar(datos: dict, ruta_json):
    ruta_json.parent.mkdir(parents=True, exist_ok=True)
    ruta_json.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
