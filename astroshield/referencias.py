"""Métodos de referencia para demostrar que el AG es mejor que alternativas triviales."""
from __future__ import annotations

import numpy as np

from .algoritmo_genetico import poblacion_aleatoria, valores_rango
from .escenario import Escenario
from .evaluacion import Evaluador
from .geometria import destino


def busqueda_aleatoria(escenario: Escenario, n_evaluaciones: int, semilla: int = 0, lote: int = 2000):
    """La mejor de `n_evaluaciones` configuraciones aleatorias uniformes (orden de Deb).
    Devuelve (mejor_configuracion, curva_del_mejor_fitness_hasta_el_momento)."""
    rng = np.random.default_rng(semilla)
    ev = Evaluador(escenario)
    mejor, mejor_rango, curva = None, -np.inf, []
    hechas = 0
    while hechas < n_evaluaciones:
        n = min(lote, n_evaluaciones - hechas)
        pob = poblacion_aleatoria(rng, escenario, n)
        b = ev.evaluar_poblacion(pob)
        r = valores_rango(b, "deb", 0.0)
        i = int(np.argmax(r))
        if r[i] > mejor_rango:
            mejor, mejor_rango = pob[i].copy(), r[i]
        hechas += n
        curva.append((hechas, float(mejor_rango)))
    return mejor, curva


def colocacion_voraz(escenario: Escenario, paso_alt_km: float = 50.0):
    """Heurística constructiva: agrega satélites uno por uno, eligiendo cada vez el
    candidato factible (alrededor de los centros de las regiones x rejilla de
    altitudes) con la mayor ganancia de fitness. Imita lo que haría un diseñador."""
    ev = Evaluador(escenario)
    alts = np.arange(escenario.alt_min_km, escenario.alt_max_km + 1e-9, paso_alt_km)
    candidatos = []
    for r in escenario.regiones:
        puntos = [(r.lat, r.lon)]
        for dist in (1.0, 2.0, 3.5, 5.0, 7.0):
            rumbos = np.arange(0, 360, 45.0)
            la, lo = destino(r.lat, r.lon, rumbos, dist)
            puntos.extend(zip(la, lo))
        for la, lo in puntos:
            for h in alts:
                candidatos.append((la, lo, h))
    candidatos = np.array(candidatos)

    elegidos = np.zeros((0, 3))
    for _ in range(escenario.n_satelites):
        pob = np.concatenate(
            [np.repeat(elegidos[None], len(candidatos), axis=0), candidatos[:, None, :]], axis=1
        )
        sc_parcial = escenario.con_parametros(n_satelites=pob.shape[1])
        parcial = Evaluador(sc_parcial)
        b = parcial.evaluar_poblacion(pob)
        r = valores_rango(b, "deb", 0.0)
        elegidos = pob[int(np.argmax(r))]
    return elegidos, ev.evaluar(elegidos)
