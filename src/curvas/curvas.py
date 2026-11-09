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
                      "fecha": f, "precio": p, "tir": a["tir"], "md": a["md"], "duration": a["duration"],
                      "fecha_7d": f7, "precio_7d": p7, "tir_7d": b["tir"] if b else None,
                      "duration_7d": b["duration"] if b else None,
                      "delta_pb": (a["tir"] - b["tir"]) * 1e4 if b else None,
                      "volumen": precios.volumenes.get(tk)})
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
                      "tna_7d": b["tna"] if b else None, "tea_7d": b["tea"] if b else None,
                      "delta_tem_pb": (a["tem"] - b["tem"]) * 1e4 if b else None,
                      "volumen": precios.volumenes.get(tk)})
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
                      "delta_pb": (a["tir"] - b["tir"]) * 1e4 if b else None,
                      "volumen": precios.volumenes.get(tk)})
    df = pd.DataFrame(filas)
    return (df.sort_values("dias").reset_index(drop=True) if not df.empty else df), errores


def tamar(precios, feriados, hoy: date, serie_tamar: dict) -> tuple[pd.DataFrame, list]:
    """TAMAR capitalizables: monto al vencimiento proyectado con la TAMAR publicada y,
    para los días que faltan, el promedio de los últimos 30 días."""
    from .config import TAMAR_BONOS
    filas, errores = [], []
    if not serie_tamar:
        return pd.DataFrame(), [("TAMAR", "sin serie del BCRA")]
    ref = hoy - timedelta(days=DIAS_ATRAS)

    def futura(corte):
        ult = [v for f, v in serie_tamar.items() if 0 <= (corte - f).days < 30]
        return sum(ult) / len(ult) if ult else serie_tamar[max(f for f in serie_tamar if f <= corte)]

    def ultima(corte):
        previas = [f for f in serie_tamar if f <= corte]
        return serie_tamar[max(previas)] if previas else None

    for tk, (emi, vto, margen) in TAMAR_BONOS.items():
        emi, vto = date.fromisoformat(emi), date.fromisoformat(vto)
        if vto <= hoy:
            continue
        try:
            p, f = precios.actual(tk, "BONOS")
        except Exception as e:
            errores.append((tk, f"precio actual: {e}")); continue
        if not p:
            errores.append((tk, "sin precio")); continue
        try:
            p7, f7 = precios.cierre_en(tk, "BONOS", ref)
        except Exception:
            p7, f7 = None, None
        monto = motor.monto_tamar(emi, vto, margen, serie_tamar, f, futura(f))
        a = motor.metricas_tamar(p, monto, vto, motor.liquidacion(f, feriados), ultima(f))
        b = None
        if p7:
            monto7 = motor.monto_tamar(emi, vto, margen, serie_tamar, f7, futura(f7))
            b = motor.metricas_tamar(p7, monto7, vto, motor.liquidacion(f7, feriados), ultima(f7))
        if not a:
            continue
        filas.append({"ticker": tk, "tipo": "TAMAR", "fecha": f, "precio": p, "vto": vto, "margen": margen,
                      "monto_vto": monto, **a, "fecha_7d": f7, "precio_7d": p7,
                      "tna_7d": b["tna"] if b else None, "tem_7d": b["tem"] if b else None,
                      "tea_7d": b["tea"] if b else None,
                      "delta_tem_pb": (a["tem"] - b["tem"]) * 1e4 if b else None,
                      "volumen": precios.volumenes.get(tk)})
    df = pd.DataFrame(filas)
    return (df.sort_values("dias").reset_index(drop=True) if not df.empty else df), errores
