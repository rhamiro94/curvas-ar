# Metodología y fuentes de curvas-ar

Cómo se calcula cada número de la terminal, de dónde sale cada dato y contra qué se controla.
Actualizado al 18-11-2026.

**Última validación integral (17-Nov-26 contra IAMC):** hard dollar D 0,0 a 2 pb (salvo GD41/AL41, ya corregidos), LECAP/BONCAP 0 a 3 pb, CER 0,0 pb. Pendiente: TAMAR (TMF27 +32 pb, TML27 −15 pb: revisar la proyección del monto al vencimiento) y S29E7 (−2,8 pb: revisar el pago final).

## 1. Fuentes de datos (APIs)

| # | Fuente | Qué trae | Dónde se usa | Acceso |
|---|---|---|---|---|
| 1 | **API de PPI** (`ppi-client`) | Precios actuales e históricos (liquidación A-24HS), volumen, feriados | Todas las curvas, MEP, canje, riesgo país, histórico | Keys `PPI_PUBLIC_KEY` / `PPI_PRIVATE_KEY` (Secrets de GitHub y `.env`) |
| 2 | **rendimientos-ar** `config.json` (`raw.githubusercontent.com/arisbdar/rendimientos-ar/main/public/config.json`) | Flujos futuros de los soberanos hard dollar y pago final de LECAP/BONCAP | Hard dollar, tasa fija, colchón, calculadora | Público. Copia diaria en `data/flujos/` |
| 3 | **BCRA, API de Estadísticas v4.0** (`api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id}`) | CER (id 30), A3500 (id 5), TAMAR bancos privados TNA (id 44) | Curva CER, curva TAMAR, KPIs, histórico | Público |
| 4 | **Tesoro de EE.UU.** (`home.treasury.gov`, XML `daily_treasury_yield_curve`) | Curva par de los Treasuries (1 mes a 30 años) | Spread de cada bono y riesgo país | Público. Meses cerrados guardados en `data/historico/ust_cache.json` |
| 5 | **ArgentinaDatos** (`api.argentinadatos.com/v1/finanzas/indices/riesgo-pais`) | Riesgo país publicado (EMBI de JP Morgan), serie diaria | Control del riesgo país (KPI, histórico y Sheet) | Público |
| 6 | **Google Sheets API** (`gspread`, cuenta de servicio) | Escritura del Sheet de control "IOL pro" | Pestañas renta fija, indices, control curvas, control ajustes | Secret `GOOGLE_SA_JSON` |
| 7 | **GitHub Actions / Pages** | Corrida diaria (lun a vie 18:20 ART) y publicación de `docs/` | Automatización | Repo `rhamiro94/curvas-ar` |
| 8 | **cdnjs** (d3 7.9.0) y **Google Fonts** | Gráficos y tipografías de la web | `docs/index.html` | Público |

Referencia para validar (no se consulta en la corrida): **informe diario de renta fija BYMA/IAMC** (iamc.com.ar/informediario). Publica, para cada instrumento y especie (pesos, D y C), precio, TIR, duration y el flujo de fondos completo, además del EMBI del día. Se guardó el cierre del 17-Nov-26 en `tests/datos/iamc_2026-11-17.json` y `tests/test_vs_iamc.py` valida contra él el motor y los flujos. El del 05-Oct-26 (PDF) se usa en `test_motor.py` y `test_kpis.py`. El sitio no permite lectura automática (robots.txt), así que la actualización es manual.

## 2. Convenciones generales

- Precio: último cierre de PPI. Liquidación T+1 hábil (feriados de PPI).
- TIR: efectiva anual, base actual/365, desde la liquidación, por bisección.
- Duration: Macaulay; MD = Macaulay / (1 + TIR).
- Tendencias: y = a + b·ln(x) por mínimos cuadrados (hoy y hace 7 días).
- Comparación: cierre de hace 7 días corridos (o el último anterior).

## 3. Curvas

**Tasa fija (LECAP/BONCAP).** TEA = (pago final / precio)^(365/días) − 1; TEM = (1 + TEA)^(1/12) − 1; TNA = TEM × 12.

**CER cupón cero.** VR = 100 × CER(10 días hábiles antes de la liquidación) / CER de emisión. TIR real = (VR / precio)^(365/días) − 1.

**TAMAR capitalizables.** Monto al vencimiento proyectado: capitaliza cada mes (mismo día que el vencimiento) a (TAMAR promedio del período + margen) × días/365. Días pasados: TAMAR publicada; días futuros: promedio de los últimos 30 días. Margen implícito = TNA − TAMAR de hoy. Validado contra el informe (0,0% a 0,2%).

**Hard dollar.** TIR que iguala el precio en USD MEP (sufijo D) con los flujos futuros. Incluye BOPREAL BPD7D y BPB8D. La columna *Spread UST* es la TIR llevada a semestral menos la curva del Tesoro a la duration del bono (precio MEP).

**Colchón de precio.** Cobros entre la liquidación y el 09-07-2027; caída que deja el rendimiento en 0 = −cobros / precio. La web permite reinvertir los cobros a la TIR del bono o a una tasa fija.

