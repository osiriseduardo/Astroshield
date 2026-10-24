"""Gráficas estáticas de análisis (matplotlib) para los documentos del repositorio.

La vista interactiva (globo 3D, mapa 2D y gráficas) está en centro_control.py;
estas figuras PNG se guardan en outputs/ y se citan desde docs/.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from .escenario import Escenario
from .evaluacion import Evaluador, semiangulo_huella
from .geometria import circulo, km_a_grados

# Paleta de AstroShield (personalizada, tema oscuro de "centro de control").
PALETA = {
    "fondo": "#0B1026",
    "panel": "#131B3D",
    "rejilla": "#26305C",
    "texto": "#E6ECFF",
    "tenue": "#8D97C9",
    "final": "#22D3EE",  # constelación final
    "inicial": "#A78BFA",  # constelación inicial
    "cubierta": "#34D399",
    "no_cubierta": "#F87171",
    "desechos": "#FB923C",
    "ocupada": "#F472B6",
    "media": "#FACC15",
}
SERIES = ["#22D3EE", "#FACC15", "#34D399", "#F472B6", "#A78BFA", "#FB923C", "#60A5FA", "#F87171"]


def aplicar_tema():
    plt.rcParams.update(
        {
            "figure.facecolor": PALETA["fondo"],
            "axes.facecolor": PALETA["panel"],
            "axes.edgecolor": PALETA["rejilla"],
            "axes.labelcolor": PALETA["texto"],
            "axes.titlecolor": PALETA["texto"],
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.color": PALETA["rejilla"],
            "grid.linewidth": 0.6,
            "xtick.color": PALETA["tenue"],
            "ytick.color": PALETA["tenue"],
            "text.color": PALETA["texto"],
            "legend.facecolor": PALETA["panel"],
            "legend.edgecolor": PALETA["rejilla"],
            "axes.prop_cycle": plt.cycler(color=SERIES),
            "figure.dpi": 110,
            "savefig.facecolor": PALETA["fondo"],
            "savefig.bbox": "tight",
            "font.size": 10,
        }
    )


# ---------------------------------------------------------------- gráficas
def graficar_evolucion(resultado, titulo=None):
    """Mejor / media / dispersión del fitness, factibilidad y diversidad por generación."""
    h = resultado.tabla_historial()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, height_ratios=[2.2, 1])
    g = h["generacion"]
    ax1.fill_between(g, h["fitness_media"] - h["fitness_desv"], h["fitness_media"] + h["fitness_desv"],
                     color=PALETA["media"], alpha=0.15, label="media ± desv. estándar")
    ax1.plot(g, h["fitness_media"], color=PALETA["media"], lw=1.4, label="fitness media")
    ax1.plot(g, h["fitness_mejor"], color=PALETA["final"], lw=2.2, label="mejor válida de la generación")
    ax1.plot(g, h["fitness_peor"], color=PALETA["tenue"], lw=0.8, ls=":", label="peor")
    from .evaluacion import cota_referencia

    cota = cota_referencia(resultado.escenario)["fitness"]
    ax1.axhline(cota, color=PALETA["cubierta"], ls="--", lw=1, label=f"cota de referencia {cota:.3f}")
    ax1.set_ylabel("fitness")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="lower right", fontsize=8)
    ax1.set_title(titulo or f"Evolución — {resultado.escenario.nombre} (semilla {resultado.semilla})")
    ax2.plot(g, h["fraccion_factible"], color=PALETA["cubierta"], lw=1.6, label="fracción válida")
    ax2.set_ylabel("válidas")
    ax2.set_ylim(-0.02, 1.02)
    ax3 = ax2.twinx()
    ax3.plot(g, h["diversidad_grados"], color=PALETA["ocupada"], lw=1.2, label="diversidad (°)")
    ax3.set_ylabel("diversidad (°)", color=PALETA["ocupada"])
    ax3.grid(False)
    ax2.set_xlabel("generación")
    lineas = ax2.get_lines() + ax3.get_lines()
    ax2.legend(lineas, [l.get_label() for l in lineas], loc="center right", fontsize=8)
    fig.tight_layout()
    return fig


def graficar_ejecuciones(ejecuciones, titulo="Curvas de convergencia de todas las ejecuciones"):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    curvas = []
    for r in ejecuciones:
        y = [max(h["mejor_rango_historico"], 0) for h in r.historial]
        curvas.append(y)
        ax.plot(y, lw=1, alpha=0.55)
    m = np.mean(curvas, axis=0)
    ax.plot(m, color="white", lw=2.4, label=f"media de {len(ejecuciones)} ejecuciones")
    ax.set_xlabel("generación")
    ax.set_ylabel("mejor fitness hasta el momento")
    ax.set_ylim(0, 1)
    ax.set_title(titulo)
    ax.legend()
    fig.tight_layout()
    return fig


def graficar_regiones(evaluaciones: dict, titulo="Calidad por región"):
    """Barras agrupadas de cobertura por región para varias evaluaciones etiquetadas."""
    etiquetas = [r.nombre for r in next(iter(evaluaciones.values())).regiones]
    x = np.arange(len(etiquetas))
    w = 0.8 / len(evaluaciones)
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for k, (nombre, ev) in enumerate(evaluaciones.items()):
        cob = [r.cobertura for r in ev.regiones]
        red = [r.redundancia for r in ev.regiones]
        barras = ax.bar(x + k * w, cob, w * 0.95, label=f"{nombre} · cobertura", color=SERIES[k % len(SERIES)])
        ax.bar(x + k * w, red, w * 0.45, color="white", alpha=0.55,
               label="redundancia (≥2 satélites)" if k == 0 else None)
        for b, v in zip(barras, cob):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.0%}", ha="center", fontsize=7)
    ax.axhline(0.95, color=PALETA["cubierta"], ls="--", lw=1)
    ax.set_xticks(x + w * (len(evaluaciones) - 1) / 2)
    ax.set_xticklabels([f"{l}\n({r.prioridad})" for l, r in zip(etiquetas, next(iter(evaluaciones.values())).regiones)],
                       fontsize=8)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("fracción de la región")
    ax.set_title(titulo)
    ax.legend(fontsize=8, loc="upper right", ncol=2)
    fig.tight_layout()
    return fig


def graficar_mapa_mision(escenario: Escenario, configuracion, inicial=None, titulo=None):
    """Mapa 2-D equirectangular (vista de análisis, complementa al globo 3D)."""
    ev = Evaluador(escenario).evaluar(configuracion)
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_aspect("equal")

    def dibujar_casquete(lat, lon, radio, **kw):
        la, lo = circulo(lat, lon, radio, 120)
        saltos = np.flatnonzero(np.abs(np.diff(lo)) > 180)
        for seg_la, seg_lo in zip(np.split(la, saltos + 1), np.split(lo, saltos + 1)):
            ax.plot(seg_lo, seg_la, **kw)

    for z in escenario.zonas:
        c = PALETA["desechos"] if z.tipo == "desechos" else PALETA["ocupada"]
        dibujar_casquete(z.lat, z.lon, z.radio_grados, color=c, lw=1.6, ls="--" if z.tipo == "desechos" else "-")
        ax.text(z.lon, z.lat, z.nombre, color=c, fontsize=7, ha="center", va="center")
    lam = semiangulo_huella(configuracion[:, 2], escenario.semiangulo_sensor_grados)
    for s, (la, lo, h) in enumerate(configuracion):
        dibujar_casquete(la, lo, lam[s], color=PALETA["final"], lw=1, alpha=0.8)
    if inicial is not None:
        ax.scatter(inicial[:, 1], inicial[:, 0], marker="x", color=PALETA["inicial"], s=40,
                   label="satélites iniciales (gen 0)")
    ax.scatter(configuracion[:, 1], configuracion[:, 0], marker="*", color=PALETA["final"], s=120, zorder=5,
               edgecolor="white", linewidth=0.5, label="satélites finales")
    for s, (la, lo, h) in enumerate(configuracion):
        ax.text(lo + 2, la + 2, f"S{s} · {h:.0f} km", fontsize=7, color=PALETA["final"])
    for r, rr in zip(escenario.regiones, ev.regiones):
        c = PALETA["cubierta"] if rr.cubierta else PALETA["no_cubierta"]
        dibujar_casquete(r.lat, r.lon, km_a_grados(r.radio_km), color=c, lw=2)
        ax.text(r.lon, r.lat - 4.5, f"{r.nombre}\n{rr.cobertura:.0%}", fontsize=7, color=c, ha="center", va="top")
    ax.set_xlabel("longitud (°)")
    ax.set_ylabel("latitud (°)")
    ax.set_xticks(range(-180, 181, 30))
    ax.set_yticks(range(-90, 91, 30))
    ax.set_title(titulo or f"Mapa de misión — fitness {ev.fitness:.4f}, {ev.n_cubiertas}/{len(ev.regiones)} regiones cubiertas")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    return fig
