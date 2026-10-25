"""Algoritmo genético con codificación real para el problema de la constelación.

Genoma: arreglo (n_satelites, 3) con (lat, lon, alt_km).

Ciclo por generación:
  1. ordenar la población (manejo de restricciones: reglas de factibilidad de Deb por defecto)
  2. elitismo: copiar sin cambios a los mejores `tam_elite` individuos
  3. selección de padres por torneo
  4. cruce alineado: los satélites del padre B se emparejan con los del padre A
     con el algoritmo húngaro antes de mezclarlos, porque el orden de los
     satélites en el genoma es arbitrario (simetría de permutación)
  5. mutación: paso gaussiano sobre la esfera + ajuste de altitud, ambos con
     sigma que decae exponencialmente; una reubicación aleatoria poco frecuente
     mantiene la exploración
  6. reparación (probabilística): los satélites dentro de una zona prohibida
     se empujan hasta su borde por el gran círculo desde el centro de la zona
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Callable, List, Optional

import numpy as np
from scipy.optimize import linear_sum_assignment

from .escenario import Escenario
from .evaluacion import Evaluacion, Evaluador
from .geometria import a_unitario, desde_unitario, destino, distancia_angular, paso_gaussiano, puntos_aleatorios, rumbo_inicial

MODOS_RESTRICCION = ("deb", "penalizacion", "ninguno")


# Configuración del algoritmo genético.
# Permite ajustar el tamaño de la población, las generaciones,
# la selección, el cruce, la mutación y el manejo de restricciones.
@dataclass
class ParametrosAG:
    tam_poblacion: int = 120
    generaciones: int = 400
    tam_torneo: int = 4
    prob_cruce: float = 0.9
    prob_mezcla: float = 0.3  # probabilidad por satélite de cruce aritmético (en vez de intercambio)
    cruce_alineado: bool = True  # emparejar satélites antes del cruce
    prob_mutacion: float = 0.15  # por satélite
    sigma_inicial_grados: float = 12.0
    sigma_final_grados: float = 0.05
    sigma_alt_inicial_km: float = 250.0
    sigma_alt_final_km: float = 2.0
    prob_reubicacion: float = 0.02  # reubicación aleatoria por satélite
    prob_reparacion: float = 0.3  # probabilidad por hijo de aplicar la reparación
    tam_elite: int = 4
    manejo_restricciones: str = "deb"  # "deb" | "penalizacion" | "ninguno"
    factor_penalizacion: float = 0.05  # fitness perdido por grado de intrusión
    paciencia: Optional[int] = None  # parar tras N generaciones sin mejora

    def __post_init__(self):
        if self.manejo_restricciones not in MODOS_RESTRICCION:
            raise ValueError(f"manejo_restricciones debe ser uno de {MODOS_RESTRICCION}")
        if not 0 <= self.tam_elite < self.tam_poblacion:
            raise ValueError("tam_elite debe ser menor que tam_poblacion")

    def a_dict(self):
        return asdict(self)


@dataclass
class ResultadoAG:
    escenario: Escenario
    parametros: ParametrosAG
    semilla: int
    mejor: np.ndarray
    eval_mejor: Evaluacion
    mejor_inicial: np.ndarray
    eval_inicial: Evaluacion
    historial: List[dict]
    poblacion_final: np.ndarray
    evaluaciones: int
    tiempo_s: float
    motivo_parada: str
    # generación -> mejor configuración, guardada en la generación 0 y en cada mejora
    instantaneas: dict = field(default_factory=dict)

    @property
    def encontro_factible(self) -> bool:
        return self.eval_mejor.factible

    def tabla_historial(self):
        import pandas as pd

        return pd.DataFrame(self.historial)


# ---------------------------------------------------------------- operadores
def poblacion_aleatoria(rng, escenario: Escenario, n: int) -> np.ndarray:
    s = escenario.n_satelites
    lat, lon = puntos_aleatorios(rng, n * s)
    alt = rng.uniform(escenario.alt_min_km, escenario.alt_max_km, n * s)
    return np.stack([lat, lon, alt], axis=-1).reshape(n, s, 3)


def valores_rango(lote: dict, modo: str, penalizacion: float) -> np.ndarray:
    """Mayor es mejor. Deb: cualquier factible le gana a cualquier infactible; las
    infactibles se ordenan por su violación total."""
    f, v = lote["fitness"], lote["violacion"]
    if modo == "ninguno":
        return f.copy()
    if modo == "penalizacion":
        return f - penalizacion * v
    return np.where(lote["factible"], f, -1.0 - v)


def alinear(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Reordena los satélites de b para que b[i] sea el más cercano a a[i]."""
    costo = distancia_angular(a[:, None, 0], a[:, None, 1], b[None, :, 0], b[None, :, 1])
    _, columnas = linear_sum_assignment(costo)
    return b[columnas]


