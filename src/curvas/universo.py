"""Universo de instrumentos que se cargan en la pestaña "renta fija" del Sheet.
Copiado del script de Colab renta_fija_ppi.py (tickers BYMA/IAMC 29-Sep-26,
vencimientos y montos al vencimiento del informe 05-Oct-26).

Para agregar o sacar especies, editá las listas. Las que tienen "vto" ya vencido
se saltean solas.
"""

# ---------------------------------------------------------------------
# LISTAS DE INSTRUMENTOS
# "moneda"    : moneda en la que cotiza la especie (default: ARS)
# "vto"       : fecha de vencimiento (AAAA-MM-DD)
# "monto_vto" : pago final por VN 100 (LECAP / BONCAP / TAMAR / pata tasa fija del dual)
# "monto_cer" : monto al vto de la pata CER de los duales CER vs TAMAR
# "monto_tamar": monto al vto de la pata TAMAR + margen de los duales
# "vr"        : CER y dollar linked: valor residual ajustado del informe IAMC 05-Oct-26
#               (capital ajustado por CER / USD a esa fecha; se mueve con el índice)
# "cer_emision": CER inicial (CER de 10 días hábiles antes de la emisión, serie BCRA).
#               Verificado: 100 x CER(22-Sep-26) / cer_emision = VR del informe 05-Oct-26.
# OJO: en TAMAR y duales el monto es una PROYECCIÓN del informe a esa fecha
#      (depende de la TAMAR / CER futuros). Actualizarlo con cada informe nuevo.
# ---------------------------------------------------------------------

# === LECAP ===
lecap = [
    {"ticker": "S16O6", "type": "LETRAS", "vto": "2026-10-16", "monto_vto": 105.28},
    {"ticker": "S30O6", "type": "LETRAS", "vto": "2026-10-30", "monto_vto": 135.28},
    {"ticker": "S13N6", "type": "LETRAS", "vto": "2026-11-13", "monto_vto": 109.65},
    {"ticker": "S30N6", "type": "LETRAS", "vto": "2026-11-30", "monto_vto": 129.89},
    {"ticker": "S29E7", "type": "LETRAS", "vto": "2027-01-29", "monto_vto": 111.68},
]

# === BONCAP ===
boncap = [
    {"ticker": "T15E7", "type": "BONOS", "vto": "2027-01-15", "monto_vto": 161.10},
    {"ticker": "T30A7", "type": "BONOS", "vto": "2027-04-30", "monto_vto": 157.34},
    {"ticker": "T31Y7", "type": "BONOS", "vto": "2027-05-31", "monto_vto": 151.56},
    {"ticker": "T30J7", "type": "BONOS", "vto": "2027-06-30", "monto_vto": 156.04},
]

# === TASA FIJA EN PESOS (con cupón) ===
tasa_fija = [
    {"ticker": "TO26",  "type": "BONOS"},
    {"ticker": "TY30P", "type": "BONOS"},
]

# === CER - CUPÓN CERO ===
cer = [
    # Letras
    {"ticker": "X30N6", "type": "LETRAS", "vto": "2026-11-30", "vr": 127.9, "cer_emision": 659.678896},
    {"ticker": "X29E7", "type": "LETRAS", "vto": "2027-01-29", "vr": 103.4, "cer_emision": 815.434511},
    # Bonos
    {"ticker": "TZXO6", "type": "BONOS", "vto": "2026-10-30", "vr": 175.7},
    {"ticker": "TZXD6", "type": "BONOS", "vto": "2026-12-15", "vr": 313.2, "cer_emision": 269.302519},
    {"ticker": "TZXM7", "type": "BONOS", "vto": "2027-03-31", "vr": 235.9, "cer_emision": 357.5665},
    {"ticker": "TZXA7", "type": "BONOS", "vto": "2027-04-30", "vr": 129.4, "cer_emision": 651.898062},
    {"ticker": "TZXY7", "type": "BONOS", "vto": "2027-05-31", "vr": 127.9, "cer_emision": 659.678896},
    {"ticker": "TZX27", "type": "BONOS", "vto": "2027-06-30", "vr": 420.9, "cer_emision": 200.388015},
    {"ticker": "TZXS7", "type": "BONOS", "vto": "2027-09-30", "vr": 116.7, "cer_emision": 723.059981},
    {"ticker": "TZXO7", "type": "BONOS", "vto": "2027-10-29", "vr": 106.6, "cer_emision": 791.489705},
    {"ticker": "TZXD7", "type": "BONOS", "vto": "2027-12-15", "vr": 313.2, "cer_emision": 269.302519},
    {"ticker": "TZXM8", "type": "BONOS", "vto": "2028-03-31", "vr": 116.7, "cer_emision": 723.059981},
    {"ticker": "TZX28", "type": "BONOS", "vto": "2028-06-30", "vr": 420.9, "cer_emision": 200.388015},
    {"ticker": "TZXS8", "type": "BONOS", "vto": "2028-09-29", "vr": 116.7, "cer_emision": 723.059981},
    {"ticker": "TZXD8", "type": "BONOS", "vto": "2028-12-15", "vr": 106.6, "cer_emision": 791.489705},
    {"ticker": "TZXM9", "type": "BONOS", "vto": "2029-03-28", "vr": 116.7, "cer_emision": 723.059981},
]

