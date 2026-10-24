"""Datos del problema: regiones a observar, zonas prohibidas y parámetros del modelo.

Un Escenario es inmutable. Cada "cambio de condiciones" (sección 3.3 del
enunciado) produce un Escenario nuevo con los métodos `con_*`, para poder
revalidar las configuraciones anteriores contra el nuevo.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from typing import Tuple

# Cómo se traducen las prioridades cualitativas del enunciado a pesos numéricos.
# Una región Alta cuenta el triple que una Normal; una Media, el doble.
PESOS_PRIORIDAD = {"alta": 3.0, "media": 2.0, "normal": 1.0}


@dataclass(frozen=True)
class Region:
    nombre: str
    lat: float
    lon: float
    prioridad: str  # "alta" | "media" | "normal"
    radio_km: float = 300.0

    @property
    def peso(self) -> float:
        return PESOS_PRIORIDAD[self.prioridad]


@dataclass(frozen=True)
class Zona:
    """Casquete prohibido sobre la esfera. Un satélite cuyo punto subsatelital
    cae dentro del casquete (a cualquier altitud) lo viola."""

    nombre: str
    lat: float
    lon: float
    radio_grados: float
    tipo: str = "desechos"  # "desechos" | "ocupada"


@dataclass(frozen=True)
class Escenario:
    regiones: Tuple[Region, ...]
    zonas: Tuple[Zona, ...] = ()
    nombre: str = "base"
    n_satelites: int = 8
    alt_min_km: float = 500.0
    alt_max_km: float = 2000.0
    semiangulo_sensor_grados: float = 30.0
    separacion_min_grados: float = 2.0
    umbral_cobertura: float = 0.95
    # Pesos del fitness (suman 1): cobertura simple, cobertura doble, resolución.
    w_cobertura: float = 0.70
    w_redundancia: float = 0.15
    w_resolucion: float = 0.15
    anillos_muestra: int = 3
    notas: Tuple[str, ...] = field(default_factory=tuple)

    # --- cambios de condiciones -----------------------------------------
    def renombrado(self, nombre: str, nota: str = "") -> "Escenario":
        notas = self.notas + ((nota,) if nota else ())
        return replace(self, nombre=nombre, notas=notas)

    def con_zona(self, zona: Zona, nombre: str = None) -> "Escenario":
        return replace(
            self,
            zonas=self.zonas + (zona,),
            nombre=nombre or f"{self.nombre}+{zona.nombre}",
            notas=self.notas + (f"nueva zona {zona.nombre} ({zona.radio_grados}°)",),
        )

    def sin_zona(self, nombre_zona: str, nombre: str = None) -> "Escenario":
        return replace(
            self,
            zonas=tuple(z for z in self.zonas if z.nombre != nombre_zona),
            nombre=nombre or f"{self.nombre}-{nombre_zona}",
        )

    def con_prioridad(self, nombre_region: str, prioridad: str, nombre: str = None) -> "Escenario":
        if prioridad not in PESOS_PRIORIDAD:
            raise ValueError(f"prioridad desconocida {prioridad!r}")
        if nombre_region not in {r.nombre for r in self.regiones}:
            raise KeyError(nombre_region)
        regiones = tuple(
            replace(r, prioridad=prioridad) if r.nombre == nombre_region else r for r in self.regiones
        )
        return replace(
            self,
            regiones=regiones,
            nombre=nombre or f"{self.nombre}:{nombre_region}={prioridad}",
            notas=self.notas + (f"prioridad {nombre_region} -> {prioridad}",),
        )

    def con_parametros(self, nombre: str = None, **parametros) -> "Escenario":
        return replace(self, nombre=nombre or self.nombre, **parametros)

    @property
    def zonas_desechos(self):
        return tuple(z for z in self.zonas if z.tipo == "desechos")

    @property
    def zonas_ocupadas(self):
        return tuple(z for z in self.zonas if z.tipo == "ocupada")

    def a_dict(self) -> dict:
        return asdict(self)

    def a_json(self, **kw) -> str:
        return json.dumps(self.a_dict(), ensure_ascii=False, **kw)


REGIONES = (
    Region("Península de Yucatán", 20.5, -89.0, "alta"),
    Region("Amazonía brasileña", -3.5, -62.0, "alta"),
    Region("California", 36.8, -119.4, "media"),
    Region("Sahel", 15.0, 0.0, "media"),
    Region("Japón", 36.0, 138.0, "media"),
    Region("Interior de Australia", -25.0, 133.0, "normal"),
)

ZONAS_DESECHOS = (
    Zona("Atlántico Norte", 45.0, -35.0, 12.0, "desechos"),
    Zona("Pacífico Sur", -30.0, -120.0, 10.0, "desechos"),
    Zona("Polar Norte", 78.0, 30.0, 8.0, "desechos"),
)

ZONAS_OCUPADAS = (
    Zona("Objeto A", 10.0, 45.0, 5.0, "ocupada"),
    Zona("Objeto B", -15.0, 110.0, 5.0, "ocupada"),
)


def escenario_inicial() -> Escenario:
    """Etapa 1: solo regiones, sin restricciones espaciales."""
    return Escenario(regiones=REGIONES, zonas=(), nombre="etapa1-sin-restricciones")


def escenario_base() -> Escenario:
    """Etapa 2: regiones + zonas de desechos + posiciones ocupadas."""
    return Escenario(regiones=REGIONES, zonas=ZONAS_DESECHOS + ZONAS_OCUPADAS, nombre="base")
