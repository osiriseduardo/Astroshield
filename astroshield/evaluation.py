"""Coverage model, constraint checking and fitness.

A configuration is a float array of shape (n_satellites, 3) whose columns
are (latitude deg, longitude deg, altitude km) of each satellite's
sub-satellite point. A population is an array (P, n_satellites, 3).

Coverage model
--------------
Each satellite carries a nadir-pointing sensor with half-angle eta. Its
ground footprint is a spherical cap of central angle

    lambda(h) = asin((R + h) / R * sin(eta)) - eta

(or the horizon angle acos(R / (R + h)) if the sensor sees past it).
Each region is a 300 km disk discretised into sample points; a point is
seen by a satellite when its angular distance to the sub-satellite point
is <= lambda(h). A region is "covered" when the fraction of its points
seen by at least one satellite reaches `coverage_threshold`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from .geo import EARTH_RADIUS_KM, angular_distance, deg_to_km, disk_samples, km_to_deg, to_unit
from .scenario import Scenario

FEASIBILITY_TOL = 1e-9


def footprint_half_angle(alt_km, sensor_half_angle_deg):
    """Central angle (deg) of the footprint for altitude(s) `alt_km`."""
    alt_km = np.asarray(alt_km, dtype=float)
    eta = np.radians(sensor_half_angle_deg)
    ratio = (EARTH_RADIUS_KM + alt_km) / EARTH_RADIUS_KM * np.sin(eta)
    horizon = np.arccos(EARTH_RADIUS_KM / (EARTH_RADIUS_KM + alt_km))
    lam = np.where(ratio < 1.0, np.arcsin(np.minimum(ratio, 1.0)) - eta, horizon)
    return np.degrees(np.minimum(lam, horizon))


def resolution_quality(alt_km, alt_min_km, alt_max_km):
    """1.0 at the lowest allowed altitude, 0.0 at the highest (linear)."""
    return 1.0 - (np.asarray(alt_km) - alt_min_km) / (alt_max_km - alt_min_km)


@dataclass
class RegionResult:
    name: str
    priority: str
    weight: float
    coverage: float  # fraction of points seen by >= 1 satellite
    redundancy: float  # fraction of points seen by >= 2 satellites
    resolution: float  # mean best resolution quality over points (0 if unseen)
    score: float
    covered: bool
    satellites: List[int]  # satellites that see at least one point


@dataclass
class Violation:
    satellite: int
    constraint: str  # "debris" | "occupied" | "separation"
    target: str
    distance_deg: float
    limit_deg: float

    @property
    def intrusion_deg(self) -> float:
        return self.limit_deg - self.distance_deg


@dataclass
class Evaluation:
    config: np.ndarray
    fitness: float
    feasible: bool
    violation: float  # total intrusion in degrees (0 when feasible)
    regions: List[RegionResult]
    violations: List[Violation] = field(default_factory=list)

    @property
    def n_covered(self) -> int:
        return sum(r.covered for r in self.regions)

    @property
    def weighted_coverage(self) -> float:
        w = np.array([r.weight for r in self.regions])
        c = np.array([r.coverage for r in self.regions])
        return float((w * c).sum() / w.sum())

    def region_table(self):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "región": r.name,
                    "prioridad": r.priority,
                    "peso": r.weight,
                    "cobertura": round(r.coverage, 3),
                    "redundancia": round(r.redundancy, 3),
                    "resolución": round(r.resolution, 3),
                    "score": round(r.score, 3),
                    "cubierta": "sí" if r.covered else "NO",
                    "satélites": ",".join(map(str, r.satellites)) or "-",
                }
                for r in self.regions
            ]
        )

    def satellite_table(self, scenario: Scenario):
        import pandas as pd

        lam = footprint_half_angle(self.config[:, 2], scenario.sensor_half_angle_deg)
        return pd.DataFrame(
            {
                "sat": np.arange(len(self.config)),
                "lat": self.config[:, 0].round(2),
                "lon": self.config[:, 1].round(2),
                "alt_km": self.config[:, 2].round(0),
                "huella_km": deg_to_km(lam).round(0),
            }
        )


class Evaluator:
    """Pre-computes the scenario geometry and evaluates populations fast."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        pts, owner = [], []
        for i, r in enumerate(scenario.regions):
            s = disk_samples(r.lat, r.lon, km_to_deg(r.radius_km), scenario.sample_rings)
            pts.append(s)
            owner.extend([i] * len(s))
        pts = np.vstack(pts)
        self.points = pts
        self.point_owner = np.array(owner)
        self.point_unit = to_unit(pts[:, 0], pts[:, 1])  # (M, 3)
        counts = np.bincount(self.point_owner, minlength=len(scenario.regions))
        self.region_offsets = np.concatenate([[0], np.cumsum(counts)[:-1]])
        self.region_counts = counts
        self.weights = np.array([r.weight for r in scenario.regions])
        if scenario.zones:
            self.zone_unit = to_unit(
                np.array([z.lat for z in scenario.zones]), np.array([z.lon for z in scenario.zones])
            )
            self.zone_radius = np.array([z.radius_deg for z in scenario.zones])
        else:
            self.zone_unit = np.zeros((0, 3))
            self.zone_radius = np.zeros(0)
        self.n_evaluations = 0

    # ------------------------------------------------------------------ batch
    def _region_mean(self, per_point):
        """(P, M) -> (P, R) mean over each region's points."""
        sums = np.add.reduceat(per_point, self.region_offsets, axis=1)
        return sums / self.region_counts

    def evaluate_population(self, pop):
        """Vectorised evaluation of a population (P, S, 3).

        Returns a dict of arrays: fitness (P,), violation (P,), feasible (P,),
        coverage/redundancy/resolution/score (P, R).
        """
        sc = self.scenario
        pop = np.asarray(pop, dtype=float)
        self.n_evaluations += len(pop)
        sat_u = to_unit(pop[..., 0], pop[..., 1])  # (P, S, 3)
        alt = pop[..., 2]
        lam = footprint_half_angle(alt, sc.sensor_half_angle_deg)  # (P, S)

        cos_ang = np.einsum("psk,mk->psm", sat_u, self.point_unit)  # (P, S, M)
        inside = cos_ang >= np.cos(np.radians(lam))[..., None]
        count = inside.sum(axis=1)  # (P, M)
        q = resolution_quality(alt, sc.alt_min_km, sc.alt_max_km)  # (P, S)
        best_q = np.where(inside, q[..., None], 0.0).max(axis=1)  # (P, M)

        cov = self._region_mean((count >= 1).astype(float))
        red = self._region_mean((count >= 2).astype(float))
        res = self._region_mean(best_q)
        score = sc.w_coverage * cov + sc.w_redundancy * red + sc.w_resolution * res
        fitness = (score * self.weights).sum(axis=1) / self.weights.sum()

        violation = np.zeros(len(pop))
        if len(self.zone_radius):
            zang = np.degrees(
                np.arccos(np.clip(np.einsum("psk,zk->psz", sat_u, self.zone_unit), -1, 1))
            )
            violation += np.clip(self.zone_radius - zang, 0, None).sum(axis=(1, 2))
        if sc.min_separation_deg > 0 and pop.shape[1] > 1:
            sang = np.degrees(
                np.arccos(np.clip(np.einsum("psk,pqk->psq", sat_u, sat_u), -1, 1))
            )
            iu = np.triu_indices(pop.shape[1], k=1)
            violation += np.clip(sc.min_separation_deg - sang[:, iu[0], iu[1]], 0, None).sum(axis=1)

        return {
            "fitness": fitness,
            "violation": violation,
            "feasible": violation <= FEASIBILITY_TOL,
            "coverage": cov,
            "redundancy": red,
            "resolution": res,
            "score": score,
            "inside": inside,
        }

    # ----------------------------------------------------------------- single
    def evaluate(self, config) -> Evaluation:
        """Detailed evaluation of one configuration (S, 3)."""
        config = np.asarray(config, dtype=float)
        b = self.evaluate_population(config[None])
        sc = self.scenario
        inside = b["inside"][0]  # (S, M)
        regions = []
        for i, r in enumerate(sc.regions):
            sl = slice(self.region_offsets[i], self.region_offsets[i] + self.region_counts[i])
            sats = [int(s) for s in np.flatnonzero(inside[:, sl].any(axis=1))]
            cov = float(b["coverage"][0, i])
            regions.append(
                RegionResult(
                    name=r.name,
                    priority=r.priority,
                    weight=r.weight,
                    coverage=cov,
                    redundancy=float(b["redundancy"][0, i]),
                    resolution=float(b["resolution"][0, i]),
                    score=float(b["score"][0, i]),
                    covered=cov >= sc.coverage_threshold - 1e-12,
                    satellites=sats,
                )
            )
        return Evaluation(
            config=config.copy(),
            fitness=float(b["fitness"][0]),
            feasible=bool(b["feasible"][0]),
            violation=float(b["violation"][0]),
            regions=regions,
            violations=list_violations(config, sc),
        )