def cruzar(rng, a, b, prob_mezcla, alineado=True):
    if alineado:
        b = alinear(a, b)
    s = len(a)
    h1, h2 = a.copy(), b.copy()
    intercambio = rng.random(s) < 0.5
    h1[intercambio], h2[intercambio] = b[intercambio], a[intercambio]
    mezcla = rng.random(s) < prob_mezcla
    if mezcla.any():
        w = rng.random(mezcla.sum())[:, None]
        ua, ub = a_unitario(a[mezcla, 0], a[mezcla, 1]), a_unitario(b[mezcla, 0], b[mezcla, 1])
        for hijo, ww in ((h1, w), (h2, 1 - w)):
            v = ww * ua + (1 - ww) * ub
            ok = np.linalg.norm(v, axis=1) > 1e-6  # omite pares antipodales
            lat, lon = desde_unitario(np.where(ok[:, None], v, ua))
            idx = np.flatnonzero(mezcla)
            hijo[idx, 0], hijo[idx, 1] = lat, lon
            hijo[idx, 2] = ww[:, 0] * a[mezcla, 2] + (1 - ww[:, 0]) * b[mezcla, 2]
    return h1, h2


def reflejar_altitud(alt, minimo, maximo):
    rango = maximo - minimo
    x = np.mod(alt - minimo, 2 * rango)
    return minimo + np.where(x > rango, 2 * rango - x, x)


def mutar(rng, individuo, escenario, prob, sigma_grados, sigma_alt, prob_reubicacion):
    s = len(individuo)
    m = rng.random(s) < prob
    if m.any():
        lat, lon = paso_gaussiano(rng, individuo[m, 0], individuo[m, 1], sigma_grados)
        individuo[m, 0], individuo[m, 1] = lat, lon
        individuo[m, 2] = reflejar_altitud(
            individuo[m, 2] + rng.normal(0, sigma_alt, m.sum()), escenario.alt_min_km, escenario.alt_max_km
        )
    r = rng.random(s) < prob_reubicacion
    if r.any():
        lat, lon = puntos_aleatorios(rng, r.sum())
        individuo[r, 0], individuo[r, 1] = lat, lon
        individuo[r, 2] = rng.uniform(escenario.alt_min_km, escenario.alt_max_km, r.sum())
    return individuo


def reparar(rng, individuo, escenario: Escenario, margen_grados=0.25, max_iter=4):
    """Saca a los satélites de las zonas prohibidas (en el mismo arreglo). Las zonas
    pueden traslaparse, así que el empuje se repite unas veces; lo que quede lo
    resuelve la selección."""
    for _ in range(max_iter):
        movido = False
        for z in escenario.zonas:
            d = distancia_angular(individuo[:, 0], individuo[:, 1], z.lat, z.lon)
            malos = np.flatnonzero(d < z.radio_grados)
            for i in malos:
                if d[i] < 1e-6:
                    rumbo = rng.uniform(0, 360)
                else:
                    rumbo = rumbo_inicial(z.lat, z.lon, individuo[i, 0], individuo[i, 1])
                individuo[i, 0], individuo[i, 1] = destino(z.lat, z.lon, rumbo, z.radio_grados + margen_grados)
                movido = True
        if not movido:
            break
    return individuo


def diversidad(rng, poblacion, n_pares=12):
    """Distancia angular media entre los satélites alineados de pares aleatorios."""
    if len(poblacion) < 2:
        return 0.0
    salida = []
    for _ in range(n_pares):
        i, j = rng.choice(len(poblacion), 2, replace=False)
        b = alinear(poblacion[i], poblacion[j])
        salida.append(distancia_angular(poblacion[i][:, 0], poblacion[i][:, 1], b[:, 0], b[:, 1]).mean())
    return float(np.mean(salida))


