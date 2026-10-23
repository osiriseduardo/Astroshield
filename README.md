# 🛰️ AstroShield — Evolucionar una constelación inteligente

Algoritmo genético que diseña una constelación de **8 satélites** de observación para cubrir **6 regiones
prioritarias**, respetando **zonas de desechos espaciales** y **posiciones ocupadas**. Incluye pruebas, análisis
estadístico y un **globo 3D interactivo** generado con los datos reales de cada ejecución.

![Evolución](outputs/fig_e2_evolucion.png)

## Resultado principal

| Métrica | Valor |
|---|---|
| Fitness de la solución de referencia | **0.9174** (99.94 % de la cota de referencia 0.9179) |
| Regiones cubiertas | **6/6**, con redundancia en las dos regiones Alta |
| Violaciones de restricciones | **0**, en 10/10 ejecuciones |
| 10 semillas | 0.9151 ± 0.0052, frente a 0.4232 de la búsqueda aleatoria (p = 8 × 10⁻⁵) |

## Ejecutar en Google Colab (recomendado)

1. Abre <https://colab.research.google.com> → **Archivo → Subir notebook** → elige `notebooks/AstroShield.ipynb`.
   Si el repositorio ya está en GitHub, también puedes usar **Archivo → Abrir notebook → GitHub** y pegar la URL.
2. **Entorno de ejecución → Ejecutar todo** (≈ 5 minutos).

El notebook es **autocontenido**: sus primeras celdas recrean el paquete `astroshield` y las pruebas con `%%writefile`,
así que no hace falta subir ningún otro archivo ni instalar nada. El notebook ya incluye las salidas de una ejecución,
así que también se puede revisar sin ejecutarlo.

## Ejecutar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest                       # 36 pruebas unitarias
python tools/run_experiments.py        # todas las pruebas E1–E10 → outputs/ (≈ 4 min)
open outputs/globe.html                # globo 3D interactivo
python tools/build_notebook.py --execute   # regenera el notebook desde el código fuente
```

Uso mínimo desde Python:

```python
from astroshield.scenario import default_scenario
from astroshield.ga import run_ga, GAConfig
r = run_ga(default_scenario(), GAConfig(generations=400), seed=0)
print(r.best_eval.fitness, r.best_eval.n_covered)
print(r.best_eval.region_table())
```

## Estructura

```
astroshield/          paquete
  geo.py              geometría esférica
  scenario.py         regiones, zonas, parámetros y cambios de condiciones
  evaluation.py       modelo de cobertura, restricciones, fitness y criterios de aceptación
  ga.py               algoritmo genético (cruce alineado, Deb + reparación, elitismo)
  baselines.py        búsqueda aleatoria y heurística voraz
  experiments.py      pruebas E1–E10
  viz.py              gráficas, mapa de misión y globo 3D (globe.gl)
tests/                pruebas unitarias (pytest)
tools/                run_experiments.py, build_notebook.py
notebooks/            AstroShield.ipynb (para Colab)
docs/                 entregables escritos
outputs/              evidencia: results.json, CSV, figuras, globe.html
```

## Entregables

| # | Entregable | Dónde |
|---|---|---|
| 1 | Definición del problema | [`docs/01_definicion_problema.md`](docs/01_definicion_problema.md) |
| 2 | Implementación funcional | [`astroshield/`](astroshield) y [`notebooks/AstroShield.ipynb`](notebooks/AstroShield.ipynb) |
| 3 | Pruebas y validación | [`docs/03_pruebas_validacion.md`](docs/03_pruebas_validacion.md), [`tests/`](tests) y la sección 5 del notebook |
| 4 | Análisis de resultados | [`docs/04_analisis_resultados.md`](docs/04_analisis_resultados.md) |
| 5 | Visualización 3D | [`outputs/globe.html`](outputs/globe.html) y la sección 4 del notebook |
| 6 | Repositorio y presentación | este README, el historial de commits y [`docs/06_guia_presentacion.md`](docs/06_guia_presentacion.md) |

## Paleta y diseño

Tema oscuro tipo "centro de control de misión", aplicado igual en las gráficas, los mapas y el globo:
cian `#22D3EE` para la constelación final, violeta `#A78BFA` para la inicial, verde `#34D399` para regiones cubiertas,
rojo `#F87171` para regiones no cubiertas o violaciones, naranja `#FB923C` para zonas de desechos y rosa `#F472B6` para
posiciones ocupadas.

## Uso de herramientas de inteligencia artificial

> **Completar por el equipo antes de entregar.**

Se usó un asistente de IA (Claude, de Anthropic) para: proponer la estructura del código, redactar la primera versión
de los módulos, las pruebas y la documentación, y generar el notebook.

Verificaciones que hizo el equipo sobre esos resultados:

* Revisar y ejecutar las 36 pruebas unitarias, incluidas las que comprueban la geometría con valores conocidos
  (por ejemplo, la distancia entre (0°, 0°) y (0°, 90°) es 90°).
* Verificar a mano la fórmula de la huella (λ a 500 km = 293 km < 300 km) y la cota de referencia.
* Auditar con un cálculo independiente que ninguna solución final viola zonas (E3/E4).
* Comprobar que el globo muestra exactamente la configuración del AG (celda 5.7 del notebook).
* Contrastar cada afirmación de los documentos con `outputs/results.json`.
* _(Agregar aquí lo que cada integrante revisó, modificó o decidió.)_

## Equipo

| Integrante | Parte que puede explicar y demostrar |
|---|---|
| _Nombre 1_ | Modelo de cobertura y función de evaluación (`evaluation.py`) |
| _Nombre 2_ | Algoritmo genético y operadores (`ga.py`) |
| _Nombre 3_ | Restricciones, escenarios difíciles y cambios de condiciones (E3–E6, E9) |
| _Nombre 4_ | Visualización 3D y análisis de resultados (`viz.py`, docs 03–04) |
