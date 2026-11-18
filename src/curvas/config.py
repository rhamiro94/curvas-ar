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
               "AE38D", "GD38D", "AL35D", "GD35D", "AL41D", "GD41D", "GD46D", "BPD7D", "BPB8D"]

# Flujos por VN 100 USD de especies que no están en el repo de flujos.
# BOPREAL Serie IV (BPOA8 / BPOB8): 3% anual, cupón semestral 30-abr / 31-oct, amortiza al vencimiento 31-oct-2028
# (informe BYMA/IAMC 05-Oct-26; verificado: TIR 9,03% vs 9,04% del informe para BPOB8).
FLUJOS_EXTRA = {
    "BPB8": [("2026-10-31", 1.5), ("2027-04-30", 1.5), ("2027-11-01", 1.5), ("2028-05-02", 1.5), ("2028-10-31", 101.5)],
    "BPA8": [("2026-10-31", 1.5), ("2027-04-30", 1.5), ("2027-11-01", 1.5), ("2028-05-02", 1.5), ("2028-10-31", 101.5)],
}

# Flujos que reemplazan a los del repo cuando el repo está mal.
# GD41 / AL41: el repo usa cupón 3,125% hasta 2029 y la TIR daba ~95 pb por debajo del informe BYMA/IAMC.
# Condiciones de emisión: 3,5% hasta el 09-jul-29 y 4,875% después; amortiza en 28 cuotas semestrales desde el 09-ene-28.
# Con estos flujos: GD41 10,76% y AL41 11,93% vs 10,75% y 11,92% del informe del 05-Oct-26.
def _flujos_41():
    from datetime import date
    res, out = 100.0, []
    for y in range(2026, 2042):
        for m in (1, 7):
            d = date(y, m, 9)
            if not date(2026, 7, 9) <= d <= date(2041, 7, 9):
                continue
            amort = 100 / 28 if d >= date(2028, 1, 9) else 0.0
            cupon = res * (0.035 if d <= date(2029, 7, 9) else 0.04875) / 2
            out.append((d.isoformat(), round(cupon + amort, 6)))
            res -= amort
    return out


# GD46 (no está en el repo): 3,625% hasta jul-24, 4,125% hasta jul-27, 4,375% hasta jul-28 y 5% después;
# amortiza en 44 cuotas semestrales desde el 09-ene-25. Desde 2024 para que sirva también al histórico.
def _flujos_46():
    from datetime import date
    res, out = 100.0, []
    for y in range(2024, 2047):
        for m in (1, 7):
            d = date(y, m, 9)
            if d > date(2046, 7, 9):
                continue
            tasa = 0.03625 if d <= date(2024, 7, 9) else 0.04125 if d <= date(2027, 7, 9) else \
                0.04375 if d <= date(2028, 7, 9) else 0.05
            amort = 100 / 44 if d >= date(2025, 1, 9) else 0.0
            out.append((d.isoformat(), round(res * tasa / 2 + amort, 6)))
            res -= amort
    return out


# Validados flujo por flujo contra el informe diario BYMA/IAMC del 17-Nov-26 (tests/datos/iamc_2026-11-17.json).
FLUJOS_CORREGIDOS = {"GD41": _flujos_41(), "AL41": _flujos_41(), "GD46": _flujos_46()}

# Pagos ya hechos de los bonos del canje 2020 (el repo de flujos solo trae los futuros). Los usa la pestaña
# "Histórico" para el riesgo país diario y el retorno total desde 2024. Por VN 100 original, Bonar = Global.
# Armados con las condiciones de emisión y verificados contra el primer pago futuro del repo (09-Jul-26).
_P = ["2024-01-09", "2024-07-09", "2025-01-09", "2025-07-09", "2026-01-09"]
_PASADOS = {
    "29": [0.5, 0.5, 10.5, 10.45, 10.40],          # 1%; amortiza 10% semestral desde ene-25
    "30": [0.375, 4.375, 8.36, 8.33, 8.30],        # 0,75%; amortiza 4% jul-24 y 8% semestral desde ene-25
    "35": [1.8125, 1.8125, 2.0625, 2.0625, 2.0625],  # 3,625% hasta jul-24, luego 4,125%
    "38": [2.125, 2.125, 2.5, 2.5, 2.5],           # 4,25% hasta jul-24, luego 5%
    "41": [1.75, 1.75, 1.75, 1.75, 1.75],          # 3,5% (cupón vigente según informe BYMA/IAMC)
}
FLUJOS_PASADOS = {pre + s: list(zip(_P, m)) for s, m in _PASADOS.items()
                  for pre in (["GD", "AE"] if s == "38" else ["GD", "AL"])}

# LECAP/BONCAP que no están en el repo de flujos (fuente: informe BYMA/IAMC 05-Oct-26)
LECAP_EXTRA = {"S29E7": {"pago_final": 111.68, "fecha_vencimiento": "2027-01-29"}}
# En el repo de flujos figura como LECAP pero es un bono con cupones semestrales
LECAP_EXCLUIR = {"TY30P"}

# Monto emitido en USD millones de los bonos del canje 2020 (informe BYMA/IAMC 05-Oct-26).
# Pondera por valor de mercado = monto x precio / 100 (riesgo país y retorno total del histórico).
MONTOS_EMITIDOS = {"GD29": 2635, "GD30": 13587, "GD35": 20502, "GD38": 11405, "GD41": 10482, "GD46": 2092,
                   "AL29": 1395, "AL30": 13103, "AL35": 15854, "AE38": 10063, "AL41": 1542}

# Riesgo país (aproximación del EMBI de JP Morgan): solo Globales (ley NY; los Bonares no entran al índice),
# con precio en dólar cable (sufijo C), que es el precio de referencia internacional.
RIESGO_PAIS = ["GD29", "GD30", "GD35", "GD38", "GD41", "GD46"]
SUFIJO_RIESGO_PAIS = "C"
# Valor publicado, para control (serie diaria del riesgo país de JP Morgan)
URL_RIESGO_PAIS_PUBLICADO = "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais"

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
