"""Build notebooks/AstroShield.ipynb from the package sources.

The notebook is self-contained for Google Colab: its first cells recreate
the `astroshield` package and the tests with %%writefile, so the code that
runs in Colab is byte-for-byte the code in this repository.

Usage:  python tools/build_notebook.py [--execute]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB_PATH = ROOT / "notebooks" / "AstroShield.ipynb"
MODULES = ["__init__", "geo", "scenario", "evaluation", "ga", "baselines", "experiments", "viz"]
TESTS = ["test_model", "test_ga", "test_viz"]

cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(src, hidden=False):
    c = nbf.v4.new_code_cell(src.strip("\n"))
    if hidden:
        c.metadata["cellView"] = "form"
    cells.append(c)


def build(R):
    e2, e7 = R["E2"], R["E7"]["summary"]
    md(f"""
# 🛰️ AstroShield — Evolucionar una constelación inteligente

**Algoritmo genético para diseñar una constelación de 8 satélites de observación** que cubra seis regiones prioritarias
de la Tierra, respetando zonas de desechos espaciales y posiciones ocupadas, con visualización en un globo 3D.

| | |
|---|---|
| **Representación** | 8 satélites × (latitud, longitud, altitud) — 24 genes reales |
| **Cobertura** | huella cónica del sensor (semiángulo 30°), región = disco de 300 km muestreado con 49 puntos |
| **Fitness** | Σ peso·(0.70·cobertura + 0.15·redundancia + 0.15·resolución) / Σ pesos, con pesos Alta 3 · Media 2 · Normal 1 |
| **Restricciones** | reglas de factibilidad de Deb + reparación probabilística + separación mínima de 2° |
| **Resultado de referencia** | fitness **{e2['fitness']:.4f}** (cota de referencia {e2['bound']['fitness']:.4f}), 6/6 regiones, 0 violaciones |

> **Cómo usarlo en Google Colab**
> 1. `Entorno de ejecución → Ejecutar todo`. Si Colab advierte que el notebook "no fue creado por Google", elige
>    **Ejecutar de todos modos**: el notebook no usa tu Drive ni pide permisos.
> 2. Tiempo aproximado: **≈ 6 min** en modo `completo` y **≈ 2 min** en modo `rápido` (lo eliges en la celda de configuración).
> 3. La sección 0 crea el paquete `astroshield` dentro de Colab y verifica las librerías; si falta alguna, la instala.
> 4. Al final, la sección 9 descarga un `.zip` con todas las figuras, CSV y el globo 3D.
>
> Las interpretaciones citan los valores de la **ejecución de referencia** (modo completo). En modo rápido los números
> pueden variar un poco.

**Índice:** 0 Instalación · 1 Modelo · 2 Etapa 1 · 3 Etapa 2 · 4 Globo 3D · 5 Pruebas (E3–E10) · 6 Pruebas unitarias · 7 Laboratorio interactivo · 8 Conclusiones · 9 Descarga
""")

    md("""
## 0. Instalación del paquete `astroshield`

Cada celda escribe un módulo del repositorio. Están colapsadas para no estorbar, pero puedes abrirlas para revisar el código.

| Módulo | Responsabilidad |
|---|---|
| `geo.py` | geometría esférica (haversine, rumbos, círculos sobre la esfera) |
| `scenario.py` | datos del problema: regiones, zonas, parámetros y cambios de condiciones |
| `evaluation.py` | modelo de cobertura, restricciones, fitness y criterios de aceptación |
| `ga.py` | algoritmo genético: selección, cruce alineado, mutación, reparación y elitismo |
| `baselines.py` | búsqueda aleatoria y heurística voraz, para comparar |
| `experiments.py` | las pruebas E1–E10 |
| `viz.py` | gráficas, mapa de misión y globo 3D |
""")
    code("import os\nos.makedirs('astroshield', exist_ok=True)\nos.makedirs('tests', exist_ok=True)\nos.makedirs('outputs', exist_ok=True)")
    for m in MODULES:
        src = (ROOT / "astroshield" / f"{m}.py").read_text(encoding="utf-8")
        code(f"%%writefile astroshield/{m}.py\n{src}", hidden=True)
    for t in TESTS:
        src = (ROOT / "tests" / f"{t}.py").read_text(encoding="utf-8")
        code(f"%%writefile tests/{t}.py\n{src}", hidden=True)
    code("%%writefile pytest.ini\n[pytest]\ntestpaths = tests\npythonpath = .", hidden=True)

    md("### Verificación del entorno y configuración")
    code("""