def list_violations(config, scenario: Scenario) -> List[Violation]:
    """Human-readable list of every constraint a configuration breaks."""
    out = []
    lat, lon = config[:, 0], config[:, 1]
    for z in scenario.zones:
        d = angular_distance(lat, lon, z.lat, z.lon)
        for s in np.flatnonzero(d < z.radius_deg):
            out.append(Violation(int(s), z.kind, z.name, float(d[s]), z.radius_deg))
    if scenario.min_separation_deg > 0:
        n = len(config)
        for i in range(n):
            for j in range(i + 1, n):
                d = float(angular_distance(lat[i], lon[i], lat[j], lon[j]))
                if d < scenario.min_separation_deg:
                    out.append(Violation(i, "separation", f"sat {j}", d, scenario.min_separation_deg))
    return out


def min_altitude_for_full_view(radius_km, scenario: Scenario, offset_deg=0.0):
    """Lowest altitude whose footprint covers a disk of `radius_km` whose
    centre is `offset_deg` away from the sub-satellite point (None if none)."""
    need = km_to_deg(radius_km) + offset_deg
    alts = np.arange(scenario.alt_min_km, scenario.alt_max_km + 1e-9, 1.0)
    ok = footprint_half_angle(alts, scenario.sensor_half_angle_deg) >= need
    return float(alts[ok][0]) if ok.any() else None


