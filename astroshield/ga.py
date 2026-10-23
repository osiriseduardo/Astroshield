"""Real-coded genetic algorithm for the constellation problem.

Genome: (n_satellites, 3) array of (lat, lon, alt_km).

Loop per generation:
  1. rank population (constraint handling: Deb's feasibility rules by default)
  2. elitism: copy the best `elite_size` individuals unchanged
  3. tournament selection of parents
  4. aligned crossover: parent B's satellites are matched to parent A's with
     the Hungarian algorithm before mixing, because the satellite order in
     the genome is arbitrary (permutation symmetry)
  5. mutation: Gaussian step on the sphere + altitude jitter, both with
     exponentially decaying sigma; rare random relocation keeps exploring
  6. repair (probabilistic): satellites inside a forbidden zone are pushed
     to its border along the great circle from the zone centre
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Callable, List, Optional

import numpy as np
from scipy.optimize import linear_sum_assignment

from .evaluation import Evaluation, Evaluator
from .geo import angular_distance, destination, from_unit, gaussian_step, initial_bearing, random_points, to_unit
from .scenario import Scenario

CONSTRAINT_MODES = ("deb", "penalty", "none")


@dataclass
class GAConfig:
    population_size: int = 120
    generations: int = 400
    tournament_size: int = 4
    crossover_rate: float = 0.9
    blend_rate: float = 0.3  # per-satellite chance of arithmetic (vs. swap) crossover
    mutation_rate: float = 0.15  # per-satellite
    sigma_start_deg: float = 12.0
    sigma_end_deg: float = 0.05
    alt_sigma_start_km: float = 250.0
    alt_sigma_end_km: float = 2.0
    reset_rate: float = 0.02  # per-satellite random relocation
    repair_rate: float = 0.3  # per-child probability of applying repair
    elite_size: int = 4
    constraint_handling: str = "deb"  # "deb" | "penalty" | "none"
    penalty_factor: float = 0.05  # fitness lost per degree of intrusion
    patience: Optional[int] = None  # stop after N gens without improvement

    def __post_init__(self):
        if self.constraint_handling not in CONSTRAINT_MODES:
            raise ValueError(f"constraint_handling must be one of {CONSTRAINT_MODES}")
        if self.elite_size >= self.population_size:
            raise ValueError("elite_size must be smaller than population_size")

    def to_dict(self):
        return asdict(self)


@dataclass
class GAResult:
    scenario: Scenario
    config: GAConfig
    seed: int
    best: np.ndarray
    best_eval: Evaluation
    initial_best: np.ndarray
    initial_eval: Evaluation
    history: List[dict]
    final_population: np.ndarray
    evaluations: int
    elapsed_s: float
    stop_reason: str
    snapshots: dict = field(default_factory=dict)  # generation -> best config

    @property
    def found_feasible(self) -> bool:
        return self.best_eval.feasible

    def history_frame(self):
        import pandas as pd

        return pd.DataFrame(self.history)


# ---------------------------------------------------------------- operators
def random_population(rng, scenario: Scenario, n: int) -> np.ndarray:
    s = scenario.n_satellites
    lat, lon = random_points(rng, n * s)
    alt = rng.uniform(scenario.alt_min_km, scenario.alt_max_km, n * s)
    return np.stack([lat, lon, alt], axis=-1).reshape(n, s, 3)


def rank_values(batch: dict, mode: str, penalty: float) -> np.ndarray:
    """Higher is better. Deb: any feasible beats any infeasible; infeasible
    ones are ordered by total violation."""
    f, v = batch["fitness"], batch["violation"]
    if mode == "none":
        return f.copy()
    if mode == "penalty":
        return f - penalty * v
    return np.where(batch["feasible"], f, -1.0 - v)


def align(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Reorder b's satellites so b[i] is the satellite closest to a[i]."""
    cost = angular_distance(a[:, None, 0], a[:, None, 1], b[None, :, 0], b[None, :, 1])
    _, cols = linear_sum_assignment(cost)
    return b[cols]