import importlib, importlib.util, subprocess, sys, warnings
IN_COLAB = "google.colab" in sys.modules
REQUIRED = {"numpy": "numpy", "scipy": "scipy", "pandas": "pandas", "matplotlib": "matplotlib",
            "plotly": "plotly", "pytest": "pytest"}
missing = [pkg for mod, pkg in REQUIRED.items() if importlib.util.find_spec(mod) is None]
if missing:
    print("Instalando:", missing)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])
for mod in REQUIRED:
    print(f"  {mod:<11}", importlib.import_module(mod).__version__)
print("Python", sys.version.split()[0], "| Colab:", IN_COLAB)
""")
    code("""
#@title Configuración de la ejecución
MODO = "completo"  #@param ["completo", "rápido"]
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
for _m in [m for m in sys.modules if m == "astroshield" or m.startswith("astroshield.")]:
    del sys.modules[_m]  # re-running the notebook picks up edited %%writefile cells
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from IPython.display import display, Markdown
import astroshield
from astroshield import experiments as X
from astroshield.scenario import default_scenario, initial_scenario, Zone
from astroshield.evaluation import Evaluator, acceptance, reference_upper_bound, footprint_half_angle
from astroshield.ga import GAConfig, run_ga
from astroshield.geo import deg_to_km
from astroshield.viz import (apply_theme, plot_evolution, plot_runs, plot_regions, plot_mission_map,
                             show_globe, plotly_comparison)
apply_theme()
import plotly.io as pio
pio.renderers.default = "colab" if IN_COLAB else "notebook_connected"  # keeps the notebook light
pd.set_option("display.width", 160)
if MODO == "completo":
    CFG, N_SEEDS, N_ABLATION = GAConfig(), 10, 5        # parámetros finales (sección 5.8)
else:
    CFG, N_SEEDS, N_ABLATION = GAConfig(generations=200), 5, 3
print("AstroShield", astroshield.__version__, "| modo:", MODO, "| semillas:", N_SEEDS)
print("GA:", CFG)
""")

    # ------------------------------------------------------------------ model
    md("""
## 1. Del escenario al problema computacional

El documento completo está en `docs/01_definicion_problema.md`. Resumen de las decisiones:

* **Configuración**: matriz `8 × 3` con `(lat, lon, alt_km)`. Cada satélite está fijo sobre su punto subsatelital
  (modelo educativo de *station-keeping*, no mecánica orbital). La altitud va de 500 a 2000 km.
* **Huella**: sensor nadir con semiángulo η = 30°. El ángulo central de la huella es
  $\\lambda(h)=\\arcsin\\!\\big(\\tfrac{R+h}{R}\\sin\\eta\\big)-\\eta$. A mayor altitud la huella crece,
  pero la resolución empeora. **Ese es el compromiso central del problema.**
* **Región cubierta**: al menos el 95 % de sus 49 puntos de muestra (centro y 3 anillos hasta 300 km) caen dentro de alguna huella.
* **Fitness** ∈ [0, 1]: por región, `0.70·cobertura + 0.15·redundancia (≥ 2 satélites) + 0.15·resolución`,
  promediado con pesos de prioridad (Alta = 3, Media = 2, Normal = 1).
* **Configuración inválida**: un punto subsatelital dentro de una zona de desechos o de exclusión (interpretadas como
  conos desde el centro de la Tierra, que aplican a cualquier altitud), o dos satélites a menos de 2°.
""")
    code("""
sc = default_scenario()
display(pd.DataFrame([dict(región=r.name, lat=r.lat, lon=r.lon, prioridad=r.priority, peso=r.weight, radio_km=r.radius_km)
                      for r in sc.regions]))
display(pd.DataFrame([dict(zona=z.name, tipo=z.kind, lat=z.lat, lon=z.lon, radio_deg=z.radius_deg) for z in sc.zones]))
alts = np.array([500, 513, 750, 1000, 1500, 2000])
display(pd.DataFrame({"altitud_km": alts, "radio_huella_km": deg_to_km(footprint_half_angle(alts, 30)).round(0),
                      "calidad_resolución": (1 - (alts - 500) / 1500).round(3)}))
ub = reference_upper_bound(sc)
print(f"Cota de referencia (relajación sin restricciones): {ub['fitness']:.4f}")
""")
    md("""
**Lectura:** a 500 km la huella mide 293 km, así que **no alcanza** a cubrir un disco de 300 km. Hacen falta al menos 513 km.
Con 8 satélites y 6 regiones sobran 2 satélites. Si se asignan como redundancia a las dos regiones Alta, se llega a la
**cota de referencia**, que no se puede superar porque cada término ya está en su máximo. Esa cota permite medir
*qué tan lejos del óptimo* quedó cada solución, no solo compararlas entre sí.
""")

    # ----------------------------------------------------------------- stage 1
    e1 = R["E1"]
    md(f"""
