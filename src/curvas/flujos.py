"""Flujos de fondos desde el repo rendimientos-ar, con copia local diaria de respaldo."""
import json
import urllib.request
from datetime import date

from .config import DIR_FLUJOS, URL_FLUJOS, LECAP_EXTRA, LECAP_EXCLUIR


def cargar(hoy: date | None = None, url: str = URL_FLUJOS) -> dict:
    """Descarga config.json y guarda data/flujos/config_AAAA-MM-DD.json.
    Si la descarga falla, usa la copia más reciente."""
    hoy = hoy or date.today()
    DIR_FLUJOS.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            cfg = json.load(r)
        (DIR_FLUJOS / f"config_{hoy.isoformat()}.json").write_text(json.dumps(cfg, ensure_ascii=False))
        return cfg
    except Exception as e:
        copias = sorted(DIR_FLUJOS.glob("config_*.json"))
        if not copias:
            raise RuntimeError(f"No pude descargar los flujos y no hay copia local: {e}")
        print(f"⚠️ Flujos sin descargar ({e}); uso {copias[-1].name}")
        return json.loads(copias[-1].read_text())


def flujos_soberano(cfg: dict, ticker_base: str):
    s = cfg["soberanos"].get(ticker_base)
    if not s:
        return None
    return [(date.fromisoformat(f["fecha"]), float(f["monto"])) for f in s["flujos"]]


def lecaps_vigentes(cfg: dict, hoy: date) -> dict:
    out = {x["ticker"]: {"pago_final": float(x["pago_final"]),
                         "vto": date.fromisoformat(x["fecha_vencimiento"])}
           for x in cfg["lecaps"]["letras"] if x["ticker"] not in LECAP_EXCLUIR}
    for t, v in LECAP_EXTRA.items():
        out.setdefault(t, {"pago_final": v["pago_final"], "vto": date.fromisoformat(v["fecha_vencimiento"])})
    return {t: v for t, v in out.items() if v["vto"] > hoy}
