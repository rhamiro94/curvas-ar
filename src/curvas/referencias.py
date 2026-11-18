"""Valores publicados por terceros, para controlar nuestros cálculos."""
import json
import urllib.request
from datetime import date

from .config import URL_RIESGO_PAIS_PUBLICADO

_cache = {}


def riesgo_pais_publicado() -> dict:
    """{fecha: pb} del riesgo país publicado (JP Morgan EMBI, vía ArgentinaDatos). {} si no responde."""
    if "rp" in _cache:
        return _cache["rp"]
    out = {}
    try:
        req = urllib.request.Request(URL_RIESGO_PAIS_PUBLICADO, headers={"User-Agent": "curvas-ar"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for x in json.load(r):
                try:
                    out[date.fromisoformat(str(x["fecha"])[:10])] = float(x["valor"])
                except (KeyError, TypeError, ValueError):
                    continue
    except Exception as e:
        print(f"⚠️ Riesgo país publicado (ArgentinaDatos): {e}")
    _cache["rp"] = out
    return out