## 2. Etapa 1 — escenario inicial sin restricciones espaciales (prueba E1)

Población de 120 configuraciones aleatorias uniformes sobre la esfera, evolucionada durante 400 generaciones.
""")
    code("""
r1 = X.e1_initial(CFG, seed=0)
print(X.summarize(r1))
display(r1.best_eval.region_table())
display(acceptance(r1.best_eval, r1.scenario))
plot_mission_map(r1.scenario, r1.best, r1.initial_best); plt.show()
""")
    md(f"""
**Interpretación (ejecución de referencia):** el AG pasa de fitness {e1['initial_fitness']:.3f} (el mejor individuo aleatorio)
a **{e1['fitness']:.4f}** y cubre las {e1['regions_covered']}/6 regiones desde la generación {e1['full_coverage_gen']}.
En el mapa, las ✕ moradas son la mejor configuración aleatoria inicial y las ★ cian, la final.
""")

    # ----------------------------------------------------------------- stage 2
    md(f"""
## 3. Etapa 2 — con zonas de desechos y posiciones ocupadas (pruebas E2: evolución)
""")
    code("""
base = X.e2_base(CFG, seed=0)
print(X.summarize(base))
display(base.best_eval.region_table())
display(base.best_eval.satellite_table(base.scenario))
display(acceptance(base.best_eval, base.scenario))
""")
    code("""
plot_evolution(base); plt.show()
plot_regions({"inicial (gen 0)": base.initial_eval, "final": base.best_eval}); plt.show()
plot_mission_map(base.scenario, base.best, base.initial_best); plt.show()
h = base.history_frame()
display(h.iloc[[0, 10, 25, 50, 100, 200, 300, len(h) - 1]][
    ["generation", "best_fitness", "mean_fitness", "std_fitness", "feasible_ratio", "diversity_deg", "sigma_deg"]].round(4))
""")
    md(f"""
**Interpretación (ejecución de referencia):**

* **Mejora:** el fitness pasa de {e2['initial_fitness']:.4f} a **{e2['fitness']:.4f}**, que es el
  {100 * e2['fitness'] / e2['bound']['fitness']:.2f} % de la cota de referencia ({e2['bound']['fitness']:.4f}).
  Las 6 regiones quedan cubiertas desde la generación {e2['full_coverage_gen']} y se alcanza el 99 % del valor final en la
  generación {e2['convergence_gen']}.
* **Dos fases visibles:** primero *exploración*, con σ de mutación alto, diversidad alta y saltos grandes en las primeras
  ~30 generaciones (la diversidad baja de ~47° a ~7°); después *explotación*, con σ decayendo exponencialmente de 12° a
  0.05°, la diversidad bajando a ~2° y ajustes finos de altitud hasta ≈ 515 km, que son los que suben la resolución.
* **Estrategia emergente:** cada región tiene su satélite casi exacto sobre el centro a ≈ 515 km (el mínimo que cubre los
  300 km). Los 2 satélites sobrantes se usaron como **redundancia en las dos regiones Alta**, a mayor altitud (~1400–1500 km)
  y desplazados ≥ 2° para respetar la separación mínima. Nadie programó esa regla: **surge de la función de evaluación.**
* **Restricciones:** el {100 * e2['initial_feasible_ratio']:.0f} % de la población aleatoria inicial era válida. Las
  inválidas desaparecen por las reglas de Deb, y la solución final no tiene ninguna violación.
""")

    # ------------------------------------------------------------------ globe
    md("""
## 4. Visualización 3D de la constelación (Entregable 5)

Globo **WebGL interactivo** (globe.gl) generado con los datos **reales** de la ejecución anterior:

* 🟢/🔴 regiones cubiertas o no cubiertas, con anillos pulsantes · 🟠 zonas de desechos · 🩷 posiciones ocupadas
* columnas cian = satélites a su **altitud real a escala** · círculos cian = huellas del sensor
* pestañas **Inicial (gen 0) / Generación 50 / Final** para comparar la evolución, y la opción *Superponer otro estado*
* arrastra para girar, rueda para acercar, pasa el cursor sobre cualquier objeto para ver sus datos

También se guarda como `outputs/globe.html`, que se abre en cualquier navegador.
""")
    code("""
_ = show_globe(base.scenario, {"Inicial (gen 0)": base.initial_best, "Generación 50": base.snapshots[50], "Final": base.best},
               height=680, save_to="outputs/globe.html")
