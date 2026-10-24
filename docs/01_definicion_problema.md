# Entregable 1 — Definición del problema

Este documento convierte el escenario de AstroShield en un problema de optimización que se puede resolver con un
algoritmo evolutivo. Cada decisión que **no** viene dada por el enunciado está marcada con **[D]** y justificada.

## 1. Supuestos del modelo

| Supuesto | Justificación |
|---|---|
| La Tierra es una esfera de radio R = 6371 km. | El enunciado expresa las zonas en grados angulares "sobre el modelo esférico". |
| **[D]** Cada satélite se mantiene fijo sobre un punto de la superficie (*station-keeping*). Se describe por su punto subsatelital y su altitud. | El enunciado permite no reproducir la mecánica orbital real. Una posición fija hace que la cobertura sea una propiedad geométrica, fácil de verificar y de visualizar. |
| **[D]** La altitud permitida va de 500 a 2000 km (órbita baja). | Es el rango típico de observación terrestre. Por debajo de 500 km la huella ya no alcanza a cubrir 300 km. |
| **[D]** Cada satélite lleva un sensor que apunta al nadir con semiángulo de visión η = 30°. | Introduce el compromiso entre altitud y resolución: subir el satélite agranda la huella pero empeora el detalle. Sin ese compromiso, la solución trivial sería poner todos los satélites a 2000 km. |
| Las zonas de desechos y de exclusión son **casquetes esféricos** (centro y radio angular) que aplican a **cualquier altitud**, es decir, conos desde el centro de la Tierra. | Es la interpretación conservadora de "no se permite colocar satélites en esa región": la prohibición no depende de la altitud. |
| **[D]** Dos satélites propios deben estar separados al menos 2° (≈ 222 km). | Evita colisiones y soluciones degeneradas con satélites apilados. Con 2° todavía es posible tener redundancia sobre una misma región. |

## 2. Representación de una configuración

Una configuración es una matriz de **8 × 3 números reales**, es decir, 24 genes:

```
[[lat_0, lon_0, alt_0],      lat ∈ [-90, 90]°, lon ∈ [-180, 180)°, alt ∈ [500, 2000] km
 [lat_1, lon_1, alt_1],
 ...
 [lat_7, lon_7, alt_7]]
```

* Se eligió una **codificación real** y no binaria porque las variables son continuas y la mutación gaussiana sobre la
  esfera tiene un significado físico directo: "mover el satélite unos grados".
* El orden de los satélites no importa, porque la misma constelación tiene 8! codificaciones posibles. Esa **simetría
  de permutación** se resuelve en el cruce (ver la sección 5).
* Los límites se mantienen por construcción: la latitud y la longitud se calculan con trigonometría esférica, siempre
  válida, y la altitud se refleja en los bordes del intervalo.

## 3. ¿Cuándo está cubierta una región?

1. **Huella del sensor.** Un satélite a altitud *h* ve un casquete de ángulo central

   λ(h) = arcsin( (R + h)/R · sin η ) − η

   (si el sensor viera más allá del horizonte, se limita a arccos(R/(R+h))). Así quedan 293 km de radio a 500 km,
   594 km a 1000 km y 1231 km a 2000 km.
2. **Región discretizada.** Cada región es un disco de 300 km alrededor de su centro, representado por **49 puntos de
   muestra**: el centro y anillos a 100, 200 y 300 km con 8, 16 y 24 puntos. El anillo exterior está justo en el
   borde, así que cubrir la región exige cubrir también su borde.
3. **Punto visto.** Un punto está visto por un satélite si su distancia angular al punto subsatelital es ≤ λ(h).
4. **Métricas por región:**
   * **cobertura** = fracción de puntos vistos por ≥ 1 satélite;
   * **redundancia** = fracción de puntos vistos por ≥ 2 satélites, que mide la tolerancia a fallas;
   * **resolución** = promedio, sobre los puntos, de la mejor calidad `q = 1 − (h − 500)/1500` entre los satélites
     que ven el punto (0 si nadie lo ve).
5. **[D] Región cubierta ⇔ cobertura ≥ 95 %.** Se exige casi toda la región y se tolera que un punto aislado del
   borde quede fuera por la discretización.

## 4. Evaluación de la calidad (fitness)

Para cada región *r*:

score_r = 0.70 · cobertura_r + 0.15 · redundancia_r + 0.15 · resolución_r

fitness = Σ_r w_r · score_r / Σ_r w_r  ∈ [0, 1]

* **Prioridades → pesos [D]:** Alta = 3, Media = 2, Normal = 1. Con esto, perder una región Alta cuesta tres veces más
  que perder una Normal, y cuando los recursos no alcanzan el AG sacrifica primero la de menor prioridad (prueba E6-I2).
* **Por qué 0.70 / 0.15 / 0.15 [D]:** la cobertura es el objetivo principal del enunciado, así que domina. Con estos
  pesos, cubrir completa una región vale más que cualquier combinación de redundancia y resolución (0.70 > 0.30).
  La redundancia le da uso a los 2 satélites sobrantes (8 − 6) y la resolución evita poner todo a la máxima altitud.
