"""Riesgo país y breakeven, validados con datos del informe BYMA/IAMC del 05-Oct-26."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from curvas import motor, ust  # noqa: E402

# Curva del Tesoro de EE.UU. del 05-Oct-26 (treasury.gov, par yields)
UST_05OCT = [(1 / 12, .0405), (.25, .0422), (.5, .0430), (1, .0447), (2, .0484), (3, .0497),
             (5, .0506), (7, .0519), (10, .0531), (20, .0570), (30, .0566)]


def test_interpolacion_ust():
    assert abs(ust.interpolar(UST_05OCT, 4) - .05015) < 1e-9
    assert ust.interpolar(UST_05OCT, 0.01) == .0405
    assert ust.interpolar(UST_05OCT, 40) == .0566


def test_riesgo_pais_rango_informe():
    # Globales (TIR, duration Macaulay ~ MD x (1+TIR), monto USD M, precio USD) del informe 05-Oct-26
    bonos = {"GD29": (.0624, 1.49, 2635, 55.8), "GD30": (.0767, 1.94, 13587, 57.0),
             "GD38": (.1054, 4.53, 11405, 79.4), "GD35": (.1069, 5.31, 20502, 75.2),
             "GD41": (.1075, 5.76, 10482, 69.9)}
    rp = motor.riesgo_pais([(motor.spread_ust(t, d, UST_05OCT), m, p) for t, d, m, p in bonos.values()])
    # El EMBI publicado rondaba los 489 pb: la aproximación tiene que quedar cerca
    assert 440 < rp < 540


def test_indice_grupo_pondera_por_valor_de_mercado():
    from datetime import date
    from curvas.historico import _indice_grupo
    d0, d1 = date(2026, 1, 2), date(2026, 1, 5)
    # A sube 10% y B no cambia. A vale 2 x 50 = 100 y B 1 x 100 = 100 -> mismo peso -> +5%
    idx = _indice_grupo({"A": {d0: 1.0, d1: 1.1}, "B": {d0: 1.0, d1: 1.0}},
                        {"A": 2, "B": 1}, {"A": {d0: 50, d1: 55}, "B": {d0: 100, d1: 100}})
    assert abs(idx[d1] - 105) < 1e-9


def test_breakeven():
    # 2.2% TEM fija (TEA 29.8%) contra 5% real -> ~1.82% mensual
    be = motor.breakeven_mensual((1.022 ** 12) - 1, .05)
    assert abs(be - (1.022 / 1.05 ** (1 / 12) - 1)) < 1e-12
    assert 0.017 < be < 0.019
