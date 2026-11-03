"""Gráficos de las curvas: actual (punto lleno) vs hace N días (círculo vacío)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .config import DIAS_ATRAS


def _etiquetar(ax, xs, ys, textos, dx_min, dy_min):
    """Etiqueta puntos; si dos quedan muy cerca, baja la segunda etiqueta."""
    puestos = []
    for x, y, t in zip(xs, ys, textos):
        n = sum(1 for px, py in puestos if abs(px - x) < dx_min and abs(py - y) < dy_min)
        ax.annotate(t, (x, y), xytext=(5, 4 - 12 * n), textcoords="offset points", fontsize=8)
        puestos.append((x, y))


def _pct(s):
    return pd.to_numeric(s, errors="coerce") * 100


def curva_hard_dollar(df: pd.DataFrame, ruta):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for ley, col in [("ARG", "#2a6fdb"), ("NY", "#e0732e")]:
        g = df[df["ley"] == ley]
        ax.scatter(g["md"], _pct(g["tir"]), color=col, s=45, zorder=3, label=f"Ley {ley.replace('ARG', 'local')}")
        g7 = g.dropna(subset=["tir_7d"])
        ax.scatter(g7["md"], _pct(g7["tir_7d"]), facecolors="none", edgecolors=col, s=45, zorder=2)
        for _, r in g7.iterrows():
            ax.plot([r["md"], r["md"]], [r["tir_7d"] * 100, r["tir"] * 100], color=col, alpha=.35)
    _etiquetar(ax, df["md"], _pct(df["tir"]), df["ticker"].str[:-1], 0.15, 0.35)
    ax.scatter([], [], facecolors="none", edgecolors="gray", label=f"Hace {DIAS_ATRAS} días")
    ax.set(xlabel="Duration modificada (años)", ylabel="TIR (%)", title="Curva hard dollar (USD MEP)")
    ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(ruta, dpi=130); plt.close(fig)


def curva_lecap(df: pd.DataFrame, ruta):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(df["dias"], _pct(df["tem"]), color="gray", alpha=.35)
    for tipo, col in [("LECAP", "#2a9d8f"), ("BONCAP", "#8e44ad")]:
        g = df[df["tipo"] == tipo]
        ax.scatter(g["dias"], _pct(g["tem"]), color=col, s=45, zorder=3, label=tipo)
        g7 = g.dropna(subset=["tem_7d"])
        ax.scatter(g7["dias"], _pct(g7["tem_7d"]), facecolors="none", edgecolors=col, s=45, zorder=2)
    _etiquetar(ax, df["dias"], _pct(df["tem"]), df["ticker"], 12, 0.03)
    ax.scatter([], [], facecolors="none", edgecolors="gray", label=f"Hace {DIAS_ATRAS} días")
    ax.set(xlabel="Días al vencimiento", ylabel="TEM (%)", title="Curva LECAP / BONCAP")
    ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(ruta, dpi=130); plt.close(fig)
