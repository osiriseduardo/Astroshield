# Entregable 3 — Pruebas y validación

Todos los valores salen de la ejecución de referencia `python tools/run_experiments.py`, que produce
`outputs/results.json`, los CSV y las figuras `outputs/fig_*.png`. Se usaron los parámetros finales (población 120,
400 generaciones) y la semilla 0, salvo que se indique otra cosa. El notebook vuelve a ejecutar cada prueba.

Además hay **36 pruebas unitarias automatizadas** (`pytest`, en `tests/`). Todas pasan.

---

## E1 — Escenario inicial (etapa 1, sin restricciones espaciales)

* **Condiciones:** 6 regiones, sin zonas, separación mínima de 2°, semilla 0.
* **Resultados:** el fitness pasa de 0.2696 (el mejor aleatorio) a **0.9054**. Las 6/6 regiones quedan cubiertas desde
  la generación 11 y la solución es válida. No cumple C3: en esta semilla la redundancia quedó en una sola región Alta.
* **Interpretación:** el AG encuentra por sí solo dónde están las regiones y les asigna un satélite a cada una. La
  falla en C3 muestra que el criterio de aceptación es más exigente que "cubrir todo", y que una sola ejecución no basta
  para juzgar el método (ver E7). Figura: `fig_e1_mapa.png`.

## E2 — Evolución (etapa 2, escenario completo)

* **Condiciones:** las 6 regiones, las 3 zonas de desechos, los 2 objetos ocupados y la semilla 0.
* **Resultados:**

  | Generación | 0 | 10 | 30 | 50 | 100 | 200 | 399 |
  |---|---|---|---|---|---|---|---|
  | Mejor fitness válido | 0.210 | 0.671 | 0.826 | 0.841 | 0.866 | 0.896 | **0.9174** |
  | Diversidad (°) | 46.6 | 25.5 | 6.8 | 10.9 | 9.5 | 6.0 | 2.1 |
  | σ de mutación (°) | 12.0 | 10.6 | 8.1 | 6.1 | 3.1 | 0.78 | 0.05 |

  Las 6 regiones quedan cubiertas desde la generación 14, y en la 314 ya se tiene el 99 % del valor final. El resultado
  es el **99.94 % de la cota de referencia** (0.9179) y se **acepta** (C1–C4).
* **Interpretación:** hay una mejora rápida en la fase de exploración y luego una mejora lenta por ajuste fino de
  altitud y posición. Los 2 satélites sobrantes terminan como redundancia de Yucatán y de la Amazonía (las dos regiones
  Alta), a 1445 y 1537 km. Figuras: `fig_e2_evolucion.png`, `fig_e2_regiones.png`, `fig_e2_mapa.png`.
  Historial completo: `history_base_seed0.csv`.

## E3 — Zonas restringidas por desechos

* **Condiciones:** auditoría geométrica, independiente del AG, de la mejor solución de las 10 semillas de E7.
* **Resultados:** **0 violaciones en 10/10 ejecuciones.** Margen mínimo: Atlántico Norte 30.0°, Pacífico Sur 45.6° y
  Polar Norte 50.5°. En la población aleatoria inicial el 21.5 % de las configuraciones era inválida, y en la
  población final queda el 99.75 % de válidas. Además, cada zona tiene una prueba unitaria que coloca un satélite
  dentro y verifica que se detecte (`test_satellite_inside_each_zone_is_invalid`).
* **Interpretación:** las restricciones se cumplen. **Limitación honesta:** en el escenario base las zonas están lejos de
  las regiones, así que en el óptimo no están activas. Por eso E4-estrés, E5 y E6 las ponen encima de las regiones.
  Datos: `e3_e4_auditoria.csv`.

## E4 — Posiciones ocupadas

* **Condiciones:** (a) la misma auditoría para el Objeto A y el Objeto B; (b) **estrés**: el Objeto A se reubica en
  (15°, 2°), a 2° del centro del Sahel, de modo que su exclusión de 5° invade la región.
