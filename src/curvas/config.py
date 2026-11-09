"""Parámetros del proyecto. Editá acá las especies a seguir."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_FLUJOS = RAIZ / "data" / "flujos"
DIR_RESULTADOS = RAIZ / "data" / "resultados"
DIR_DOCS = RAIZ / "docs"

URL_FLUJOS = "https://raw.githubusercontent.com/arisbdar/rendimientos-ar/main/public/config.json"

SETTLEMENT = "A-24HS"
DIAS_ATRAS = 7
PAUSA_PPI = 0.4  # segundos entre consultas

# Soberanos hard dollar en USD MEP (sufijo D). La base sin "D" es la clave en config.json.
HARD_DOLLAR = ["AO27D", "AL29D", "GD29D", "AL30D", "GD30D", "AO28D", "AO29D", "AN29D",
               "AE38D", "GD38D", "AL35D", "GD35D", "AL41D", "GD41D", "BPD7D", "BPB8D"]

# Flujos por VN 100 USD de especies que no están en el repo de flujos.
# BOPREAL Serie IV (BPOA8 / BPOB8): 3% anual, cupón semestral 30-abr / 31-oct, amortiza al vencimiento 31-oct-2028
# (informe BYMA/IAMC 05-Oct-26; verificado: TIR 9,03% vs 9,04% del informe para BPOB8).
FLUJOS_EXTRA = {
    "BPB8": [("2026-10-31", 1.5), ("2027-04-30", 1.5), ("2027-11-01", 1.5), ("2028-05-02", 1.5), ("2028-10-31", 101.5)],
    "BPA8": [("2026-10-31", 1.5), ("2027-04-30", 1.5), ("2027-11-01", 1.5), ("2028-05-02", 1.5), ("2028-10-31", 101.5)],
}

# LECAP/BONCAP que no están en el repo de flujos (fuente: informe BYMA/IAMC 05-Oct-26)
LECAP_EXTRA = {"S29E7": {"pago_final": 111.68, "fecha_vencimiento": "2027-01-29"}}
# En el repo de flujos figura como LECAP pero es un bono con cupones semestrales
LECAP_EXCLUIR = {"TY30P"}

# Riesgo país (aproximación EMBI): bonos del canje 2020 y monto emitido en USD millones
# (informe BYMA/IAMC 05-Oct-26). Pondera por valor de mercado = monto x precio / 100.
RIESGO_PAIS = {"GD29": 2635, "GD30": 13587, "GD35": 20502, "GD38": 11405, "GD41": 10482,
               "AL29": 1395, "AL30": 13103, "AL35": 15854, "AE38": 10063, "AL41": 1542}

# TAMAR capitalizables: emisión, vencimiento y margen (informe BYMA/IAMC 05-Oct-26)
TAMAR_BONOS = {
    "TMF27": ("2026-02-13", "2027-02-26", 0.065),
    "TML27": ("2026-06-30", "2027-07-30", 0.054),
    "TMG27": ("2026-03-31", "2027-08-31", 0.060),
    "TMF28": ("2026-04-20", "2028-02-25", 0.000),
    "TMG28": ("2026-04-30", "2028-08-31", 0.069),
}

# Colchón de precio hard dollar: cobros hasta esta fecha (dos cupones, antes de las elecciones de oct-2027)
HORIZONTE_COLCHON = "2027-07-09"

# Tabla de rendimiento en dólares de las letras: escalones de MEP en pesos
MEP_PASO = 50
MEP_NIVELES = 9

# Histórico
HISTORICO_DESDE = "2024-01-01"     # riesgo país desde 2024; el resto se muestra desde 2025
MERVAL_CANDIDATOS = [("MERVAL", "INDICES"), ("M", "INDICES"), ("MERV", "INDICES")]