def reference_upper_bound(scenario: Scenario) -> dict:
    """Optimistic reference value of the fitness (a relaxation).

    Ignores forbidden zones and assumes each region gets its own satellite
    right over its centre at the lowest altitude that sees the whole disk;
    the spare satellites (n_satellites - n_regions) are given to the
    heaviest regions as full redundancy. Valid for this scenario because no
    footprint (max ~11°) can reach two regions at once (min gap ~30°).
    """
    regions = sorted(scenario.regions, key=lambda r: -r.weight)
    spares = max(scenario.n_satellites - len(regions), 0)
    total, detail = 0.0, {}
    for k, r in enumerate(regions):
        h = min_altitude_for_full_view(r.radius_km, scenario)
        if h is None:
            q, cov = 0.0, 0.0
        else:
            q, cov = float(resolution_quality(h, scenario.alt_min_km, scenario.alt_max_km)), 1.0
        red = 1.0 if (k < spares and cov > 0) else 0.0
        s = scenario.w_coverage * cov + scenario.w_redundancy * red + scenario.w_resolution * q
        detail[r.name] = {"alt_km": h, "score": s}
        total += r.weight * s
    return {"fitness": total / sum(r.weight for r in regions), "regions": detail}


def acceptance(ev: Evaluation, scenario: Scenario) -> dict:
    """Team criteria for 'good enough' (see docs/01_definicion_problema.md)."""
    alta = [r for r in ev.regions if r.priority == "alta"]
    checks = {
        "C1 válida (sin violaciones)": ev.feasible,
        "C2 todas las regiones cubiertas": ev.n_covered == len(ev.regions),
        "C3 regiones Alta con redundancia ≥ 95%": all(r.redundancy >= 0.95 for r in alta),
        "C4 fitness ≥ 90% de la cota de referencia": ev.fitness
        >= 0.90 * reference_upper_bound(scenario)["fitness"],
    }
    checks["ACEPTADA"] = all(checks.values())
    return checks
