"""Corrida completa: flujos + precios PPI + índices BCRA -> curvas -> terminal web y Sheet.

Uso local:   python main.py          (lee credenciales de .env)
Uso diario:  .github/workflows/diario.yml (credenciales en GitHub Secrets)
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

from curvas import bcra, curvas, export, flujos, sheet
from curvas.config import DIR_DOCS, DIR_RESULTADOS
from curvas.motor import liquidacion
from curvas.precios import Precios, conectar


def main():
    load_dotenv()
    hoy = date.today()
    cfg = flujos.cargar(hoy)
    precios = Precios(conectar())
    feriados = precios.feriados(hoy - timedelta(days=60), hoy + timedelta(days=30))

    # Índice CER del BCRA (para la curva CER y la pestaña "indices")
    try:
        serie_cer = bcra.serie(bcra.ID_CER, hoy - timedelta(days=45), hoy + timedelta(days=5))
    except Exception as e:
        print(f"⚠️ No se pudo traer el CER del BCRA: {e}")
        serie_cer = {}

    df_hd, err_hd = curvas.hard_dollar(cfg, precios, feriados, hoy)
    df_lc, err_lc = curvas.lecap_boncap(cfg, precios, feriados, hoy)
    df_cer, err_cer = curvas.cer(precios, feriados, hoy, serie_cer) if serie_cer else (None, [])
    if df_hd.empty and df_lc.empty:
        sys.exit("❌ PPI no devolvió precios: no se guarda nada.")
    fecha = max(df["fecha"].max() for df in (df_hd, df_lc) if not df.empty)

    # Índice del día para mostrar en la terminal y en el Sheet
    liq = liquidacion(hoy, feriados)
    f_cer = bcra.habil_menos(liq, 10, feriados)
    indices = {"cer_t10": {"fecha": f_cer.isoformat(), "valor": serie_cer.get(f_cer),
                           "liquidacion": liq.isoformat()}} if serie_cer.get(f_cer) else {}

    # Resultados: CSV histórico + datos de la terminal web
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    for nombre, df in (("hard_dollar", df_hd), ("lecap", df_lc), ("cer", df_cer)):
        if df is not None and not df.empty:
            df.to_csv(DIR_RESULTADOS / f"{nombre}_{fecha}.csv", index=False)
    datos = export.armar({"hard-dollar": df_hd, "tasa-fija": df_lc, "cer": df_cer}, fecha, indices)
    export.guardar(datos, DIR_DOCS / "data" / "curvas.json")

    for tk, e in err_hd + err_lc + err_cer:
        print(f"⚠️ {tk}: {e}")
    print(f"✅ Curvas del {fecha}: " + ", ".join(f"{c['id']} ({len(c['filas'])})" for c in datos["curvas"]))

    # Google Sheet (solo si hay credenciales de Google)
    libro = sheet.conectar_sheet()
    if libro is None:
        print("ℹ️ Sin credenciales de Google (GOOGLE_SA_JSON / GOOGLE_SA_FILE): no se actualiza el Sheet")
        return
    filas, err_sh = sheet.armar_filas(precios, hoy)
    if filas:
        sheet.escribir(libro, filas)
        print(f"✅ {len(filas)} instrumentos en '{sheet.LIBRO}' / '{sheet.HOJA}' (columnas A:U)")
    for tk, e in err_sh:
        print(f"⚠️ Sheet {tk}: {e}")
    if indices:
        c = indices["cer_t10"]
        sheet.escribir_indices(libro, [["CER T-10", c["fecha"], c["valor"], c["liquidacion"], hoy.isoformat()]])
    sheet.escribir_control(libro, *export.tablas_control(datos))
    print("✅ Pestañas 'indices', 'control curvas' y 'control ajustes' actualizadas")


if __name__ == "__main__":
    main()
