"""Visualisation: analysis charts (matplotlib) and the interactive 3D globe.

The globe is a self-contained HTML page built with globe.gl (WebGL). It is
generated from the *actual* run data (scenario + evaluated configurations),
so what you see is exactly what the algorithm produced.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np

from .evaluation import Evaluator, footprint_half_angle
from .geo import EARTH_RADIUS_KM, circle, deg_to_km, km_to_deg
from .scenario import Scenario

# AstroShield palette (custom, dark "mission control" theme).
PALETTE = {
    "bg": "#0B1026",
    "panel": "#131B3D",
    "grid": "#26305C",
    "text": "#E6ECFF",
    "muted": "#8D97C9",
    "final": "#22D3EE",  # final constellation
    "initial": "#A78BFA",  # initial constellation
    "covered": "#34D399",
    "uncovered": "#F87171",
    "debris": "#FB923C",
    "occupied": "#F472B6",
    "mean": "#FACC15",
}
SERIES = ["#22D3EE", "#FACC15", "#34D399", "#F472B6", "#A78BFA", "#FB923C", "#60A5FA", "#F87171"]


def apply_theme():
    plt.rcParams.update(
        {
            "figure.facecolor": PALETTE["bg"],
            "axes.facecolor": PALETTE["panel"],
            "axes.edgecolor": PALETTE["grid"],
            "axes.labelcolor": PALETTE["text"],
            "axes.titlecolor": PALETTE["text"],
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.color": PALETTE["grid"],
            "grid.linewidth": 0.6,
            "xtick.color": PALETTE["muted"],
            "ytick.color": PALETTE["muted"],
            "text.color": PALETTE["text"],
            "legend.facecolor": PALETTE["panel"],
            "legend.edgecolor": PALETTE["grid"],
            "axes.prop_cycle": plt.cycler(color=SERIES),
            "figure.dpi": 110,
            "savefig.facecolor": PALETTE["bg"],
            "savefig.bbox": "tight",
            "font.size": 10,
        }
    )


# ------------------------------------------------------------------ charts
def plot_evolution(result, title=None):
    """Best / mean / spread of fitness, feasibility and diversity per generation."""
    h = result.history_frame()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, height_ratios=[2.2, 1])
    g = h["generation"]
    ax1.fill_between(g, h["mean_fitness"] - h["std_fitness"], h["mean_fitness"] + h["std_fitness"],
                     color=PALETTE["mean"], alpha=0.15, label="media ± desv. estándar")
    ax1.plot(g, h["mean_fitness"], color=PALETTE["mean"], lw=1.4, label="fitness media")
    ax1.plot(g, h["best_fitness"], color=PALETTE["final"], lw=2.2, label="mejor válida de la generación")
    ax1.plot(g, h["worst_fitness"], color=PALETTE["muted"], lw=0.8, ls=":", label="peor")
    from .evaluation import reference_upper_bound

    bound = reference_upper_bound(result.scenario)["fitness"]
    ax1.axhline(bound, color=PALETTE["covered"], ls="--", lw=1, label=f"cota de referencia {bound:.3f}")
    ax1.set_ylabel("fitness")
    ax1.set_ylim(0, 1)
    ax1.legend(loc="lower right", fontsize=8)
    ax1.set_title(title or f"Evolución — {result.scenario.name} (semilla {result.seed})")
    ax2.plot(g, h["feasible_ratio"], color=PALETTE["covered"], lw=1.6, label="fracción válida")
    ax2.set_ylabel("válidas")
    ax2.set_ylim(-0.02, 1.02)
    ax3 = ax2.twinx()
    ax3.plot(g, h["diversity_deg"], color=PALETTE["occupied"], lw=1.2, label="diversidad (°)")
    ax3.set_ylabel("diversidad (°)", color=PALETTE["occupied"])
    ax3.grid(False)
    ax2.set_xlabel("generación")
    lines = ax2.get_lines() + ax3.get_lines()
    ax2.legend(lines, [l.get_label() for l in lines], loc="center right", fontsize=8)
    fig.tight_layout()
    return fig


def plot_runs(runs, title="Curvas de convergencia de todas las ejecuciones"):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    curves = []
    for r in runs:
        y = [max(h["best_so_far_rank"], 0) for h in r.history]
        curves.append(y)
        ax.plot(y, lw=1, alpha=0.55)
    m = np.mean(curves, axis=0)
    ax.plot(m, color="white", lw=2.4, label=f"media de {len(runs)} ejecuciones")
    ax.set_xlabel("generación")
    ax.set_ylabel("mejor fitness hasta el momento")
    ax.set_ylim(0, 1)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_regions(evaluations: dict, title="Calidad por región"):
    """Grouped bars of coverage per region for several labelled evaluations."""
    labels = [r.name for r in next(iter(evaluations.values())).regions]
    x = np.arange(len(labels))
    w = 0.8 / len(evaluations)
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for k, (name, ev) in enumerate(evaluations.items()):
        cov = [r.coverage for r in ev.regions]
        red = [r.redundancy for r in ev.regions]
        bars = ax.bar(x + k * w, cov, w * 0.95, label=f"{name} · cobertura", color=SERIES[k % len(SERIES)])
        ax.bar(x + k * w, red, w * 0.45, color="white", alpha=0.55,
               label="redundancia (≥2 satélites)" if k == 0 else None)
        for b, v in zip(bars, cov):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.0%}", ha="center", fontsize=7)
    ax.axhline(0.95, color=PALETTE["covered"], ls="--", lw=1)
    ax.set_xticks(x + w * (len(evaluations) - 1) / 2)
    ax.set_xticklabels([f"{l}\n({r.priority})" for l, r in zip(labels, next(iter(evaluations.values())).regions)],
                       fontsize=8)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("fracción de la región")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="upper right", ncol=2)
    fig.tight_layout()
    return fig


def plot_mission_map(scenario: Scenario, config, initial=None, title=None):
    """2-D equirectangular map (analysis view, complements the 3D globe)."""
    ev = Evaluator(scenario).evaluate(config)
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_aspect("equal")

    def draw_cap(lat, lon, radius, **kw):
        la, lo = circle(lat, lon, radius, 120)
        jumps = np.flatnonzero(np.abs(np.diff(lo)) > 180)
        for seg_la, seg_lo in zip(np.split(la, jumps + 1), np.split(lo, jumps + 1)):
            ax.plot(seg_lo, seg_la, **kw)

    for z in scenario.zones:
        c = PALETTE["debris"] if z.kind == "debris" else PALETTE["occupied"]
        draw_cap(z.lat, z.lon, z.radius_deg, color=c, lw=1.6, ls="--" if z.kind == "debris" else "-")
        ax.text(z.lon, z.lat, z.name, color=c, fontsize=7, ha="center", va="center")
    lam = footprint_half_angle(config[:, 2], scenario.sensor_half_angle_deg)
    for s, (la, lo, h) in enumerate(config):
        draw_cap(la, lo, lam[s], color=PALETTE["final"], lw=1, alpha=0.8)
    if initial is not None:
        ax.scatter(initial[:, 1], initial[:, 0], marker="x", color=PALETTE["initial"], s=40,
                   label="satélites iniciales (gen 0)")
    ax.scatter(config[:, 1], config[:, 0], marker="*", color=PALETTE["final"], s=120, zorder=5,
               edgecolor="white", linewidth=0.5, label="satélites finales")
    for s, (la, lo, h) in enumerate(config):
        ax.text(lo + 2, la + 2, f"S{s} · {h:.0f} km", fontsize=7, color=PALETTE["final"])
    for r, rr in zip(scenario.regions, ev.regions):
        c = PALETTE["covered"] if rr.covered else PALETTE["uncovered"]
        draw_cap(r.lat, r.lon, km_to_deg(r.radius_km), color=c, lw=2)
        ax.text(r.lon, r.lat - 4.5, f"{r.name}\n{rr.coverage:.0%}", fontsize=7, color=c, ha="center", va="top")
    ax.set_xlabel("longitud (°)")
    ax.set_ylabel("latitud (°)")
    ax.set_xticks(range(-180, 181, 30))
    ax.set_yticks(range(-90, 91, 30))
    ax.set_title(title or f"Mapa de misión — fitness {ev.fitness:.4f}, {ev.n_covered}/6 regiones cubiertas")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------- globe
def _cap_feature(lat, lon, radius, props, n=96):
    la, lo = circle(lat, lon, radius, n)
    la, lo = la[::-1], lo[::-1]  # globe.gl follows d3-geo: clockwise exterior ring
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "Polygon", "coordinates": [[[float(x), float(y)] for y, x in zip(la, lo)]]},
    }


def _state(scenario: Scenario, config, label):
    ev = Evaluator(scenario).evaluate(config)
    lam = footprint_half_angle(config[:, 2], scenario.sensor_half_angle_deg)
    bad = {v.satellite for v in ev.violations}
    sats, feet = [], []
    for s, (la, lo, h) in enumerate(config):
        sats.append({"id": int(s), "lat": float(la), "lng": float(lo), "alt_km": float(h),
                     "alt": float(h) / EARTH_RADIUS_KM, "footprint_km": float(deg_to_km(lam[s])),
                     "violating": s in bad})
        feet.append(_cap_feature(la, lo, float(lam[s]), {"kind": "footprint", "sat": int(s)}))
    regions = [{"name": r.name, "priority": r.priority, "lat": sr.lat, "lng": sr.lon,
                "coverage": r.coverage, "redundancy": r.redundancy, "covered": r.covered,
                "sats": r.satellites}
               for r, sr in zip(ev.regions, scenario.regions)]
    return {"label": label, "fitness": ev.fitness, "feasible": ev.feasible, "violation": ev.violation,
            "covered": ev.n_covered, "satellites": sats, "footprints": feet, "regions": regions,
            "violations": [f"S{v.satellite} → {v.target}" for v in ev.violations]}


def globe_data(scenario: Scenario, states: dict) -> dict:
    """states: {label: config}. Returns JSON-ready data for the globe page."""
    zones = [_cap_feature(z.lat, z.lon, z.radius_deg,
                          {"kind": z.kind, "name": z.name, "radius": z.radius_deg})
             for z in scenario.zones]
    regions = [_cap_feature(r.lat, r.lon, km_to_deg(r.radius_km),
                            {"kind": "region", "name": r.name, "priority": r.priority})
               for r in scenario.regions]
    return {
        "scenario": scenario.name,
        "palette": PALETTE,
        "zones": zones,
        "regionShapes": regions,
        "zoneCenters": [{"name": z.name, "kind": z.kind, "lat": z.lat, "lng": z.lon} for z in scenario.zones],
        "states": [_state(scenario, np.asarray(c, float), k) for k, c in states.items()],
    }


GLOBE_TEMPLATE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AstroShield Globe</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0B1026;--panel:rgba(19,27,61,.86);--line:#26305C;--text:#E6ECFF;--muted:#8D97C9;
--final:#22D3EE;--initial:#A78BFA;--ok:#34D399;--bad:#F87171;--debris:#FB923C;--occ:#F472B6}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);
font-family:'Space Grotesk',system-ui,sans-serif}
#wrap{position:relative;width:100%;height:__HEIGHT__px;overflow:hidden;border-radius:14px;background:var(--bg)}
#globe{position:absolute;inset:0}
.panel{position:absolute;background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:12px 14px;backdrop-filter:blur(6px);font-size:12px;line-height:1.45}
#hud{top:12px;left:12px;width:270px;max-height:calc(100% - 24px);overflow:auto}
#legend{bottom:12px;right:12px;width:210px}
h1{font-size:15px;margin:0 0 2px;letter-spacing:.04em}h1 span{color:var(--final)}
.sub{color:var(--muted);font-size:11px;margin-bottom:8px}
.tabs{display:flex;gap:6px;margin:8px 0}
.tabs button{flex:1;background:transparent;color:var(--text);border:1px solid var(--line);border-radius:8px;
padding:6px 4px;cursor:pointer;font:inherit;font-size:11px}
.tabs button.on{background:var(--final);color:#04121a;border-color:var(--final);font-weight:700}
.kpi{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin:6px 0 8px}
.kpi div{background:rgba(255,255,255,.04);border-radius:8px;padding:6px;text-align:center}
.kpi b{display:block;font-size:15px}.kpi small{color:var(--muted);font-size:10px}
table{width:100%;border-collapse:collapse;font-size:11px}td{padding:3px 2px;border-bottom:1px solid var(--line)}
td.r{text-align:right}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:middle}
.ok{color:var(--ok)}.bad{color:var(--bad)}
label{display:flex;align-items:center;gap:6px;cursor:pointer;margin:2px 0}
.warn{color:var(--bad);margin-top:6px}
@media (max-width:640px){#hud{width:calc(100% - 24px);max-height:45%}#legend{display:none}}
</style></head><body>
<div id="wrap"><div id="globe"></div>
<div class="panel" id="hud">
 <h1>ASTRO<span>SHIELD</span></h1>
 <div class="sub">Escenario: <b id="scn"></b> · arrastra para girar, rueda para acercar</div>
 <div class="tabs" id="tabs"></div>
 <div class="kpi"><div><b id="kf"></b><small>fitness</small></div><div><b id="kc"></b><small>cubiertas</small></div>
 <div><b id="kv"></b><small>válida</small></div></div>
 <table id="rt"></table><div id="viol" class="warn"></div>
</div>
<div class="panel" id="legend">
 <label><input type="checkbox" id="lFoot" checked> <span class="dot" style="background:var(--final)"></span>Huellas de sensor</label>
 <label><input type="checkbox" id="lZones" checked> <span class="dot" style="background:var(--debris)"></span>Zonas de desechos</label>
 <label><input type="checkbox" id="lObj" checked> <span class="dot" style="background:var(--occ)"></span>Posiciones ocupadas</label>
 <label><input type="checkbox" id="lGhost"> <span class="dot" style="background:var(--initial)"></span>Superponer otro estado</label>
 <label><input type="checkbox" id="lSpin" checked> Rotación automática</label>
 <div class="sub" style="margin:6px 0 0"><span class="ok">●</span> región cubierta · <span class="bad">●</span> no cubierta<br>
 columnas = altitud real del satélite (escala 1:1)</div>
</div></div>
<script src="https://unpkg.com/globe.gl@2.33.1/dist/globe.gl.min.js"></script>
<script>
const D = __DATA__;
const P = D.palette, IMG = 'https://unpkg.com/three-globe@2.33.0/example/img/';
let cur = D.states.length - 1;
const el = document.getElementById('globe'), wrap = document.getElementById('wrap');
const G = Globe()(el).width(wrap.clientWidth).height(wrap.clientHeight)
  .backgroundColor(P.bg).backgroundImageUrl(IMG + 'night-sky.png')
  .globeImageUrl(IMG + 'earth-blue-marble.jpg').bumpImageUrl(IMG + 'earth-topology.png')
  .showAtmosphere(true).atmosphereColor(P.final).atmosphereAltitude(0.18)
  .polygonCapCurvatureResolution(2).polygonSideColor(() => 'rgba(0,0,0,0)')
  .polygonStrokeColor(d => d.properties.stroke).polygonCapColor(d => d.properties.fill)
  .polygonAltitude(d => d.properties.alt)
  .polygonLabel(d => d.properties.tip)
  .pointLat('lat').pointLng('lng').pointAltitude('alt').pointRadius(d => d.r).pointColor('color')
  .pointLabel('tip').pointsMerge(false).pointsTransitionDuration(600)
  // Browser text supports Spanish glyphs missing from the default 3D typeface.
  .htmlLat('lat').htmlLng('lng').htmlAltitude(d => d.alt || 0.012)
  .htmlElement(d => {
    const label = document.createElement('span');
    label.textContent = d.text;
    label.style.color = d.color;
    label.style.fontFamily = 'system-ui, sans-serif';
    label.style.fontSize = `${Math.round(18 * d.size)}px`;
    label.style.whiteSpace = 'nowrap';
    label.style.pointerEvents = 'none';
    label.style.textShadow = '0 1px 3px #000';
    label.style.transition = 'opacity .2s';
    d.el = label;
    return label;
  })
  .ringLat('lat').ringLng('lng').ringColor(d => t => d.rgba.replace('A', 1 - t))
  .ringMaxRadius(4).ringPropagationSpeed(1.2).ringRepeatPeriod(1600);
G.pointOfView({lat: 15, lng: -70, altitude: 2.3});
G.controls().autoRotate = true; G.controls().autoRotateSpeed = 0.45;
window.addEventListener('resize', () => G.width(wrap.clientWidth).height(wrap.clientHeight));

// HTML labels are drawn over the canvas, so hide those on the far side of the Earth.
let labels = [];
function updateLabelVisibility() {
  const cam = G.camera().position;
  labels.forEach(d => { if (!d.el) return;
    const p = G.getCoords(d.lat, d.lng, d.alt || 0.012);
    d.el.style.opacity = (p.x * cam.x + p.y * cam.y + p.z * cam.z) > 0 ? 1 : 0; });
}
G.controls().addEventListener('change', updateLabelVisibility);

const pct = x => (100 * x).toFixed(0) + '%';
const hex2rgba = (h, a) => { const n = parseInt(h.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };

function render() {
  const s = D.states[cur], ghost = document.getElementById('lGhost').checked ? D.states[cur === 0 ? D.states.length - 1 : 0] : null;
  const showFoot = document.getElementById('lFoot').checked, showZ = document.getElementById('lZones').checked,
        showO = document.getElementById('lObj').checked;
  const regionStatus = Object.fromEntries(s.regions.map(r => [r.name, r]));
  const polys = [];
  D.zones.forEach(z => { const k = z.properties.kind; if ((k === 'debris' && !showZ) || (k === 'occupied' && !showO)) return;
    const c = k === 'debris' ? P.debris : P.occupied;
    polys.push({...z, properties: {...z.properties, fill: hex2rgba(c, .28), stroke: c, alt: .006,
      tip: `<b>${z.properties.name}</b><br>${k === 'debris' ? 'Zona de desechos' : 'Posición ocupada'} · radio ${z.properties.radius}°`}}); });
  D.regionShapes.forEach(r => { const st = regionStatus[r.properties.name], c = st.covered ? P.covered : P.uncovered;
    polys.push({...r, properties: {...r.properties, fill: hex2rgba(c, .55), stroke: c, alt: .009,
      tip: `<b>${st.name}</b> (${st.priority})<br>cobertura ${pct(st.coverage)} · redundancia ${pct(st.redundancy)}`}}); });
  if (showFoot) s.footprints.forEach(f => polys.push({...f, properties: {...f.properties,
      fill: hex2rgba(P.final, .10), stroke: hex2rgba(P.final, .9), alt: .003, tip: `Huella S${f.properties.sat}`}}));
  if (ghost && showFoot) ghost.footprints.forEach(f => polys.push({...f, properties: {...f.properties,
      fill: 'rgba(0,0,0,0)', stroke: hex2rgba(P.initial, .9), alt: .002, tip: `Huella S${f.properties.sat} (${ghost.label})`}}));
  G.polygonsData(polys);

  const mk = (st, color, r) => st.satellites.map(x => ({...x, color: x.violating ? P.uncovered : color, r,
     tip: `<b>S${x.id}</b> · ${st.label}<br>${x.lat.toFixed(2)}°, ${x.lng.toFixed(2)}°<br>altitud ${x.alt_km.toFixed(0)} km · huella ${x.footprint_km.toFixed(0)} km${x.violating ? '<br><b>¡viola una restricción!</b>' : ''}`}));
  G.pointsData(mk(s, cur === 0 ? P.initial : P.final, .55).concat(ghost ? mk(ghost, P.initial, .3) : []));

  labels = s.satellites.map(x => ({lat: x.lat, lng: x.lng, alt: x.alt + .01, text: 'S' + x.id, size: 1.1, dot: .5,
      color: cur === 0 ? P.initial : P.final}))
    .concat(s.regions.map(r => ({lat: r.lat, lng: r.lng, text: r.name, size: .75, dot: .25, color: r.covered ? P.covered : P.uncovered})))
    .concat(D.zoneCenters.filter(z => (z.kind === 'debris' ? showZ : showO)).map(z => ({lat: z.lat, lng: z.lng, text: z.name, size: .7, dot: 0,
      color: z.kind === 'debris' ? P.debris : P.occupied})));
  G.htmlElementsData(labels);
  requestAnimationFrame(updateLabelVisibility);
  G.ringsData(s.regions.map(r => ({lat: r.lat, lng: r.lng, rgba: hex2rgba(r.covered ? P.covered : P.uncovered, 'A')})));

  document.getElementById('scn').textContent = D.scenario;
  document.getElementById('kf').textContent = s.fitness.toFixed(4);
  document.getElementById('kc').textContent = s.covered + '/' + s.regions.length;
  document.getElementById('kv').innerHTML = s.feasible ? '<span class="ok">sí</span>' : '<span class="bad">no</span>';
  document.getElementById('rt').innerHTML = s.regions.map(r => `<tr><td><span class="dot" style="background:${r.covered ? P.covered : P.uncovered}"></span>${r.name}</td>
    <td class="r">${pct(r.coverage)}</td><td class="r">${r.sats.map(i => 'S' + i).join(' ') || '—'}</td></tr>`).join('');
  document.getElementById('viol').textContent = s.violations.length ? 'Violaciones: ' + s.violations.join(', ') : '';
  document.querySelectorAll('#tabs button').forEach((b, i) => b.classList.toggle('on', i === cur));
}
document.getElementById('tabs').innerHTML = D.states.map((s, i) => `<button data-i="${i}">${s.label}</button>`).join('');
document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => { cur = +b.dataset.i; render(); });
['lFoot', 'lZones', 'lObj', 'lGhost'].forEach(id => document.getElementById(id).onchange = render);
document.getElementById('lSpin').onchange = e => { G.controls().autoRotate = e.target.checked; };
render();
</script></body></html>"""


