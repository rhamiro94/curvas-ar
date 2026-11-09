"""Arma los datos de la terminal web (docs/data/curvas.json) y las tablas de control.

Cada curva lleva sus puntos (hoy y hace N días) y sus líneas de tendencia
logarítmicas y = a + b·ln(x), calculadas acá en Python para que la web y el
Sheet de control muestren exactamente los mismos números.
"""
import json
import math
from datetime import date, datetime

import pandas as pd

from . import motor
from .config import DIAS_ATRAS, HORIZONTE_COLCHON, MEP_NIVELES, MEP_PASO

# Definición de cada curva: qué va en cada eje, cómo se agrupa y qué columnas muestra
CURVAS = {
    "tasa-fija": {
        "titulo": "Tasa fija: LECAP y BONCAP",
        "descripcion": "TEM contra días al vencimiento. Pago final fijo.",
        "x": {"campo": "dias", "etiqueta": "Días al vencimiento", "formato": "dias"},
        "y": {"campo": "tem", "etiqueta": "TEM", "formato": "pct"},
        "y_ref": "tem_7d",
        "y_opciones": [{"campo": "tna", "etiqueta": "TNA", "ref": "tna_7d"},
                       {"campo": "tea", "etiqueta": "TEA", "ref": "tea_7d"},
                       {"campo": "tem", "etiqueta": "TEM", "ref": "tem_7d"}],
        "campo_grupo": "tipo",
        "grupos": [{"id": "LECAP", "etiqueta": "LECAP"}, {"id": "BONCAP", "etiqueta": "BONCAP"}],
        "ajuste_por_grupo": False,
        "columnas": [("ticker", "Ticker", "txt"), ("tipo", "Tipo", "txt"), ("vto", "Vto", "fecha"),
                     ("dias", "Días", "dias"), ("precio", "Precio", "num3"), ("pago_final", "Pago final", "num3"),
                     ("tna", "TNA", "pct"), ("tea", "TEA", "pct"), ("tem", "TEM", "pct"),
                     ("delta_tem_pb", "Δ TEM pb", "pb"), ("volumen", "Volumen", "vol")],
    },
    "tamar": {
        "titulo": "TAMAR: bonos capitalizables",
        "descripcion": "TNA contra días al vencimiento. Monto al vencimiento proyectado con la TAMAR publicada y el promedio de los últimos 30 días para lo que falta.",
        "x": {"campo": "dias", "etiqueta": "Días al vencimiento", "formato": "dias"},
        "y": {"campo": "tna", "etiqueta": "TNA", "formato": "pct"},
        "y_ref": "tna_7d",
        "y_opciones": [{"campo": "tna", "etiqueta": "TNA", "ref": "tna_7d"},
                       {"campo": "tea", "etiqueta": "TEA", "ref": "tea_7d"},
                       {"campo": "tem", "etiqueta": "TEM", "ref": "tem_7d"}],
        "campo_grupo": "tipo",
        "grupos": [{"id": "TAMAR", "etiqueta": "TAMAR capitalizable"}],
        "ajuste_por_grupo": False,
        "columnas": [("ticker", "Ticker", "txt"), ("vto", "Vto", "fecha"), ("dias", "Días", "dias"),
                     ("margen", "Margen", "pct"), ("precio", "Precio", "num2"), ("monto_vto", "Monto vto proy.", "num2"),
                     ("tna", "TNA", "pct"), ("tem", "TEM", "pct"), ("margen_implicito", "Margen implícito", "pct"),
                     ("delta_tem_pb", "Δ TEM pb", "pb"), ("volumen", "Volumen", "vol")],
    },
    "cer": {
        "titulo": "CER: LECER y BONCER cupón cero",
        "descripcion": "TIR real (sobre CER) contra días al vencimiento. VR = 100 × CER T−10 / CER de emisión.",
        "x": {"campo": "dias", "etiqueta": "Días al vencimiento", "formato": "dias"},
        "y": {"campo": "tir", "etiqueta": "TIR real", "formato": "pct"},
        "y_ref": "tir_7d",
        "campo_grupo": "tipo",
        "grupos": [{"id": "LECER", "etiqueta": "LECER"}, {"id": "BONCER", "etiqueta": "BONCER"}],
        "ajuste_por_grupo": False,
        "columnas": [("ticker", "Ticker", "txt"), ("vto", "Vto", "fecha"), ("dias", "Días", "dias"),
                     ("precio", "Precio", "num2"), ("vr", "VR", "num2"), ("tir", "TIR real", "pct"),
                     ("md", "MD", "num2"), ("tir_7d", "TIR 7d", "pct"), ("delta_pb", "Δ pb", "pb"),
                     ("volumen", "Volumen", "vol")],
    },
    "hard-dollar": {
        "titulo": "Hard dollar: Bonares y Globales",
        "descripcion": "TIR contra duration modificada. Precios en USD MEP. Una tendencia por ley (los BOPREAL no tienen tendencia: son dos puntos).",
        "x": {"campo": "md", "etiqueta": "Duration modificada (años)", "formato": "num2"},
        "y": {"campo": "tir", "etiqueta": "TIR", "formato": "pct"},
        "y_ref": "tir_7d",
        "campo_grupo": "ley",
        "grupos": [{"id": "ARG", "etiqueta": "Bonares (ley local)"}, {"id": "NY", "etiqueta": "Globales (ley NY)"},
                   {"id": "BCRA", "etiqueta": "BOPREAL (BCRA)"}],
        "ajuste_por_grupo": True,
        "columnas": [("ticker", "Ticker", "txt"), ("ley", "Ley", "txt"), ("precio", "Precio", "num2"),
                     ("tir", "TIR", "pct"), ("md", "MD", "num2"), ("spread_pb", "Spread UST", "pbs"),
                     ("tir_7d", "TIR 7d", "pct"), ("delta_pb", "Δ pb", "pb"), ("volumen", "Volumen", "vol")],
        "colchon": [("ticker", "Ticker", "txt"), ("precio", "Precio T+1", "num2"), ("tir", "TIR", "pct"),
                    ("cobros_horizonte", "Cobros hasta el horizonte", "num2"),
                    ("caida_eq", "Caída para retorno 0", "pctneg"), ("precio_eq", "Precio de salida de equilibrio", "num2")],
    },
}


