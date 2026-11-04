"""Valida el motor contra el informe BYMA/IAMC del 05-Oct-26 (liquidación 06-Oct-26).
Precio USD = paridad × valor técnico / 100, ambos del informe. Tolerancia: 6 pb."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from curvas import motor  # noqa: E402

LIQ = date(2026, 10, 6)

# Flujos futuros por VN 100 USD al 06-Oct-26 (repo rendimientos-ar)
AL30 = [("2027-01-09", 8.24), ("2027-07-09", 8.21), ("2028-01-09", 8.42), ("2028-07-09", 8.35),
        ("2029-01-09", 8.28), ("2029-07-09", 8.21), ("2030-01-09", 8.14), ("2030-07-09", 8.07)]
GD35 = [("2027-01-09", 2.0625), ("2027-07-09", 2.0625), ("2028-01-09", 2.375), ("2028-07-09", 2.375),
        ("2029-01-09", 2.5), ("2029-07-09", 2.5), ("2030-01-09", 2.5), ("2030-07-09", 2.5),
        ("2031-01-09", 12.5), ("2031-07-09", 12.25), ("2032-01-09", 12), ("2032-07-09", 11.75),
        ("2033-01-09", 11.5), ("2033-07-09", 11.25), ("2034-01-09", 11), ("2034-07-09", 10.75),
        ("2035-01-09", 10.5), ("2035-07-09", 10.25)]


def _fl(lista):
    return [(date.fromisoformat(d), m) for d, m in lista]


def test_tir_al30_vs_informe():
    # Informe: paridad 86.7, VT 64.1, YTM 9.16%
    assert abs(motor.tir(86.7 * 64.1 / 100, _fl(AL30), LIQ) - 0.0916) < 0.0006


def test_tir_gd35_vs_informe():
    # Informe: paridad 74.5, VT 101.0, YTM 10.69%
    assert abs(motor.tir(74.5 * 101.0 / 100, _fl(GD35), LIQ) - 0.1069) < 0.0006


def test_boncap_t30j7_vs_informe():
    # Informe 29-Sep-26 (liquidación 30-Sep): precio 128.40, pago 156.04 -> 273 días, TEA 29.78%, TEM 2.20%
    m = motor.metricas_lecap(128.40, 156.04, date(2027, 6, 30), date(2026, 9, 30))
    assert m["dias"] == 273
    assert abs(m["tea"] - 0.2978) < 0.0003
    assert abs(m["tem"] - 0.0220) < 0.0001


def test_liquidacion_saltea_fin_de_semana():
    assert motor.liquidacion(date(2026, 10, 30)) == date(2026, 11, 2)


def test_tir_sin_flujos_futuros():
    assert motor.tir(50, [(date(2020, 1, 1), 100)], LIQ) is None


def test_ajuste_log_recupera_parametros():
    import math
    xs = [10, 30, 90, 180, 365]
    ys = [0.02 + 0.003 * math.log(x) for x in xs]
    f = motor.ajuste_log(xs, ys)
    assert abs(f["a"] - 0.02) < 1e-9 and abs(f["b"] - 0.003) < 1e-9 and abs(f["r2"] - 1) < 1e-9


def test_ajuste_log_pocos_puntos():
    assert motor.ajuste_log([1, 2], [0.1, 0.2]) is None


def test_cer_x30n6_vs_informe():
    m = motor.metricas_cer(127.5, 659.678896, 843.486823, date(2026, 11, 30), LIQ)
    assert m["dias"] == 55
    assert abs(m["vr"] - 127.9) < 0.06
    assert abs(m["tir"] - 0.0196) < 0.002
