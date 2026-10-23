"""Run every experiment and store the evidence in outputs/.

Usage:  python tools/run_experiments.py [--seeds 10] [--quick]
Writes outputs/results.json, outputs/*.csv, outputs/fig_*.png and
outputs/globe.html. docs/ cite the numbers produced here.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from astroshield import experiments as X  # noqa: E402
from astroshield.evaluation import acceptance, reference_upper_bound  # noqa: E402
from astroshield.ga import GAConfig  # noqa: E402
from astroshield.viz import apply_theme, globe_html, plot_evolution, plot_mission_map, plot_regions, plot_runs  # noqa: E402

OUT = ROOT / "outputs"


def save(fig, name):
    fig.savefig(OUT / name, dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--quick", action="store_true", help="smaller GA for a fast smoke run")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    apply_theme()
    cfg = GAConfig(generations=80, population_size=60) if args.quick else GAConfig()
    t0 = time.time()
    res = {"ga_config": cfg.to_dict()}

    # E1 — stage 1, no restrictions
    e1 = X.e1_initial(cfg)
    res["E1"] = {**X.summarize(e1), "regions": e1.best_eval.region_table().to_dict("records"),
                 "acceptance": acceptance(e1.best_eval, e1.scenario)}
    save(plot_mission_map(e1.scenario, e1.best, e1.initial_best), "fig_e1_mapa.png")

    # E2 — base run with every restriction
    base = X.e2_base(cfg)
    res["E2"] = {**X.summarize(base), "regions": base.best_eval.region_table().to_dict("records"),
                 "satellites": base.best_eval.satellite_table(base.scenario).to_dict("records"),
                 "acceptance": acceptance(base.best_eval, base.scenario),
                 "initial_feasible_ratio": base.history[0]["feasible_ratio"],
                 "bound": reference_upper_bound(base.scenario)}
    base.history_frame().to_csv(OUT / "history_base_seed0.csv", index=False)
    save(plot_evolution(base), "fig_e2_evolucion.png")
    save(plot_mission_map(base.scenario, base.best, base.initial_best), "fig_e2_mapa.png")
    save(plot_regions({"inicial (gen 0)": base.initial_eval, "final": base.best_eval}), "fig_e2_regiones.png")

    # E7 — variation (also feeds E3/E4 audits)
    runs, table, summary, rnd, dist = X.e7_variation(cfg, seeds=range(args.seeds))
    table.to_csv(OUT / "e7_runs.csv", index=False)
    res["E7"] = {"summary": summary, "runs": table.to_dict("records"), "random": rnd}
    save(plot_runs(runs), "fig_e7_convergencia.png")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot([table["fitness"], rnd], widths=0.5)
    ax.set_xticks([1, 2], [f"AG ({args.seeds} semillas)", "Búsqueda aleatoria"])
    ax.axhline(summary["greedy"], color="#FACC15", ls="--", label=f"voraz {summary['greedy']:.4f}")
    ax.axhline(summary["bound"], color="#34D399", ls=":", label=f"cota {summary['bound']:.4f}")
    ax.set_ylabel("fitness final")
    ax.legend()
    ax.set_title("Mismo presupuesto de evaluaciones")
    save(fig, "fig_e7_comparacion.png")

    # E3/E4 — constraint audits over every run
    audit = X.e3_e4_constraint_audit(runs)
    audit.to_csv(OUT / "e3_e4_auditoria.csv", index=False)
    res["E3_E4"] = {
        "all_respected": bool(audit["respeta"].all()),
        "min_margin_by_zone": audit.groupby("zona")["margen_deg"].min().to_dict(),
        "initial_feasible_ratio_mean": float(sum(r.history[0]["feasible_ratio"] for r in runs) / len(runs)),
        "final_feasible_ratio_mean": float(sum(r.history[-1]["feasible_ratio"] for r in runs) / len(runs)),
    }
    near = X.e4_object_near_region(cfg)
    res["E4_near"] = {**X.summarize(near), "margins": X.zone_margins(near.best, near.scenario).to_dict("records"),
                      "regions": near.best_eval.region_table().to_dict("records")}
    save(plot_mission_map(near.scenario, near.best), "fig_e4_objeto_sahel.png")

    # E5 — reduced space
    red, unc = X.e5_reduced_space(cfg)
    res["E5"] = {"levels": [
        {**X.summarize(r), "regions": r.best_eval.region_table().to_dict("records"),
         "satellites": r.best_eval.satellite_table(r.scenario).to_dict("records")} for r in red],
        "unconstrained_R1": {**X.summarize(unc), "violations": [
            f"S{v.satellite} en {v.target} ({v.distance_deg:.2f}° < {v.limit_deg}°)" for v in unc.best_eval.violations]}}
    save(plot_mission_map(red[3].scenario, red[3].best), "fig_e5_R3.png")
    save(plot_regions({r.scenario.name.split(" ")[0]: r.best_eval for r in red}, "Espacio reducido: cobertura por nivel"),
         "fig_e5_regiones.png")

    # E6 — infeasible / hard conditions
    inf = X.e6_infeasible(cfg)
    res["E6"] = {k: {**X.summarize(r), "regions": r.best_eval.region_table().to_dict("records"),
                     "violations": [f"S{v.satellite}: {v.constraint} {v.target} ({v.distance_deg:.1f}° < {v.limit_deg}°)"
                                    for v in r.best_eval.violations][:12],
                     "n_violations": len(r.best_eval.violations)} for k, r in inf.items()}
    save(plot_evolution(inf["I3 separación 80° imposible"]), "fig_e6_inviable.png")
    save(plot_mission_map(inf["I2 solo 5 satélites"].scenario, inf["I2 solo 5 satélites"].best), "fig_e6_5sats.png")

    # E8 — own test: robustness to one satellite failure
    rob = X.e8_robustness(base, cfg)
    res["E8"] = {k: rob[k].to_dict("records") for k in ("con_redundancia", "sin_redundancia")}
    res["E8"]["summary"] = {k: {"fitness_media_N-1": float(rob[k]["fitness"].mean()),
                                "peor_regiones_cubiertas": int(rob[k]["regiones_cubiertas"].min()),
                                "fallos_sin_pérdida": int((rob[k]["regiones_perdidas"] == "ninguna").sum())}
                            for k in ("con_redundancia", "sin_redundancia")}

    # E9 — change of conditions
    ch = X.e9_change_of_conditions(base, cfg)
    res["E9"] = {
        "prioridad": {"revalidación": ch["prioridad"]["revalidación"], "reoptimizado": X.summarize(ch["prioridad"]["reoptimizado"])},
        "zona_nueva": {"revalidación": ch["zona_nueva"]["revalidación"],
                       "warm": X.summarize(ch["zona_nueva"]["warm"]), "cold": X.summarize(ch["zona_nueva"]["cold"])},
    }
    fig, ax = plt.subplots(figsize=(9, 4))
    for k, c in (("warm", "#22D3EE"), ("cold", "#A78BFA")):
        r = ch["zona_nueva"][k]
        ax.plot([max(h["best_so_far_rank"], -0.05) for h in r.history], color=c,
                label={"warm": "re-optimización desde la población anterior", "cold": "desde cero"}[k])
    ax.set_xlabel("generación"); ax.set_ylabel("mejor fitness (<0 = aún inválida)")
    ax.set_title("Nueva zona sobre el satélite de Japón"); ax.legend()
    save(fig, "fig_e9_reoptimizacion.png")

    # E10 — ablation
    abl_runs, abl = X.e10_ablation(cfg, seeds=range(5))
    abl.to_csv(OUT / "e10_ablacion.csv", index=False)
    res["E10"] = abl.to_dict("records")

    # Globe for the base run
    (OUT / "globe.html").write_text(globe_html(base.scenario, {"Inicial (gen 0)": base.initial_best,
                                                                "Generación 50": base.snapshots[50],
                                                                "Final": base.best}, height=720), encoding="utf-8")
    res["elapsed_s"] = round(time.time() - t0, 1)
    (OUT / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"done in {res['elapsed_s']} s -> {OUT}")


if __name__ == "__main__":
    main()