def _limpio(v):
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if hasattr(v, "item"):  # numpy
        return _limpio(v.item())
    return v


def ajustes(df: pd.DataFrame, cfg: dict) -> list:
    """Tendencias log de hoy y de hace N días, por grupo o para toda la curva."""
    if df.empty:
        return []
    x, g = cfg["x"]["campo"], cfg["campo_grupo"]
    opciones = cfg.get("y_opciones") or [{"campo": cfg["y"]["campo"], "ref": cfg["y_ref"]}]
    conjuntos = ([(gr["id"], df[df[g] == gr["id"]]) for gr in cfg["grupos"]]
                 if cfg["ajuste_por_grupo"] else [("todos", df)])
    out = []
    for op in opciones:
        for gid, sub in conjuntos:
            for serie, campo in (("hoy", op["campo"]), ("ref", op["ref"])):
                if campo not in sub:
                    continue
                f = motor.ajuste_log(sub[x].tolist(), pd.to_numeric(sub[campo], errors="coerce").tolist())
                if f:
                    out.append({"y": op["campo"], "grupo": gid, "serie": serie, **f,
                                "x_min": float(sub[x].min()), "x_max": float(sub[x].max())})
    return out


def colchon(df_hd, flujos_cfg: dict, liq: date):
    """Cuánto puede caer el precio hasta el horizonte cobrando los flujos intermedios y terminar en 0."""
    from .flujos import flujos_soberano
    h = date.fromisoformat(HORIZONTE_COLCHON)
    cobros, caidas, precios_eq = [], [], []
    for r in df_hd.itertuples():
        fl = flujos_soberano(flujos_cfg, r.ticker[:-1]) or []
        c = sum(m for d, m in fl if liq < d <= h)
        cobros.append(c)
        caidas.append(-c / r.precio if r.precio else None)
        precios_eq.append(r.precio - c)
    df_hd["cobros_horizonte"], df_hd["caida_eq"], df_hd["precio_eq"] = cobros, caidas, precios_eq


def breakeven(df_fija, df_cer, aj_fija: list, aj_cer: list, plazos=(30, 90, 180, 270, 365)) -> dict | None:
    """Inflación implícita entre tasa fija y CER: por pares del mismo vencimiento y por las tendencias."""
    if df_fija is None or df_cer is None or df_fija.empty or df_cer.empty:
        return None
    pares = []
    cer_por_vto = {r["vto"]: r for r in df_cer.to_dict("records")}
    for r in df_fija.to_dict("records"):
        c = cer_por_vto.get(r["vto"])
        if c:
            be = motor.breakeven_mensual(r["tea"], c["tir"])
            pares.append({"vto": _limpio(r["vto"]), "dias": r["dias"], "fija": r["ticker"], "cer": c["ticker"],
                          "tea_fija": r["tea"], "tir_real": c["tir"], "be_mensual": be,
                          "be_anual": (1 + be) ** 12 - 1})
    tf = next((a for a in aj_fija if a["serie"] == "hoy"), None)
    tc = next((a for a in aj_cer if a["serie"] == "hoy"), None)
    curva = []
    if tf and tc:
        lo, hi = max(tf["x_min"], tc["x_min"]), min(tf["x_max"], tc["x_max"])
        for d in plazos:
            if lo <= d <= hi:
                tem = tf["a"] + tf["b"] * math.log(d)
                real = tc["a"] + tc["b"] * math.log(d)
                be = motor.breakeven_mensual((1 + tem) ** 12 - 1, real)
                curva.append({"dias": d, "tem_fija": tem, "tir_real": real, "be_mensual": be,
                              "be_anual": (1 + be) ** 12 - 1})
    return {"pares": pares, "curva": curva}


