# curvas-ar

Curvas soberanas argentinas calculadas todos los días hábiles:

- **Hard dollar** (Bonares y Globales en USD MEP): TIR y duration modificada.
- **LECAP y BONCAP**: TNA, TEA, TEM y días al vencimiento.
- **CER cupón cero**: TIR real con CER de emisión y CER T-10 del BCRA.

Cada curva tiene líneas de tendencia logarítmicas (y = a + b·ln(x)) de hoy y de hace 7 días.

Cada curva se compara con el cierre de hace 7 días.

## De dónde salen los datos

| Dato | Fuente |
|---|---|
| Flujos de fondos y pagos finales | [`config.json` de rendimientos-ar](https://github.com/arisbdar/rendimientos-ar) (se lee en cada corrida y se guarda una copia diaria en `data/flujos/`) |
| Precios actuales e históricos | API de PPI (`ppi-client`) |
| Feriados para la liquidación T+1 | API de PPI |

## Estructura

```
main.py                  corrida completa
src/curvas/config.py     especies a seguir y parámetros
src/curvas/flujos.py     descarga y respaldo de flujos
src/curvas/precios.py    login y precios de PPI
src/curvas/motor.py      TIR, duration, TNA/TEA/TEM
src/curvas/curvas.py     arma las tablas de cada curva
src/curvas/bcra.py       índice CER del BCRA
src/curvas/export.py     datos de la terminal (docs/data/curvas.json) y tablas de control
src/curvas/sheet.py      carga del Google Sheet
src/curvas/universo.py   instrumentos de la pestaña "renta fija"
docs/index.html, app.js, style.css   terminal web
tests/test_motor.py      validación contra el informe BYMA/IAMC
.github/workflows/diario.yml   corrida automática
data/resultados/         CSV diarios (histórico)
docs/                    página publicada
```

## Usarlo en tu compu (VS Code)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # y completá tus keys de PPI
pytest                    # valida el motor
python main.py            # calcula y genera data/ y docs/
```

Para ver la terminal en tu compu:

```bash
cd docs
python -m http.server
```

y abrí http://localhost:8000 (con doble clic sobre index.html no carga los datos).

## Sheet de control

Si hay credenciales de Google, cada corrida escribe en "IOL pro":
- **renta fija** (columnas A:U): precios de hoy y de hace 7 días, vencimientos, montos, CER de emisión / VR de los DL. De la V en adelante es tuyo.
- **indices**: CER T-10 de la liquidación del día.
- **control curvas** y **control ajustes**: exactamente lo que muestra la terminal (tasas y parámetros a, b, R² de cada tendencia), para compararlo con tus cálculos.

## Automatización en GitHub

1. Creá un repositorio nuevo y subí esta carpeta.
2. En **Settings → Secrets and variables → Actions** cargá `PPI_PUBLIC_KEY` y `PPI_PRIVATE_KEY`.
3. En la pestaña **Actions**, abrí "Curvas diarias" y apretá **Run workflow** para probarlo.
4. Desde ahí corre solo de lunes a viernes a las 18:20 (hora Argentina) y guarda los resultados en el repo.
5. Para ver la página online: **Settings → Pages → Deploy from a branch → main / docs**.
   GitHub Pages en repositorios privados requiere un plan pago; con el plan gratuito el repo tiene que ser público
   (las keys siguen protegidas como Secrets).

## Agregar especies

Editá `HARD_DOLLAR`, `LECAP_EXTRA` o `LECAP_EXCLUIR` en `src/curvas/config.py`. Las LECAP nuevas que el repo de flujos
agregue entran solas.
