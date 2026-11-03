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
               "AE38D", "GD38D", "AL35D", "GD35D", "AL41D", "GD41D"]

# LECAP/BONCAP que no están en el repo de flujos (fuente: informe BYMA/IAMC 05-Oct-26)
LECAP_EXTRA = {"S29E7": {"pago_final": 111.68, "fecha_vencimiento": "2027-01-29"}}
# En el repo de flujos figura como LECAP pero es un bono con cupones semestrales
LECAP_EXCLUIR = {"TY30P"}
