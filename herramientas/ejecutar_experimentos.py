"""Ejecuta todos los experimentos y guarda la evidencia en outputs/.

Uso:  python herramientas/ejecutar_experimentos.py [--semillas 10] [--rapido]
Escribe outputs/resultados.json, outputs/*.csv, outputs/fig_*.png,
outputs/centro_control.html y outputs/datos_centro_control.json (los datos de
referencia que el notebook incrusta). Los documentos de docs/ citan estos números.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from astroshield import centro_control as C  # noqa: E402
from astroshield import experimentos as X  # noqa: E402
from astroshield.algoritmo_genetico import ParametrosAG  # noqa: E402
from astroshield.visualizacion import (  # noqa: E402
    aplicar_tema,
    graficar_ejecuciones,
    graficar_evolucion,
    graficar_mapa_mision,
    graficar_regiones,
)

SALIDA = RAIZ / "outputs"


def guardar(fig, nombre):
    fig.savefig(SALIDA / nombre, dpi=130)
    plt.close(fig)


def figuras(todo):
    """Figuras PNG estáticas que citan los documentos."""
    e1, base, e7 = todo["e1"], todo["base"], todo["e7"]
    guardar(graficar_mapa_mision(e1.escenario, e1.mejor, e1.mejor_inicial), "fig_e1_mapa.png")
    guardar(graficar_evolucion(base), "fig_e2_evolucion.png")
    guardar(graficar_mapa_mision(base.escenario, base.mejor, base.mejor_inicial), "fig_e2_mapa.png")
    guardar(graficar_regiones({"inicial (gen 0)": base.eval_inicial, "final": base.eval_mejor}), "fig_e2_regiones.png")
    guardar(graficar_ejecuciones(e7["ejecuciones"]), "fig_e7_convergencia.png")
    res = e7["resumen"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot([e7["tabla"]["fitness"], e7["aleatoria"]], widths=0.5)
    ax.set_xticks([1, 2], [f"AG ({res['n_ejecuciones']} semillas)", "Búsqueda aleatoria"])
    ax.axhline(res["voraz"], color="#FACC15", ls="--", label=f"voraz {res['voraz']:.4f}")
    ax.axhline(res["cota"], color="#34D399", ls=":", label=f"cota {res['cota']:.4f}")
    ax.set_ylabel("fitness final")
    ax.legend()
    ax.set_title("Mismo presupuesto de evaluaciones")
    guardar(fig, "fig_e7_comparacion.png")
    junto = todo["e4"]
    guardar(graficar_mapa_mision(junto.escenario, junto.mejor), "fig_e4_objeto_sahel.png")
    niveles = todo["e5"]["niveles"]
    guardar(graficar_mapa_mision(niveles[3].escenario, niveles[3].mejor), "fig_e5_R3.png")
    guardar(graficar_regiones({r.escenario.nombre.split(" ")[0]: r.eval_mejor for r in niveles},
                              "Espacio reducido: cobertura por nivel"), "fig_e5_regiones.png")
    inv = todo["e6"]
    guardar(graficar_evolucion(inv["I3 separación 80° imposible"]), "fig_e6_inviable.png")
    guardar(graficar_mapa_mision(inv["I2 solo 5 satélites"].escenario, inv["I2 solo 5 satélites"].mejor), "fig_e6_5sats.png")
    fig, ax = plt.subplots(figsize=(9, 4))
    zona = todo["e9"]["zona_nueva"]
    for clave, color, etiqueta in (("desde_poblacion_previa", "#22D3EE", "reoptimización desde la población anterior"),
                                   ("desde_cero", "#A78BFA", "desde cero")):
        ax.plot([max(h["mejor_rango_historico"], -0.05) for h in zona[clave].historial], color=color, label=etiqueta)
    ax.set_xlabel("generación")
    ax.set_ylabel("mejor fitness (<0 = aún inválida)")
    ax.set_title("Nueva zona sobre el satélite de Japón")
    ax.legend()
    guardar(fig, "fig_e9_reoptimizacion.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semillas", type=int, default=10)
    ap.add_argument("--rapido", action="store_true", help="AG más pequeño para una prueba rápida")
    args = ap.parse_args()
    SALIDA.mkdir(exist_ok=True)
    aplicar_tema()
    cfg = ParametrosAG(generaciones=80, tam_poblacion=60) if args.rapido else ParametrosAG()
    todo = X.ejecutar_todo(cfg, n_semillas=args.semillas, n_ablacion=3 if args.rapido else 5, progreso=True)

    print("Pruebas unitarias...", flush=True)
    pruebas = C.ejecutar_pruebas_unitarias(str(RAIZ))
    print(" ", pruebas["resumen"])

    resultados = X.resumen_resultados(todo)
    (SALIDA / "resultados.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2, default=str),
                                            encoding="utf-8")
    todo["base"].tabla_historial().to_csv(SALIDA / "historial_base_semilla0.csv", index=False)
    todo["e7"]["tabla"].to_csv(SALIDA / "e7_ejecuciones.csv", index=False)
    todo["auditoria"].to_csv(SALIDA / "e3_e4_auditoria.csv", index=False)
    todo["e10"]["agregado"].to_csv(SALIDA / "e10_ablacion.csv", index=False)
    figuras(todo)

    datos = C.datos_centro_control(todo, pruebas, modo="rápido" if args.rapido else "completo")
    C.guardar_centro_control(datos, str(SALIDA / "centro_control.html"))
    (SALIDA / "datos_centro_control.json").write_text(
        json.dumps(datos, ensure_ascii=False, separators=(",", ":"), default=C._json_default, allow_nan=False),
        encoding="utf-8")
    print(f"Listo en {todo['tiempo_s']:.0f} s -> {SALIDA}")


if __name__ == "__main__":
    main()
