import numpy as np
import pytest

from astroshield.evaluation import (
    Evaluator,
    acceptance,
    footprint_half_angle,
    list_violations,
    min_altitude_for_full_view,
    reference_upper_bound,
)
from astroshield.geo import angular_distance, destination, disk_samples, km_to_deg, wrap_lon
from astroshield.scenario import Zone, default_scenario, initial_scenario


def overhead_config(scenario, alt=900.0):
    """One satellite over each region centre; spares far apart over oceans."""
    rows = [(r.lat, r.lon, alt) for r in scenario.regions]
    spares = [(-60.0, -150.0, alt), (-60.0, 60.0, alt)]
    return np.array((rows + spares)[: scenario.n_satellites])


# ---------------------------------------------------------------- geometry
def test_angular_distance_known_values():
    assert angular_distance(0, 0, 0, 90) == pytest.approx(90)
    assert angular_distance(90, 0, -90, 0) == pytest.approx(180)
    assert angular_distance(10, 179, 10, -179) == pytest.approx(2 * np.cos(np.radians(10)), rel=1e-3)


def test_destination_travels_requested_distance():
    lat, lon = destination(20.5, -89.0, np.arange(0, 360, 30), 7.0)
    assert np.allclose(angular_distance(20.5, -89.0, lat, lon), 7.0)


def test_wrap_lon_range():
    assert wrap_lon(190) == pytest.approx(-170)
    assert wrap_lon(-180) == pytest.approx(-180)


def test_disk_samples_cover_exactly_the_region():
    pts = disk_samples(0, 0, 3.0, rings=3)
    assert len(pts) == 1 + 8 + 16 + 24
    d = angular_distance(0, 0, pts[:, 0], pts[:, 1])
    assert d.max() == pytest.approx(3.0)


# ---------------------------------------------------------------- coverage
def test_footprint_grows_with_altitude():
    lam = footprint_half_angle(np.linspace(500, 2000, 20), 30)
    assert np.all(np.diff(lam) > 0)


def test_lowest_altitude_cannot_see_whole_region():
    sc = initial_scenario()
    assert footprint_half_angle(500, 30) < km_to_deg(300)
    assert 500 < min_altitude_for_full_view(300, sc) < 600


def test_satellite_overhead_covers_its_region_fully():
    sc = initial_scenario()
    ev = Evaluator(sc).evaluate(overhead_config(sc))
    assert all(r.coverage == 1.0 and r.covered for r in ev.regions)
    assert 0 < ev.fitness <= 1


def test_far_satellites_cover_nothing():
    sc = initial_scenario()
    cfg = np.tile([-80.0, 0.0, 2000.0], (8, 1))
    cfg[:, 1] = np.arange(8) * 45
    ev = Evaluator(sc).evaluate(cfg)
    assert ev.n_covered == 0 and ev.fitness == 0


def test_priority_weights_change_fitness():
    sc = initial_scenario()
    cfg = overhead_config(sc)
    cfg[0] = (-60, 170, 900)  # leave Yucatán (alta) uncovered
    base = Evaluator(sc).evaluate(cfg).fitness
    lower = Evaluator(sc.with_priority("Península de Yucatán", "normal")).evaluate(cfg).fitness
    assert lower > base  # missing a Normal region costs less than missing an Alta one


def test_batch_and_single_evaluation_agree():
    sc = default_scenario()
    rng = np.random.default_rng(3)
    pop = np.stack([overhead_config(sc) + rng.normal(0, [1, 1, 10], (8, 3)) for _ in range(5)])
    ev = Evaluator(sc)
    batch = ev.evaluate_population(pop)
    for i in range(5):
        single = ev.evaluate(pop[i])
        assert single.fitness == pytest.approx(batch["fitness"][i])
        assert single.feasible == bool(batch["feasible"][i])


# ------------------------------------------------------------- constraints
@pytest.mark.parametrize("zone_name", ["Atlántico Norte", "Pacífico Sur", "Polar Norte", "Objeto A", "Objeto B"])
def test_satellite_inside_each_zone_is_invalid(zone_name):
    sc = default_scenario()
    z = next(z for z in sc.zones if z.name == zone_name)
    cfg = overhead_config(sc)
    cfg[7, :2] = destination(z.lat, z.lon, 45, z.radius_deg * 0.9)
    ev = Evaluator(sc).evaluate(cfg)
    assert not ev.feasible
    assert [v.target for v in ev.violations] == [zone_name]
    assert ev.violation == pytest.approx(z.radius_deg * 0.1, rel=1e-6)


def test_satellite_just_outside_zone_is_valid():
    sc = default_scenario()
    z = sc.zones[0]
    cfg = overhead_config(sc)
    cfg[7, :2] = destination(z.lat, z.lon, 90, z.radius_deg + 0.01)
    assert Evaluator(sc).evaluate(cfg).feasible


def test_min_separation_is_enforced():
    sc = default_scenario()
    cfg = overhead_config(sc)
    cfg[7] = (cfg[0, 0] + 1.0, cfg[0, 1], 900)  # 1° from satellite 0 (< 2°)
    v = list_violations(cfg, sc)
    assert len(v) == 1 and v[0].constraint == "separation"


def test_new_zone_invalidates_previous_configuration():
    sc = default_scenario()
    cfg = overhead_config(sc)
    assert Evaluator(sc).evaluate(cfg).feasible
    changed = sc.with_zone(Zone("Nueva", cfg[3, 0], cfg[3, 1], 3.0))
    ev = Evaluator(changed).evaluate(cfg)
    assert not ev.feasible and ev.violations[0].satellite == 3


def test_reference_bound_is_above_known_solution():
    sc = default_scenario()
    ev = Evaluator(sc).evaluate(overhead_config(sc, alt=520))
    assert ev.fitness <= reference_upper_bound(sc)["fitness"]
    assert set(acceptance(ev, sc)) >= {"C1 válida (sin violaciones)", "ACEPTADA"}


def test_acceptance_redundancy_demand_adapts_to_spare_satellites():
    # Three Alta regions but only two spare satellites: two redundant Alta
    # regions must be enough to satisfy C3.
    sc = default_scenario().with_priority("Interior de Australia", "alta")
    cfg = overhead_config(sc, alt=520)
    cfg[6] = (sc.regions[0].lat + 2.5, sc.regions[0].lon, 1300)  # 2nd sat over Yucatán
    cfg[7] = (sc.regions[1].lat + 2.5, sc.regions[1].lon, 1300)  # 2nd sat over Amazonía
    checks = acceptance(Evaluator(sc).evaluate(cfg), sc)
    c3 = next(k for k in checks if k.startswith("C3"))
    assert "≥2" in c3 and checks[c3]