# === CER CON CUPÓN ===
cer_cupon = [
    {"ticker": "TX26", "type": "BONOS"},
    {"ticker": "TX28", "type": "BONOS"},
    {"ticker": "TX31", "type": "BONOS"},
    {"ticker": "DICP", "type": "BONOS"},
    {"ticker": "PARP", "type": "BONOS"},
    {"ticker": "PAP0", "type": "BONOS"},
    {"ticker": "CUAP", "type": "BONOS"},
]

# === TAMAR CAPITALIZABLES ===
tamar = [
    {"ticker": "TMF27", "type": "BONOS", "vto": "2027-02-26", "monto_vto": 137.08},
    {"ticker": "TML27", "type": "BONOS", "vto": "2027-07-30", "monto_vto": 136.78},
    {"ticker": "TMG27", "type": "BONOS", "vto": "2027-08-31", "monto_vto": 151.51},
    {"ticker": "TMF28", "type": "BONOS", "vto": "2028-02-25", "monto_vto": 154.42},
    {"ticker": "TMG28", "type": "BONOS", "vto": "2028-08-31", "monto_vto": 202.92},
]

# === DUALES ===
duales = [
    # Tasa fija vs TAMAR + margen
    {"ticker": "TTD26", "type": "BONOS", "vto": "2026-12-15", "monto_vto": 161.14, "monto_tamar": 179.99},
    # CER vs TAMAR + margen
    {"ticker": "TXMJ8", "type": "BONOS", "vto": "2028-06-30", "monto_cer": 112.08, "monto_tamar": 175.65},
    {"ticker": "TXMD8", "type": "BONOS", "vto": "2028-12-15", "monto_cer": 108.95, "monto_tamar": 194.72},
    {"ticker": "TXMJ9", "type": "BONOS", "vto": "2029-06-29", "monto_cer": 113.84, "monto_tamar": 231.61},
    {"ticker": "TXMD9", "type": "BONOS", "vto": "2029-12-14", "monto_cer": 108.95, "monto_tamar": 254.06},
    {"ticker": "TXMJ0", "type": "BONOS", "vto": "2030-06-28", "monto_cer": 108.95, "monto_tamar": 293.33},
    # Dollar linked vs TAMAR (la pata DL paga en USD convertidos: no se carga monto fijo)
    {"ticker": "TMVE8", "type": "BONOS", "vto": "2028-01-31", "monto_tamar": 142.72},
]

# === BADLAR ===
badlar = [
    {"ticker": "TB27", "type": "BONOS"},
]

# === DOLLAR LINKED (cotizan y pagan en pesos) ===
dollar_linked = [
    # Letras
    {"ticker": "D30O6", "type": "LETRAS", "vto": "2026-10-30", "vr": 102.3},
    {"ticker": "D30N6", "type": "LETRAS", "vto": "2026-11-30", "vr": 101.1},
    {"ticker": "D15E7", "type": "LETRAS", "vto": "2027-01-15", "vr": 102.3},
    {"ticker": "D31M7", "type": "LETRAS", "vto": "2027-03-31", "vr": 107.9},
    {"ticker": "D10Y7", "type": "LETRAS", "vto": "2027-05-10", "vr": 103.3},
    # Bonos
    {"ticker": "TZV27", "type": "BONOS", "vto": "2027-06-30", "vr": 165.5},
    {"ticker": "TZV28", "type": "BONOS", "vto": "2028-06-30", "vr": 109.2},
    {"ticker": "TZVD8", "type": "BONOS", "vto": "2028-12-15", "vr": 106.5},
]

