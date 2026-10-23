"""Reference methods to prove the GA is better than trivial alternatives."""
from __future__ import annotations

import numpy as np

from .evaluation import Evaluator
from .ga import random_population, rank_values
from .geo import destination
from .scenario import Scenario


def random_search(scenario: Scenario, n_evaluations: int, seed: int = 0, batch: int = 2000):
    """Best of `n_evaluations` uniformly random configurations (Deb ranking).
    Returns (best_config, best_so_far_fitness_curve)."""
    rng = np.random.default_rng(seed)
    ev = Evaluator(scenario)
    best, best_rank, curve = None, -np.inf, []
    done = 0
    while done < n_evaluations:
        n = min(batch, n_evaluations - done)
        pop = random_population(rng, scenario, n)
        b = ev.evaluate_population(pop)
        r = rank_values(b, "deb", 0.0)
        i = int(np.argmax(r))
        if r[i] > best_rank:
            best, best_rank = pop[i].copy(), r[i]
        done += n
        curve.append((done, float(best_rank)))
    return best, curve


def greedy_placement(scenario: Scenario, alt_step_km: float = 50.0):
    """Constructive heuristic: add satellites one by one, each time choosing
    the feasible candidate (around region centres x altitude grid) with the
    largest fitness gain. Mimics what a human designer would do."""
    ev = Evaluator(scenario)
    alts = np.arange(scenario.alt_min_km, scenario.alt_max_km + 1e-9, alt_step_km)
    cands = []
    for r in scenario.regions:
        pts = [(r.lat, r.lon)]
        for dist in (1.0, 2.0, 3.5, 5.0, 7.0):
            bearings = np.arange(0, 360, 45.0)
            la, lo = destination(r.lat, r.lon, bearings, dist)
            pts.extend(zip(la, lo))
        for la, lo in pts:
            for h in alts:
                cands.append((la, lo, h))
    cands = np.array(cands)

    chosen = np.zeros((0, 3))
    for _ in range(scenario.n_satellites):
        pop = np.concatenate(
            [np.repeat(chosen[None], len(cands), axis=0), cands[:, None, :]], axis=1
        )
        sc_part = scenario.with_params(n_satellites=pop.shape[1])
        part = Evaluator(sc_part)
        b = part.evaluate_population(pop)
        r = rank_values(b, "deb", 0.0)
        chosen = pop[int(np.argmax(r))]
    return chosen, ev.evaluate(chosen)
