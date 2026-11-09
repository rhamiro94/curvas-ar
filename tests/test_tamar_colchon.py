"""TAMAR (contra el informe BYMA/IAMC 05-Oct-26), colchón de precio y retorno total."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from curvas import motor  # noqa: E402
from curvas.historico import _indice_grupo, _retorno_total  # noqa: E402

DATOS = Path(__file__).parent / "datos" / "tamar_bcra_2026.txt"


def _serie():
    out = {}
    for tok in DATOS.read_text().split():
        k, v = tok.split(":")
        out[date(2000 + int(k[:2]), int(k[2:4]), int(k[4:]))] = float(v) / 100
    return out


def test_monto_tamar_vs_informe():
    serie, hoy = _serie(), date(2026, 10, 5)
    ult = [v for f, v in serie.items() if 0 <= (hoy - f).days < 30]
    futura = sum(ult) / len(ult)
    informe = {"TMF27": ("2026-02-13", "2027-02-26", .065, 137.08), "TML27": ("2026-06-30", "2027-07-30", .054, 136.78),
               "TMG27": ("2026-03-31", "2027-08-31", .060, 151.51), "TMF28": ("2026-04-20", "2028-02-25", 0, 154.42),
               "TMG28": ("2026-04-30", "2028-08-31", .069, 202.92)}
    for tk, (e, v, m, esperado) in informe.items():
        monto = motor.monto_tamar(date.fromisoformat(e), date.fromisoformat(v), m, serie, hoy, futura)
        assert abs(monto / esperado - 1) < 0.0025, tk


def test_retorno_total_neutraliza_el_cupon():
    # El precio cae 8 el día que paga 8 de cupón: el retorno total no cambia
    precios = {date(2027, 1, 8): 60.0, date(2027, 1, 11): 52.0}
    idx = _retorno_total(precios, [(date(2027, 1, 9), 8.0)])
    assert abs(idx[date(2027, 1, 11)] - 1.0) < 1e-12


def test_indice_grupo_pondera():
    s = {"A": {date(2025, 1, 2): 1.0, date(2025, 1, 3): 1.1}, "B": {date(2025, 1, 2): 1.0, date(2025, 1, 3): 1.0}}
    idx = _indice_grupo(s, {"A": 3, "B": 1})
    assert abs(idx[date(2025, 1, 3)] - 107.5) < 1e-9