""")
    md("Vista alternativa (Plotly, proyección ortográfica girable) para comparar lado a lado la configuración inicial y la final:")
    code("plotly_comparison(base.scenario, base.initial_best, base.best).show()")

    # ------------------------------------------------------------------ tests
    a = R["E3_E4"]
    md(f"""
## 5. Pruebas y validación (Entregable 3)

Cada prueba registra **condiciones → resultados → interpretación**. Los valores de las interpretaciones vienen de la
ejecución de referencia (`outputs/results.json`). Si tu ejecución difiere ligeramente por la versión de numpy, la
conclusión debe ser la misma.

### 5.1 Variación entre ejecuciones (E7) y comparación con métodos de referencia

**Condiciones:** escenario base, {e7['n_runs']} semillas distintas, los mismos parámetros y el mismo presupuesto de
{e7['budget_evaluations']:,} evaluaciones para el AG y para la búsqueda aleatoria. La heurística voraz agrega satélites
uno por uno, siempre el de mayor ganancia.
""")
    code("""
runs, table, summary, rnd, dist = X.e7_variation(CFG, seeds=range(N_SEEDS), progress=True)
display(table[["seed", "fitness", "initial_fitness", "regions_covered", "accepted", "full_coverage_gen", "convergence_gen", "time_s"]])
display(pd.Series(summary).to_frame("valor"))
plot_runs(runs); plt.show()
fig, ax = plt.subplots(figsize=(8, 4))
ax.boxplot([table["fitness"], rnd], widths=0.5); ax.set_xticks([1, 2], ["AG", "Búsqueda aleatoria"])
ax.axhline(summary["greedy"], color="#FACC15", ls="--", label="voraz"); ax.axhline(summary["bound"], color="#34D399", ls=":", label="cota")
ax.set_ylabel("fitness final"); ax.legend(); plt.show()
print("Distancia media (°) entre las soluciones de cada par de semillas:")
display(pd.DataFrame(dist, columns=[f"s{i}" for i in range(len(dist))]).round(1))
""")
    md(f"""
**Interpretación:**

* **Estabilidad:** fitness {e7['ga_mean']:.4f} ± {e7['ga_std']:.4f} (CV = {e7['ga_cv_percent']:.2f} %), rango
  [{e7['ga_min']:.4f}, {e7['ga_max']:.4f}]. Las 10 ejecuciones cubren 6/6 regiones y son válidas; {e7['ga_accepted']}/{e7['n_runs']}
  cumplen **todos** los criterios de aceptación. Las 2 que fallan (semillas 4 y 5, fitness ≈ 0.905) lo hacen **solo por C3**:
  uno de los satélites de redundancia quedó sobre una región Media (Sahel o Japón) en lugar de la segunda Alta. Es un
  **óptimo local**: para salir de ahí habría que mover un satélite ~90° de golpe, y la mutación fina ya no da saltos tan
  grandes.
* **AG vs. aleatoria:** con el mismo presupuesto, la búsqueda aleatoria se queda en {e7['random_mean']:.3f} (máx.
  {e7['random_max']:.3f}). La prueba de Mann-Whitney unilateral da p = {e7['mannwhitney_p_ga_gt_random']:.1e}: la diferencia
  es estadísticamente significativa. **El AG no está ganando por suerte.**
* **AG vs. voraz:** la heurística voraz ({e7['greedy']:.4f}) usa conocimiento del dominio, porque solo prueba posiciones
  cercanas a los centros de las regiones. El AG parte de cero, la iguala en promedio y la supera en su mejor ejecución
  ({e7['ga_max']:.4f}). El AG **no conoce** dónde están las regiones; lo descubre.
* **Soluciones distintas con calidad similar:** la distancia media entre soluciones es {e7['solution_distance_mean_deg']:.1f}°
  (máx. {e7['solution_distance_max_deg']:.1f}°). El paisaje es **multimodal**: los satélites base casi coinciden, pero los
  dos de redundancia cambian de posición según la semilla. Por eso se reportan distribuciones y no una sola corrida.
""")

    md("### 5.2 Zonas restringidas por desechos (E3) y posiciones ocupadas (E4)\n\n"
       "**Condiciones:** auditoría geométrica independiente del AG: para la mejor solución de **cada** semilla se mide "
       "la distancia del satélite más cercano a cada zona.")
    code("""
audit = X.e3_e4_constraint_audit(runs)
display(audit.groupby(["zona", "tipo", "radio_deg"]).agg(distancia_mín=("distancia_deg", "min"),
        margen_mín=("margen_deg", "min"), todas_respetan=("respeta", "all")).reset_index())