def crossover(rng, a, b, blend_rate):
    b = align(a, b)
    s = len(a)
    c1, c2 = a.copy(), b.copy()
    swap = rng.random(s) < 0.5
    c1[swap], c2[swap] = b[swap], a[swap]
    blend = rng.random(s) < blend_rate
    if blend.any():
        w = rng.random(blend.sum())[:, None]
        ua, ub = to_unit(a[blend, 0], a[blend, 1]), to_unit(b[blend, 0], b[blend, 1])
        for child, ww in ((c1, w), (c2, 1 - w)):
            v = ww * ua + (1 - ww) * ub
            ok = np.linalg.norm(v, axis=1) > 1e-6  # skip antipodal pairs
            lat, lon = from_unit(np.where(ok[:, None], v, ua))
            idx = np.flatnonzero(blend)
            child[idx, 0], child[idx, 1] = lat, lon
            child[idx, 2] = ww[:, 0] * a[blend, 2] + (1 - ww[:, 0]) * b[blend, 2]
    return c1, c2


def reflect_altitude(alt, lo, hi):
    span = hi - lo
    x = np.mod(alt - lo, 2 * span)
    return lo + np.where(x > span, 2 * span - x, x)


def mutate(rng, ind, scenario, rate, sigma_deg, alt_sigma, reset_rate):
    s = len(ind)
    m = rng.random(s) < rate
    if m.any():
        lat, lon = gaussian_step(rng, ind[m, 0], ind[m, 1], sigma_deg)
        ind[m, 0], ind[m, 1] = lat, lon
        ind[m, 2] = reflect_altitude(
            ind[m, 2] + rng.normal(0, alt_sigma, m.sum()), scenario.alt_min_km, scenario.alt_max_km
        )
    r = rng.random(s) < reset_rate
    if r.any():
        lat, lon = random_points(rng, r.sum())
        ind[r, 0], ind[r, 1] = lat, lon
        ind[r, 2] = rng.uniform(scenario.alt_min_km, scenario.alt_max_km, r.sum())
    return ind


def repair(rng, ind, scenario: Scenario, margin_deg=0.25, max_iter=4):
    """Push satellites out of forbidden zones (in place). Zones may overlap,
    so the push is repeated a few times; leftovers are left to selection."""
    for _ in range(max_iter):
        moved = False
        for z in scenario.zones:
            d = angular_distance(ind[:, 0], ind[:, 1], z.lat, z.lon)
            bad = np.flatnonzero(d < z.radius_deg)
            for i in bad:
                if d[i] < 1e-6:
                    bearing = rng.uniform(0, 360)
                else:
                    bearing = initial_bearing(z.lat, z.lon, ind[i, 0], ind[i, 1])
                ind[i, 0], ind[i, 1] = destination(z.lat, z.lon, bearing, z.radius_deg + margin_deg)
                moved = True
        if not moved:
            break
    return ind


def diversity(rng, pop, n_pairs=12):
    """Mean angular distance between aligned satellites of random pairs."""
    if len(pop) < 2:
        return 0.0
    out = []
    for _ in range(n_pairs):
        i, j = rng.choice(len(pop), 2, replace=False)
        b = align(pop[i], pop[j])
        out.append(angular_distance(pop[i][:, 0], pop[i][:, 1], b[:, 0], b[:, 1]).mean())
    return float(np.mean(out))


