"""Centro de control: una sola página HTML con el globo 3D / mapa 2D y todas las
gráficas y comparativas de E1-E10.

La página se genera con los datos *reales* de la ejecución: cada configuración
que se dibuja sale de un ResultadoAG y se evalúa con el mismo Evaluador que usa
el algoritmo, así que lo que se ve es exactamente lo que produjo el AG.
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys

import numpy as np

from . import __version__
from .algoritmo_genetico import alinear
from .escenario import PESOS_PRIORIDAD, Escenario
from .evaluacion import (
    Evaluador,
    aceptacion,
    altitud_minima_vista_completa,
    calidad_resolucion,
    cota_referencia,
    semiangulo_huella,
)
from .experimentos import generacion_cobertura_completa, generacion_convergencia, margenes_zonas, resumir
from .geometria import grados_a_km
from .plantilla_centro_control import PLANTILLA
from .visualizacion import PALETA

MAX_CUADROS = 24  # cuadros de la línea de tiempo en las vistas secundarias
ALTO_PX = 1060


def _r(x, n=4):
    """Redondea para el JSON; NaN e infinitos se vuelven null."""
    if x is None:
        return None
    x = float(x)
    return round(x, n) if np.isfinite(x) else None


def _pct(x, total):
    return 100.0 * x / total if total else 0.0


def _lista(nombres):
    nombres = list(nombres)
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


# --------------------------------------------------------------- escenarios
def _escenario(sc: Escenario) -> dict:
    return {
        "nombre": sc.nombre,
        "regiones": [{"nombre": r.nombre, "lat": r.lat, "lon": r.lon, "prioridad": r.prioridad, "peso": r.peso,
                      "radio_km": r.radio_km} for r in sc.regiones],
        "zonas": [{"nombre": z.nombre, "lat": z.lat, "lon": z.lon, "radio": z.radio_grados, "tipo": z.tipo}
                  for z in sc.zonas],
        "n_satelites": sc.n_satelites,
        "alt_min_km": sc.alt_min_km,
        "alt_max_km": sc.alt_max_km,
        "semiangulo_sensor": sc.semiangulo_sensor_grados,
        "umbral_cobertura": sc.umbral_cobertura,
        "separacion_min": sc.separacion_min_grados,
        "anillos": sc.anillos_muestra,
        "pesos_fitness": [sc.w_cobertura, sc.w_redundancia, sc.w_resolucion],
        "cota": _r(cota_referencia(sc)["fitness"]),
        "notas": list(sc.notas),
    }


# ------------------------------------------------------------------- vistas
def _cuadro(evaluador: Evaluador, gen, configuracion, decimales: int = 5) -> dict:
    """Un cuadro de la línea de tiempo: configuración + su evaluación completa.

    `decimales` fija la precisión de lat/lon: 5 (≈ 1 m) en la vista principal, que
    se verifica en el navegador, y 4 (≈ 11 m) en las secundarias, para aligerar."""
    sc = evaluador.escenario
    configuracion = np.asarray(configuracion, dtype=float)
    ev = evaluador.evaluar(configuracion)
    lam = semiangulo_huella(configuracion[:, 2], sc.semiangulo_sensor_grados)
    malos = {v.satelite for v in ev.violaciones}
    return {
        "g": gen,
        "f": _r(ev.fitness),
        "ok": int(ev.factible),
        "v": _r(ev.violacion, 3),
        "c": ev.n_cubiertas,
        "s": [[_r(la, decimales), _r(lo, decimales), _r(h, decimales - 2), _r(lam[i], decimales), int(i in malos)]
              for i, (la, lo, h) in enumerate(configuracion)],
        "r": [[_r(x.cobertura), _r(x.redundancia), _r(x.resolucion), int(x.cubierta), x.satelites]
              for x in ev.regiones],
        "x": [f"S{v.satelite} → {v.objetivo} ({v.distancia_grados:.2f}° < {v.limite_grados}°)"
              for v in ev.violaciones][:12],
    }


def _adelgazar(gens, maximo):
    if maximo is None or len(gens) <= maximo:
        return gens
    idx = np.unique(np.round(np.linspace(0, len(gens) - 1, maximo)).astype(int))
    return [gens[i] for i in idx]


def _historial(resultado) -> dict:
    h = resultado.historial
    return {
        "mejor": [_r(x["mejor_rango_historico"]) if x["mejor_rango_historico"] >= 0 else None for x in h],
        "media": [_r(x["fitness_media"], 3) for x in h],
        "fact": [_r(x["fraccion_factible"], 3) for x in h],
        "div": [_r(x["diversidad_grados"], 1) for x in h],
    }


class _Constructor:
    """Junta escenarios y vistas sin duplicar escenarios iguales."""

    def __init__(self):
        self.escenarios, self.vistas = {}, []

    def escenario(self, sc: Escenario) -> str:
        datos = _escenario(sc)
        clave = sc.nombre
        while clave in self.escenarios and self.escenarios[clave] != datos:
            clave += "'"
        self.escenarios[clave] = datos
        return clave

    def vista_resultado(self, id_, grupo, titulo, resultado, nota="", max_cuadros=MAX_CUADROS):
        sc = resultado.escenario
        ev = Evaluador(sc)
        gens = _adelgazar(sorted(resultado.instantaneas), max_cuadros)
        configs = [np.asarray(resultado.instantaneas[g], dtype=float) for g in gens]
        # El orden de los satélites en el genoma es arbitrario: se alinea cada cuadro
        # con el siguiente para que S3 sea el mismo satélite en toda la línea de
        # tiempo. El último cuadro conserva el orden exacto del resultado del AG.
        for i in range(len(configs) - 2, -1, -1):
            if len(configs[i]) == len(configs[i + 1]):
                configs[i] = alinear(configs[i + 1], configs[i])
        self.vistas.append({
            "id": id_, "grupo": grupo, "titulo": titulo, "escenario": self.escenario(sc),
            "semilla": resultado.semilla, "nota": nota, "gen_total": resultado.historial[-1]["generacion"],
            "cuadros": [_cuadro(ev, int(g), cfg, 5 if max_cuadros is None else 4) for g, cfg in zip(gens, configs)],
            "hist": _historial(resultado),
        })
        return id_

    def vista_fija(self, id_, grupo, titulo, escenario: Escenario, configuracion, nota=""):
        """Una configuración evaluada bajo otro escenario (por ejemplo, una revalidación)."""
        self.vistas.append({
            "id": id_, "grupo": grupo, "titulo": titulo, "escenario": self.escenario(escenario),
            "semilla": None, "nota": nota, "gen_total": None,
            "cuadros": [_cuadro(Evaluador(escenario), None, configuracion, 4)], "hist": None,
        })
        return id_


# ------------------------------------------------------------------- textos
def _texto_evolucion(base) -> dict:
    sc, ev, cfg = base.escenario, base.eval_mejor, base.parametros
    h = base.historial
    cota = cota_referencia(sc)["fitness"]
    hmin = altitud_minima_vista_completa(300.0, sc)
    g30 = min(30, len(h) - 1)
    redundantes = [r.nombre for r in ev.regiones if r.redundancia >= 0.95]
    principales = sorted({min(r.satelites, key=lambda s: base.mejor[s, 2]) for r in ev.regiones if r.satelites})
    alts = base.mejor[principales, 2] if principales else np.array([np.nan])
    estrategia = (
        f"Cada región cubierta tiene un satélite principal entre {alts.min():.0f} y {alts.max():.0f} km, "
        f"justo arriba del mínimo de {hmin:.0f} km que cubre los 300 km."
    )
    if redundantes:
        estrategia += (f" Los satélites restantes dan redundancia a {_lista(redundantes)}. "
                       "**Nadie programó esa regla: surge de la función de evaluación.**")
    return {
        "condiciones": (f"Escenario base con {len(sc.zonas_desechos)} zonas de desechos, {len(sc.zonas_ocupadas)} "
                        f"posiciones ocupadas y separación mínima de {sc.separacion_min_grados:g}°. Población de "
                        f"{cfg.tam_poblacion}, {h[-1]['generacion']} generaciones, semilla {base.semilla}."),
        "resultado": (f"El fitness pasa de {base.eval_inicial.fitness:.4f} (mejor individuo aleatorio) a "
                      f"**{ev.fitness:.4f}**, el {_pct(ev.fitness, cota):.2f}% de la cota de referencia ({cota:.4f}). "
                      f"Regiones cubiertas: {ev.n_cubiertas}/{len(ev.regiones)} desde la generación "
                      f"{generacion_cobertura_completa(base)}; el 99% del valor final se alcanza en la generación "
                      f"{generacion_convergencia(base)}."),
        "interpretacion": [
            (f"**Primero explora y luego explota.** La diversidad baja de {h[0]['diversidad_grados']:.0f}° a "
             f"{h[g30]['diversidad_grados']:.0f}° en las primeras {g30} generaciones, con σ de mutación alto; después "
             f"σ decae de {cfg.sigma_inicial_grados:g}° a {cfg.sigma_final_grados:g}° y el AG solo afina "
             f"(diversidad final {h[-1]['diversidad_grados']:.1f}°)."),
            estrategia,
            (f"Al inicio, el {100 * h[0]['fraccion_factible']:.0f}% de la población aleatoria era válida. Con las "
             f"reglas de Deb, las inválidas pierden contra cualquier válida, y la solución final tiene "
             f"{len(ev.violaciones)} violaciones."),
        ],
    }


def _criterios_fallidos(resultado):
    criterios = aceptacion(resultado.eval_mejor, resultado.escenario)
    return [k.split(" ")[0] for k, v in criterios.items() if k != "ACEPTADA" and not v]


def _texto_ejecuciones(e7) -> dict:
    res, ejec = e7["resumen"], e7["ejecuciones"]
    n = res["n_ejecuciones"]
    validas = sum(r.eval_mejor.factible for r in ejec)
    completas = sum(r.eval_mejor.n_cubiertas == len(r.escenario.regiones) for r in ejec)
    fallidas = {r.semilla: _criterios_fallidos(r) for r in ejec}
    fallidas = {s: c for s, c in fallidas.items() if c}
    interp = [f"**Validez:** {validas}/{n} ejecuciones son válidas y {completas}/{n} cubren todas las regiones."]
    if fallidas:
        detalle = "; ".join(f"semilla {s}: {', '.join(c)}" for s, c in fallidas.items())
        interp.append(f"**No aceptadas:** {detalle}.")
        if all(c == ["C3"] for c in fallidas.values()):
            interp.append(
                "Todas fallan solo por C3: un satélite de redundancia quedó sobre una región Media en lugar de una "
                "Alta. Es un **óptimo local**: salir de ahí exige mover un satélite decenas de grados de golpe, y la "
                "mutación fina del final ya no da saltos tan grandes.")
    else:
        interp.append("**Todas las ejecuciones cumplen los cuatro criterios de aceptación.**")
    interp += [
        (f"**AG contra búsqueda aleatoria:** con el mismo presupuesto, la aleatoria se queda en "
         f"{res['aleatoria_media']:.3f} (máx. {res['aleatoria_max']:.3f}). La prueba de Mann-Whitney unilateral da "
         f"p = {res['p_mannwhitney_ag_mayor_aleatoria']:.1e}: **el AG no gana por suerte**."),
        (f"**AG contra voraz:** la heurística voraz ({res['voraz']:.4f}) solo prueba posiciones cerca de las regiones, "
         f"es decir, usa conocimiento del problema. El AG parte de cero y obtiene en promedio {res['ag_media']:.4f} "
         f"(mejor ejecución {res['ag_max']:.4f})."),
        (f"**Soluciones distintas, calidad parecida:** la distancia media entre las soluciones de dos semillas es "
         f"{res['distancia_media_soluciones_grados']:.1f}° (máx. {res['distancia_max_soluciones_grados']:.1f}°). "
         "El paisaje es multimodal; por eso se reportan distribuciones y no una sola ejecución."),
    ]
    return {
        "condiciones": (f"Escenario base, {n} semillas con los mismos parámetros y el mismo presupuesto de "
                        f"{res['presupuesto_evaluaciones']:,} evaluaciones para el AG y para la búsqueda aleatoria. "
                        "La heurística voraz agrega un satélite a la vez, siempre el de mayor ganancia."),
        "resultado": (f"Fitness {res['ag_media']:.4f} ± {res['ag_desv']:.4f} (CV {res['ag_cv_porcentaje']:.2f}%), "
                      f"rango [{res['ag_min']:.4f}, {res['ag_max']:.4f}]. {res['ag_aceptadas']}/{n} ejecuciones "
                      "cumplen todos los criterios."),
        "interpretacion": interp,
    }


def _satelite_de(resultado, nombre_region):
    region = next(r for r in resultado.eval_mejor.regiones if r.nombre == nombre_region)
    if not region.satelites:
        return None
    return min(region.satelites, key=lambda s: resultado.mejor[s, 2])


def _texto_restricciones(todo) -> dict:
    auditoria, ejec, junto, base = todo["auditoria"], todo["e7"]["ejecuciones"], todo["e4"], todo["base"]
    margenes = auditoria.groupby("zona", sort=False)["margen_grados"].min()
    ini = np.mean([r.historial[0]["fraccion_factible"] for r in ejec])
    fin = np.mean([r.historial[-1]["fraccion_factible"] for r in ejec])
    todas = bool(auditoria["respeta"].all())
    s_junto, s_base = _satelite_de(junto, "Sahel"), _satelite_de(base, "Sahel")
    sahel = next(r for r in junto.eval_mejor.regiones if r.nombre == "Sahel")
    zona = next(z for z in junto.escenario.zonas if "reubicado" in z.nombre)
    m = margenes_zonas(junto.mejor, junto.escenario)
    margen = float(m.loc[m["zona"] == zona.nombre, "margen_grados"].iloc[0])
    estres = (f"**Objeto junto al Sahel:** el margen mínimo a la zona reubicada es {margen:.2f}°. "
              f"Cobertura del Sahel {sahel.cobertura:.0%}, resolución {sahel.resolucion:.2f}.")
    if s_junto is not None and s_base is not None:
        estres += (f" El satélite del Sahel pasa de {base.mejor[s_base, 2]:.0f} km a {junto.mejor[s_junto, 2]:.0f} km "
                   "para alcanzar la región desde fuera de la zona.")
    estres += (f" La restricción tiene un **costo medible**: el fitness baja de {base.eval_mejor.fitness:.4f} a "
               f"{junto.eval_mejor.fitness:.4f}.")

    niveles, sin_manejo = todo["e5"]["niveles"], todo["e5"]["sin_manejo"]
    fits = [r.eval_mejor.fitness for r in niveles]
    monotono = all(b <= a + 1e-9 for a, b in zip(fits, fits[1:]))
    todas_cubiertas = all(r.eval_mejor.n_cubiertas == len(r.escenario.regiones) for r in niveles)
    e5 = [f"El fitness {'baja de forma monótona' if monotono else 'cambia'} al reducir el espacio: "
          + " → ".join(f"{f:.4f}" for f in fits) + "."]
    e5.append("**Las regiones siguen cubiertas en todos los niveles**: el AG compensa subiendo o alejando satélites, "
              "y lo que se pierde es resolución y redundancia." if todas_cubiertas else
              "En algunos niveles ya no se pueden cubrir todas las regiones; el AG sacrifica primero las de menor peso.")
    e5.append(f"**Sin manejo de restricciones**, R1 obtiene un fitness aparente de {sin_manejo.eval_mejor.fitness:.4f} "
              f"con {sin_manejo.eval_mejor.violacion:.1f}° de intrusión: un puntaje más alto que **no es válido**. "
              f"Con las reglas de Deb, R1 queda en {niveles[1].eval_mejor.fitness:.4f}, pero válida.")
    return {
        "auditoria": {
            "condiciones": (f"Auditoría geométrica independiente del AG: para la mejor solución de cada una de las "
                            f"{len(ejec)} semillas se mide la distancia del satélite más cercano a cada zona."),
            "resultado": (f"{'Todas las zonas se respetan' if todas else 'Hay zonas invadidas'} en las {len(ejec)} "
                          "ejecuciones. Margen mínimo por zona: "
                          + ", ".join(f"{k} {v:.1f}°" for k, v in margenes.items()) + "."),
            "interpretacion": [
                (f"La población aleatoria inicial tenía {100 * (1 - ini):.0f}% de configuraciones inválidas; al final "
                 f"queda {100 * fin:.0f}% de válidas. Las inválidas restantes son hijos recién mutados que la "
                 "selección descarta."),
                ("**Observación honesta:** en el escenario base las zonas quedan lejos de las regiones, así que en el "
                 "óptimo no están activas. Por eso las pruebas de estrés, E5 y E6 las ponen encima de las regiones."),
                estres,
            ],
        },
        "e5": {
            "condiciones": ("Se reduce el espacio en 4 niveles acumulativos: R0 base → R1 + zona de 6° a 2.6° de "
                            "Yucatán → R2 + techo de 1200 km → R3 + zona sobre Japón. R1 también se ejecuta sin "
                            "manejo de restricciones para ver qué evita el sistema."),
            "resultado": " · ".join(f"{r.escenario.nombre.split(' ')[0]}: {r.eval_mejor.fitness:.4f} "
                                    f"({r.eval_mejor.n_cubiertas}/{len(r.escenario.regiones)})" for r in niveles),
            "interpretacion": e5,
        },
    }


DIFICULTAD_E6 = {
    "I1 Amazonía inalcanzable": "Zona de 15° centrada en la Amazonía: ninguna huella (máx. ≈ 11°) la alcanza desde "
                                "fuera. **Objetivo inalcanzable.**",
    "I2 solo 5 satélites": "Solo 5 satélites para 6 regiones. **Recursos insuficientes.**",
    "I3 separación 80° imposible": "Separación mínima de 80° entre 8 satélites: imposible por geometría (problema de "
                                   "Tammes, máx. ≈ 74.9°). **No existe ninguna configuración válida.**",
}


def _texto_e6(clave, r) -> str:
    ev = r.eval_mejor
    sin_cubrir = [x for x in ev.regiones if not x.cubierta]
    if not ev.factible:
        nunca = max(h["fraccion_factible"] for h in r.historial) == 0
        return (f"No se encontró ninguna configuración válida{' en ninguna generación' if nunca else ''}. El AG lo "
                f"reporta (factible = no) y devuelve la que **menos** viola: {len(ev.violaciones)} violaciones, "
                f"{ev.violacion:.1f}° de intrusión total. **Que el algoritmo termine no significa que haya resuelto "
                "el problema.**")
    if not sin_cubrir:
        return f"Solución válida con todas las regiones cubiertas (fitness {ev.fitness:.4f})."
    nombres = _lista(f"{x.nombre} ({x.prioridad}, {x.cobertura:.0%})" for x in sin_cubrir)
    texto = (f"Solución **válida** (fitness {ev.fitness:.4f}) con {ev.n_cubiertas}/{len(ev.regiones)} regiones "
             f"cubiertas; queda sin cubrir: {nombres}. El sistema **no hace trampa**: lo reporta (C2 = falso).")
    if all(x.prioridad == "normal" for x in sin_cubrir):
        texto += " Sacrifica justo la región de **menor prioridad**: las prioridades deciden qué se pierde."
    return texto


def _texto_e9(todo) -> dict:
    cambios = todo["e9"]
    a, b = cambios["prioridad"], cambios["zona_nueva"]
    ra, rb = a["revalidacion"], b["revalidacion"]
    previa, cero = b["desde_poblacion_previa"], b["desde_cero"]
    return {
        "condiciones": ("(a) El Interior de Australia sube a prioridad Alta. (b) Aparece una zona de desechos de 3° "
                        "justo donde está el satélite que observa Japón. Primero se revalida la solución anterior y "
                        "luego se reoptimiza desde la población previa y, para comparar, desde cero."),
        "resultado": (f"(a) válida antes/ahora: {'sí' if ra['valida_antes'] else 'no'}/{'sí' if ra['valida_ahora'] else 'no'}"
                      f", fitness {ra['fitness_antes']:.4f} → {ra['fitness_ahora']:.4f}. (b) válida antes/ahora: "
                      f"{'sí' if rb['valida_antes'] else 'no'}/{'sí' if rb['valida_ahora'] else 'no'}."),
        "interpretacion": [
            (f"**(a) Prioridad:** la solución anterior {'sigue siendo válida' if ra['valida_ahora'] else 'deja de ser válida'}"
             f", porque una prioridad no cambia la geometría; su fitness cambia porque cambian los pesos. La "
             f"reoptimización llega a {a['reoptimizado'].eval_mejor.fitness:.4f} "
             f"(cota {cota_referencia(a['escenario'])['fitness']:.4f})."),
            (f"**(b) Zona nueva:** la solución anterior {'deja de ser válida' if not rb['valida_ahora'] else 'sigue siendo válida'}"
             + (f" ({'; '.join(rb['violaciones'])})" if rb["violaciones"] else "")
             + f", aunque su fitness sea {rb['fitness_ahora']:.4f}. **Puntaje y validez son cosas distintas.**"),
            (f"Desde la población previa, el AG llega a {previa.eval_mejor.fitness:.4f} "
             f"(99% en la generación {generacion_convergencia(previa)}); desde cero, con el mismo presupuesto, a "
             f"{cero.eval_mejor.fitness:.4f}. "
             + ("**Reutilizar la población anterior es más eficiente.**"
                if previa.eval_mejor.fitness >= cero.eval_mejor.fitness else
                "En esta ejecución, empezar de cero dio un resultado igual o mejor.")),
        ],
    }


def _texto_e8(robustez) -> dict:
    con, sin = robustez["con_redundancia"], robustez["sin_redundancia"]
    n = len(con)
    ok_con = int((con["regiones_perdidas"] == "ninguna").sum())
    ok_sin = int((sin["regiones_perdidas"] == "ninguna").sum())
    return {
        "condiciones": ("Pregunta propia: ¿el término de redundancia del fitness tiene valor real o solo infla el "
                        "puntaje? Se simula la falla de cada satélite (análisis N-1) en la solución base y en una "
                        "optimizada **sin** término de redundancia (pesos 0.80 / 0 / 0.20)."),
        "resultado": (f"Con redundancia, {ok_con}/{n} fallas no hacen perder ninguna región (fitness medio tras una "
                      f"falla {con['fitness'].mean():.4f}). Sin redundancia, {ok_sin}/{n} "
                      f"({sin['fitness'].mean():.4f})."),
        "interpretacion": [
            ("El término de redundancia hace la constelación **más tolerante a fallas**." if ok_con > ok_sin else
             "En esta ejecución el término de redundancia no mejoró la tolerancia a fallas."),
            (f"En el peor caso, con redundancia quedan {int(con['regiones_cubiertas'].min())} regiones cubiertas; "
             f"sin ella, {int(sin['regiones_cubiertas'].min())}."),
        ],
    }


def _texto_e10(agregado, n_semillas) -> dict:
    final = agregado.iloc[0]
    peores = agregado.sort_values("fitness_media").head(2)["variante"].tolist()
    dudosas = [
        f["variante"] for _, f in agregado.iloc[1:].iterrows()
        if abs(f["fitness_media"] - final["fitness_media"]) < max(f["fitness_desv"] or 0, final["fitness_desv"] or 0)
    ]
    interp = [f"Las variantes que más empeoran el resultado son {_lista(peores)}."]
    if dudosas:
        interp.append(f"Las diferencias de {_lista(dudosas)} son menores que la desviación estándar, así que **no son "
                      f"concluyentes con {n_semillas} semillas**; se reporta así en lugar de sobreinterpretarlas.")
    interp.append("La calibración inicial (docs/04) mostró que el número de generaciones y el ajuste fino final "
                  "(σ final de 0.05° y 2 km) son los parámetros que más mejoran el resultado.")
    return {
        "condiciones": (f"Escenario R1 (las restricciones sí afectan aquí), {n_semillas} semillas por variante. Se "
                        "apaga un operador a la vez para medir su aporte."),
        "resultado": f"Configuración final: {final['fitness_media']:.4f} ± {final['fitness_desv'] or 0:.4f}.",
        "interpretacion": interp,
    }


# -------------------------------------------------------------------- datos
def _modelo(base, cfg) -> dict:
    sc = base.escenario
    alts = [500, altitud_minima_vista_completa(300.0, sc), 750, 1000, 1500, 2000]
    cota = cota_referencia(sc)
    return {
        "parametros_ag": cfg.a_dict(),
        "pesos_prioridad": PESOS_PRIORIDAD,
        "pesos_fitness": [sc.w_cobertura, sc.w_redundancia, sc.w_resolucion],
        "huella": [{"alt_km": a, "radio_km": _r(grados_a_km(semiangulo_huella(a, sc.semiangulo_sensor_grados)), 0),
                    "calidad": _r(calidad_resolucion(a, sc.alt_min_km, sc.alt_max_km), 3)} for a in alts],
        "cota": {"fitness": _r(cota["fitness"]),
                 "regiones": {k: {"alt_km": v["alt_km"], "puntaje": _r(v["puntaje"])} for k, v in cota["regiones"].items()}},
        "aceptacion": {k: bool(v) for k, v in aceptacion(base.eval_mejor, sc).items()},
        "supuestos": [
            "La Tierra es una esfera de radio 6371 km.",
            "Cada satélite se mantiene fijo sobre un punto (station-keeping); altitud permitida de 500 a 2000 km.",
            "Sensor apuntando al nadir con semiángulo de 30°: subir agranda la huella pero empeora la resolución.",
            "Las zonas prohibidas son casquetes (conos desde el centro de la Tierra) que aplican a cualquier altitud.",
            "Separación mínima de 2° entre satélites propios.",
            "Región cubierta ⇔ al menos el 95% de sus 49 puntos de muestra está dentro de alguna huella.",
        ],
    }


def _verificacion(vista_base, base) -> dict:
    final = vista_base["cuadros"][-1]
    dibujada = np.array([s[:3] for s in final["s"]])
    return {
        "max_dif_configuracion": float(np.abs(dibujada - base.mejor).max()),
        "fitness_igual": final["f"] == _r(base.eval_mejor.fitness),
        "cobertura_igual": [r[3] for r in final["r"]] == [int(x.cubierta) for x in base.eval_mejor.regiones],
    }


def ejecutar_pruebas_unitarias(directorio: str = ".") -> dict:
    """Ejecuta pytest y devuelve el resumen que muestra el centro de control."""
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "--color=no", "-p", "no:cacheprovider"], cwd=directorio,
                          capture_output=True, text=True)
    lineas = [l for l in proc.stdout.strip().splitlines() if l.strip()]
    ultima = lineas[-1] if lineas else proc.stderr.strip()[-200:]
    cuenta = {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|error)", ultima)}
    return {"aprobadas": cuenta.get("passed", 0), "fallidas": cuenta.get("failed", 0) + cuenta.get("error", 0),
            "resumen": ultima, "codigo_salida": proc.returncode}


def datos_centro_control(todo: dict, pruebas_unitarias: dict = None, modo: str = "completo") -> dict:
    """Arma el JSON del centro de control a partir de los resultados de `ejecutar_todo`."""
    base, e7, cfg = todo["base"], todo["e7"], todo["parametros"]
    c = _Constructor()

    principal = "Ejecución principal"
    c.vista_resultado("base", principal, "Etapa 2 · escenario base", base,
                      "Todas las restricciones. Cada cuadro es una mejora del mejor individuo.", max_cuadros=None)
    c.vista_resultado("e1", "Etapa 1", "E1 · sin restricciones", todo["e1"], "Solo regiones, sin zonas prohibidas.")
    for r in e7["ejecuciones"]:
        c.vista_resultado(f"e7-{r.semilla}", "Variación entre semillas (E7)", f"E7 · semilla {r.semilla}", r)
    c.vista_resultado("e4", "Restricciones (E4, E5)", "E4 · objeto junto al Sahel", todo["e4"],
                      "El Objeto A se reubica a 2° del centro del Sahel.")
    niveles = todo["e5"]["niveles"]
    for r in niveles:
        c.vista_resultado(f"e5-{r.escenario.nombre.split(' ')[0]}", "Restricciones (E4, E5)",
                          f"E5 · {r.escenario.nombre}", r)
    c.vista_resultado("e5-R1-sin", "Restricciones (E4, E5)", "E5 · R1 sin manejo de restricciones",
                      todo["e5"]["sin_manejo"], "Configuración con mejor puntaje pero inválida.")
    for k, r in todo["e6"].items():
        c.vista_resultado(f"e6-{k.split(' ')[0]}", "Escenarios límite (E6)", f"E6 · {k}", r, DIFICULTAD_E6[k])
    ca, cb = todo["e9"]["prioridad"], todo["e9"]["zona_nueva"]
    grupo9 = "Cambio de condiciones (E9)"
    c.vista_fija("e9-a-anterior", grupo9, "E9a · solución anterior revalidada", ca["escenario"], base.mejor,
                 "La solución base evaluada con Australia en prioridad Alta.")
    c.vista_resultado("e9-a-reopt", grupo9, "E9a · reoptimizada", ca["reoptimizado"])
    c.vista_fija("e9-b-anterior", grupo9, "E9b · solución anterior revalidada", cb["escenario"], base.mejor,
                 "La solución base frente a la zona nueva: ahora viola una restricción.")
    c.vista_resultado("e9-b-previa", grupo9, "E9b · desde la población previa", cb["desde_poblacion_previa"])
    c.vista_resultado("e9-b-cero", grupo9, "E9b · desde cero", cb["desde_cero"])
    c.vista_resultado("e8-sin", "Prueba propia (E8)", "E8 · optimizada sin redundancia",
                      todo["e8"]["ejecucion_sin_redundancia"], "Pesos 0.80 / 0 / 0.20.")

    vista_base = c.vistas[0]
    h = base.historial
    auditoria = todo["auditoria"]
    robustez = todo["e8"]
    agregado = todo["e10"]["agregado"]
    n_ablacion = int(todo["e10"]["detalle"]["semilla"].nunique())
    textos_restr = _texto_restricciones(todo)
    return {
        "version": __version__,
        "generado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "modo": modo,
        "paleta": PALETA,
        "vista_inicial": "base",
        "escenarios": c.escenarios,
        "vistas": c.vistas,
        "evolucion": {
            "fitness_mejor": [_r(x["fitness_mejor"]) for x in h],
            "fitness_media": [_r(x["fitness_media"]) for x in h],
            "fitness_desv": [_r(x["fitness_desv"]) for x in h],
            "fitness_peor": [_r(x["fitness_peor"]) for x in h],
            "fact": [_r(x["fraccion_factible"], 3) for x in h],
            "div": [_r(x["diversidad_grados"], 2) for x in h],
            "sigma": [_r(x["sigma_grados"], 3) for x in h],
            "sigma_alt": [_r(x["sigma_alt_km"], 1) for x in h],
            "cota": _r(cota_referencia(base.escenario)["fitness"]),
            "gen_convergencia": generacion_convergencia(base),
            "gen_cobertura_completa": generacion_cobertura_completa(base),
            "texto": _texto_evolucion(base),
        },
        "ejecuciones": {
            "resumen": e7["resumen"],
            "filas": [{**resumir(r), "fallidos": _criterios_fallidos(r), "vista": f"e7-{r.semilla}"}
                      for r in e7["ejecuciones"]],
            "aleatoria": [_r(x) for x in e7["aleatoria"]],
            "distancias": [[_r(x, 1) for x in fila] for fila in e7["distancias"]],
            "texto": _texto_ejecuciones(e7),
        },
        "restricciones": {
            "zonas": [{"zona": z, "tipo": g["tipo"].iloc[0], "radio": float(g["radio_grados"].iloc[0]),
                       "distancia_min": float(g["distancia_grados"].min()), "margen_min": float(g["margen_grados"].min()),
                       "todas": bool(g["respeta"].all())} for z, g in auditoria.groupby("zona", sort=False)],
            "fact_inicial": _r(np.mean([r.historial[0]["fraccion_factible"] for r in e7["ejecuciones"]]), 3),
            "fact_final": _r(np.mean([r.historial[-1]["fraccion_factible"] for r in e7["ejecuciones"]]), 3),
            "junto": {"margenes": margenes_zonas(todo["e4"].mejor, todo["e4"].escenario).to_dict("records"),
                      "fitness": _r(todo["e4"].eval_mejor.fitness), "fitness_base": _r(base.eval_mejor.fitness)},
            "niveles": [{"nombre": r.escenario.nombre, "vista": f"e5-{r.escenario.nombre.split(' ')[0]}",
                         "fitness": _r(r.eval_mejor.fitness), "factible": r.eval_mejor.factible,
                         "cubiertas": r.eval_mejor.n_cubiertas, "cota": _r(cota_referencia(r.escenario)["fitness"]),
                         "aceptada": aceptacion(r.eval_mejor, r.escenario)["ACEPTADA"],
                         "cobertura": [_r(x.cobertura, 3) for x in r.eval_mejor.regiones],
                         "altitudes": [int(round(a)) for a in r.mejor[:, 2]]} for r in niveles],
            "sin_manejo": {"fitness": _r(todo["e5"]["sin_manejo"].eval_mejor.fitness),
                           "violacion": _r(todo["e5"]["sin_manejo"].eval_mejor.violacion, 2),
                           "violaciones": [f"S{v.satelite} en {v.objetivo} ({v.distancia_grados:.2f}° < {v.limite_grados}°)"
                                           for v in todo["e5"]["sin_manejo"].eval_mejor.violaciones]},
            "texto": textos_restr,
        },
        "limite": {
            "casos": [{"clave": k, "vista": f"e6-{k.split(' ')[0]}", "dificultad": DIFICULTAD_E6[k],
                       "fitness": _r(r.eval_mejor.fitness), "factible": r.eval_mejor.factible,
                       "violacion": _r(r.eval_mejor.violacion, 2), "n_violaciones": len(r.eval_mejor.violaciones),
                       "cubiertas": r.eval_mejor.n_cubiertas, "regiones": len(r.escenario.regiones),
                       "fact_max": _r(max(x["fraccion_factible"] for x in r.historial), 3),
                       "texto": _texto_e6(k, r)} for k, r in todo["e6"].items()],
            "e9": {
                "a": {**ca["revalidacion"], "reoptimizado": _r(ca["reoptimizado"].eval_mejor.fitness),
                      "cota": _r(cota_referencia(ca["escenario"])["fitness"])},
                "b": {**cb["revalidacion"], "previa": _r(cb["desde_poblacion_previa"].eval_mejor.fitness),
                      "cero": _r(cb["desde_cero"].eval_mejor.fitness)},
                "texto": _texto_e9(todo),
            },
        },
        "propia": {
            "con": robustez["con_redundancia"].to_dict("records"),
            "sin": robustez["sin_redundancia"].to_dict("records"),
            "texto": _texto_e8(robustez),
        },
        "calibracion": {
            "filas": [{k: (_r(v) if isinstance(v, float) else v) for k, v in f.items()}
                      for f in agregado.to_dict("records")],
            "n_semillas": n_ablacion,
            "texto": _texto_e10(agregado, n_ablacion),
        },
        "modelo": _modelo(base, cfg),
        "pruebas_unitarias": pruebas_unitarias,
        "verificacion": _verificacion(vista_base, base),
        "tiempo_s": _r(todo["tiempo_s"], 0),
    }


def agregar_laboratorio(datos: dict, resultado, configuracion_anterior, escenario_anterior: Escenario) -> dict:
    """Agrega (o reemplaza) las vistas del laboratorio y las deja seleccionadas."""
    c = _Constructor()
    c.escenarios = dict(datos["escenarios"])
    c.vista_fija("lab-anterior", "Laboratorio", "Laboratorio · solución base revalidada", resultado.escenario,
                 configuracion_anterior, f"Solución de «{escenario_anterior.nombre}» bajo las nuevas condiciones.")
    c.vista_resultado("lab", "Laboratorio", "Laboratorio · reoptimizada", resultado,
                      "; ".join(resultado.escenario.notas) or "Escenario personalizado.")
    datos = dict(datos)
    datos["escenarios"] = c.escenarios
    datos["vistas"] = [v for v in datos["vistas"] if not v["id"].startswith("lab")] + c.vistas
    datos["vista_inicial"] = "lab"
    return datos


# ---------------------------------------------------------------- salida
def html_centro_control(datos: dict, alto: int = ALTO_PX) -> str:
    """Página HTML autocontenida (UTF-8) con el centro de control."""
    js = json.dumps(datos, ensure_ascii=False, separators=(",", ":"), default=_json_default,
                    allow_nan=False).replace("</", "<\\/")
    return PLANTILLA.replace("__ALTO__", str(alto)).replace("__DATOS__", js)


def _json_default(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return _r(x, 6)
    if isinstance(x, np.bool_):
        return bool(x)
    raise TypeError(type(x))


def guardar_centro_control(datos: dict, ruta: str, alto: int = ALTO_PX) -> str:
    html = html_centro_control(datos, alto)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(html)
    return ruta


def en_colab() -> bool:
    return "google.colab" in sys.modules


def mostrar_centro_control(datos: dict, manejador=None, alto: int = ALTO_PX):
    """Muestra el centro de control en el notebook. Si recibe el `manejador` de una
    salida anterior, la actualiza en su lugar en vez de crear otro bloque."""
    from IPython.display import HTML, display

    html = html_centro_control(datos, alto)
    if not en_colab():
        # Jupyter no aísla las salidas: se envuelve en un iframe propio.
        srcdoc = html.replace("&", "&amp;").replace('"', "&quot;")
        html = (f'<iframe srcdoc="{srcdoc}" style="width:100%;height:{alto + 8}px;border:0" '
                'allow="fullscreen"></iframe>')
    if manejador is None:
        return display(HTML(html), display_id=True)
    manejador.update(HTML(html))
    return manejador