print("Fracción válida en la población aleatoria inicial:", np.mean([r.history[0]["feasible_ratio"] for r in runs]).round(3))
print("Fracción válida en la población final:          ", np.mean([r.history[-1]["feasible_ratio"] for r in runs]).round(3))
""")
    md("**Prueba de estrés E4:** el *Objeto A* se reubica a solo 2° del centro del Sahel, de modo que su zona de exclusión "
       "invade la región.")
    code("""
near = X.e4_object_near_region(CFG, seed=0)
display(X.zone_margins(near.best, near.scenario))
display(near.best_eval.region_table())
plot_mission_map(near.scenario, near.best); plt.show()
""")
    ne = R["E4_near"]
    sah = next(x for x in ne["regions"] if x["región"] == "Sahel")
    md(f"""
**Interpretación:**

* **Las {len(a['min_margin_by_zone'])} zonas se respetan en las {e7['n_runs']} ejecuciones** (`todas_respetan = True`).
  Margen mínimo por zona: {', '.join(f"{k} {v:.1f}°" for k, v in a['min_margin_by_zone'].items())}.
* La población inicial tenía {100 * (1 - a['initial_feasible_ratio_mean']):.0f} % de configuraciones inválidas; al final
  queda {100 * a['final_feasible_ratio_mean']:.0f} % de válidas. Las inválidas restantes son hijos recién mutados que
  la selección descarta.
* **Observación honesta:** en el escenario base, las zonas quedan lejos de las regiones, así que *en el óptimo* las
  restricciones no están activas. Por eso las pruebas E4-estrés, E5 y E6 las ponen **encima** de las regiones.
* **E4 estrés:** el satélite del Sahel se coloca **exactamente en el borde** de la zona de exclusión (margen
  {min(m['margen_deg'] for m in ne['margins'] if 'reubicado' in m['zona']):.2f}°) y sube de ~519 km a ~1077 km para
  alcanzar la región desde fuera: cobertura {sah['cobertura']:.0%}, pero la resolución baja a {sah['resolución']:.2f}. La restricción tiene
  **un costo medible**: el fitness baja de {e2['fitness']:.4f} a {ne['fitness']:.4f}.
""")

    md("### 5.3 Espacio reducido (E5)\n\n**Condiciones:** se reduce el espacio en 4 niveles acumulativos: R0 base → "
       "R1 + zona de 6° centrada a 2.6° de Yucatán → R2 + techo de altitud de 1200 km → R3 + zona sobre Japón. "
       "Además, R1 se corre **sin manejo de restricciones** (`constraint_handling='none'`) para ver qué está evitando el sistema.")
    code("""
red, unc = X.e5_reduced_space(CFG, seed=0)
display(pd.DataFrame([X.summarize(r) for r in red])[["scenario", "fitness", "feasible", "regions_covered", "accepted", "bound", "full_coverage_gen"]])
for r in red:
    print(r.scenario.name, "→ altitudes:", r.best[:, 2].round(0).astype(int).tolist())
print("\\nR1 SIN manejo de restricciones:", X.summarize(unc)["fitness"], "| válida:", unc.best_eval.feasible)
for v in unc.best_eval.violations:
    print(f"   ✗ S{v.satellite} viola {v.target}: {v.distance_deg:.2f}° < {v.limit_deg}°")
plot_regions({r.scenario.name.split(" ")[0]: r.best_eval for r in red}, "Cobertura por nivel de reducción"); plt.show()
plot_mission_map(red[3].scenario, red[3].best); plt.show()
""")
    lv = R["E5"]["levels"]
    md(f"""
**Interpretación:**

* El fitness baja de forma monótona conforme se reduce el espacio: {' → '.join(f"{l['fitness']:.4f}" for l in lv)}.
  **Las 6 regiones siguen cubiertas en todos los niveles**: el AG compensa subiendo satélites o alejándolos de las zonas,
  y lo que se pierde es resolución y redundancia.
* **Sin manejo de restricciones**, el AG pone satélites *dentro* de la zona del Golfo (fitness aparente
  {R['E5']['unconstrained_R1']['fitness']:.4f}, pero con {R['E5']['unconstrained_R1']['violation_deg']:.1f}° de intrusión total).
  Es una configuración con mejor puntaje que **no es válida**, justo lo que advierte el enunciado. Con las reglas de Deb, la
  solución de R1 ({lv[1]['fitness']:.4f}) es peor en puntaje pero **válida**.
