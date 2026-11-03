"""Genera docs/index.html: página estática para GitHub Pages con gráficos y tablas."""
import html

import pandas as pd

from .config import DIAS_ATRAS


def _tabla(df, cols):
    th = "".join(f"<th>{html.escape(t)}</th>" for t, _, _ in cols)
    filas = []
    for _, r in df.iterrows():
        tds = []
        for _, c, fmt in cols:
            v = r.get(c)
            tds.append(f"<td>{'' if v is None or pd.isna(v) else html.escape(fmt(v))}</td>")
        filas.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(filas)}</tbody></table>"


def generar(df_hd, df_lc, fecha, ruta):
    pct = lambda v: f"{v*100:.2f}%"
    pb = lambda v: f"{v:+.0f}"
    t_hd = _tabla(df_hd, [("Ticker", "ticker", str), ("Ley", "ley", str), ("Precio", "precio", lambda v: f"{v:.2f}"),
                          ("TIR", "tir", pct), ("MD", "md", lambda v: f"{v:.2f}"),
                          (f"TIR {DIAS_ATRAS}d", "tir_7d", pct), ("Δ pb", "delta_pb", pb)])
    t_lc = _tabla(df_lc, [("Ticker", "ticker", str), ("Precio", "precio", lambda v: f"{v:.3f}"),
                          ("Pago final", "pago_final", lambda v: f"{v:.3f}"), ("Días", "dias", lambda v: f"{v:.0f}"),
                          ("TNA", "tna", pct), ("TEA", "tea", pct), ("TEM", "tem", pct),
                          (f"TEM {DIAS_ATRAS}d", "tem_7d", pct), ("Δ pb", "delta_tem_pb", pb)])
    pagina = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Curvas soberanas AR</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#f7f8fa;color:#1d2330}}
main{{max-width:1100px;margin:auto;display:grid;gap:24px}}
section{{background:#fff;border:1px solid #e3e6eb;border-radius:8px;padding:16px;display:grid;gap:12px}}
img{{max-width:100%;height:auto}} .tabla{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px}}
th,td{{padding:6px 8px;border-bottom:1px solid #e3e6eb;text-align:right;white-space:nowrap}}
th:first-child,td:first-child{{text-align:left}} th{{color:#5b6475}}
p{{margin:0;color:#5b6475}}
</style></head><body><main>
<h1>Curvas soberanas</h1><p>Precios de PPI al {fecha:%d/%m/%Y}, comparados con el cierre de hace {DIAS_ATRAS} días.</p>
<section><h2>Hard dollar</h2><img src="curva_hard_dollar.png" alt="Curva hard dollar"><div class="tabla">{t_hd}</div></section>
<section><h2>LECAP y BONCAP</h2><img src="curva_lecap.png" alt="Curva LECAP y BONCAP"><div class="tabla">{t_lc}</div></section>
<p>TIR efectiva anual (actual/365) desde la liquidación T+1. Flujos: repo rendimientos-ar.</p>
</main></body></html>"""
    ruta.write_text(pagina, encoding="utf-8")
