"""Experimentos reproducibles detrás de los Entregables 3 y 4.

Cada función devuelve datos simples (dicts / DataFrames / ResultadoAG) para que
el notebook los muestre y herramientas/ejecutar_experimentos.py los guarde en JSON.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
from scipy import stats

from .algoritmo_genetico import ParametrosAG, ResultadoAG, alinear, ejecutar_ag
from .escenario import Escenario, Zona, escenario_base, escenario_inicial
from .evaluacion import Evaluador, aceptacion, cota_referencia
from .geometria import distancia_angular
from .referencias import busqueda_aleatoria, colocacion_voraz


# ------------------------------------------------------------------ auxiliares
def generacion_convergencia(resultado: ResultadoAG, fraccion: float = 0.99):
    """Primera generación cuyo mejor valor histórico alcanza `fraccion` del valor final."""
    curva = np.array([h["mejor_rango_historico"] for h in resultado.historial])
    final = curva[-1]
    if final <= 0:
        return None
    return int(np.argmax(curva >= fraccion * final))


def generacion_cobertura_completa(resultado: ResultadoAG):
    n = len(resultado.escenario.regiones)
    for h in resultado.historial:
        if h["regiones_cubiertas_mejor"] == n and h["fraccion_factible"] > 0 and not np.isnan(h["fitness_mejor"]):
            return h["generacion"]
    return None


def resumir(resultado: ResultadoAG) -> dict:
    ev, sc = resultado.eval_mejor, resultado.escenario
    return {
        "escenario": sc.nombre,
        "semilla": resultado.semilla,
        "fitness": round(ev.fitness, 4),
        "fitness_inicial": round(resultado.eval_inicial.fitness, 4),
        "factible": ev.factible,
        "violacion_grados": round(ev.violacion, 3),
        "regiones_cubiertas": ev.n_cubiertas,
        "cobertura_ponderada": round(ev.cobertura_ponderada, 4),
        "aceptada": aceptacion(ev, sc)["ACEPTADA"],
        "gen_convergencia": generacion_convergencia(resultado),
        "gen_cobertura_completa": generacion_cobertura_completa(resultado),
        "generaciones": resultado.historial[-1]["generacion"],
        "evaluaciones": resultado.evaluaciones,
        "tiempo_s": round(resultado.tiempo_s, 2),
        "cota": round(cota_referencia(sc)["fitness"], 4),
    }


def distancia_soluciones(a, b) -> float:
    """Distancia angular media (grados) entre satélites tras el emparejamiento óptimo."""
    b = alinear(a, b)
    return float(distancia_angular(a[:, 0], a[:, 1], b[:, 0], b[:, 1]).mean())


def margenes_zonas(configuracion, escenario: Escenario) -> pd.DataFrame:
    """Para cada zona: distancia del satélite más cercano y su margen."""
    filas = []
    for z in escenario.zonas:
        d = distancia_angular(configuracion[:, 0], configuracion[:, 1], z.lat, z.lon)
        filas.append(
            {
                "zona": z.nombre,
                "tipo": z.tipo,
                "radio_grados": z.radio_grados,
                "sat_mas_cercano": int(d.argmin()),
                "distancia_grados": round(float(d.min()), 2),
                "margen_grados": round(float(d.min() - z.radio_grados), 2),
                "respeta": bool(d.min() >= z.radio_grados),
            }
        )
    return pd.DataFrame(filas)


# ----------------------------------------------------------------- experimentos
def e1_inicial(cfg: ParametrosAG = None, semilla: int = 0) -> ResultadoAG:
    """Etapa 1: sin restricciones espaciales."""
    return ejecutar_ag(escenario_inicial(), cfg, semilla=semilla, instantanea_cada=25)


def e2_base(cfg: ParametrosAG = None, semilla: int = 0) -> ResultadoAG:
    """Ejecución de referencia de la etapa 2 (todas las restricciones), usada por E2, E3, E4, E8 y E9."""
    return ejecutar_ag(escenario_base(), cfg, semilla=semilla, instantanea_cada=25)


def e3_e4_auditoria_restricciones(resultados) -> pd.DataFrame:
    """Márgenes de cada mejor solución a cada zona, en muchas ejecuciones."""
    marcos = []
    for r in resultados:
        df = margenes_zonas(r.mejor, r.escenario)
        df.insert(0, "semilla", r.semilla)
        marcos.append(df)
    return pd.concat(marcos, ignore_index=True)


def e4_objeto_junto_a_region(cfg: ParametrosAG = None, semilla: int = 0) -> ResultadoAG:
    """Posición ocupada reubicada junto al Sahel (a 2° de su centro)."""
    sc = escenario_base().sin_zona("Objeto A").con_zona(
        Zona("Objeto A (reubicado)", 15.0, 2.0, 5.0, "ocupada"), nombre="objeto-junto-al-Sahel"
    )
    return ejecutar_ag(sc, cfg, semilla=semilla)


def escenarios_espacio_reducido():
    base = escenario_base()
    r1 = base.con_zona(Zona("Desechos Golfo de México", 23.0, -90.0, 6.0), nombre="R1 +zona sobre Yucatán")
    r2 = r1.con_parametros(nombre="R2 R1 + techo 1200 km", alt_max_km=1200.0)
    r3 = r2.con_zona(Zona("Desechos Pacífico Norte", 40.0, 140.0, 5.0), nombre="R3 R2 + zona sobre Japón")
    return [base.renombrado("R0 base"), r1, r2, r3]


def e5_espacio_reducido(cfg: ParametrosAG = None, semilla: int = 0):
    """Reduce el espacio utilizable paso a paso. También ejecuta R1 *sin* manejo
    de restricciones para mostrar lo que las restricciones evitan."""
    resultados = [ejecutar_ag(sc, cfg, semilla=semilla) for sc in escenarios_espacio_reducido()]
    sin_manejo = ejecutar_ag(
        escenarios_espacio_reducido()[1], replace(cfg or ParametrosAG(), manejo_restricciones="ninguno"),
        semilla=semilla,
    )
    return resultados, sin_manejo


def escenarios_inviables():
    base = escenario_base()
    return {
        "I1 Amazonía inalcanzable": base.con_zona(
            Zona("Bloqueo Amazonía", -3.5, -62.0, 15.0), nombre="I1 Amazonía inalcanzable"
        ),
        "I2 solo 5 satélites": base.con_parametros(nombre="I2 solo 5 satélites", n_satelites=5),
        "I3 separación 80° imposible": base.con_parametros(
            nombre="I3 separación 80° imposible", separacion_min_grados=80.0
        ),
    }


def e6_inviables(cfg: ParametrosAG = None, semilla: int = 0):
    return {k: ejecutar_ag(sc, cfg, semilla=semilla) for k, sc in escenarios_inviables().items()}


def e7_variacion(cfg: ParametrosAG = None, semillas=range(10), progreso: bool = False):
    """Ejecuciones repetidas + métodos de referencia con el mismo presupuesto de evaluaciones."""
    sc = escenario_base()
    ejecuciones = []
    for k, s in enumerate(semillas, 1):
        ejecuciones.append(ejecutar_ag(sc, cfg, semilla=s))
        if progreso:
            print(f"  semilla {s}: fitness {ejecuciones[-1].eval_mejor.fitness:.4f} ({k}/{len(semillas)})", flush=True)
    tabla = pd.DataFrame([resumir(r) for r in ejecuciones])
    presupuesto = ejecuciones[0].evaluaciones
    aleatoria = [busqueda_aleatoria(sc, presupuesto, semilla=1000 + s)[1][-1][1] for s in semillas]
    _, ev_voraz = colocacion_voraz(sc)
    f_ag = tabla["fitness"].to_numpy()
    mw = stats.mannwhitneyu(f_ag, aleatoria, alternative="greater")
    n = len(ejecuciones)
    dist = np.full((n, n), 0.0)
    for i in range(n):
        for j in range(i + 1, n):
            dist[i, j] = dist[j, i] = distancia_soluciones(ejecuciones[i].mejor, ejecuciones[j].mejor)
    iu = np.triu_indices(n, 1)
    resumen = {
        "n_ejecuciones": n,
        "presupuesto_evaluaciones": int(presupuesto),
        "ag_media": float(f_ag.mean()),
        "ag_desv": float(f_ag.std(ddof=1)) if n > 1 else 0.0,
        "ag_min": float(f_ag.min()),
        "ag_max": float(f_ag.max()),
        "ag_cv_porcentaje": float(100 * f_ag.std(ddof=1) / f_ag.mean()) if n > 1 else 0.0,
        "ag_aceptadas": int(tabla["aceptada"].sum()),
        "aleatoria_media": float(np.mean(aleatoria)),
        "aleatoria_max": float(np.max(aleatoria)),
        "voraz": float(ev_voraz.fitness),
        "cota": float(cota_referencia(sc)["fitness"]),
        "p_mannwhitney_ag_mayor_aleatoria": float(mw.pvalue),
        "distancia_media_soluciones_grados": float(dist[iu].mean()) if n > 1 else 0.0,
        "distancia_max_soluciones_grados": float(dist[iu].max()) if n > 1 else 0.0,
    }
    return ejecuciones, tabla, resumen, aleatoria, dist


def analisis_fallas(configuracion, escenario: Escenario) -> pd.DataFrame:
    """N-1: lo que se pierde si falla cada satélite."""
    ev_completa = Evaluador(escenario).evaluar(configuracion)
    sc_menos = escenario.con_parametros(n_satelites=len(configuracion) - 1)
    ev = Evaluador(sc_menos)
    filas = []
    for s in range(len(configuracion)):
        e = ev.evaluar(np.delete(configuracion, s, axis=0))
        perdidas = [r.nombre for r, f in zip(e.regiones, ev_completa.regiones) if f.cubierta and not r.cubierta]
        filas.append(
            {
                "satelite_fallado": s,
                "fitness": round(e.fitness, 4),
                "cobertura_ponderada": round(e.cobertura_ponderada, 4),
                "regiones_cubiertas": e.n_cubiertas,
                "regiones_perdidas": ", ".join(perdidas) or "ninguna",
            }
        )
    return pd.DataFrame(filas)


def e8_robustez(base: ResultadoAG, cfg: ParametrosAG = None, semilla: int = 0):
    """Prueba propia: valor del término de redundancia ante la falla de un satélite."""
    sc_sin_red = escenario_base().con_parametros(
        nombre="sin término de redundancia", w_cobertura=0.80, w_redundancia=0.0, w_resolucion=0.20
    )
    sin_red = ejecutar_ag(sc_sin_red, cfg, semilla=semilla)
    sc = escenario_base()
    return {
        "con_redundancia": analisis_fallas(base.mejor, sc),
        "sin_redundancia": analisis_fallas(sin_red.mejor, sc),
        "ejecucion_sin_redundancia": sin_red,
    }


def revalidar(configuracion, anterior: Escenario, nuevo: Escenario) -> dict:
    """¿Una configuración anterior sigue siendo válida y buena bajo las nuevas condiciones?"""
    a, b = Evaluador(anterior).evaluar(configuracion), Evaluador(nuevo).evaluar(configuracion)
    return {
        "valida_antes": a.factible,
        "valida_ahora": b.factible,
        "fitness_antes": round(a.fitness, 4),
        "fitness_ahora": round(b.fitness, 4),
        "regiones_cubiertas_ahora": b.n_cubiertas,
        "violaciones": [
            f"sat {v.satelite} en {v.objetivo} ({v.distancia_grados:.2f}° < {v.limite_grados}°)" for v in b.violaciones
        ],
        "aceptada_ahora": aceptacion(b, nuevo)["ACEPTADA"],
    }


def e9_cambio_condiciones(base: ResultadoAG, cfg: ParametrosAG = None, semilla: int = 0):
    """Sección 3.3: cambio de prioridad y una zona que de pronto deja de estar disponible."""
    cfg = cfg or ParametrosAG()
    anterior = base.escenario
    salida = {}
    # (a) El Interior de Australia pasa a prioridad Alta.
    sc_a = anterior.con_prioridad("Interior de Australia", "alta", nombre="C1 Australia -> Alta")
    salida["prioridad"] = {
        "escenario": sc_a,
        "revalidacion": revalidar(base.mejor, anterior, sc_a),
        "reoptimizado": ejecutar_ag(sc_a, cfg, semilla=semilla, poblacion_inicial=base.poblacion_final),
    }
    # (b) Zona de desechos nueva justo donde está el satélite que observa Japón.
    japon = next(r for r in base.eval_mejor.regiones if r.nombre == "Japón")
    s = japon.satelites[0]
    lat, lon = base.mejor[s, 0], base.mejor[s, 1]
    sc_b = anterior.con_zona(Zona("Desechos nuevos", float(lat), float(lon), 3.0), nombre="C2 nueva zona sobre Japón")
    corto = replace(cfg, generaciones=min(cfg.generaciones, 150))
    salida["zona_nueva"] = {
        "escenario": sc_b,
        "revalidacion": revalidar(base.mejor, anterior, sc_b),
        "desde_poblacion_previa": ejecutar_ag(sc_b, corto, semilla=semilla, poblacion_inicial=base.poblacion_final),
        "desde_cero": ejecutar_ag(sc_b, corto, semilla=semilla),
    }
    return salida


ABLACIONES = {
    "configuración final": {},
    "sin alineación en cruce": {"cruce_alineado": False},
    "sin reparación": {"prob_reparacion": 0.0},
    "sin elitismo": {"tam_elite": 0},
    "mutación alta (0.5)": {"prob_mutacion": 0.5},
    "penalización en vez de Deb": {"manejo_restricciones": "penalizacion"},
    "población 40": {"tam_poblacion": 40},
}


def e10_ablacion(cfg: ParametrosAG = None, semillas=range(3), escenario: Escenario = None, progreso: bool = False):
    """Efecto de cada operador o parámetro sobre la calidad final."""
    cfg = cfg or ParametrosAG()
    sc = escenario or escenarios_espacio_reducido()[1]  # aquí las restricciones sí afectan
    filas = []
    for nombre, cambio in ABLACIONES.items():
        if progreso:
            print(f"  variante: {nombre}", flush=True)
        for s in semillas:
            r = ejecutar_ag(sc, replace(cfg, **cambio), semilla=s)
            filas.append(
                {
                    "variante": nombre,
                    "semilla": s,
                    "fitness": r.eval_mejor.fitness,
                    "valida": r.eval_mejor.factible,
                    "gen_convergencia": generacion_convergencia(r),
                }
            )
    df = pd.DataFrame(filas)
    agregado = (
        df.groupby("variante", sort=False)
        .agg(fitness_media=("fitness", "mean"), fitness_desv=("fitness", "std"),
             validas=("valida", "sum"), gen_convergencia_media=("gen_convergencia", "mean"))
        .round(4)
        .reset_index()
    )
    return df, agregado
