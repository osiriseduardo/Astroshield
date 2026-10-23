import numpy as np
import pytest

from astroshield.baselines import greedy_placement, random_search
from astroshield.evaluation import Evaluator, reference_upper_bound
from astroshield.ga import GAConfig, align, random_population, reflect_altitude, repair, run_ga
from astroshield.geo import angular_distance
from astroshield.scenario import Zone, default_scenario

FAST = GAConfig(population_size=40, generations=60)


@pytest.fixture(scope="module")
def base_run():
    return run_ga(default_scenario(), FAST, seed=1)


def test_ga_improves_over_initial_population(base_run):
    assert base_run.best_eval.fitness > base_run.initial_eval.fitness + 0.2
    assert len(base_run.history) == FAST.generations + 1


def test_best_so_far_never_decreases(base_run):
    curve = [h["best_so_far_rank"] for h in base_run.history]
    assert all(b >= a - 1e-12 for a, b in zip(curve, curve[1:]))


def test_final_solution_respects_every_zone(base_run):
    sc = base_run.scenario
    best = base_run.best
    assert base_run.best_eval.feasible
    for z in sc.zones:
        assert angular_distance(best[:, 0], best[:, 1], z.lat, z.lon).min() >= z.radius_deg


def test_altitudes_stay_in_bounds(base_run):
    sc = base_run.scenario
    pop = base_run.final_population
    assert pop[..., 2].min() >= sc.alt_min_km and pop[..., 2].max() <= sc.alt_max_km


def test_same_seed_is_reproducible():
    sc = default_scenario()
    a = run_ga(sc, GAConfig(population_size=20, generations=10), seed=7)
    b = run_ga(sc, GAConfig(population_size=20, generations=10), seed=7)
    assert np.array_equal(a.best, b.best)


def test_impossible_constraints_are_reported_not_hidden():
    # 8 points on a sphere cannot all be 80° apart (Tammes bound ~74.9°).
    sc = default_scenario().with_params(min_separation_deg=80.0)
    r = run_ga(sc, GAConfig(population_size=30, generations=20), seed=0)
    assert not r.found_feasible
    assert r.best_eval.violation > 0 and r.best_eval.violations
    assert np.isnan(r.history[-1]["best_fitness"])


def test_unreachable_region_is_left_uncovered_but_solution_valid():
    sc = default_scenario().with_zone(Zone("Bloqueo Amazonía", -3.5, -62.0, 15.0))
    r = run_ga(sc, FAST, seed=0)
    amazon = next(x for x in r.best_eval.regions if x.name == "Amazonía brasileña")
    assert r.found_feasible and amazon.coverage == 0.0


def test_warm_start_keeps_seed_solution(base_run):
    r = run_ga(base_run.scenario, GAConfig(population_size=40, generations=1), seed=5,
               initial_population=base_run.best[None])
    assert r.initial_eval.fitness == pytest.approx(base_run.best_eval.fitness)


def test_ga_beats_random_search_with_same_budget(base_run):
    _, curve = random_search(base_run.scenario, base_run.evaluations, seed=1)
    assert base_run.best_eval.fitness > curve[-1][1]


def test_greedy_and_ga_below_reference_bound(base_run):
    sc = base_run.scenario
    bound = reference_upper_bound(sc)["fitness"]
    _, g = greedy_placement(sc)
    assert g.feasible and g.fitness <= bound and base_run.best_eval.fitness <= bound


# ---------------------------------------------------------------- operators
def test_repair_pushes_satellite_out_of_zone():
    sc = default_scenario()
    ind = np.array([[45.0, -35.0, 800.0], [44.0, -30.0, 800.0]])
    repair(np.random.default_rng(0), ind, sc)
    assert Evaluator(sc.with_params(n_satellites=2)).evaluate(ind).feasible


def test_align_matches_nearest_satellites():
    a = np.array([[0, 0, 1000], [0, 90, 1000], [45, 180, 1000]], float)
    b = a[[2, 0, 1]] + [0.5, 0.5, 0]
    assert np.allclose(align(a, b)[:, :2], a[:, :2] + 0.5)


def test_reflect_altitude_stays_inside():
    x = reflect_altitude(np.array([400.0, 2100.0, 4100.0, 1000.0]), 500, 2000)
    assert np.all((x >= 500) & (x <= 2000)) and x[3] == 1000


def test_invalid_constraint_mode_rejected():
    with pytest.raises(ValueError):
        GAConfig(constraint_handling="magic")


def test_random_population_shape():
    pop = random_population(np.random.default_rng(0), default_scenario(), 5)
    assert pop.shape == (5, 8, 3)
