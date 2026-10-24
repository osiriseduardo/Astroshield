# Entregable 4 — Análisis de resultados

Las respuestas se apoyan en los resultados reales del programa (`outputs/resultados.json` y `docs/03_pruebas_validacion.md`).

## 1. ¿Qué tan bien se observan las regiones en la configuración final?

En la solución de referencia (semilla 0, escenario completo) **las 6 regiones están cubiertas al 100 %** de sus puntos
de muestra:

| Región | Prioridad | Cobertura | Redundancia | Resolución | Satélites (altitud) |
|---|---|---|---|---|---|
| Península de Yucatán | Alta | 100 % | 100 % | 0.990 | S3 (515 km) + S5 (1445 km) |
| Amazonía brasileña | Alta | 100 % | 100 % | 0.990 | S6 (516 km) + S1 (1537 km) |
| California | Media | 100 % | 0 % | 0.989 | S0 (516 km) |
| Sahel | Media | 100 % | 0 % | 0.987 | S4 (519 km) |
| Japón | Media | 100 % | 0 % | 0.989 | S7 (516 km) |
| Interior de Australia | Normal | 100 % | 0 % | 0.968 | S2 (548 km) |

El fitness es 0.9174, el 99.94 % de la cota de referencia (0.9179). La diferencia restante (0.0005) se debe a que
algunas altitudes quedaron unos kilómetros por encima de 513 km (Australia está a 548 km). La solución cumple los cuatro
criterios de aceptación.

## 2. ¿Cómo cambió la calidad durante la evolución?

Se distinguen tres fases (`fig_e2_evolucion.png`):

1. **Descubrimiento (gen 0–15):** el fitness sube de 0.21 a ≈ 0.7. La selección y el cruce juntan los satélites que
   por azar quedaron cerca de alguna región, y en la generación 14 las 6 regiones ya están cubiertas.
2. **Organización (gen 15–100):** la diversidad cae de 47° a ≈ 7–10°. Los satélites sobrantes se reubican como
   redundancia y las altitudes empiezan a bajar (fitness 0.87).
3. **Ajuste fino (gen 100–400):** σ baja de 3° a 0.05°. El AG centra cada satélite sobre su región y baja la altitud
   hasta ≈ 515 km. El fitness sube de 0.87 a 0.917, una mejora pequeña pero constante.

La media de la población queda por debajo del mejor porque la mutación sigue generando hijos peores cada generación.
Esa brecha es la exploración que se mantiene viva.

## 3. ¿Qué diferencias hay entre ejecuciones?

* **En calidad, poca:** 0.9151 ± 0.0052 (CV 0.57 %) en 10 semillas. Hay 8 ejecuciones en 0.9174–0.9176 (prácticamente
  la cota) y 2 en ≈ 0.905.
* **En geometría, mucha:** dos soluciones difieren en promedio 6.2° (hasta 18.4°). Los 6 satélites "base" casi
  coinciden; lo que cambia es dónde quedan los de redundancia.
* **Las 2 ejecuciones peores** asignan un satélite de redundancia a una región Media (Sahel o Japón) en lugar de la
  segunda Alta. Es un **óptimo local**: corregirlo exige trasladar un satélite decenas de grados en una sola mutación,
  y cuando eso se vuelve necesario σ ya es pequeño. Una mejora posible sería una mutación de "reasignación" que mueva un
  satélite redundante hacia otra región.

## 4. ¿Qué efecto tuvieron las restricciones espaciales?

* **En el escenario base, casi ninguno en el óptimo:** las zonas están a ≥ 18° de distancia de cualquier satélite final.
  Durante la búsqueda sí actúan: el 21.5 % de la población inicial era inválida y la selección de Deb elimina esas
  configuraciones.
* **Cuando las zonas invaden regiones, tienen un costo claro y medible:**

  | Situación | Fitness | Pérdida frente al base |
  |---|---|---|
  | Base | 0.9174 | — |
  | Objeto A junto al Sahel (E4) | 0.9090 | −0.008 |
  | Zona sobre Yucatán (R1) | 0.8920 | −0.025 |
  | + techo de 1200 km (R2) | 0.8742 | −0.043 |
  | + zona sobre Japón (R3) | 0.8697 | −0.048 |

  El mecanismo siempre es el mismo: el satélite se coloca **en el borde** de la zona y sube de altitud para alcanzar la
  región desde fuera. Se conserva la cobertura y se pierde resolución.
