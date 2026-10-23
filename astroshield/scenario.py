"""Problem data: regions to observe, forbidden zones and model parameters.

A Scenario is immutable. Every "change of conditions" (section 3.3 of the
brief) produces a new Scenario via the `with_*` helpers, so previous
configurations can be re-validated against the new one.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from typing import Tuple

# How the brief's qualitative priorities become numeric weights.
# Alta counts three times a Normal region; Media twice.
PRIORITY_WEIGHTS = {"alta": 3.0, "media": 2.0, "normal": 1.0}


@dataclass(frozen=True)
class Region:
    name: str
    lat: float
    lon: float
    priority: str  # "alta" | "media" | "normal"
    radius_km: float = 300.0

    @property
    def weight(self) -> float:
        return PRIORITY_WEIGHTS[self.priority]


@dataclass(frozen=True)
class Zone:
    """Forbidden cap on the sphere. A satellite whose sub-satellite point lies
    inside the cap (at any altitude) violates it."""

    name: str
    lat: float
    lon: float
    radius_deg: float
    kind: str = "debris"  # "debris" | "occupied"


@dataclass(frozen=True)
class Scenario:
    regions: Tuple[Region, ...]
    zones: Tuple[Zone, ...] = ()
    name: str = "base"
    n_satellites: int = 8
    alt_min_km: float = 500.0
    alt_max_km: float = 2000.0
    sensor_half_angle_deg: float = 30.0
    min_separation_deg: float = 2.0
    coverage_threshold: float = 0.95
    # Fitness weights (sum to 1): single coverage, double coverage, resolution.
    w_coverage: float = 0.70
    w_redundancy: float = 0.15
    w_resolution: float = 0.15
    sample_rings: int = 3
    notes: Tuple[str, ...] = field(default_factory=tuple)

    # --- changes of conditions -------------------------------------------
    def renamed(self, name: str, note: str = "") -> "Scenario":
        notes = self.notes + ((note,) if note else ())
        return replace(self, name=name, notes=notes)

    def with_zone(self, zone: Zone, name: str = None) -> "Scenario":
        return replace(
            self,
            zones=self.zones + (zone,),
            name=name or f"{self.name}+{zone.name}",
            notes=self.notes + (f"nueva zona {zone.name} ({zone.radius_deg}°)",),
        )

    def without_zone(self, zone_name: str, name: str = None) -> "Scenario":
        return replace(
            self,
            zones=tuple(z for z in self.zones if z.name != zone_name),
            name=name or f"{self.name}-{zone_name}",
        )

    def with_priority(self, region_name: str, priority: str, name: str = None) -> "Scenario":
        if priority not in PRIORITY_WEIGHTS:
            raise ValueError(f"unknown priority {priority!r}")
        if region_name not in {r.name for r in self.regions}:
            raise KeyError(region_name)
        regions = tuple(
            replace(r, priority=priority) if r.name == region_name else r for r in self.regions
        )
        return replace(
            self,
            regions=regions,
            name=name or f"{self.name}:{region_name}={priority}",
            notes=self.notes + (f"prioridad {region_name} -> {priority}",),
        )

    def with_params(self, name: str = None, **params) -> "Scenario":
        return replace(self, name=name or self.name, **params)

    @property
    def debris_zones(self):
        return tuple(z for z in self.zones if z.kind == "debris")

    @property
    def occupied_zones(self):
        return tuple(z for z in self.zones if z.kind == "occupied")

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, **kw)


REGIONS = (
    Region("Península de Yucatán", 20.5, -89.0, "alta"),
    Region("Amazonía brasileña", -3.5, -62.0, "alta"),
    Region("California", 36.8, -119.4, "media"),
    Region("Sahel", 15.0, 0.0, "media"),
    Region("Japón", 36.0, 138.0, "media"),
    Region("Interior de Australia", -25.0, 133.0, "normal"),
)

DEBRIS_ZONES = (
    Zone("Atlántico Norte", 45.0, -35.0, 12.0, "debris"),
    Zone("Pacífico Sur", -30.0, -120.0, 10.0, "debris"),
    Zone("Polar Norte", 78.0, 30.0, 8.0, "debris"),
)

OCCUPIED_ZONES = (
    Zone("Objeto A", 10.0, 45.0, 5.0, "occupied"),
    Zone("Objeto B", -15.0, 110.0, 5.0, "occupied"),
)


def initial_scenario() -> Scenario:
    """Stage 1: regions only, no spatial restrictions."""
    return Scenario(regions=REGIONS, zones=(), name="etapa1-sin-restricciones")


def default_scenario() -> Scenario:
    """Stage 2: regions + debris zones + occupied positions."""
    return Scenario(regions=REGIONS, zones=DEBRIS_ZONES + OCCUPIED_ZONES, name="base")
