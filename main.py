"""Corrida completa: flujos + precios PPI -> curvas -> CSV, gráficos y página.

Uso local:   python main.py          (lee credenciales de .env)
Uso diario:  .github/workflows/diario.yml (credenciales en GitHub Secrets)
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

from curvas import curvas, flujos, graficos, pagina
from curvas.config import DIR_DOCS, DIR_RESULTADOS
from curvas.precios import Precios, conectar


def main():
    load_dotenv()
    hoy = date.today()
    cfg = flujos.cargar(hoy)
    precios = Precios(conectar())
    feriados = precios.feriados(hoy - timedelta(days=60), hoy + timedelta(days=30))

    df_hd, err_hd = curvas.hard_dollar(cfg, precios, feriados, hoy)
    df_lc, err_lc = curvas.lecap_boncap(cfg, precios, feriados, hoy)
    if df_hd.empty and df_lc.empty:
        sys.exit("❌ PPI no devolvió precios: no se guarda nada.")

    fecha = max(df_hd["fecha"].max() if not df_hd.empty else hoy, df_lc["fecha"].max() if not df_lc.empty else hoy)
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    DIR_DOCS.mkdir(parents=True, exist_ok=True)
    df_hd.to_csv(DIR_RESULTADOS / f"hard_dollar_{fecha}.csv", index=False)
    df_lc.to_csv(DIR_RESULTADOS / f"lecap_{fecha}.csv", index=False)
    graficos.curva_hard_dollar(df_hd, DIR_DOCS / "curva_hard_dollar.png")
    graficos.curva_lecap(df_lc, DIR_DOCS / "curva_lecap.png")
    pagina.generar(df_hd, df_lc, fecha, DIR_DOCS / "index.html")

    print(df_hd.to_string(index=False))
    print(df_lc.to_string(index=False))
    for tk, e in err_hd + err_lc:
        print(f"⚠️ {tk}: {e}")
    print(f"✅ Curvas del {fecha} guardadas en data/resultados y docs/")


if __name__ == "__main__":
    main()
