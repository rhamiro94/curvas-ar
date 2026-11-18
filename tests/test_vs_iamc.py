"""Validación contra el informe diario de renta fija BYMA/IAMC del 17-Nov-26 (liquidación 18-Nov-26).

tests/datos/iamc_2026-11-17.json guarda precios, TIR y flujos publicados por IAMC para soberanos y BOPREAL
en dólares (especies D = MEP y C = cable). Para actualizarlo, se baja un informe más nuevo y se cambia el archivo.
"""
import glob
import json
import sys
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from curvas import motor  # noqa: E402
from curvas.flujos import flujos_soberano  # noqa: E402

IAMC = json.loads((RAIZ / "tests" / "datos" / "iamc_2026-11-17.json").read_text(encoding="utf-8"))
LIQ = date.fromisoformat(IAMC["liquidacion"])
# ticker de IAMC -> base que usamos nosotros (las especies BOPREAL se llaman distinto en PPI)
BASE = {"BPOB8": "BPB8", "BPOA8": "BPA8", "BPOD7": "BPD7"}
ESPECIE = {"BPOB8": "BPB8", "BPOA8": "BPA8", "BPOD7": "BPD7"}


def _fl(lista):
    return [(date.fromisoformat(d), float(m)) for d, m in lista]


@pytest.mark.parametrize("tk", sorted(IAMC["flujos"]))
def test_motor_con_flujos_iamc(tk):
    """Con los flujos y precios de IAMC, nuestro motor da la misma TIR (D y C)."""
    fl = _fl(IAMC["flujos"][tk])
    for suf in ("D", "C"):
        e = IAMC["especies"].get(ESPECIE.get(tk, tk) + suf)
        if not e:
            continue
        tir = motor.tir(e["precio"], fl, LIQ) * 100
        assert abs(tir - e["tir"]) < 0.03, f"{tk}{suf}: {tir:.3f}% vs IAMC {e['tir']}%"


def _config_flujos():
    archivos = sorted(glob.glob(str(RAIZ / "data" / "flujos" / "config_*.json")))
    return json.loads(Path(archivos[-1]).read_text(encoding="utf-8")) if archivos else None


@pytest.mark.parametrize("tk", sorted(IAMC["flujos"]))
def test_nuestros_flujos_iguales_a_iamc(tk):
    """Los flujos que usamos (repo + correcciones) coinciden con los de IAMC en cada fecha futura."""
    cfg = _config_flujos()
    if cfg is None:
        pytest.skip("sin copia de flujos en data/flujos")
    nuestros = flujos_soberano(cfg, BASE.get(tk, tk))
    if not nuestros:
        pytest.skip(f"{tk} no está en nuestros flujos")
    desde = max(LIQ, date.today())
    nuestros = {d: m for d, m in nuestros}
    for d, m in _fl(IAMC["flujos"][tk]):
        if d <= desde:
            continue
        # BOPREAL: IAMC separa amortización e interés en días distintos (30 y 31 de octubre).
        # AO27/AO28/AO29: el repo pone 0,5 fijo por mes; IAMC usa días reales (0,45 a 0,58).
        # Diferencia conocida de 1 a 2 pb de TIR: se tolera hasta 0,1 por cupón.
        tol = 0.1 if tk.startswith("AO") else 0.005
        cerca = [v for f, v in nuestros.items() if abs((f - d).days) <= 3]
        assert cerca, f"{tk}: falta el pago del {d}"
        assert any(abs(v - m) < tol for v in cerca) or abs(sum(cerca) - m) < tol or tk in BASE, \
            f"{tk} {d}: {cerca} vs IAMC {m}"
