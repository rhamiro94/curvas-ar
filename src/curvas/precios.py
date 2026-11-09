"""Precios desde la API de PPI (librería oficial ppi-client)."""
import os
import time
from datetime import date, datetime, timedelta

import pandas as pd

from .config import SETTLEMENT, PAUSA_PPI


def conectar():
    """Login con las credenciales del entorno (.env en local, Secrets en GitHub Actions)."""
    from ppi_client.ppi import PPI
    pub, priv = os.environ.get("PPI_PUBLIC_KEY"), os.environ.get("PPI_PRIVATE_KEY")
    if not pub or not priv:
        raise RuntimeError("Faltan PPI_PUBLIC_KEY / PPI_PRIVATE_KEY (ver .env.example)")
    ppi = PPI(sandbox=False)
    ppi.account.login_api(pub, priv)
    return ppi


def _reintentar(fn, *args, intentos=4):
    """PPI a veces responde vacío (límite de consultas o corte momentáneo):
    reintenta esperando 1, 2 y 4 segundos antes de rendirse."""
    for i in range(intentos):
        try:
            return fn(*args)
        except Exception:
            if i == intentos - 1:
                raise
            time.sleep(2 ** i)


class Precios:
    def __init__(self, ppi):
        self.ppi = ppi
        self.volumenes = {}  # ticker -> volumen del día (PPI)

    def feriados(self, desde: date, hasta: date) -> set:
        try:
            fer = self.ppi.configuration.get_holidays(
                start_date=datetime.combine(desde, datetime.min.time()),
                end_date=datetime.combine(hasta, datetime.min.time()))
            return {date.fromisoformat(f["date"][:10]) for f in fer}
        except Exception as e:
            print(f"⚠️ Sin feriados de PPI ({e}): uso solo fines de semana")
            return set()

    def actual(self, ticker: str, tipo: str):
        """(precio, fecha) del último precio."""
        d = _reintentar(self.ppi.marketdata.current, ticker, tipo, SETTLEMENT)
        time.sleep(PAUSA_PPI)
        if not d or not d.get("price"):
            return None, None
        try:
            self.volumenes[ticker] = float(d.get("volume") or 0)
        except (TypeError, ValueError):
            self.volumenes[ticker] = None
        f = pd.to_datetime(d.get("date")).date() if d.get("date") else date.today()
        return float(d["price"]), f

    def cierre_en(self, ticker: str, tipo: str, fecha_obj: date, ventana: int = 10):
        """(precio, fecha) del último cierre en o antes de fecha_obj."""
        hist = _reintentar(
            self.ppi.marketdata.search, ticker, tipo, SETTLEMENT,
            datetime.combine(fecha_obj - timedelta(days=ventana), datetime.min.time()),
            datetime.combine(fecha_obj, datetime.max.time()))
        time.sleep(PAUSA_PPI)
        df = pd.DataFrame(hist or [])
        if df.empty or "price" not in df:
            return None, None
        df["f"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df = df[(df["f"] <= fecha_obj) & (df["price"] > 0)].sort_values("f")
        if df.empty:
            return None, None
        return float(df.iloc[-1]["price"]), df.iloc[-1]["f"]

    def historico(self, ticker: str, tipo: str, desde: date, hasta: date) -> dict:
        """{fecha: precio de cierre} entre dos fechas."""
        hist = _reintentar(self.ppi.marketdata.search, ticker, tipo, SETTLEMENT,
                           datetime.combine(desde, datetime.min.time()),
                           datetime.combine(hasta, datetime.max.time()))
        time.sleep(PAUSA_PPI)
        out = {}
        for h in hist or []:
            try:
                p = float(h.get("price") or 0)
                if p > 0:
                    out[pd.to_datetime(h["date"]).date()] = p
            except (TypeError, ValueError, KeyError):
                continue
        return out