def calculadora(cfg: dict, dfs: dict, liq: date) -> list:
    """Datos para recalcular en la web la TIR de cada especie a un precio manual."""
    from .flujos import flujos_soberano
    out = []
    df = dfs.get("hard-dollar")
    for r in ([] if df is None else df.to_dict("records")):
        fl = flujos_soberano(cfg, r["ticker"][:-1]) or []
        out.append({"ticker": r["ticker"], "curva": "Hard dollar", "tipo": "flujos", "precio": r["precio"],
                    "flujos": [[d.isoformat(), m] for d, m in fl if d > liq], "tir": r["tir"]})
    df = dfs.get("tasa-fija")
    for r in ([] if df is None else df.to_dict("records")):
        out.append({"ticker": r["ticker"], "curva": "Tasa fija", "tipo": "pago_final", "precio": r["precio"],
                    "flujos": [[_limpio(r["vto"]), r["pago_final"]]], "tir": r["tea"]})
    df = dfs.get("cer")
    for r in ([] if df is None else df.to_dict("records")):
        out.append({"ticker": r["ticker"], "curva": "CER", "tipo": "cer", "precio": r["precio"],
                    "flujos": [[_limpio(r["vto"]), r["vr"]]], "tir": r["tir"]})
    return out


def armar(dfs: dict, fecha_precios: date, extras: dict | None = None, kpis: dict | None = None,
          flujos_cfg: dict | None = None, liq: date | None = None) -> dict:
    if flujos_cfg and liq and dfs.get("hard-dollar") is not None and not dfs["hard-dollar"].empty:
        colchon(dfs["hard-dollar"], flujos_cfg, liq)
    curvas = []
    for cid, cfg in CURVAS.items():
        df = dfs.get(cid)
        if df is None or df.empty:
            continue
        filas = [{k: _limpio(v) for k, v in r.items()} for r in df.to_dict("records")]
        curvas.append({
            "id": cid, "titulo": cfg["titulo"], "descripcion": cfg["descripcion"],
            "x": cfg["x"], "y": cfg["y"], "y_ref": cfg["y_ref"], "y_opciones": cfg.get("y_opciones"),
            "colchon": [{"campo": c, "etiqueta": e, "formato": f} for c, e, f in cfg.get("colchon", [])] or None,
            "campo_grupo": cfg["campo_grupo"], "grupos": cfg["grupos"],
            "ajuste_por_grupo": cfg["ajuste_por_grupo"],
            "ajustes": ajustes(df, cfg),
            "columnas": [{"campo": c, "etiqueta": e, "formato": f} for c, e, f in cfg["columnas"]],
            "filas": filas,
        })
    aj = {c["id"]: c["ajustes"] for c in curvas}
    return {"generado": datetime.now().isoformat(timespec="seconds"),
            "fecha_precios": fecha_precios.isoformat(), "dias_atras": DIAS_ATRAS,
            "liquidacion": liq.isoformat() if liq else None,
            "config": {"horizonte_colchon": HORIZONTE_COLCHON, "mep_paso": MEP_PASO, "mep_niveles": MEP_NIVELES},
            "indices": extras or {}, "kpis": kpis or {},
            "breakeven": breakeven(dfs.get("tasa-fija"), dfs.get("cer"), aj.get("tasa-fija", []), aj.get("cer", [])),
            "calculadora": calculadora(flujos_cfg, dfs, liq) if flujos_cfg and liq else [],
            "curvas": curvas}


def guardar(datos: dict, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def tablas_control(datos: dict):
    """Filas para las pestañas de control del Sheet: 'curvas' y 'ajustes'."""
    enc_c = ["Curva", "Ticker", "Grupo", "Fecha precio", "Vto", "Días", "MD", "Precio",
             "Monto / VR usado", "Tasa", "Medida", f"Precio {DIAS_ATRAS}d", f"Tasa {DIAS_ATRAS}d", "Δ pb"]
    filas_c = []
    for c in datos["curvas"]:
        yc, yr = c["y"]["campo"], c["y_ref"]
        for r in c["filas"]:
            monto = r.get("pago_final") or r.get("vr") or r.get("monto_vto") or ""
            delta = r.get("delta_pb", r.get("delta_tem_pb"))
            filas_c.append([c["id"], r["ticker"], r.get(c["campo_grupo"], ""), r.get("fecha", ""),
                            r.get("vto", ""), r.get("dias", ""), r.get("md", ""), r.get("precio", ""),
                            monto, r.get(yc, ""), c["y"]["etiqueta"], r.get("precio_7d") or "",
                            r.get(yr) if r.get(yr) is not None else "", delta if delta is not None else ""])
    enc_a = ["Curva", "Grupo", "Serie", "a", "b", "R²", "Puntos", "Fórmula"]
    filas_a = []
    for c in datos["curvas"]:
        for a in c["ajustes"]:
            filas_a.append([c["id"], a["grupo"], "hoy" if a["serie"] == "hoy" else f"hace {DIAS_ATRAS}d",
                            a["a"], a["b"], a["r2"], a["n"],
                            f"{c['y']['etiqueta']} = a + b·ln({c['x']['etiqueta']})"])
    return [enc_c] + filas_c, [enc_a] + filas_a
