"""CER: VR = 100 x CER(T-10 de la liquidación) / CER de emisión. Datos BCRA e informe IAMC 05-Oct-26."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from curvas.bcra import habil_menos  # noqa: E402
from curvas.universo import grupos  # noqa: E402

CER_22SEP26 = 843.486823  # T-10 hábiles de la liquidación 06-Oct-26


def test_t10_de_la_liquidacion_del_informe():
    assert habil_menos(date(2026, 10, 6), 10) == date(2026, 9, 22)


def test_vr_reproduce_el_informe():
    vr_informe = {i["ticker"]: (i["vr"], i["cer_emision"]) for i in grupos["CER"] if "cer_emision" in i}
    assert len(vr_informe) == 15
    for tk, (vr, cer_emi) in vr_informe.items():
        assert abs(100 * CER_22SEP26 / cer_emi - vr) < 0.06, tk


def test_tir_real_x30n6():
    # Informe: precio 127.5, 55 días, YTM 1.96%. El precio viene redondeado a 0.1.
    vr = 100 * CER_22SEP26 / 659.678896
    tir = (vr / 127.5) ** (365 / 55) - 1
    assert abs(tir - 0.0196) < 0.002