* **Cota de referencia:** si se relaja el problema (sin zonas, cada región con su satélite sobre el centro a la altitud
  mínima que la cubre, 513 km, y los 2 sobrantes como redundancia en las regiones de mayor peso), se obtiene
  **0.9179**. Ningún término puede superar ese valor, así que sirve para medir *qué tan cerca del óptimo* estamos.

## 5. Configuraciones inválidas y manejo de restricciones

Una configuración es **inválida** si ocurre cualquiera de estas condiciones:

| Restricción | Condición de violación | Magnitud (grados de intrusión) |
|---|---|---|
| 3 zonas de desechos (Atlántico Norte, Pacífico Sur, Polar Norte) | distancia(satélite, centro) < radio | radio − distancia |
| 2 posiciones ocupadas (Objeto A, Objeto B), con radio de 5° | igual | igual |
| Separación mínima propia | distancia(sat_i, sat_j) < 2° | 2° − distancia |

La **violación total** es la suma de las intrusiones, y una configuración es válida si esa suma es 0.

**Estrategia [D]: reglas de factibilidad de Deb + reparación.**

1. En la selección y el elitismo, **toda configuración válida le gana a cualquier inválida**. Entre dos válidas gana
   la de mayor fitness, y entre dos inválidas, la de menor violación. Esto garantiza que una solución inválida nunca
   se reporte como la mejor si existe alguna válida, sin tener que calibrar un coeficiente de penalización.
2. A un 30 % de los hijos se les aplica **reparación**: cada satélite dentro de una zona se empuja por el gran círculo
   hasta el borde de la zona (+0.25°).
3. Si **no existe** ninguna configuración válida, el AG devuelve la que menos viola y lo informa (`factible = False`).
   Nunca la presenta como solución.

Se comparó contra la penalización estática (fitness − 0.05·violación) y contra no manejar restricciones (pruebas E5 y E10).

## 6. Estrategia evolutiva

Es un algoritmo genético generacional con codificación real:

| Paso | Operador | Por qué |
|---|---|---|
| Inicialización | 120 configuraciones uniformes sobre la esfera, con altitud uniforme | No se le da al AG ninguna pista de dónde están las regiones. |
| Selección | Torneo de tamaño 4 con el orden de Deb | Presión selectiva ajustable y sin escalar el fitness. |
| Cruce (p = 0.9) | **Cruce alineado**: con el algoritmo húngaro se empareja cada satélite del padre B con el más cercano del padre A y luego (a) se intercambian satélites completos al azar y (b) a un 30 % se les aplica un promedio esférico ponderado | Sin alinear, mezclar el "satélite 3" de dos padres combina satélites que observan cosas distintas, y la simetría de permutación destruye a los buenos bloques. |
| Mutación | Por satélite con p = 0.15: un paso gaussiano sobre la esfera con σ que decae de 12° a 0.05°, más un ajuste de altitud con σ de 250 km a 2 km. Además, con p = 0.02, reubicación aleatoria | Al principio explora y al final ajusta con precisión. La reubicación evita el estancamiento. |
| Reparación | p = 0.3 por hijo (ver la sección 5) | Acelera la llegada a la región válida. |
| Reemplazo | Generacional con **elitismo de 4** | El mejor nunca se pierde, así que la curva del mejor es monótona. |

## 7. Parámetros y cómo se fijaron

| Parámetro | Valor | Origen |
|---|---|---|
| Población | 120 | Valor típico de 5 × el número de genes (24). En E10, con 40 el resultado empeora. |
| Generaciones | 400 | Calibración (4 semillas): con 250 el fitness medio era 0.894 y con 400, 0.908. |
| Torneo / élite | 4 / 4 | Calibración (4 semillas): más presión selectiva mejoró el ajuste fino. |
| p cruce / p mezcla | 0.9 / 0.3 | Valores estándar en AG reales. |
| p mutación por satélite | 0.15 | ≈ 1.2 satélites mutados por hijo. En E10, con 0.5 empeora. |
| σ posición / altitud | 12° → 0.05° / 250 → 2 km | El σ inicial es del orden de la distancia entre regiones y el σ final, del orden del ajuste necesario. |
| p reubicación / p reparación | 0.02 / 0.3 | Exploración residual y apoyo a la factibilidad. |
| Semilla | Configurable | Reproducibilidad: misma semilla ⇒ mismo resultado (hay una prueba unitaria para esto). |

Los valores iniciales salieron de reglas generales y luego se ajustaron con una calibración documentada en
`docs/04_analisis_resultados.md`: la combinación final llevó el fitness medio de 0.894 a 0.9175.

## 8. ¿Cuándo es "suficientemente buena" una solución?

Una configuración se **acepta** si cumple todo lo siguiente:

* **C1:** es válida (0 violaciones).
* **C2:** las 6 regiones están cubiertas (cobertura ≥ 95 %).
* **C3:** hay redundancia (≥ 95 %) en tantas regiones Alta como satélites sobrantes haya, es decir, min(#Alta, 8 − 6).
* **C4:** el fitness es ≥ 90 % de la cota de referencia.

El AG se detiene al completar las generaciones configuradas (o por estancamiento, si se activa `paciencia`). **Que el AG
deje de mejorar no prueba que la solución sea óptima**. Por eso se compara contra la cota, contra la búsqueda
aleatoria y contra una heurística voraz, y se analiza la variación entre semillas.