**Rendimiento en dólares de las letras.** (pago final / precio) × (MEP hoy / MEP al vencimiento) − 1. MEP de equilibrio = MEP hoy × pago final / precio.

## 4. Indicadores de cabecera

| KPI | Cálculo |
|---|---|
| Riesgo país | Ver sección 5 |
| TAMAR | Último dato BCRA (TNA) |
| MEP implícito | AL30 / AL30D |
| A3500 | Último dato BCRA |
| Canje | AL30D / AL30C − 1 |

## 5. Riesgo país

Aproximación del **EMBI de JP Morgan**:

1. Bonos: **solo Globales** (ley NY): GD29, GD30, GD35, GD38, GD41 y GD46. Los Bonares (ley local) no forman parte del índice.
2. Precio: **dólar cable (sufijo C)**, que es el precio internacional. Con el canje MEP/cable en ~6%, usar el precio MEP baja la TIR y subestima el spread en más de 100 pb.
3. Spread de cada bono = TIR llevada a semestral (2·((1+TIR)^0,5 − 1)) − tasa del Tesoro interpolada a su duration Macaulay.
4. Promedio ponderado por valor de mercado = monto emitido × precio / 100.

Diferencias que quedan contra el EMBI publicado (de 20 a 50 pb esperables):
- JP Morgan usa el *stripped spread* contra la curva cupón cero, no el rendimiento par a la duration.
- Pondera por monto en circulación (no emitido) y usa sus propios precios de cierre en Nueva York.

**Validación con 15 ruedas (28-10 al 17-11), precios y TIR de IAMC:** con precio cable la diferencia contra el publicado promedió +14 pb (desvío 25 pb). Con precio MEP habría dado −158 pb en promedio. La curva del Tesoro se tomó fija, así que parte del desvío viene de ahí.

**Cambio del 18-11-2026.** Antes se usaban Globales y Bonares a precio MEP. Contra el publicado (Rava) daba entre 52 y 116 pb menos del 28-10 al 17-11. Por eso se pasó a Globales en cable y se agregó el valor publicado como control.

## 6. Histórico

- A3500, CER y TAMAR: BCRA. MEP implícito: AL30/AL30D. Canje: AL30D/AL30C − 1.
- Merval (pesos y USD): **pendiente**. PPI responde "Instrument Type not found: INDICES" para los tickers probados.
- **Retorno total Bonares / Globales:** por bono, (precio de hoy + pagos del período) / precio anterior, encadenado. Grupo: promedio de los retornos diarios ponderado por monto emitido × precio del día anterior.
- **Riesgo país diario:** la misma cuenta que el KPI (Globales cable), con la curva del Tesoro de cada día. Se muestra junto al publicado.
- Pagos anteriores a jul-26: el repo de flujos solo trae los futuros, así que los cupones y amortizaciones de ene-24 a ene-26 están en `FLUJOS_PASADOS` (`config.py`). Sin ellos, el riesgo país y el retorno total anteriores a jul-26 estaban mal.

Limitación conocida: el pago se suma en la fecha de pago, pero el precio cae unos días antes (cuando el bono empieza a cotizar sin el cupón). En cada fecha de pago el índice puede mostrar un bajón de 2 o 3 días.

## 7. Correcciones a los flujos del repo

| Bono | Problema | Corrección | Validación |
|---|---|---|---|
| GD41 / AL41 | El repo usa cupón 3,125% hasta 2029 (TIR ~100 pb por debajo de IAMC) | `FLUJOS_CORREGIDOS`: 3,5% hasta jul-29, 4,875% después, 28 cuotas desde ene-28 | Igual flujo por flujo a IAMC; TIR 12,25% vs 12,25% (GD41D, 17-Nov) |
| AO27 / AO28 / AO29 | El repo pone cupón mensual fijo de 0,50; IAMC usa días reales | Sin corregir (1 a 2 pb de TIR) | Tolerado en el test |
| GD46 | No está en el repo | `FLUJOS_CORREGIDOS`: 3,625% → 4,125% (jul-24) → 4,375% (jul-27) → 5% (jul-28); 44 cuotas desde ene-25 | Igual flujo por flujo a IAMC |
| BPB8 / BPA8 | No están en el repo | `FLUJOS_EXTRA` (3% semestral, amortiza oct-28) | 9,03% vs 9,04% |
| S29E7 | No está en el repo | `LECAP_EXTRA` | Informe |

## 8. Controles

| Control | Cómo | Frecuencia |
|---|---|---|
| Motor (TIR, TEA, CER, TAMAR, BOPREAL) | `pytest` contra el informe BYMA/IAMC del 05-Oct-26 | Cada cambio de código |
| Flujos y TIR de soberanos y BOPREAL (D y C) | `tests/test_vs_iamc.py` contra IAMC del 17-Nov-26: flujo por flujo y TIR con tolerancia de 3 pb | Cada cambio de código; actualizar el archivo de IAMC una vez por mes |
| Riesgo país | Publicado (ArgentinaDatos) junto al calculado: KPI, gráfico histórico, Sheet y log de la corrida | Diario, automático |
| Curvas y tendencias | Pestañas "control curvas" y "control ajustes" del Sheet | Diario |
| TIR por bono | Comparar con el informe diario BYMA/IAMC | Manual, semanal sugerido |
