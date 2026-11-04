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
from .config import DIAS_ATRAS

# Definición de cada curva: qué va en cada eje, cómo se agrupa y qué columnas muestra
CURVAS = {
    "tasa-fija": {
        "titulo": "Tasa fija: LECAP y BONCAP",
        "descripcion": "TEM contra días al vencimiento. Pago final fijo.",
        "x": {"campo": "dias", "etiqueta": "Días al vencimiento", "formato": "dias"},
        "y": {"campo": "tem", "etiqueta": "TEM", "formato": "pct"},
        "y_ref": "tem_7d",
        "campo_grupo": "tipo",
        "grupos": [{"id": "LECAP", "etiqueta": "LECAP"}, {"id": "BONCAP", "etiqueta": "BONCAP"}],
        "ajuste_por_grupo": False,
        "columnas": [("ticker", "Ticker", "txt"), ("tipo", "Tipo", "txt"), ("vto", "Vto", "fecha"),
                     ("dias", "Días", "dias"), ("precio", "Precio", "num3"), ("pago_final", "Pago final", "num3"),
                     ("tna", "TNA", "pct"), ("tea", "TEA", "pct"), ("tem", "TEM", "pct"),
                     ("tem_7d", "TEM 7d", "pct"), ("delta_tem_pb", "Δ pb", "pb")],
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
                     ("md", "MD", "num2"), ("tir_7d", "TIR 7d", "pct"), ("delta_pb", "Δ pb", "pb")],
    },
    "hard-dollar": {
        "titulo": "Hard dollar: Bonares y Globales",
        "descripcion": "TIR contra duration modificada. Precios en USD MEP. Una tendencia por ley.",
        "x": {"campo": "md", "etiqueta": "Duration modificada (años)", "formato": "num2"},
        "y": {"campo": "tir", "etiqueta": "TIR", "formato": "pct"},
        "y_ref": "tir_7d",
        "campo_grupo": "ley",
        "grupos": [{"id": "ARG", "etiqueta": "Bonares (ley local)"}, {"id": "NY", "etiqueta": "Globales (ley NY)"}],
        "ajuste_por_grupo": True,
        "columnas": [("ticker", "Ticker", "txt"), ("ley", "Ley", "txt"), ("precio", "Precio", "num2"),
                     ("tir", "TIR", "pct"), ("md", "MD", "num2"), ("tir_7d", "TIR 7d", "pct"),
                     ("delta_pb", "Δ pb", "pb")],
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
    x, y, yr, g = cfg["x"]["campo"], cfg["y"]["campo"], cfg["y_ref"], cfg["campo_grupo"]
    conjuntos = ([(gr["id"], df[df[g] == gr["id"]]) for gr in cfg["grupos"]]
                 if cfg["ajuste_por_grupo"] else [("todos", df)])
    out = []
    for gid, sub in conjuntos:
        for serie, campo in (("hoy", y), ("ref", yr)):
            f = motor.ajuste_log(sub[x].tolist(), pd.to_numeric(sub[campo], errors="coerce").tolist())
            if f:
                out.append({"grupo": gid, "serie": serie, **f,
                            "x_min": float(sub[x].min()), "x_max": float(sub[x].max())})
    return out


def armar(dfs: dict, fecha_precios: date, extras: dict | None = None) -> dict:
    curvas = []
    for cid, cfg in CURVAS.items():
        df = dfs.get(cid)
        if df is None or df.empty:
            continue
        filas = [{k: _limpio(v) for k, v in r.items()} for r in df.to_dict("records")]
        curvas.append({
            "id": cid, "titulo": cfg["titulo"], "descripcion": cfg["descripcion"],
            "x": cfg["x"], "y": cfg["y"], "y_ref": cfg["y_ref"],
            "campo_grupo": cfg["campo_grupo"], "grupos": cfg["grupos"],
            "ajuste_por_grupo": cfg["ajuste_por_grupo"],
            "ajustes": ajustes(df, cfg),
            "columnas": [{"campo": c, "etiqueta": e, "formato": f} for c, e, f in cfg["columnas"]],
            "filas": filas,
        })
    return {"generado": datetime.now().isoformat(timespec="seconds"),
            "fecha_precios": fecha_precios.isoformat(), "dias_atras": DIAS_ATRAS,
            "indices": extras or {}, "curvas": curvas}


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
            monto = r.get("pago_final") or r.get("vr") or ""
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