* **Resultados:** (a) 0 violaciones; margen mínimo de 36.4° (A) y 18.5° (B). (b) La solución es válida, el Sahel sigue
  cubierto al 100 %, pero su satélite queda **justo en el borde** de la exclusión (margen 0.00°) y sube de 519 a 1077 km.
  La resolución de la región baja a 0.615 y el fitness pasa de 0.9174 a **0.9090**.
* **Interpretación:** el sistema evita las exclusiones aunque estén encima de una región y encuentra la forma de seguir
  observándola desde fuera. La restricción tiene un costo medible en resolución. Figura: `fig_e4_objeto_sahel.png`.

## E5 — Espacio reducido

* **Condiciones:** 4 niveles acumulativos, y R1 repetido **sin** manejo de restricciones.

  | Nivel | Cambio | Fitness | Regiones | ¿Válida? |
  |---|---|---|---|---|
  | R0 | base | 0.9174 | 6/6 | sí |
  | R1 | + zona de 6° en (23°, −90°), a 2.6° de Yucatán | 0.8920 | 6/6 | sí |
  | R2 | + techo de altitud de 1200 km | 0.8742 | 6/6 | sí |
  | R3 | + zona de 5° en (40°, 140°), a 4.3° de Japón | 0.8697 | 6/6 | sí |
  | R1 sin restricciones | `constraint_handling="none"` | 0.9174 | 6/6 | **no**: S0 y S4 dentro de la zona del Golfo, más 2 pares a menos de 2° |

* **Interpretación:** al reducir el espacio el fitness baja de forma monótona, pero la cobertura se mantiene. El AG paga
  con resolución y redundancia, no con regiones. Sin manejo de restricciones se obtiene un puntaje mayor (0.9174) que es
  **inválido**, justo el caso que advierte el enunciado. Figuras: `fig_e5_regiones.png`, `fig_e5_R3.png`.

## E6 — Condiciones difíciles o inviables

| Caso | Condiciones | Resultado | Interpretación |
|---|---|---|---|
| I1 | Zona de 15° centrada en la Amazonía | Válida, fitness 0.7334, **Amazonía al 0 %**, 5/6 regiones | La región es inalcanzable: la huella máxima es de 11° y la zona mide 15°. El sistema lo reporta (C2 = falso) en vez de violar la zona. |
| I2 | Solo 5 satélites | Válida, fitness 0.7668, **Australia al 0 %** | Con recursos insuficientes se sacrifica la única región Normal: las prioridades funcionan. |
| I3 | Separación mínima de 80° | **Inválida**, 13 violaciones, 65.0° de intrusión, fitness válido = ninguno | No existe solución: el problema de Tammes da un máximo de ≈ 74.9° para 8 puntos. El AG devuelve la configuración que menos viola y la marca como `feasible = False`. |

Figuras: `fig_e6_5sats.png` y `fig_e6_inviable.png` (la fracción válida se queda en 0 toda la ejecución).

## E7 — Variación entre ejecuciones

* **Condiciones:** 10 semillas (0–9), los mismos parámetros y el mismo presupuesto (48 122 evaluaciones) para el AG y la
  búsqueda aleatoria.
* **Resultados:**

  | Método | Media | Desv. est. | Mín. | Máx. |
  |---|---|---|---|---|
  | **AG** | **0.9151** | 0.0052 | 0.9046 | 0.9176 |
  | Búsqueda aleatoria | 0.4232 | — | — | 0.4567 |
  | Heurística voraz (determinista) | 0.9142 | — | — | — |
  | Cota de referencia | 0.9179 | — | — | — |

  * Las 10/10 ejecuciones son válidas y cubren 6/6 regiones; 8/10 se aceptan. Las semillas 4 y 5 fallan solo en C3
    porque pusieron la redundancia en Sahel o Japón (Media) en lugar de la segunda Alta.
  * Mann-Whitney unilateral (AG > aleatoria): p = 8.1 × 10⁻⁵.
  * Coeficiente de variación: 0.57 %. Distancia media entre las soluciones de dos semillas: 6.2° (máx. 18.4°).
* **Interpretación:** el resultado es estable en calidad pero **no** en geometría, porque el paisaje es multimodal. Las
  dos ejecuciones no aceptadas muestran un óptimo local reproducible. Figuras: `fig_e7_convergencia.png`,
  `fig_e7_comparacion.png`.