* El techo de 1200 km (R2) impide la estrategia de "huella grande", así que la redundancia se vuelve más cara.
""")

    md("### 5.4 Condiciones difíciles o inviables (E6)\n\nTres tipos de dificultad, de distinta naturaleza:\n\n"
       "| Caso | Qué lo hace difícil |\n|---|---|\n"
       "| I1 | Zona de 15° centrada en la Amazonía: ninguna huella (máx. 11°) puede alcanzarla desde fuera → **objetivo inalcanzable** |\n"
       "| I2 | Solo 5 satélites para 6 regiones → **recursos insuficientes** |\n"
       "| I3 | Separación mínima de 80° entre 8 satélites: imposible por geometría (problema de Tammes, máx. ≈ 74.9°) → **ninguna configuración válida existe** |")
    code("""
inf = X.e6_infeasible(CFG, seed=0)
display(pd.DataFrame([X.summarize(r) for r in inf.values()])[["scenario", "fitness", "feasible", "violation_deg", "regions_covered", "accepted"]])
for k, r in inf.items():
    lost = [x.name for x in r.best_eval.regions if not x.covered]
    print(f"{k}: regiones sin cubrir = {lost} | violaciones = {len(r.best_eval.violations)}")
plot_mission_map(inf["I2 solo 5 satélites"].scenario, inf["I2 solo 5 satélites"].best); plt.show()
plot_evolution(inf["I3 separación 80° imposible"]); plt.show()
""")
    e6 = R["E6"]
    md(f"""
**Interpretación:**

* **I1:** el sistema **no hace trampa**. Entrega una solución válida (fitness {e6['I1 Amazonía inalcanzable']['fitness']:.4f})
  con la Amazonía al 0 % y las otras 5 regiones cubiertas, y lo reporta explícitamente (criterio C2 = falso).
* **I2:** con 5 satélites, el AG **sacrifica el Interior de Australia**, la única región de prioridad Normal. Las
  prioridades sí deciden qué se pierde cuando no alcanza para todo.
* **I3:** no existe ninguna configuración válida. El AG lo reporta (`feasible = False`, curva de mejor válida vacía) y
  devuelve la configuración que **menos** viola: {e6['I3 separación 80° imposible']['n_violations']} pares de satélites,
  {e6['I3 separación 80° imposible']['violation_deg']:.1f}° de intrusión total. La gráfica muestra la fracción válida en 0
  durante toda la ejecución. **Que el algoritmo termine no significa que haya resuelto el problema.**
""")

    md("### 5.5 Cambio en las condiciones (E9, sección 3.3 del enunciado)\n\n"
       "**Condiciones:** (a) el Interior de Australia sube a prioridad Alta; (b) aparece una zona de desechos de 3° "
       "justo donde está el satélite que observa Japón. Primero se **revalida** la solución anterior y luego se re-optimiza "
       "partiendo de la población previa (*warm start*) y, para comparar, desde cero.")
    code("""
ch = X.e9_change_of_conditions(base, CFG, seed=0)
display(pd.DataFrame({"(a) prioridad": ch["prioridad"]["revalidación"], "(b) zona nueva": ch["zona_nueva"]["revalidación"]}))
display(pd.DataFrame([X.summarize(ch["prioridad"]["reoptimizado"]) | {"modo": "(a) warm"},
                      X.summarize(ch["zona_nueva"]["warm"]) | {"modo": "(b) warm"},
                      X.summarize(ch["zona_nueva"]["cold"]) | {"modo": "(b) desde cero"}])
        [["modo", "fitness", "initial_fitness", "feasible", "accepted", "convergence_gen", "bound"]])
fig, ax = plt.subplots(figsize=(9, 4))
for k, c, lab in (("warm", "#22D3EE", "warm start"), ("cold", "#A78BFA", "desde cero")):
    ax.plot([max(h["best_so_far_rank"], -0.05) for h in ch["zona_nueva"][k].history], color=c, label=lab)
ax.set_xlabel("generación"); ax.set_ylabel("mejor fitness"); ax.legend(); ax.set_title("Re-optimización tras la zona nueva"); plt.show()
""")
    e9 = R["E9"]
    md(f"""
**Interpretación:**

* **(a) Prioridad:** la solución anterior **sigue siendo válida**, porque una prioridad no cambia la geometría, pero su
  fitness cambia de {e9['prioridad']['revalidación']['fitness_antes']:.4f} a {e9['prioridad']['revalidación']['fitness_ahora']:.4f}
  porque cambian los pesos. La re-optimización llega a {e9['prioridad']['reoptimizado']['fitness']:.4f}, frente a una cota de
  {e9['prioridad']['reoptimizado']['bound']:.4f}.