# ---------------------------------------------------------------- principal
def ejecutar_ag(
    escenario: Escenario,
    parametros: ParametrosAG = None,
    semilla: int = 0,
    poblacion_inicial: np.ndarray = None,
    al_registrar: Callable[[dict], None] = None,
) -> ResultadoAG:
    """Ejecuta el AG y devuelve la mejor configuración junto con el historial completo."""
    cfg = parametros or ParametrosAG()
    rng = np.random.default_rng(semilla)
    ev = Evaluador(escenario)
    p = cfg.tam_poblacion

    pob = poblacion_aleatoria(rng, escenario, p)
    if poblacion_inicial is not None:  # arranque en caliente (cambio de condiciones)
        semillas = np.asarray(poblacion_inicial, dtype=float)[:p]
        pob[: len(semillas)] = semillas

    t0 = time.perf_counter()
    lote = ev.evaluar_poblacion(pob)
    rango = valores_rango(lote, cfg.manejo_restricciones, cfg.factor_penalizacion)
    i0 = int(np.argmax(rango))
    mejor_inicial = pob[i0].copy()
    mejor, mejor_rango = pob[i0].copy(), rango[i0]
    historial, instantaneas = [], {0: mejor_inicial.copy()}
    sin_mejora, motivo_parada = 0, "generaciones completadas"

    def registrar(gen, sigma, sigma_alt):
        fact = lote["factible"]
        f = lote["fitness"]
        fila = {
            "generacion": gen,
            "mejor_rango": float(rango.max()),
            "fitness_mejor": float(f[fact].max()) if fact.any() else np.nan,
            "fitness_media": float(f.mean()),
            "fitness_desv": float(f.std()),
            "fitness_peor": float(f.min()),
            "fraccion_factible": float(fact.mean()),
            "violacion_media": float(lote["violacion"].mean()),
            "mejor_rango_historico": float(mejor_rango),
            "regiones_cubiertas_mejor": int(
                (lote["cobertura"][int(np.argmax(rango))] >= escenario.umbral_cobertura - 1e-12).sum()
            ),
            "diversidad_grados": diversidad(rng, pob),
            "sigma_grados": float(sigma),
            "sigma_alt_km": float(sigma_alt),
            "evaluaciones": ev.n_evaluaciones,
        }
        historial.append(fila)
        if al_registrar:
            al_registrar(fila)

    registrar(0, cfg.sigma_inicial_grados, cfg.sigma_alt_inicial_km)
    for gen in range(1, cfg.generaciones + 1):
        t = (gen - 1) / max(cfg.generaciones - 1, 1)
        sigma = cfg.sigma_inicial_grados * (cfg.sigma_final_grados / cfg.sigma_inicial_grados) ** t
        sigma_alt = cfg.sigma_alt_inicial_km * (cfg.sigma_alt_final_km / cfg.sigma_alt_inicial_km) ** t

        orden = np.argsort(-rango)
        hijos = [pob[i].copy() for i in orden[: cfg.tam_elite]]
        while len(hijos) < p:
            candidatos = rng.integers(0, p, size=(2, cfg.tam_torneo))
            pa, pb = (pob[c[np.argmax(rango[c])]] for c in candidatos)
            if rng.random() < cfg.prob_cruce:
                h1, h2 = cruzar(rng, pa, pb, cfg.prob_mezcla, cfg.cruce_alineado)
            else:
                h1, h2 = pa.copy(), pb.copy()
            for h in (h1, h2):
                mutar(rng, h, escenario, cfg.prob_mutacion, sigma, sigma_alt, cfg.prob_reubicacion)
                if cfg.manejo_restricciones != "ninguno" and rng.random() < cfg.prob_reparacion:
                    reparar(rng, h, escenario)
                hijos.append(h)
        pob = np.array(hijos[:p])
        lote = ev.evaluar_poblacion(pob)
        rango = valores_rango(lote, cfg.manejo_restricciones, cfg.factor_penalizacion)

        i = int(np.argmax(rango))
        if rango[i] > mejor_rango + 1e-9:
            mejor, mejor_rango, sin_mejora = pob[i].copy(), rango[i], 0
            instantaneas[gen] = mejor.copy()
        else:
            sin_mejora += 1
        registrar(gen, sigma, sigma_alt)
        if cfg.paciencia and sin_mejora >= cfg.paciencia:
            motivo_parada = f"estancamiento ({cfg.paciencia} generaciones sin mejora)"
            break

    instantaneas[historial[-1]["generacion"]] = mejor.copy()
    return ResultadoAG(
        escenario=escenario,
        parametros=cfg,
        semilla=semilla,
        mejor=mejor,
        eval_mejor=ev.evaluar(mejor),
        mejor_inicial=mejor_inicial,
        eval_inicial=ev.evaluar(mejor_inicial),
        historial=historial,
        poblacion_final=pob,
        evaluaciones=ev.n_evaluaciones,
        tiempo_s=time.perf_counter() - t0,
        motivo_parada=motivo_parada,
        instantaneas=instantaneas,
    )
