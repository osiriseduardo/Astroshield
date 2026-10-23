# Guía para la presentación y la revisión

## Demostración en vivo (≈ 8 min)

1. **Abrir el notebook en Colab** y mostrar la tabla de la sección 1: a 500 km la huella mide 293 km y no cubre 300 km.
   Ese es el compromiso entre altitud y resolución.
2. **Sección 3:** la curva de evolución. Señalar las fases de exploración y de ajuste fino, y la cota de referencia
   (línea verde).
3. **Sección 4, el globo 3D:** girarlo, cambiar entre *Inicial (gen 0) → Generación 50 → Final*, activar *Superponer
   otro estado* y pasar el cursor sobre un satélite para ver su altitud y su huella.
4. **Sección 5.3:** R1 sin restricciones da un puntaje alto pero es inválido. "Un puntaje alto no significa una
   solución válida."
5. **Sección 7, el laboratorio:** con la profesora o el profesor, agregar una zona nueva sobre Japón (radio 5°) y
   mostrar que la solución anterior se revalida como **inválida** y que el AG la repara.

## Preguntas probables y respuestas cortas

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Por qué no poner todos los satélites a 2000 km? | Porque la resolución vale el 15 % del score. Además, la huella de 513 km ya basta para cubrir la región. | Doc 01 §4 |
| ¿Cómo sabes que la solución es buena y no solo mejor que la inicial? | La cota de referencia: llegamos al 99.94 %. Y le ganamos a la búsqueda aleatoria con p = 8 × 10⁻⁵. | E2, E7 |
| ¿Por qué Deb y no penalización? | No hay que calibrar un coeficiente y garantiza que una solución inválida nunca gane. En E10 rinden igual, pero con penalización existe el riesgo de aceptar soluciones inválidas si el coeficiente es bajo. | E5, E10 |
| ¿Para qué sirve el cruce alineado? | El orden de los satélites es arbitrario. Sin alinear, se mezclan satélites que observan cosas distintas. | Doc 01 §6 |
| ¿Por qué hay ejecuciones que no se aceptan? | Óptimo local: la redundancia quedó en una región Media. Lo reportamos en vez de esconderlo. | E7 |
| ¿Qué pasa si no hay solución? | Se distinguen 3 casos (objetivo inalcanzable, recursos insuficientes, restricciones contradictorias) y en ninguno se reporta una solución inválida como buena. | E6 |
| ¿El globo muestra los datos reales? | Sí. Se genera con la salida del AG y una celda lo verifica con `assert`. | Notebook §5.7 |
| ¿Qué limitaciones tiene? | Es un modelo estático sin órbitas, la resolución es lineal, los pesos son una decisión de diseño y el muestreo es de 49 puntos. | Doc 04 §6 |

## Recomendación para el historial de Git

El enunciado evalúa que el historial muestre el avance y las aportaciones de cada integrante. Cada integrante debería
hacer commits **propios** sobre la parte que le toca: revisar o ajustar un módulo, agregar una prueba, mejorar una
explicación o correr un experimento con otros parámetros. Usen mensajes descriptivos como los del historial actual
(`feat:`, `test:`, `docs:`, `fix:`).
