"""Corrida completa: flujos + precios PPI + índices BCRA -> curvas -> terminal web y Sheet.

Uso local:   python main.py          (lee credenciales de .env)
Uso diario:  .github/workflows/diario.yml (credenciales en GitHub Secrets)
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

from curvas import bcra, curvas, export, flujos, historico, kpis, sheet
from curvas.config import DIR_DOCS, DIR_RESULTADOS, TAMAR_BONOS
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
    try:
        serie_tamar = {f: v / 100 for f, v in bcra.serie(bcra.ID_TAMAR, min(date.fromisoformat(e) for e, _, _ in TAMAR_BONOS.values()), hoy).items()}
    except Exception as e:
        print(f"⚠️ No se pudo traer la TAMAR del BCRA: {e}")
        serie_tamar = {}
    df_tm, err_tm = curvas.tamar(precios, feriados, hoy, serie_tamar)
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
    for nombre, df in (("hard_dollar", df_hd), ("lecap", df_lc), ("cer", df_cer), ("tamar", df_tm)):
        if df is not None and not df.empty:
            df.to_csv(DIR_RESULTADOS / f"{nombre}_{fecha}.csv", index=False)
    indicadores = kpis.calcular(precios, df_hd, hoy)
    datos = export.armar({"hard-dollar": df_hd, "tasa-fija": df_lc, "tamar": df_tm, "cer": df_cer}, fecha, indices,
                         indicadores, cfg, liquidacion(fecha, feriados))
    export.guardar(datos, DIR_DOCS / "data" / "curvas.json")

    # Pestaña "Histórico" (si falla, la terminal sigue con las curvas del día)
    try:
        hist = historico.construir(precios, cfg, feriados, hoy)
        historico.guardar(hist, DIR_DOCS / "data" / "historico.json")
        print(f"✅ Histórico: {', '.join(f'{k} ({len(v)})' for k, v in hist['series'].items())}")
        for a in hist["avisos"]:
            print(f"⚠️ Histórico {a}")
    except Exception as e:
        print(f"⚠️ No se pudo armar el histórico: {e}")

    for tk, e in err_hd + err_lc + err_cer + err_tm:
        print(f"⚠️ {tk}: {e}")
    print(f"✅ Curvas del {fecha}: " + ", ".join(f"{c['id']} ({len(c['filas'])})" for c in datos["curvas"]))
    for k, v in indicadores.items():
        print(f"   {k}: {v['valor']:.4f} (hace {datos['dias_atras']}d: {v['valor_7d']})")

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
    filas_ind = []
    if indices:
        c = indices["cer_t10"]
        filas_ind.append(["CER T-10", c["fecha"], c["valor"], c["liquidacion"], hoy.isoformat()])
    nombres = {"riesgo_pais": "Riesgo país (pb)", "mep": "MEP implícito AL30", "a3500": "A3500", "tamar": "TAMAR TNA",
               "canje": "Canje AL30D/AL30C"}
    for k, v in indicadores.items():
        filas_ind.append([nombres.get(k, k), v["fecha"], v["valor"], "", hoy.isoformat()])
        if v.get("valor_7d") is not None:
            filas_ind.append([f"{nombres.get(k, k)} hace {datos['dias_atras']}d", v["fecha_7d"], v["valor_7d"], "", hoy.isoformat()])
    if filas_ind:
        sheet.escribir_indices(libro, filas_ind)
    sheet.escribir_control(libro, *export.tablas_control(datos))
    print("✅ Pestañas 'indices', 'control curvas' y 'control ajustes' actualizadas")


if __name__ == "__main__":
    main()