# --------------------------------------------------------------------- main
def run_ga(
    scenario: Scenario,
    config: GAConfig = None,
    seed: int = 0,
    initial_population: np.ndarray = None,
    snapshot_every: int = 0,
    callback: Callable[[dict], None] = None,
) -> GAResult:
    """Run the GA and return the best configuration plus full history."""
    cfg = config or GAConfig()
    rng = np.random.default_rng(seed)
    ev = Evaluator(scenario)
    p = cfg.population_size

    pop = random_population(rng, scenario, p)
    if initial_population is not None:  # warm start (change of conditions)
        seedpop = np.asarray(initial_population, dtype=float)[:p]
        pop[: len(seedpop)] = seedpop

    t0 = time.perf_counter()
    batch = ev.evaluate_population(pop)
    rank = rank_values(batch, cfg.constraint_handling, cfg.penalty_factor)
    i0 = int(np.argmax(rank))
    initial_best = pop[i0].copy()
    best, best_rank = pop[i0].copy(), rank[i0]
    history, snapshots = [], {0: initial_best.copy()}
    stale, stop_reason = 0, "generaciones completadas"

    def log(gen, sigma, alt_sigma):
        feas = batch["feasible"]
        f = batch["fitness"]
        row = {
            "generation": gen,
            "best_rank": float(rank.max()),
            "best_fitness": float(f[feas].max()) if feas.any() else np.nan,
            "mean_fitness": float(f.mean()),
            "std_fitness": float(f.std()),
            "worst_fitness": float(f.min()),
            "feasible_ratio": float(feas.mean()),
            "mean_violation": float(batch["violation"].mean()),
            "best_so_far_rank": float(best_rank),
            "regions_covered_best": int(
                (batch["coverage"][int(np.argmax(rank))] >= scenario.coverage_threshold - 1e-12).sum()
            ),
            "diversity_deg": diversity(rng, pop),
            "sigma_deg": float(sigma),
            "alt_sigma_km": float(alt_sigma),
            "evaluations": ev.n_evaluations,
        }
        history.append(row)
        if callback:
            callback(row)

    log(0, cfg.sigma_start_deg, cfg.alt_sigma_start_km)
    for gen in range(1, cfg.generations + 1):
        t = (gen - 1) / max(cfg.generations - 1, 1)
        sigma = cfg.sigma_start_deg * (cfg.sigma_end_deg / cfg.sigma_start_deg) ** t
        alt_sigma = cfg.alt_sigma_start_km * (cfg.alt_sigma_end_km / cfg.alt_sigma_start_km) ** t

        order = np.argsort(-rank)
        children = [pop[i].copy() for i in order[: cfg.elite_size]]
        while len(children) < p:
            cand = rng.integers(0, p, size=(2, cfg.tournament_size))
            pa, pb = (pop[c[np.argmax(rank[c])]] for c in cand)
            if rng.random() < cfg.crossover_rate:
                c1, c2 = crossover(rng, pa, pb, cfg.blend_rate)
            else:
                c1, c2 = pa.copy(), pb.copy()
            for c in (c1, c2):
                mutate(rng, c, scenario, cfg.mutation_rate, sigma, alt_sigma, cfg.reset_rate)
                if cfg.constraint_handling != "none" and rng.random() < cfg.repair_rate:
                    repair(rng, c, scenario)
                children.append(c)
        pop = np.array(children[:p])
        batch = ev.evaluate_population(pop)
        rank = rank_values(batch, cfg.constraint_handling, cfg.penalty_factor)

        i = int(np.argmax(rank))
        if rank[i] > best_rank + 1e-9:
            best, best_rank, stale = pop[i].copy(), rank[i], 0
        else:
            stale += 1
        log(gen, sigma, alt_sigma)
        if snapshot_every and gen % snapshot_every == 0:
            snapshots[gen] = best.copy()
        if cfg.patience and stale >= cfg.patience:
            stop_reason = f"estancamiento ({cfg.patience} generaciones sin mejora)"
            break

    snapshots[history[-1]["generation"]] = best.copy()
    return GAResult(
        scenario=scenario,
        config=cfg,
        seed=seed,
        best=best,
        best_eval=ev.evaluate(best),
        initial_best=initial_best,
        initial_eval=ev.evaluate(initial_best),
        history=history,
        final_population=pop,
        evaluations=ev.n_evaluations,
        elapsed_s=time.perf_counter() - t0,
        stop_reason=stop_reason,
        snapshots=snapshots,
    )
