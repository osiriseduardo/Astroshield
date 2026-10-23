"""Reproducible experiments behind Entregables 3 and 4.

Every function returns plain data (dicts / DataFrames / GAResult) so the
notebook can display it and tools/run_experiments.py can store it as JSON.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
from scipy import stats

from .baselines import greedy_placement, random_search
from .evaluation import Evaluator, acceptance, reference_upper_bound
from .ga import GAConfig, GAResult, align, run_ga
from .geo import angular_distance
from .scenario import Scenario, Zone, default_scenario, initial_scenario


# ----------------------------------------------------------------- helpers
def convergence_generation(result: GAResult, frac: float = 0.99):
    """First generation whose best-so-far reaches `frac` of the final value."""
    curve = np.array([h["best_so_far_rank"] for h in result.history])
    final = curve[-1]
    if final <= 0:
        return None
    return int(np.argmax(curve >= frac * final))


def first_full_coverage_generation(result: GAResult):
    n = len(result.scenario.regions)
    for h in result.history:
        if h["regions_covered_best"] == n and h["feasible_ratio"] > 0 and not np.isnan(h["best_fitness"]):
            return h["generation"]
    return None


def summarize(result: GAResult) -> dict:
    ev, sc = result.best_eval, result.scenario
    return {
        "scenario": sc.name,
        "seed": result.seed,
        "fitness": round(ev.fitness, 4),
        "initial_fitness": round(result.initial_eval.fitness, 4),
        "feasible": ev.feasible,
        "violation_deg": round(ev.violation, 3),
        "regions_covered": ev.n_covered,
        "weighted_coverage": round(ev.weighted_coverage, 4),
        "accepted": acceptance(ev, sc)["ACEPTADA"],
        "convergence_gen": convergence_generation(result),
        "full_coverage_gen": first_full_coverage_generation(result),
        "generations": result.history[-1]["generation"],
        "evaluations": result.evaluations,
        "time_s": round(result.elapsed_s, 2),
        "bound": round(reference_upper_bound(sc)["fitness"], 4),
    }


def solution_distance(a, b) -> float:
    """Mean angular distance (deg) between satellites after optimal matching."""
    b = align(a, b)
    return float(angular_distance(a[:, 0], a[:, 1], b[:, 0], b[:, 1]).mean())


def zone_margins(config, scenario: Scenario) -> pd.DataFrame:
    """For each zone: distance of the closest satellite and its margin."""
    rows = []
    for z in scenario.zones:
        d = angular_distance(config[:, 0], config[:, 1], z.lat, z.lon)
        rows.append(
            {
                "zona": z.name,
                "tipo": z.kind,
                "radio_deg": z.radius_deg,
                "sat_más_cercano": int(d.argmin()),
                "distancia_deg": round(float(d.min()), 2),
                "margen_deg": round(float(d.min() - z.radius_deg), 2),
                "respeta": bool(d.min() >= z.radius_deg),
            }
        )
    return pd.DataFrame(rows)


# ------------------------------------------------------------ experiments
def e1_initial(cfg: GAConfig = None, seed: int = 0) -> GAResult:
    """Stage 1: no spatial restrictions."""
    return run_ga(initial_scenario(), cfg, seed=seed, snapshot_every=25)


def e2_base(cfg: GAConfig = None, seed: int = 0) -> GAResult:
    """Stage 2 reference run (all restrictions) used by E2, E3, E4, E8, E9."""
    return run_ga(default_scenario(), cfg, seed=seed, snapshot_every=25)


def e3_e4_constraint_audit(results) -> pd.DataFrame:
    """Margins of every best solution to every zone, over many runs."""
    frames = []
    for r in results:
        df = zone_margins(r.best, r.scenario)
        df.insert(0, "seed", r.seed)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def e4_object_near_region(cfg: GAConfig = None, seed: int = 0) -> GAResult:
    """Occupied position moved next to the Sahel (2° from its centre)."""
    sc = default_scenario().without_zone("Objeto A").with_zone(
        Zone("Objeto A (reubicado)", 15.0, 2.0, 5.0, "occupied"), name="objeto-junto-al-Sahel"
    )
    return run_ga(sc, cfg, seed=seed)


def reduced_space_scenarios():
    base = default_scenario()
    r1 = base.with_zone(Zone("Desechos Golfo de México", 23.0, -90.0, 6.0), name="R1 +zona sobre Yucatán")
    r2 = r1.with_params(name="R2 R1 + techo 1200 km", alt_max_km=1200.0)
    r3 = r2.with_zone(Zone("Desechos Pacífico Norte", 40.0, 140.0, 5.0), name="R3 R2 + zona sobre Japón")
    return [base.renamed("R0 base"), r1, r2, r3]


def e5_reduced_space(cfg: GAConfig = None, seed: int = 0):
    """Progressively shrink the usable space. Also runs R1 *without*
    constraint handling to show what the restrictions prevent."""
    results = [run_ga(sc, cfg, seed=seed) for sc in reduced_space_scenarios()]
    unconstrained = run_ga(
        reduced_space_scenarios()[1], replace(cfg or GAConfig(), constraint_handling="none"), seed=seed
    )
    return results, unconstrained


def infeasible_scenarios():
    base = default_scenario()
    return {
        "I1 Amazonía inalcanzable": base.with_zone(
            Zone("Bloqueo Amazonía", -3.5, -62.0, 15.0), name="I1 Amazonía inalcanzable"
        ),
        "I2 solo 5 satélites": base.with_params(name="I2 solo 5 satélites", n_satellites=5),
        "I3 separación 80° imposible": base.with_params(
            name="I3 separación 80° imposible", min_separation_deg=80.0
        ),
    }


def e6_infeasible(cfg: GAConfig = None, seed: int = 0):
    return {k: run_ga(sc, cfg, seed=seed) for k, sc in infeasible_scenarios().items()}


def e7_variation(cfg: GAConfig = None, seeds=range(10)):
    """Repeated runs + baselines with the same evaluation budget."""
    sc = default_scenario()
    runs = [run_ga(sc, cfg, seed=s) for s in seeds]
    table = pd.DataFrame([summarize(r) for r in runs])
    budget = runs[0].evaluations
    rnd = [random_search(sc, budget, seed=1000 + s)[1][-1][1] for s in seeds]
    _, greedy_ev = greedy_placement(sc)
    ga_f = table["fitness"].to_numpy()
    mw = stats.mannwhitneyu(ga_f, rnd, alternative="greater")
    n = len(runs)
    dist = np.full((n, n), 0.0)
    for i in range(n):
        for j in range(i + 1, n):
            dist[i, j] = dist[j, i] = solution_distance(runs[i].best, runs[j].best)
    iu = np.triu_indices(n, 1)
    summary = {
        "n_runs": n,
        "budget_evaluations": int(budget),
        "ga_mean": float(ga_f.mean()),
        "ga_std": float(ga_f.std(ddof=1)) if n > 1 else 0.0,
        "ga_min": float(ga_f.min()),
        "ga_max": float(ga_f.max()),
        "ga_cv_percent": float(100 * ga_f.std(ddof=1) / ga_f.mean()) if n > 1 else 0.0,
        "ga_accepted": int(table["accepted"].sum()),
        "random_mean": float(np.mean(rnd)),
        "random_max": float(np.max(rnd)),
        "greedy": float(greedy_ev.fitness),
        "bound": float(reference_upper_bound(sc)["fitness"]),
        "mannwhitney_p_ga_gt_random": float(mw.pvalue),
        "solution_distance_mean_deg": float(dist[iu].mean()) if n > 1 else 0.0,
        "solution_distance_max_deg": float(dist[iu].max()) if n > 1 else 0.0,
    }
    return runs, table, summary, rnd, dist


def failure_analysis(config, scenario: Scenario) -> pd.DataFrame:
    """N-1: what is lost if each satellite fails."""
    ev_full = Evaluator(scenario).evaluate(config)
    sc_less = scenario.with_params(n_satellites=len(config) - 1)
    ev = Evaluator(sc_less)
    rows = []
    for s in range(len(config)):
        e = ev.evaluate(np.delete(config, s, axis=0))
        lost = [r.name for r, f in zip(e.regions, ev_full.regions) if f.covered and not r.covered]
        rows.append(
            {
                "satélite_fallado": s,
                "fitness": round(e.fitness, 4),
                "cobertura_ponderada": round(e.weighted_coverage, 4),
                "regiones_cubiertas": e.n_covered,
                "regiones_perdidas": ", ".join(lost) or "ninguna",
            }
        )
    return pd.DataFrame(rows)


def e8_robustness(base: GAResult, cfg: GAConfig = None, seed: int = 0):
    """Own test: value of the redundancy term under satellite failure."""
    no_red_sc = default_scenario().with_params(
        name="sin término de redundancia", w_coverage=0.80, w_redundancy=0.0, w_resolution=0.20
    )
    no_red = run_ga(no_red_sc, cfg, seed=seed)
    sc = default_scenario()
    return {
        "con_redundancia": failure_analysis(base.best, sc),
        "sin_redundancia": failure_analysis(no_red.best, sc),
        "run_sin_redundancia": no_red,
    }


def revalidate(config, old: Scenario, new: Scenario) -> dict:
    """Is a previous configuration still valid / good under new conditions?"""
    a, b = Evaluator(old).evaluate(config), Evaluator(new).evaluate(config)
    return {
        "válida_antes": a.feasible,
        "válida_ahora": b.feasible,
        "fitness_antes": round(a.fitness, 4),
        "fitness_ahora": round(b.fitness, 4),
        "regiones_cubiertas_ahora": b.n_covered,
        "violaciones": [f"sat {v.satellite} en {v.target} ({v.distance_deg:.2f}° < {v.limit_deg}°)" for v in b.violations],
        "aceptada_ahora": acceptance(b, new)["ACEPTADA"],
    }


def e9_change_of_conditions(base: GAResult, cfg: GAConfig = None, seed: int = 0):
    """Section 3.3: priority change and a zone that suddenly becomes unavailable."""
    cfg = cfg or GAConfig()
    old = base.scenario
    out = {}
    # (a) Australia becomes high priority.
    sc_a = old.with_priority("Interior de Australia", "alta", name="C1 Australia -> Alta")
    out["prioridad"] = {
        "scenario": sc_a,
        "revalidación": revalidate(base.best, old, sc_a),
        "reoptimizado": run_ga(sc_a, cfg, seed=seed, initial_population=base.final_population),
    }
    # (b) New debris zone exactly where the satellite observing Japan sits.
    japan = next(r for r in base.best_eval.regions if r.name == "Japón")
    s = japan.satellites[0]
    lat, lon = base.best[s, 0], base.best[s, 1]
    sc_b = old.with_zone(Zone("Desechos nuevos", float(lat), float(lon), 3.0), name="C2 nueva zona sobre Japón")
    short = replace(cfg, generations=min(cfg.generations, 150))
    out["zona_nueva"] = {
        "scenario": sc_b,
        "revalidación": revalidate(base.best, old, sc_b),
        "warm": run_ga(sc_b, short, seed=seed, initial_population=base.final_population),
        "cold": run_ga(sc_b, short, seed=seed),
    }
    return out


ABLATIONS = {
    "configuración final": {},
    "sin alineación en cruce": {"align_crossover": False},
    "sin reparación": {"repair_rate": 0.0},
    "sin elitismo": {"elite_size": 0},
    "mutación alta (0.5)": {"mutation_rate": 0.5},
    "penalización en vez de Deb": {"constraint_handling": "penalty"},
    "población 40": {"population_size": 40},
}


def e10_ablation(cfg: GAConfig = None, seeds=range(3), scenario: Scenario = None):
    """Effect of each operator / parameter choice on the final quality."""
    cfg = cfg or GAConfig()
    sc = scenario or reduced_space_scenarios()[1]  # constraints actually bind here
    rows = []
    for name, change in ABLATIONS.items():
        for s in seeds:
            r = run_ga(sc, replace(cfg, **change), seed=s)
            rows.append(
                {
                    "variante": name,
                    "seed": s,
                    "fitness": r.best_eval.fitness,
                    "válida": r.best_eval.feasible,
                    "conv_gen": convergence_generation(r),
                }
            )
    df = pd.DataFrame(rows)
    agg = (
        df.groupby("variante", sort=False)
        .agg(fitness_media=("fitness", "mean"), fitness_std=("fitness", "std"),
             válidas=("válida", "sum"), conv_gen_media=("conv_gen", "mean"))
        .round(4)
        .reset_index()
    )
    return df, agg