* **(b) Zona nueva:** la solución anterior **deja de ser válida** ({'; '.join(e9['zona_nueva']['revalidación']['violaciones'])}),
  aunque su fitness no haya cambiado. Esto demuestra que el puntaje y la validez son cosas distintas.
  Con *warm start*, el AG la repara y llega a {e9['zona_nueva']['warm']['fitness']:.4f} en
  {e9['zona_nueva']['warm']['convergence_gen']} generaciones. Desde cero, con el mismo presupuesto, solo alcanza
  {e9['zona_nueva']['cold']['fitness']:.4f}. **Reutilizar la población anterior es más eficiente que empezar de nuevo.**
""")

    md("### 5.6 Prueba propia: robustez ante la falla de un satélite (E8)\n\n"
       "**Pregunta:** ¿el término de redundancia del fitness tiene valor real o solo infla el puntaje? "
       "**Condiciones:** para la solución base se simula la falla de cada satélite (análisis N-1) y se compara contra una "
       "solución optimizada **sin** término de redundancia (pesos 0.80 / 0 / 0.20).")
    code("""
rob = X.e8_robustness(base, CFG, seed=0)
print("CON término de redundancia"); display(rob["con_redundancia"])
print("SIN término de redundancia"); display(rob["sin_redundancia"])
""")
    e8 = R["E8"]["summary"]
    md(f"""
**Interpretación:** con el término de redundancia, **{e8['con_redundancia']['fallos_sin_pérdida']} de 8** fallas posibles no
hacen perder ninguna región, y el fitness medio tras una falla es {e8['con_redundancia']['fitness_media_N-1']:.4f}. Sin él,
solo {e8['sin_redundancia']['fallos_sin_pérdida']} de 8 fallas son inocuas ({e8['sin_redundancia']['fitness_media_N-1']:.4f}),
y una falla puede dejar **sin cobertura una región Alta**. El término de redundancia hace que la constelación sea más
**tolerante a fallas** precisamente donde más importa.
""")

    md("### 5.7 Correspondencia entre los datos y la visualización\n\n"
       "El globo y los mapas se construyen con `Evaluator.evaluate()` sobre las mismas configuraciones que devuelve el AG. "
       "Esta celda lo verifica: lee los datos embebidos en `outputs/globe.html` y los compara con el resultado.")
    code("""
import json, re
html = open("outputs/globe.html", encoding="utf-8").read()
data = json.loads(re.search(r"const D = (\\{.*?\\});\\n", html, re.S).group(1))
final = data["states"][-1]
cfg_globe = np.array([[s["lat"], s["lng"], s["alt_km"]] for s in final["satellites"]])
assert np.allclose(cfg_globe, base.best), "¡el globo no muestra la constelación del AG!"
assert abs(final["fitness"] - base.best_eval.fitness) < 1e-12
assert [r["covered"] for r in final["regions"]] == [r.covered for r in base.best_eval.regions]
print("✔ El globo muestra exactamente la configuración, el fitness y la cobertura que calculó el AG.")
""")

    md("### 5.8 Calibración y ablación de operadores (E10)\n\n"
       "**Condiciones:** escenario R1 (las restricciones sí afectan aquí), 5 semillas por variante. Se apaga un operador "
       "a la vez para medir su aporte.")
    code("""
abl_runs, abl = X.e10_ablation(CFG, seeds=range(N_ABLATION), progress=True)
display(abl)
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.barh(abl["variante"], abl["fitness_media"], xerr=abl["fitness_std"], color="#22D3EE")
ax.set_xlim(abl["fitness_media"].min() - 0.02, abl["fitness_media"].max() + 0.01); ax.invert_yaxis()
ax.set_xlabel("fitness final medio (R1)"); plt.show()
""")
    md("""
**Interpretación:** consulta `docs/04_analisis_resultados.md` para la discusión completa. En resumen, la mutación alta y
la población pequeña empeoran claramente el resultado. Varias diferencias entre variantes son del mismo orden que la
desviación estándar, **así que no son concluyentes con 5 semillas**, y lo reportamos así en lugar de sobreinterpretarlas.
La calibración inicial (registrada en el análisis) mostró que **el número de generaciones y el ajuste fino final**
(σ final de 0.05° y 2 km) son los parámetros que más mejoran el resultado: con 250 generaciones el fitness medio era
0.894, con 400 subió a 0.908 y con la combinación final (más el elitismo 4, el torneo 4 y la mutación 0.15) llegó a 0.9175.
""")

    md("## 6. Pruebas unitarias automatizadas\n\nPruebas con `pytest`: geometría, cobertura, cada zona prohibida, "
       "separación, reproducibilidad, caso inviable, *warm start*, AG frente a la búsqueda aleatoria y operadores.")
    code("import sys\n!{sys.executable} -m pytest -q")

    md("""
