"""Arma las tablas de cada curva combinando flujos, precios y el motor."""
from datetime import date, timedelta

import pandas as pd

from . import motor
from .config import HARD_DOLLAR, DIAS_ATRAS
from .flujos import flujos_soberano, lecaps_vigentes


def hard_dollar(cfg, precios, feriados, hoy: date) -> tuple[pd.DataFrame, list]:
    filas, errores = [], []
    ref = hoy - timedelta(days=DIAS_ATRAS)
    for tk in HARD_DOLLAR:
        base = tk[:-1]
        fl = flujos_soberano(cfg, base)
        if not fl:
            errores.append((tk, "sin flujos en el repo")); continue
        try:
            p, f = precios.actual(tk, "BONOS")
        except Exception as e:
            errores.append((tk, f"precio actual: {e}")); continue
        try:
            p7, f7 = precios.cierre_en(tk, "BONOS", ref)
        except Exception as e:
            p7, f7 = None, None
            errores.append((tk, f"sin cierre de hace {DIAS_ATRAS} días: {e}"))
        if not p:
            errores.append((tk, "sin precio")); continue
        a = motor.metricas_bono(p, fl, motor.liquidacion(f, feriados))
        b = motor.metricas_bono(p7, fl, motor.liquidacion(f7, feriados)) if p7 else None
        filas.append({"ticker": tk, "ley": "NY" if base.startswith("GD") else "ARG",
                      "fecha": f, "precio": p, "tir": a["tir"], "md": a["md"],
                      "fecha_7d": f7, "precio_7d": p7, "tir_7d": b["tir"] if b else None,
                      "delta_pb": (a["tir"] - b["tir"]) * 1e4 if b else None})
    return pd.DataFrame(filas).sort_values("md").reset_index(drop=True), errores


def lecap_boncap(cfg, precios, feriados, hoy: date) -> tuple[pd.DataFrame, list]:
    filas, errores = [], []
    ref = hoy - timedelta(days=DIAS_ATRAS)
    for tk, x in lecaps_vigentes(cfg, hoy).items():
        tipo = "LETRAS" if tk.startswith("S") else "BONOS"
        try:
            p, f = precios.actual(tk, tipo)
        except Exception as e:
            errores.append((tk, f"precio actual: {e}")); continue
        try:
            p7, f7 = precios.cierre_en(tk, tipo, ref)
        except Exception as e:
            p7, f7 = None, None
            errores.append((tk, f"sin cierre de hace {DIAS_ATRAS} días: {e}"))
        if not p:
            errores.append((tk, "sin precio")); continue
        a = motor.metricas_lecap(p, x["pago_final"], x["vto"], motor.liquidacion(f, feriados))
        b = motor.metricas_lecap(p7, x["pago_final"], x["vto"], motor.liquidacion(f7, feriados)) if p7 else None
        if not a:
            continue
        filas.append({"ticker": tk, "tipo": "LECAP" if tk.startswith("S") else "BONCAP",
                      "fecha": f, "precio": p, "pago_final": x["pago_final"], "vto": x["vto"],
                      **a, "fecha_7d": f7, "precio_7d": p7, "tem_7d": b["tem"] if b else None,
                      "delta_tem_pb": (a["tem"] - b["tem"]) * 1e4 if b else None})
    return pd.DataFrame(filas).sort_values("dias").reset_index(drop=True), errores


def cer(precios, feriados, hoy: date, serie_cer: dict) -> tuple[pd.DataFrame, list]:
    """CER cupón cero: TIR real con CER de emisión (universo) y CER T-10 del BCRA."""
    from .bcra import habil_menos
    from .universo import grupos
    filas, errores = [], []
    ref = hoy - timedelta(days=DIAS_ATRAS)

    def calc(p, f, ins):
        if not p:
            return None, None
        liq = motor.liquidacion(f, feriados)
        f_cer = habil_menos(liq, 10, feriados)
        valor = serie_cer.get(f_cer)
        if valor is None:
            return None, f_cer
        return motor.metricas_cer(p, ins["cer_emision"], valor, date.fromisoformat(ins["vto"]), liq), f_cer

    for ins in grupos["CER"]:
        if "cer_emision" not in ins or date.fromisoformat(ins["vto"]) <= hoy:
            continue
        tk, tipo = ins["ticker"], ins["type"]
        try:
            p, f = precios.actual(tk, tipo)
        except Exception as e:
            errores.append((tk, f"precio actual: {e}")); continue
        if not p:
            errores.append((tk, "sin precio")); continue
        try:
            p7, f7 = precios.cierre_en(tk, tipo, ref)
        except Exception:
            p7, f7 = None, None
        a, f_cer = calc(p, f, ins)
        if not a:
            errores.append((tk, f"sin CER del {f_cer}")); continue
        b, _ = calc(p7, f7, ins) if p7 else (None, None)
        filas.append({"ticker": tk, "tipo": "LECER" if tk.startswith("X") else "BONCER",
                      "fecha": f, "precio": p, "vto": date.fromisoformat(ins["vto"]),
                      "cer_emision": ins["cer_emision"], "fecha_cer": f_cer, **a,
                      "fecha_7d": f7, "precio_7d": p7, "tir_7d": b["tir"] if b else None,
                      "delta_pb": (a["tir"] - b["tir"]) * 1e4 if b else None})
    df = pd.DataFrame(filas)
    return (df.sort_values("dias").reset_index(drop=True) if not df.empty else df), errores