def globe_html(scenario: Scenario, states: dict, height: int = 640) -> str:
    """Standalone UTF-8 HTML page with the interactive globe."""
    data = json.dumps(globe_data(scenario, states), ensure_ascii=False)
    return GLOBE_TEMPLATE.replace("__DATA__", data).replace("__HEIGHT__", str(height))


def in_colab() -> bool:
    import sys

    return "google.colab" in sys.modules


def show_globe(scenario: Scenario, states: dict, height: int = 640, save_to: str = None):
    """Display the globe inline (Jupyter / Colab) and optionally save it."""
    from IPython.display import HTML, display

    html = globe_html(scenario, states, height)
    if save_to:
        with open(save_to, "w", encoding="utf-8") as fh:
            fh.write(html)
    if in_colab():
        # Colab already renders every output in its own sandboxed iframe.
        display(HTML(html))
    else:
        srcdoc = html.replace("&", "&amp;").replace('"', "&quot;")
        display(HTML(f'<iframe srcdoc="{srcdoc}" style="width:100%;height:{height + 10}px;border:0;'
                     f'border-radius:14px" allow="fullscreen"></iframe>'))
    return html


def plotly_comparison(scenario: Scenario, initial, final):
    """Fallback 3D-like view: two rotatable orthographic globes (plotly)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "scattergeo"}] * 2],
                        subplot_titles=("Configuración inicial (gen 0)", "Configuración final"))
    for col, (cfg, color) in enumerate(((initial, PALETTE["initial"]), (final, PALETTE["final"])), start=1):
        ev = Evaluator(scenario).evaluate(cfg)
        lam = footprint_half_angle(cfg[:, 2], scenario.sensor_half_angle_deg)
        for z in scenario.zones:
            la, lo = circle(z.lat, z.lon, z.radius_deg)
            c = PALETTE["debris"] if z.kind == "debris" else PALETTE["occupied"]
            fig.add_trace(go.Scattergeo(lat=la, lon=lo, mode="lines", fill="toself", line=dict(color=c, width=2),
                                        name=z.name, showlegend=col == 1, legendgroup=z.name), row=1, col=col)
        for s, (la0, lo0, h) in enumerate(cfg):
            la, lo = circle(la0, lo0, lam[s])
            fig.add_trace(go.Scattergeo(lat=la, lon=lo, mode="lines", line=dict(color=color, width=1),
                                        showlegend=False, hoverinfo="skip"), row=1, col=col)
        for r, rr in zip(scenario.regions, ev.regions):
            la, lo = circle(r.lat, r.lon, km_to_deg(r.radius_km))
            c = PALETTE["covered"] if rr.covered else PALETTE["uncovered"]
            fig.add_trace(go.Scattergeo(lat=la, lon=lo, mode="lines", fill="toself", line=dict(color=c, width=2),
                                        name=f"{r.name} {rr.coverage:.0%}", showlegend=False), row=1, col=col)
        fig.add_trace(go.Scattergeo(lat=cfg[:, 0], lon=cfg[:, 1], mode="markers+text",
                                    text=[f"S{i}" for i in range(len(cfg))], textposition="top center",
                                    marker=dict(size=9, color=color, symbol="star"),
                                    name="satélites" if col == 2 else "satélites iniciales"), row=1, col=col)
    fig.update_geos(projection_type="orthographic", showland=True, landcolor="#1E2A55", showocean=True,
                    oceancolor="#0B1026", showcountries=True, countrycolor="#33407A", coastlinecolor="#5B6BB3",
                    bgcolor=PALETTE["bg"], projection_rotation=dict(lon=-60, lat=10))
    fig.update_layout(paper_bgcolor=PALETTE["bg"], font_color=PALETTE["text"], height=520,
                      margin=dict(l=0, r=0, t=40, b=0), legend=dict(font=dict(size=9)))
    return fig