* **Sin manejo de restricciones** (E5), el AG mete satélites en la zona del Golfo y obtiene un puntaje mayor (0.9174)
  que es inválido. **Un puntaje alto no significa una solución válida.**

## 5. ¿Qué pasa cuando no se pueden satisfacer todas las condiciones?

Distinguimos tres situaciones, cada una con su respuesta (E6):

* **Objetivo inalcanzable (I1):** la solución es válida, pero se pierde la región imposible (Amazonía al 0 %) y se informa.
* **Recursos insuficientes (I2):** se pierde la región de **menor prioridad** (Australia). Las prioridades deciden el sacrificio.
* **Restricciones contradictorias (I3):** no existe ninguna solución válida. Se devuelve la menos mala, marcada como
  inválida (`factible = False`), y en el historial la mejor válida queda vacía (NaN). El sistema **nunca** presenta
  como solución algo que viola restricciones.

## 6. Limitaciones del criterio de evaluación

1. **Modelo estático:** los satélites no orbitan. No hay tiempo de revisita, eclipses ni cobertura intermitente. En la
   realidad, un satélite en LEO no puede quedarse fijo sobre un punto.
2. **Resolución lineal en la altitud:** la calidad real de la imagen también depende del ángulo de visión (la
   resolución empeora hacia el borde de la huella) y del sensor.
3. **Pesos elegidos por diseño:** 0.70 / 0.15 / 0.15 y 3 / 2 / 1. Otros pesos cambian la solución. E8 justifica
   empíricamente el término de redundancia, pero no los valores exactos.
4. **Muestreo discreto:** 49 puntos aproximan el área. Un hueco más pequeño que la separación entre anillos (100 km)
   podría pasar desapercibido.
5. **"Cubierta" es binaria al 95 %:** una región al 94 % cuenta como "no cubierta", aunque el fitness sí refleja
   el 94 %.
6. **La cota de referencia es una relajación:** solo vale como cota superior porque ninguna huella (máx. 11°) alcanza
   dos regiones a la vez (la separación mínima entre regiones es de ≈ 30°). Con regiones más cercanas habría que
   recalcularla.
7. **Las zonas se tratan como conos a toda altitud:** es conservador. Un modelo con altitud de las zonas permitiría
   más soluciones.

## 7. ¿Qué evidencia permite afirmar que una solución es mejor que otra?

Una sola cifra no basta. Usamos cinco criterios, en este orden:

1. **Validez primero:** una solución inválida nunca es mejor que una válida, sin importar su puntaje (reglas de Deb, E5).
2. **Criterios de aceptación explícitos** (C1–C4), verificables y no subjetivos.
3. **Distancia a la cota de referencia:** dice cuánto margen de mejora queda. El AG llega al 99.7 % de media.
4. **Comparación estadística con el mismo presupuesto:** AG 0.9151 frente a búsqueda aleatoria 0.4232
   (Mann-Whitney p = 8 × 10⁻⁵) y frente a una heurística voraz con conocimiento del dominio (0.9142).
5. **Métricas fuera del fitness:** la robustez N-1 (E8) muestra que la solución con redundancia es mejor también en
   tolerancia a fallas, algo que el fitness no mide directamente.

## 8. Calibración de parámetros (registro)

Escenario base, 4 semillas por variante. Se hizo durante el desarrollo y llevó a los valores finales:

| Variante | Fitness medio | Mín. | Máx. |
|---|---|---|---|
| Inicial (250 gen, torneo 3, élite 2, mutación 0.25, σ final 0.3°) | 0.8944 | 0.8893 | 0.8995 |
| 400 generaciones | 0.9080 | 0.9044 | 0.9098 |
| σ final de 0.05° y 2 km | 0.8961 | 0.8870 | 0.9014 |
| 400 gen + σ fino | 0.9085 | 0.9049 | 0.9122 |
| 400 gen + σ fino + élite 4 + torneo 4 | 0.9152 | 0.9135 | 0.9168 |
| **Final:** lo anterior + mutación 0.15 | **0.9175** | 0.9174 | 0.9176 |

**Conclusión de la calibración:** el factor dominante es tener suficiente tiempo de ajuste fino (más generaciones y σ
final pequeño). La mayor presión selectiva y la menor tasa de mutación permiten aprovecharlo. Con 10 semillas, la
configuración final da 0.9151 ± 0.0052 (E7), algo menos que en la calibración, porque aparecen 2 óptimos locales que
las 4 semillas de calibración no mostraron.
