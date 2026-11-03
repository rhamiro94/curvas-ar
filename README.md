# curvas-ar

Curvas soberanas argentinas calculadas todos los días hábiles:

- **Hard dollar** (Bonares y Globales en USD MEP): TIR y duration modificada.
- **LECAP y BONCAP**: TNA, TEA, TEM y días al vencimiento.

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
src/curvas/graficos.py   gráficos PNG
src/curvas/pagina.py     docs/index.html
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

Abrí `docs/index.html` en el navegador para ver el resultado.

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
