"""Modelo de cobertura, verificación de restricciones y fitness.

Una configuración es un arreglo de reales con forma (n_satelites, 3) cuyas
columnas son (latitud en grados, longitud en grados, altitud en km) del punto
subsatelital de cada satélite. Una población es un arreglo (P, n_satelites, 3).

Modelo de cobertura
-------------------
Cada satélite lleva un sensor que apunta al nadir con semiángulo eta. Su
huella sobre el suelo es un casquete esférico de ángulo central

    lambda(h) = asin((R + h) / R * sin(eta)) - eta

(o el ángulo del horizonte acos(R / (R + h)) si el sensor ve más allá de él).
Cada región es un disco de 300 km discretizado en puntos de muestra; un punto
está visto por un satélite cuando su distancia angular al punto subsatelital
es <= lambda(h). Una región está "cubierta" cuando la fracción de sus puntos
vistos por al menos un satélite alcanza `umbral_cobertura`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from .escenario import Escenario
from .geometria import RADIO_TIERRA_KM, a_unitario, distancia_angular, grados_a_km, km_a_grados, muestras_disco

TOLERANCIA_FACTIBILIDAD = 1e-9


def semiangulo_huella(alt_km, semiangulo_sensor_grados):
    """Ángulo central (grados) de la huella para la(s) altitud(es) `alt_km`."""
    alt_km = np.asarray(alt_km, dtype=float)
    eta = np.radians(semiangulo_sensor_grados)
    razon = (RADIO_TIERRA_KM + alt_km) / RADIO_TIERRA_KM * np.sin(eta)
    horizonte = np.arccos(RADIO_TIERRA_KM / (RADIO_TIERRA_KM + alt_km))
    lam = np.where(razon < 1.0, np.arcsin(np.minimum(razon, 1.0)) - eta, horizonte)
    return np.degrees(np.minimum(lam, horizonte))


def calidad_resolucion(alt_km, alt_min_km, alt_max_km):
    """1.0 en la altitud mínima permitida, 0.0 en la máxima (lineal)."""
    return 1.0 - (np.asarray(alt_km) - alt_min_km) / (alt_max_km - alt_min_km)


@dataclass
class ResultadoRegion:
    nombre: str
    prioridad: str
    peso: float
    cobertura: float  # fracción de puntos vistos por >= 1 satélite
    redundancia: float  # fracción de puntos vistos por >= 2 satélites
    resolucion: float  # media de la mejor calidad de resolución por punto (0 si no se ve)
    puntaje: float
    cubierta: bool
    satelites: List[int]  # satélites que ven al menos un punto


@dataclass
class Violacion:
    satelite: int
    restriccion: str  # "desechos" | "ocupada" | "separacion"
    objetivo: str
    distancia_grados: float
    limite_grados: float

    @property
    def intrusion_grados(self) -> float:
        return self.limite_grados - self.distancia_grados


@dataclass
class Evaluacion:
    configuracion: np.ndarray
    fitness: float
    factible: bool
    violacion: float  # intrusión total en grados (0 cuando es factible)
    regiones: List[ResultadoRegion]
    violaciones: List[Violacion] = field(default_factory=list)

    @property
    def n_cubiertas(self) -> int:
        return sum(r.cubierta for r in self.regiones)

    @property
    def cobertura_ponderada(self) -> float:
        w = np.array([r.peso for r in self.regiones])
        c = np.array([r.cobertura for r in self.regiones])
        return float((w * c).sum() / w.sum())

    def tabla_regiones(self):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "región": r.nombre,
                    "prioridad": r.prioridad,
                    "peso": r.peso,
                    "cobertura": round(r.cobertura, 3),
                    "redundancia": round(r.redundancia, 3),
                    "resolución": round(r.resolucion, 3),
                    "puntaje": round(r.puntaje, 3),
                    "cubierta": "sí" if r.cubierta else "NO",
                    "satélites": ",".join(map(str, r.satelites)) or "-",
                }
                for r in self.regiones
            ]
        )

    def tabla_satelites(self, escenario: Escenario):
        import pandas as pd

        lam = semiangulo_huella(self.configuracion[:, 2], escenario.semiangulo_sensor_grados)
        return pd.DataFrame(
            {
                "sat": np.arange(len(self.configuracion)),
                "lat": self.configuracion[:, 0].round(2),
                "lon": self.configuracion[:, 1].round(2),
                "alt_km": self.configuracion[:, 2].round(0),
                "huella_km": grados_a_km(lam).round(0),
            }
        )


class Evaluador:
    """Precalcula la geometría del escenario y evalúa poblaciones rápidamente."""

    def __init__(self, escenario: Escenario):
        self.escenario = escenario
        puntos, duenio = [], []
        for i, r in enumerate(escenario.regiones):
            s = muestras_disco(r.lat, r.lon, km_a_grados(r.radio_km), escenario.anillos_muestra)
            puntos.append(s)
            duenio.extend([i] * len(s))
        puntos = np.vstack(puntos)
        self.puntos = puntos
        self.region_de_punto = np.array(duenio)
        self.puntos_unitarios = a_unitario(puntos[:, 0], puntos[:, 1])  # (M, 3)
        conteos = np.bincount(self.region_de_punto, minlength=len(escenario.regiones))
        self.inicio_region = np.concatenate([[0], np.cumsum(conteos)[:-1]])
        self.puntos_por_region = conteos
        self.pesos = np.array([r.peso for r in escenario.regiones])
        if escenario.zonas:
            self.zonas_unitarias = a_unitario(
                np.array([z.lat for z in escenario.zonas]), np.array([z.lon for z in escenario.zonas])
            )
            self.radios_zona = np.array([z.radio_grados for z in escenario.zonas])
        else:
            self.zonas_unitarias = np.zeros((0, 3))
            self.radios_zona = np.zeros(0)
        self.n_evaluaciones = 0

    # ------------------------------------------------------------- por lote
    def _media_por_region(self, por_punto):
        """(P, M) -> (P, R): media sobre los puntos de cada región."""
        sumas = np.add.reduceat(por_punto, self.inicio_region, axis=1)
        return sumas / self.puntos_por_region

    def evaluar_poblacion(self, poblacion):
        """Evaluación vectorizada de una población (P, S, 3).

        Devuelve un dict de arreglos: fitness (P,), violacion (P,), factible (P,),
        cobertura/redundancia/resolucion/puntaje (P, R).
        """
        sc = self.escenario
        poblacion = np.asarray(poblacion, dtype=float)
        self.n_evaluaciones += len(poblacion)
        sat_u = a_unitario(poblacion[..., 0], poblacion[..., 1])  # (P, S, 3)
        alt = poblacion[..., 2]
        lam = semiangulo_huella(alt, sc.semiangulo_sensor_grados)  # (P, S)

        cos_ang = np.einsum("psk,mk->psm", sat_u, self.puntos_unitarios)  # (P, S, M)
        dentro = cos_ang >= np.cos(np.radians(lam))[..., None]
        conteo = dentro.sum(axis=1)  # (P, M)
        q = calidad_resolucion(alt, sc.alt_min_km, sc.alt_max_km)  # (P, S)
        mejor_q = np.where(dentro, q[..., None], 0.0).max(axis=1)  # (P, M)

        cob = self._media_por_region((conteo >= 1).astype(float))
        red = self._media_por_region((conteo >= 2).astype(float))
        res = self._media_por_region(mejor_q)
        puntaje = sc.w_cobertura * cob + sc.w_redundancia * red + sc.w_resolucion * res
        fitness = (puntaje * self.pesos).sum(axis=1) / self.pesos.sum()

        violacion = np.zeros(len(poblacion))
        if len(self.radios_zona):
            ang_zona = np.degrees(
                np.arccos(np.clip(np.einsum("psk,zk->psz", sat_u, self.zonas_unitarias), -1, 1))
            )
            violacion += np.clip(self.radios_zona - ang_zona, 0, None).sum(axis=(1, 2))
        if sc.separacion_min_grados > 0 and poblacion.shape[1] > 1:
            ang_sat = np.degrees(
                np.arccos(np.clip(np.einsum("psk,pqk->psq", sat_u, sat_u), -1, 1))
            )
            iu = np.triu_indices(poblacion.shape[1], k=1)
            violacion += np.clip(sc.separacion_min_grados - ang_sat[:, iu[0], iu[1]], 0, None).sum(axis=1)

        return {
            "fitness": fitness,
            "violacion": violacion,
            "factible": violacion <= TOLERANCIA_FACTIBILIDAD,
            "cobertura": cob,
            "redundancia": red,
            "resolucion": res,
            "puntaje": puntaje,
            "dentro": dentro,
        }

    # ------------------------------------------------------------- individual
    def evaluar(self, configuracion) -> Evaluacion:
        """Evaluación detallada de una configuración (S, 3)."""
        configuracion = np.asarray(configuracion, dtype=float)
        b = self.evaluar_poblacion(configuracion[None])
        sc = self.escenario
        dentro = b["dentro"][0]  # (S, M)
        regiones = []
        for i, r in enumerate(sc.regiones):
            sl = slice(self.inicio_region[i], self.inicio_region[i] + self.puntos_por_region[i])
            sats = [int(s) for s in np.flatnonzero(dentro[:, sl].any(axis=1))]
            cob = float(b["cobertura"][0, i])
            regiones.append(
                ResultadoRegion(
                    nombre=r.nombre,
                    prioridad=r.prioridad,
                    peso=r.peso,
                    cobertura=cob,
                    redundancia=float(b["redundancia"][0, i]),
                    resolucion=float(b["resolucion"][0, i]),
                    puntaje=float(b["puntaje"][0, i]),
                    cubierta=cob >= sc.umbral_cobertura - 1e-12,
                    satelites=sats,
                )
            )
        return Evaluacion(
            configuracion=configuracion.copy(),
            fitness=float(b["fitness"][0]),
            factible=bool(b["factible"][0]),
            violacion=float(b["violacion"][0]),
            regiones=regiones,
            violaciones=listar_violaciones(configuracion, sc),
        )


def listar_violaciones(configuracion, escenario: Escenario) -> List[Violacion]:
    """Lista legible de todas las restricciones que incumple una configuración."""
    salida = []
    lat, lon = configuracion[:, 0], configuracion[:, 1]
    for z in escenario.zonas:
        d = distancia_angular(lat, lon, z.lat, z.lon)
        for s in np.flatnonzero(d < z.radio_grados):
            salida.append(Violacion(int(s), z.tipo, z.nombre, float(d[s]), z.radio_grados))
    if escenario.separacion_min_grados > 0:
        n = len(configuracion)
        for i in range(n):
            for j in range(i + 1, n):
                d = float(distancia_angular(lat[i], lon[i], lat[j], lon[j]))
                if d < escenario.separacion_min_grados:
                    salida.append(Violacion(i, "separacion", f"sat {j}", d, escenario.separacion_min_grados))
    return salida


def altitud_minima_vista_completa(radio_km, escenario: Escenario, desfase_grados=0.0):
    """Altitud más baja cuya huella cubre un disco de `radio_km` cuyo centro está
    a `desfase_grados` del punto subsatelital (None si ninguna lo logra)."""
    necesario = km_a_grados(radio_km) + desfase_grados
    alts = np.arange(escenario.alt_min_km, escenario.alt_max_km + 1e-9, 1.0)
    ok = semiangulo_huella(alts, escenario.semiangulo_sensor_grados) >= necesario
    return float(alts[ok][0]) if ok.any() else None


def cota_referencia(escenario: Escenario) -> dict:
    """Valor optimista de referencia para el fitness (una relajación).

    Ignora las zonas prohibidas y supone que cada región tiene su propio
    satélite justo sobre su centro, a la altitud más baja que ve el disco
    completo; los satélites sobrantes (n_satelites - n_regiones) se asignan a
    las regiones de mayor peso como redundancia completa. Es válida para este
    escenario porque ninguna huella (máx. ~11°) alcanza dos regiones a la vez
    (separación mínima ~30°).
    """
    regiones = sorted(escenario.regiones, key=lambda r: -r.peso)
    sobrantes = max(escenario.n_satelites - len(regiones), 0)
    total, detalle = 0.0, {}
    for k, r in enumerate(regiones):
        h = altitud_minima_vista_completa(r.radio_km, escenario)
        if h is None:
            q, cob = 0.0, 0.0
        else:
            q, cob = float(calidad_resolucion(h, escenario.alt_min_km, escenario.alt_max_km)), 1.0
        red = 1.0 if (k < sobrantes and cob > 0) else 0.0
        s = escenario.w_cobertura * cob + escenario.w_redundancia * red + escenario.w_resolucion * q
        detalle[r.nombre] = {"alt_km": h, "puntaje": s}
        total += r.peso * s
    return {"fitness": total / sum(r.peso for r in regiones), "regiones": detalle}


def aceptacion(ev: Evaluacion, escenario: Escenario) -> dict:
    """Criterios del equipo para "suficientemente buena" (ver docs/01_definicion_problema.md)."""
    altas = [r for r in ev.regiones if r.prioridad == "alta"]
    # Solo se exige redundancia en tantas regiones Alta como satélites sobrantes
    # haya (n_satelites - n_regiones); pedir más sería inalcanzable.
    sobrantes = max(escenario.n_satelites - len(escenario.regiones), 0)
    necesarias = min(len(altas), sobrantes)
    criterios = {
        "C1 válida (sin violaciones)": ev.factible,
        "C2 todas las regiones cubiertas": ev.n_cubiertas == len(ev.regiones),
        f"C3 ≥{necesarias} regiones Alta con redundancia ≥ 95%": sum(r.redundancia >= 0.95 for r in altas) >= necesarias,
        "C4 fitness ≥ 90% de la cota de referencia": ev.fitness
        >= 0.90 * cota_referencia(escenario)["fitness"],
    }
    criterios["ACEPTADA"] = all(criterios.values())
    return criterios