## E8 — Prueba propia: robustez ante la falla de un satélite (N-1)

* **Pregunta:** ¿el término de redundancia aporta algo real o solo sube el puntaje?
* **Condiciones:** se simula la falla de cada uno de los 8 satélites, (a) en la solución base y (b) en una solución
  optimizada sin término de redundancia (pesos 0.80 / 0 / 0.20). Ambas se evalúan con el fitness original.
* **Resultados:**

  | | Fallas sin pérdida de regiones | Fitness medio tras una falla | Peor caso |
  |---|---|---|---|
  | Con redundancia | **4 / 8** | **0.8374** | pierde una región Media o Normal |
  | Sin redundancia | 2 / 8 | 0.7424 | **pierde una región Alta** (Yucatán o Amazonía) |

* **Interpretación:** el término de redundancia hace que la constelación sea tolerante a fallas justo donde más importa.
  Es una justificación empírica de un peso del fitness.

## E9 — Cambio de condiciones (sección 3.3)

| Cambio | ¿La solución anterior sigue siendo válida? | Re-optimización |
|---|---|---|
| Australia pasa a Alta | **Sí** (la geometría no cambia). El fitness baja de 0.9174 a 0.9078 porque cambian los pesos. | Warm start: 0.9086 (cota 0.9087). |
| Nueva zona de 3° sobre el satélite de Japón | **No**: S7 queda en la zona nueva (0.00° < 3°), aunque su fitness siga en 0.9174. | Warm start: **0.9092** en 26 generaciones. Desde cero, con el mismo presupuesto: 0.8820 en 96 generaciones. |

**Interpretación:** el puntaje y la validez son cosas distintas, así que hay que **revalidar** siempre que cambien las
condiciones (`experiments.revalidate`). Reutilizar la población anterior es más rápido y da mejores resultados.
Figura: `fig_e9_reoptimizacion.png`.

## E10 — Ablación de operadores

* **Condiciones:** escenario R1, 5 semillas por variante.

  | Variante | Fitness medio | Desv. est. | Gen. al 99 % |
  |---|---|---|---|
  | Configuración final | 0.8963 | 0.0059 | 197 |
  | Sin alineación en el cruce | 0.8953 | 0.0052 | 188 |
  | Sin reparación | 0.8939 | 0.0054 | 217 |
  | Sin elitismo | 0.8969 | 0.0056 | 260 |
  | Mutación alta (0.5) | **0.8892** | 0.0072 | 304 |
  | Penalización en vez de Deb | 0.8964 | 0.0065 | 201 |
  | Población de 40 | **0.8894** | 0.0014 | 226 |

* **Interpretación:** la mutación alta y la población pequeña empeoran claramente el resultado (≈ −0.007, más que una
  desviación estándar). Sin reparación se converge más lento. **Las demás diferencias son menores que la desviación
  estándar y no son concluyentes con 5 semillas**, así que no afirmamos que esos operadores mejoren el fitness final.
  Hay un detalle sobre "sin elitismo": el AG sigue guardando la mejor solución encontrada, así que solo cambia la
  dinámica de la población (converge más lento, en la generación 260 frente a la 197).

## Pruebas unitarias (`tests/`)

| Archivo | Qué verifica |
|---|---|
| `test_model.py` | haversine con valores conocidos, destino y rumbo, muestreo de la región, huella monótona en la altitud, que 500 km no cubra 300 km, cobertura total con un satélite encima, coincidencia entre la evaluación por lotes y la individual, que **cada una de las 5 zonas** se detecte, el borde de una zona, la separación, que una zona nueva invalide una configuración, la cota y el criterio C3 adaptativo |
| `test_ga.py` | que el AG mejore, que la curva sea monótona (elitismo), que la solución final respete cada zona, los límites de altitud, la reproducibilidad por semilla, que el caso inviable se reporte, la región inalcanzable, el warm start, que el AG le gane a la búsqueda aleatoria, la cota, la reparación, la alineación y la reflexión de altitud |
| `test_viz.py` | que las etiquetas del globo usen texto HTML y conserven los acentos (Península de Yucatán, Amazonía, Japón) |