# === SOBERANOS HARD DOLLAR ===
# Cada bono en tres especies: pesos (ARS), dólar MEP (D) y dólar cable (C)
hard_dollar = [
    # Bonares nuevos
    {"ticker": "AO27",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AO27D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AO27C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "AO28",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AO28D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AO28C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "AO29",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AO29D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AO29C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "AN29",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AN29D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AN29C", "type": "BONOS", "moneda": "CCL"},
    # Bonares (Ley ARG)
    {"ticker": "AL29",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AL29D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AL29C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "AL30",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AL30D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AL30C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "AL35",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AL35D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AL35C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "AE38",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AE38D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AE38C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "AL41",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "AL41D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "AL41C", "type": "BONOS", "moneda": "CCL"},
    # Globales (Ley NY)
    {"ticker": "GD29",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "GD29D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "GD29C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "GD30",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "GD30D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "GD30C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "GD35",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "GD35D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "GD35C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "GD38",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "GD38D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "GD38C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "GD41",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "GD41D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "GD41C", "type": "BONOS", "moneda": "CCL"},
    {"ticker": "GD46",  "type": "BONOS", "moneda": "ARS"},
    {"ticker": "GD46D", "type": "BONOS", "moneda": "MEP"},
    {"ticker": "GD46C", "type": "BONOS", "moneda": "CCL"},
]

# === BOPREALES (BCRA) ===
# Solo especie en pesos: las especies en dólares usan otra nomenclatura
# (no siempre base + D). Agregarlas después de confirmar el ticker en PPI.
bopreales = [
    {"ticker": "BPOA7", "type": "BONOS"},
    {"ticker": "BPOB7", "type": "BONOS"},
    {"ticker": "BPOC7", "type": "BONOS"},
    {"ticker": "BPOD7", "type": "BONOS"},
    {"ticker": "BPOA8", "type": "BONOS"},
    {"ticker": "BPOB8", "type": "BONOS"},
]

# === PROVINCIALES HARD DOLLAR (Ley NY) ===
# Tickers de la especie en pesos según BYMA (la "D" final de algunos es parte del nombre).
prov_usd = [
    {"ticker": "BA37D", "type": "BONOS"},
    {"ticker": "BB37D", "type": "BONOS"},
    {"ticker": "BC37D", "type": "BONOS"},
    {"ticker": "BDC33", "type": "BONOS"},
    {"ticker": "BDC36", "type": "BONOS"},
    {"ticker": "CH24D", "type": "BONOS"},
    {"ticker": "CO24D", "type": "BONOS"},
    {"ticker": "CO26",  "type": "BONOS"},
    {"ticker": "CO27D", "type": "BONOS"},
    {"ticker": "CO32",  "type": "BONOS"},
    {"ticker": "CO35",  "type": "BONOS"},
    {"ticker": "ERF25", "type": "BONOS"},
    {"ticker": "ERM33", "type": "BONOS"},
    {"ticker": "JUS22", "type": "BONOS"},
    {"ticker": "NDT11", "type": "BONOS"},
    {"ticker": "NDT25", "type": "BONOS"},
    {"ticker": "PMM29", "type": "BONOS"},
    {"ticker": "PUA36", "type": "BONOS"},
    {"ticker": "SA24D", "type": "BONOS"},
    {"ticker": "SFD34", "type": "BONOS"},
    {"ticker": "TFU27", "type": "BONOS"},
]

# === PROVINCIALES EN PESOS (Ley ARG) ===
prov_ars = [
    {"ticker": "BAF27", "type": "BONOS"},
    {"ticker": "BAM27", "type": "BONOS"},
    {"ticker": "BAO27", "type": "BONOS"},
    {"ticker": "BLE27", "type": "BONOS"},
    {"ticker": "BUN26", "type": "LETRAS"},
    {"ticker": "CO2D7", "type": "BONOS"},
    {"ticker": "CO3D7", "type": "BONOS"},
    {"ticker": "COY27", "type": "BONOS"},
    {"ticker": "ERE27", "type": "BONOS"},
    {"ticker": "PBM27", "type": "BONOS"},
    {"ticker": "PBM28", "type": "BONOS"},
    {"ticker": "PMD26", "type": "BONOS"},
    {"ticker": "PMM27", "type": "BONOS"},
    {"ticker": "SFN27", "type": "BONOS"},
]

# ---------------------------------------------------------------------
# DICCIONARIO DE GRUPOS (clave = valor de la columna "Categoría")
# ---------------------------------------------------------------------
grupos = {
    "LECAP": lecap,
    "BONCAP": boncap,
    "TASA FIJA": tasa_fija,
    "CER": cer,
    "CER CUPON": cer_cupon,
    "TAMAR": tamar,
    "DUAL": duales,
    "BADLAR": badlar,
    "DOLLAR LINKED": dollar_linked,
    "HARD DOLLAR": hard_dollar,
    "BOPREAL": bopreales,
    "PROV USD": prov_usd,
    "PROV ARS": prov_ars,
}