## 7. Laboratorio interactivo

Modifica las condiciones y observa el efecto. En Colab aparecen controles de formulario a la derecha de la celda.
""")
    code("""
#@title Escenario personalizado { run: "manual" }
prioridad_australia = "normal"  #@param ["alta", "media", "normal"]
techo_altitud_km = 2000  #@param {type:"slider", min:600, max:2000, step:100}
nueva_zona_lat = 36.0  #@param {type:"number"}
nueva_zona_lon = 138.0  #@param {type:"number"}
nueva_zona_radio = 0.0  #@param {type:"slider", min:0, max:20, step:0.5}
generaciones = 200  #@param {type:"slider", min:20, max:600, step:20}
semilla = 42  #@param {type:"integer"}

lab = default_scenario().with_priority("Interior de Australia", prioridad_australia).with_params(alt_max_km=float(techo_altitud_km))
if nueva_zona_radio > 0:
    lab = lab.with_zone(Zone("Zona del laboratorio", nueva_zona_lat, nueva_zona_lon, nueva_zona_radio))
print("Solución base revalidada en el nuevo escenario:", X.revalidate(base.best, base.scenario, lab))
rl = run_ga(lab, GAConfig(generations=generaciones), seed=semilla)
print(X.summarize(rl)); display(rl.best_eval.region_table()); display(acceptance(rl.best_eval, lab))
_ = show_globe(lab, {"Solución base": base.best, "Re-optimizada": rl.best}, height=600)
""")

    md(f"""
## 8. Conclusiones

1. **El AG resuelve el problema:** alcanza el {100 * e7['ga_mean'] / e7['bound']:.1f} % de la cota de referencia en promedio,
   con todas las ejecuciones válidas y 6/6 regiones cubiertas, y es significativamente mejor que la búsqueda aleatoria
   (p = {e7['mannwhitney_p_ga_gt_random']:.1e}).
2. **Las restricciones tienen efecto real:** se auditan geométricamente en cada ejecución, se demuestra qué pasa sin
   ellas (E5) y se mide su costo en fitness cuando invaden regiones (E4, E5).
3. **El sistema es honesto ante lo imposible:** distingue entre objetivo inalcanzable, recursos insuficientes y
   ausencia total de soluciones válidas, y lo reporta en lugar de ocultarlo (E6).
4. **Limitaciones** (ver `docs/04_analisis_resultados.md`): el modelo es estático (sin órbitas ni revisita), la
   resolución es lineal en la altitud, los pesos 0.70/0.15/0.15 son decisiones de diseño, la cota de referencia es una
   relajación y el muestreo de 49 puntos aproxima el área.
""")

    md("## 9. Descargar los resultados\n\nEmpaqueta `outputs/` (globo 3D y figuras) y el código en un `.zip`. En Colab se descarga automáticamente.")
    code("""
for name, fig in [("fig_evolucion.png", plot_evolution(base)), ("fig_mapa.png", plot_mission_map(base.scenario, base.best, base.initial_best)),
                  ("fig_convergencia.png", plot_runs(runs))]:
    fig.savefig(f"outputs/{name}", dpi=130); plt.close(fig)
base.history_frame().to_csv("outputs/historial_base.csv", index=False)
table.to_csv("outputs/ejecuciones_semillas.csv", index=False)
import zipfile, os
with zipfile.ZipFile("astroshield_resultados.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for folder in ("outputs", "astroshield", "tests"):
        for root, _, files in os.walk(folder):
            for f in files:
                if not f.endswith(".pyc"):
                    z.write(os.path.join(root, f))
print("Creado astroshield_resultados.zip con", len(zipfile.ZipFile("astroshield_resultados.zip").namelist()), "archivos")
if IN_COLAB:
    from google.colab import files
    files.download("astroshield_resultados.zip")
""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="execute the notebook to embed outputs")
    args = ap.parse_args()
    R = json.loads((ROOT / "outputs" / "results.json").read_text(encoding="utf-8"))
    build(R)
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata.update({
        "colab": {"provenance": [], "toc_visible": True, "name": "AstroShield.ipynb"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    })
    NB_PATH.parent.mkdir(exist_ok=True)
    if args.execute:
        import tempfile

        from nbclient import NotebookClient

        with tempfile.TemporaryDirectory() as tmp:
            NotebookClient(nb, timeout=1200, kernel_name="python3", resources={"metadata": {"path": tmp}}).execute()
    nbf.write(nb, NB_PATH)
    print("wrote", NB_PATH, "cells:", len(nb.cells))


if __name__ == "__main__":
    sys.exit(main())
