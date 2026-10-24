"""Plantilla HTML del centro de control (HTML + CSS + JavaScript en una sola página).

centro_control.py reemplaza __DATOS__ por el JSON de la ejecución y __ALTO__ por
la altura en píxeles. Librerías (versión fija, desde CDN): d3 para el mapa 2D y
las gráficas, topojson + world-atlas para los continentes y globe.gl para el globo 3D.
"""

PLANTILLA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AstroShield · Centro de control</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{
  --fondo:#070B1A; --fondo2:#0B1026; --panel:rgba(16,23,52,.82); --linea:#26305C; --borde:rgba(34,211,238,.28);
  --texto:#E6ECFF; --tenue:#8D97C9; --final:#22D3EE; --inicial:#A78BFA; --ok:#34D399; --mal:#F87171;
  --desechos:#FB923C; --ocupada:#F472B6; --media:#FACC15;
  --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--fondo);color:var(--texto);font-family:var(--mono);font-size:12px}
button,select,input{font:inherit;color:inherit}
#app{position:relative;height:__ALTO__px;display:grid;grid-template-columns:minmax(0,1fr);grid-template-rows:58px minmax(0,1fr) 50px 36px 392px;gap:6px;padding:8px;
  background:radial-gradient(1200px 500px at 50% 0%,#101a44 0%,var(--fondo) 60%)}
.panel{position:relative;background:var(--panel);border:1px solid var(--borde);border-radius:6px}
.panel::before,.panel::after{content:"";position:absolute;width:10px;height:10px;border-color:var(--final);border-style:solid;opacity:.8}
.panel::before{top:-1px;left:-1px;border-width:2px 0 0 2px;border-top-left-radius:6px}
.panel::after{bottom:-1px;right:-1px;border-width:0 2px 2px 0;border-bottom-right-radius:6px}
h2{margin:0 0 6px;font-size:10px;letter-spacing:.18em;color:var(--final);font-weight:700}
h3{margin:10px 0 6px;font-size:11px;letter-spacing:.12em;color:var(--texto);font-weight:700}
.tenue{color:var(--tenue)} .ok{color:var(--ok)} .mal{color:var(--mal)} .cian{color:var(--final)}
/* ---------- cabecera ---------- */
#cab{display:flex;align-items:center;gap:10px;padding:6px 12px;min-width:0}
.marca{display:flex;flex-direction:column;line-height:1.15;min-width:150px}
.marca b{font-size:17px;letter-spacing:.08em}.marca b span{color:var(--final)}
.marca small{font-size:9px;letter-spacing:.3em;color:var(--tenue)}
.sel{display:flex;flex-direction:column;gap:2px;font-size:9px;letter-spacing:.2em;color:var(--tenue)}
.sel select{background:#0d1534;border:1px solid var(--linea);border-radius:4px;padding:4px 6px;font-size:11px;letter-spacing:0;color:var(--texto);max-width:250px}
#kpis{display:flex;gap:6px;flex:1;justify-content:center;min-width:0}
.kpi{min-width:84px;padding:4px 8px;border:1px solid var(--linea);border-radius:4px;background:rgba(255,255,255,.03)}
.kpi small{display:block;font-size:8.5px;letter-spacing:.16em;color:var(--tenue)}
.kpi b{font-size:15px;font-weight:700}
.interruptor{display:flex;align-items:center;gap:6px;font-weight:700;font-size:11px;color:var(--tenue)}
.interruptor .on{color:var(--final)}
#modo3d{position:relative;width:46px;height:24px;border-radius:12px;border:1px solid var(--final);background:rgba(34,211,238,.18);cursor:pointer;padding:0}
#modo3d i{position:absolute;top:3px;left:3px;width:16px;height:16px;border-radius:50%;background:var(--final);transition:left .2s}
#modo3d[aria-checked="true"] i{left:25px}
#modo3d:disabled{opacity:.4;cursor:not-allowed}
.btn{background:#0d1534;border:1px solid var(--linea);border-radius:4px;padding:5px 9px;cursor:pointer;font-size:11px}
.btn:hover{border-color:var(--final)} .btn.on{background:var(--final);color:#04121a;border-color:var(--final);font-weight:700}
/* ---------- misión ---------- */
#mision{display:grid;grid-template-columns:236px minmax(0,1fr) 262px;gap:6px;min-height:0}
#izq,#der{padding:10px;overflow:auto;min-height:0}
#centro{position:relative;overflow:hidden;min-height:0;background:radial-gradient(ellipse at 50% 45%,#0a0f26 0%,#03040c 70%)}
#estrellas{position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
#globo,#mapa{position:absolute;inset:0;z-index:1}
#mapa{width:100%;height:100%;display:none;cursor:grab}
#aviso{position:absolute;bottom:60px;left:50%;transform:translateX(-50%);background:rgba(248,113,113,.15);border:1px solid var(--mal);color:#fecaca;padding:4px 10px;border-radius:4px;font-size:11px;display:none;z-index:3;max-width:90%}
#nota-vista{position:absolute;top:8px;left:10px;max-width:60%;font-size:10.5px;color:var(--tenue);z-index:2;pointer-events:none;background:rgba(7,11,26,.72);padding:4px 8px;border-radius:4px}
#nota-vista b{color:var(--texto);font-size:12px;display:block}
#leyenda{position:absolute;bottom:8px;left:10px;font-size:10px;color:var(--tenue);z-index:2;background:rgba(7,11,26,.7);padding:5px 8px;border-radius:4px;line-height:1.6}
.punto{display:inline-block;width:8px;height:8px;border-radius:50%;margin:0 4px 0 8px;vertical-align:middle}
.punto:first-child{margin-left:0}
.region{padding:6px 6px 7px;border:1px solid transparent;border-radius:4px;cursor:pointer;margin-bottom:3px}
.region:hover{border-color:var(--linea)} .region.activa{border-color:var(--final);background:rgba(34,211,238,.07)}
.region .fila{display:flex;justify-content:space-between;align-items:center;gap:4px}
.region .nom{font-family:var(--sans);font-size:11.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prio{font-size:8.5px;letter-spacing:.1em;padding:1px 4px;border-radius:3px;border:1px solid var(--linea);color:var(--tenue)}
.prio.alta{color:var(--media);border-color:rgba(250,204,21,.5)}
.barra{position:relative;height:6px;background:#1a2350;border-radius:3px;margin:5px 0 3px;overflow:hidden}
.barra i{position:absolute;left:0;top:0;bottom:0;border-radius:3px}
.barra i.red{background:rgba(255,255,255,.55);top:2px;bottom:2px}
.region small{font-size:9.5px;color:var(--tenue)}
#detalle-region{margin-top:8px;border-top:1px solid var(--linea);padding-top:8px;font-size:10.5px;line-height:1.6}
.mini{margin-bottom:6px}
.mini-tit{display:flex;justify-content:space-between;font-size:9px;letter-spacing:.14em;color:var(--tenue)}
.mini-tit b{color:var(--texto);letter-spacing:0}
table{border-collapse:collapse;width:100%}
td,th{padding:3px 4px;border-bottom:1px solid var(--linea);text-align:right;white-space:nowrap}
th{font-size:9px;letter-spacing:.12em;color:var(--tenue);font-weight:600}
td:first-child,th:first-child{text-align:left}
#satelites td,#satelites th{font-size:10px;padding:3px 2px}
/* ---------- línea de tiempo ---------- */
#linea{display:flex;align-items:center;gap:8px;padding:0 10px;min-width:0}
#gen{flex:1;accent-color:var(--final);min-width:120px}
#gen-txt{min-width:120px;font-weight:700}
#play{width:34px}
.capas{display:flex;gap:8px;align-items:center;font-size:10.5px;color:var(--tenue)}
.capas label,#linea>label{display:flex;gap:3px;align-items:center;cursor:pointer;white-space:nowrap}
input[type=checkbox]{accent-color:var(--final)}
/* ---------- pestañas ---------- */
#pestanas{display:flex;gap:4px;overflow-x:auto}
#pestanas button{flex:none;background:transparent;border:1px solid var(--linea);border-bottom-color:transparent;border-radius:5px 5px 0 0;padding:7px 12px;cursor:pointer;color:var(--tenue);font-size:11px;letter-spacing:.05em}
#pestanas button[aria-selected="true"]{color:var(--texto);border-color:var(--final);background:rgba(34,211,238,.1);font-weight:700}
#detalle{padding:12px 14px;overflow:auto}
.rejilla{display:grid;gap:10px}
.r2{grid-template-columns:repeat(2,minmax(0,1fr))} .r3{grid-template-columns:repeat(3,minmax(0,1fr))}
.caja{border:1px solid var(--linea);border-radius:5px;padding:8px 10px;background:rgba(255,255,255,.02);min-width:0}
.caja h3{margin-top:0}
.prueba{font-family:var(--sans);font-size:12px;line-height:1.55}
.prueba .etq{font-family:var(--mono);font-size:9px;letter-spacing:.18em;color:var(--final);display:block;margin-top:6px}
.prueba ul{margin:3px 0 0;padding-left:18px} .prueba li{margin:2px 0}
.prueba b{color:#fff}
.ver{background:transparent;border:1px solid var(--final);color:var(--final);border-radius:4px;padding:2px 7px;cursor:pointer;font-size:10px}
.ver:hover{background:var(--final);color:#04121a}
.grande{font-size:22px;font-weight:700}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{border:1px solid var(--linea);border-radius:4px;padding:4px 8px}
.chip small{display:block;font-size:8.5px;letter-spacing:.14em;color:var(--tenue)}
code{font-family:var(--mono);color:var(--final)}
/* ---------- gráficas ---------- */
svg.graf{display:block;overflow:visible}
.graf .eje text{fill:var(--tenue);font-size:9.5px;font-family:var(--mono)}
.graf .eje path,.graf .eje line{stroke:var(--linea)}
.graf .rej line{stroke:rgba(141,151,201,.13)} .graf .rej path{display:none}
.graf .tit-eje{fill:var(--tenue);font-size:9.5px}
.graf .cursor{stroke:#fff;stroke-width:1;stroke-dasharray:3 3;opacity:.7}
.leyenda-g{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:10px;color:var(--tenue);margin-top:4px}
.leyenda-g i{display:inline-block;width:14px;height:3px;margin-right:4px;vertical-align:middle;border-radius:2px}
#tip{position:fixed;pointer-events:none;background:rgba(7,11,26,.95);border:1px solid var(--final);border-radius:4px;padding:5px 8px;font-size:10.5px;display:none;z-index:20;line-height:1.5;max-width:280px}
.mapa-tierra{fill:#16204a;stroke:#2e3b78;stroke-width:.5}
.mapa-costa{fill:none;stroke:rgba(255,255,255,.22);stroke-width:.4}
.mapa-esfera{fill:#0c1250;stroke:rgba(34,211,238,.35);stroke-width:1}.mapa-ret{fill:none;stroke:rgba(255,255,255,.10);stroke-width:.5}
@media (max-width:1180px){
  #mision{grid-template-columns:208px minmax(0,1fr) 236px}
  .marca{min-width:0} .marca b{font-size:15px} .sel select{max-width:180px}
  .kpi{min-width:0;padding:4px 6px} .kpi b{font-size:13px} .kpi small{letter-spacing:.08em}
  #gen-txt{min-width:0} #gen-txt .tenue,.capas>span{display:none}
  #linea{gap:6px;font-size:11px} .capas{gap:5px}
  #cab .btn{padding:5px 6px}
}
@media (max-width:900px){
  #app{height:auto;grid-template-rows:auto}
  #mision{grid-template-columns:1fr} #centro{height:420px} #izq,#der{max-height:none}
  #kpis{flex-wrap:wrap} #cab{flex-wrap:wrap} #linea{flex-wrap:wrap;padding:8px} #detalle{max-height:none}
  .r2,.r3{grid-template-columns:1fr}
}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js" onerror="(window.__fallas=window.__fallas||[]).push('d3')"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js" onerror="(window.__fallas=window.__fallas||[]).push('topojson')"></script>
<script src="https://unpkg.com/globe.gl@2.33.1/dist/globe.gl.min.js" onerror="(window.__fallas=window.__fallas||[]).push('globe.gl')"></script>
</head>
<body>
<div id="app">
  <header id="cab" class="panel">
    <div class="marca"><b>ASTRO<span>SHIELD</span></b><small>CENTRO DE CONTROL</small></div>
    <label class="sel">CONFIGURACIÓN EN EL MAPA<select id="vista" aria-label="Configuración que se muestra en el mapa"></select></label>
    <div id="kpis"></div>
    <div class="interruptor"><span id="et2d">2D</span>
      <button id="modo3d" role="switch" aria-checked="true" aria-label="Vista 3D activada; pulsa para cambiar a 2D" title="Cambiar entre globo 3D y mapa 2D"><i></i></button>
      <span id="et3d" class="on">3D</span></div>
    <button class="btn" id="descargar" title="Descargar esta página como archivo HTML">⬇ HTML</button>
  </header>
  <main id="mision">
    <section id="izq" class="panel"><h2>REGIONES</h2><div id="regiones"></div><div id="detalle-region"></div></section>
    <section id="centro" class="panel">
      <canvas id="estrellas" aria-hidden="true"></canvas>
      <div id="globo"></div><svg id="mapa" role="img" aria-label="Mapa 2D de la constelación"></svg>
      <div id="nota-vista"></div><div id="aviso" role="status"></div>
      <div id="leyenda">
        <span class="punto" style="background:var(--ok)"></span>cubierta<span class="punto" style="background:var(--mal)"></span>no cubierta
        <span class="punto" style="background:var(--desechos)"></span>desechos<span class="punto" style="background:var(--ocupada)"></span>ocupada<br>
        <span class="punto" style="background:var(--final)"></span>satélite y huella<span class="punto" style="background:var(--inicial)"></span>configuración inicial
        <span class="punto" style="background:var(--mal);border:1px solid #fff"></span>viola una restricción
      </div>
    </section>
    <section id="der" class="panel">
      <h2>TELEMETRÍA</h2>
      <div class="mini"><div class="mini-tit">MEJOR FITNESS / MEDIA <b id="m-fit"></b></div><div id="mini-fitness"></div></div>
      <div class="mini"><div class="mini-tit">FRACCIÓN VÁLIDA <b id="m-fact"></b></div><div id="mini-fact"></div></div>
      <div class="mini"><div class="mini-tit">DIVERSIDAD (°) <b id="m-div"></b></div><div id="mini-div"></div></div>
      <h2 style="margin-top:8px">SATÉLITES</h2><table id="satelites"></table>
    </section>
  </main>
  <div id="linea" class="panel">
    <button class="btn" id="play" title="Reproducir la evolución" aria-label="Reproducir la evolución">▶</button>
    <input type="range" id="gen" min="0" max="0" value="0" aria-label="Generación">
    <span id="gen-txt"></span>
    <button class="btn" id="b-ini">Inicial</button><button class="btn" id="b-fin">Final</button>
    <label title="Superpone la configuración inicial y une cada satélite con su posición final"><input type="checkbox" id="comparar"> Comparar con inicial</label>
    <span class="capas"><span>CAPAS</span>
      <label><input type="checkbox" id="c-huellas" checked>Huellas</label>
      <label><input type="checkbox" id="c-desechos" checked>Desechos</label>
      <label><input type="checkbox" id="c-ocupadas" checked>Ocupadas</label>
      <label><input type="checkbox" id="c-giro" checked>Giro</label></span>
  </div>
  <nav id="pestanas" role="tablist" aria-label="Detalle de las pruebas"></nav>
  <section id="detalle" class="panel" role="tabpanel"></section>
</div>
<div id="tip"></div>
<script id="datos" type="application/json">__DATOS__</script>
<script>
'use strict';
const FUENTE = '<!doctype html>\n' + document.documentElement.outerHTML;
const D = JSON.parse(document.getElementById('datos').textContent);
const P = D.paleta;
const $ = s => document.querySelector(s);
const RT = 6371;
// Imagen satelital NASA Blue Marble: la misma textura en el globo 3D y en el mapa 2D.
const IMG = 'https://unpkg.com/three-globe@2.33.0/example/img/';
const TEXTURA = IMG + 'earth-blue-marble.jpg';
const miles = new Intl.NumberFormat('es-MX');
const f4 = x => x == null ? '—' : Number(x).toFixed(4);
const fx = (x, n) => x == null ? '—' : Number(x).toFixed(n);
const pct = (x, n = 0) => x == null ? '—' : (100 * x).toFixed(n) + '%';
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const md = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
const sino = b => b ? '<span class="ok">sí</span>' : '<span class="mal">no</span>';
const marca = b => b ? '<span class="ok">✔</span>' : '<span class="mal">✖</span>';
const rgba = (h, a) => { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
const VISTAS = Object.fromEntries(D.vistas.map(v => [v.id, v]));
const FALLAS = window.__fallas || [];
const E = {vista: VISTAS[D.vista_inicial] || D.vistas[0], gen: 0, modo3d: true, region: null, comparar: false,
  capas: {huellas: true, desechos: true, ocupadas: true, giro: true}, reproduciendo: null};

// ---------------------------------------------------------------- geometría (igual que geometria.py)
const rad = x => x * Math.PI / 180, grad = x => x * 180 / Math.PI;
function destino(lat, lon, rumbo, dist) {
  const p1 = rad(lat), l1 = rad(lon), b = rad(rumbo), d = rad(dist);
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [grad(p2), ((grad(l2) + 180) % 360 + 360) % 360 - 180];
}
function distAng(la1, lo1, la2, lo2) {
  const p1 = rad(la1), p2 = rad(la2), dp = p2 - p1, dl = rad(lo2 - lo1);
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return grad(2 * Math.asin(Math.sqrt(Math.min(Math.max(a, 0), 1))));
}
function muestrasDisco(lat, lon, radio, anillos) {
  const pts = [[lat, lon]];
  for (let k = 1; k <= anillos; k++) {
    const n = 8 * k, desfase = k % 2 ? 0 : 180 / n;
    for (let j = 0; j < n; j++) pts.push(destino(lat, lon, desfase + j * 360 / n, radio * k / anillos));
  }
  return pts;
}
function casquete(lat, lon, r) {
  // globe.gl exige que cada anillo cierre exactamente en su primer punto.
  const c = d3.geoCircle().center([lon, lat]).radius(r).precision(1.5)();
  c.coordinates.forEach(a => { a[a.length - 1] = a[0].slice(); });
  return c;
}

// ---------------------------------------------------------------- estado
function cuadroEn(v, gen) {
  if (v.gen_total == null) return v.cuadros[0];
  let c = v.cuadros[0];
  for (const k of v.cuadros) { if (k.g <= gen) c = k; else break; }
  return c;
}
const escDe = v => D.escenarios[v.escenario];
function criterios(c, sc) {
  const altas = sc.regiones.map((r, i) => [r, i]).filter(([r]) => r.prioridad === 'alta');
  const nec = Math.min(altas.length, Math.max(sc.n_satelites - sc.regiones.length, 0));
  return [
    ['C1', 'Válida (sin violaciones)', !!c.ok],
    ['C2', 'Todas las regiones cubiertas', c.c === sc.regiones.length],
    ['C3', `≥${nec} regiones Alta con redundancia ≥ 95%`, altas.filter(([, i]) => c.r[i][1] >= 0.95).length >= nec],
    ['C4', 'Fitness ≥ 90% de la cota de referencia', c.f >= 0.9 * sc.cota - 1e-9]];
}
const colorRegion = ok => ok ? P.cubierta : P.no_cubierta;

// ---------------------------------------------------------------- tooltip
const tip = $('#tip');
function mostrarTip(ev, html) { tip.innerHTML = html; tip.style.display = 'block';
  const x = Math.min(ev.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
  tip.style.left = x + 'px'; tip.style.top = (ev.clientY + 14) + 'px'; }
const ocultarTip = () => { tip.style.display = 'none'; };

// ---------------------------------------------------------------- gráficas SVG (d3)
function grafica(cont, o) {
  cont.innerHTML = '';
  const W = Math.max(cont.clientWidth, 160), H = o.alto || 150;
  const m = {t: 8, r: o.margenDer || 14, b: o.ejeX ? 30 : 18, l: o.margenIzq || 42};
  const svg = d3.select(cont).append('svg').attr('class', 'graf').attr('width', W).attr('height', H);
  const sx = d3.scaleLinear(o.x, [m.l, W - m.r]), sy = d3.scaleLinear(o.y, [H - m.b, m.t]);
  svg.append('g').attr('class', 'rej').attr('transform', `translate(${m.l},0)`)
    .call(d3.axisLeft(sy).ticks(o.ticksY || 4).tickSize(-(W - m.l - m.r)).tickFormat(''));
  svg.append('g').attr('class', 'eje').attr('transform', `translate(0,${H - m.b})`)
    .call(d3.axisBottom(sx).ticks(Math.max(2, Math.floor(W / 70))).tickSizeOuter(0).tickFormat(o.fx || null));
  svg.append('g').attr('class', 'eje').attr('transform', `translate(${m.l},0)`)
    .call(d3.axisLeft(sy).ticks(o.ticksY || 4).tickSizeOuter(0).tickFormat(o.fy || null));
  if (o.ejeX) svg.append('text').attr('class', 'tit-eje').attr('x', W - m.r).attr('y', H - 2).attr('text-anchor', 'end').text(o.ejeX);
  if (o.ejeY) svg.append('text').attr('class', 'tit-eje').attr('x', 2).attr('y', m.t - 1).attr('dy', '.7em')
    .attr('transform', `rotate(-90 ${8} ${m.t + 40})`).attr('text-anchor', 'end').text(o.ejeY);
  const xsDe = s => s.x || s.y.map((_, i) => i);
  for (const b of o.bandas || []) {
    const xs = b.x || b.y0.map((_, i) => i);
    svg.append('path').attr('fill', b.color).attr('d', d3.area().defined((_, i) => b.y0[i] != null && b.y1[i] != null)
      .x((_, i) => sx(xs[i])).y0((_, i) => sy(b.y0[i])).y1((_, i) => sy(b.y1[i]))(xs));
  }
  for (const h of o.h || []) {
    svg.append('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', sy(h.y)).attr('y2', sy(h.y))
      .attr('stroke', h.color).attr('stroke-dasharray', '5 4').attr('stroke-width', 1);
    if (h.txt) svg.append('text').attr('x', W - m.r - 2).attr('y', sy(h.y) - 3).attr('text-anchor', 'end')
      .attr('fill', h.color).attr('font-size', 9.5).text(h.txt);
  }
  for (const v of o.v || []) {
    svg.append('line').attr('x1', sx(v.x)).attr('x2', sx(v.x)).attr('y1', m.t).attr('y2', H - m.b)
      .attr('stroke', v.color).attr('stroke-dasharray', '2 3');
    if (v.txt) svg.append('text').attr('x', sx(v.x) + 3).attr('y', m.t + 9).attr('fill', v.color).attr('font-size', 9.5).text(v.txt);
  }
  for (const s of o.series) {
    const xs = xsDe(s);
    svg.append('path').attr('fill', 'none').attr('stroke', s.color).attr('stroke-width', s.ancho || 1.6)
      .attr('stroke-dasharray', s.guion || null).attr('opacity', s.opacidad || 1)
      .attr('d', d3.line().defined((_, i) => s.y[i] != null).x((_, i) => sx(xs[i])).y((_, i) => sy(s.y[i]))(xs));
  }
  const cursor = svg.append('line').attr('class', 'cursor').attr('y1', m.t).attr('y2', H - m.b).style('display', 'none');
  const nombradas = o.series.filter(s => s.nombre);
  if (nombradas.length) {
    svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', W - m.l - m.r).attr('height', H - m.t - m.b)
      .attr('fill', 'transparent')
      .on('mousemove', ev => {
        const x = sx.invert(d3.pointer(ev)[0]);
        const filas = nombradas.map(s => { const xs = xsDe(s); const i = d3.minIndex(xs, v => Math.abs(v - x));
          return `<span style="color:${s.color}">■</span> ${esc(s.nombre)}: <b>${s.y[i] == null ? '—' : (o.fy ? o.fy(s.y[i]) : fx(s.y[i], 4))}</b>`; });
        mostrarTip(ev, `${esc(o.nombreX || 'x')} <b>${Math.round(x)}</b><br>` + filas.join('<br>'));
      }).on('mouseleave', ocultarTip);
  }
  if (o.leyenda !== false && nombradas.length > 1) {
    const l = document.createElement('div'); l.className = 'leyenda-g';
    l.innerHTML = nombradas.map(s => `<span><i style="background:${s.color}"></i>${esc(s.nombre)}</span>`).join('')
      + (o.h || []).filter(h => h.nombre).map(h => `<span><i style="background:${h.color}"></i>${esc(h.nombre)}</span>`).join('');
    cont.appendChild(l);
  }
  return {cursor(x) { if (x == null) cursor.style('display', 'none'); else cursor.style('display', null).attr('x1', sx(x)).attr('x2', sx(x)); }};
}

function barrasH(cont, filas, o) {
  cont.innerHTML = '';
  const W = Math.max(cont.clientWidth, 200), fh = o.altoFila || 22, m = {t: 4, r: 54, b: 22, l: o.margenIzq || 150};
  const H = m.t + m.b + fh * filas.length;
  const svg = d3.select(cont).append('svg').attr('class', 'graf').attr('width', W).attr('height', H);
  const sx = d3.scaleLinear(o.x, [m.l, W - m.r]).clamp(true);
  svg.append('g').attr('class', 'rej').attr('transform', `translate(0,${H - m.b})`)
    .call(d3.axisBottom(sx).ticks(5).tickSize(-(H - m.t - m.b)).tickFormat(''));
  svg.append('g').attr('class', 'eje').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(sx).ticks(5).tickFormat(o.fx || null));
  filas.forEach((f, i) => {
    const y = m.t + i * fh, x0 = sx(o.x[0] < 0 && f.valor >= 0 ? 0 : o.x[0]);
    svg.append('text').attr('x', m.l - 6).attr('y', y + fh / 2 + 3).attr('text-anchor', 'end').attr('fill', '#E6ECFF')
      .attr('font-size', 10).text(f.nombre);
    const xa = Math.min(x0, sx(f.valor)), xb = Math.max(x0, sx(f.valor));
    svg.append('rect').attr('x', xa).attr('y', y + 4).attr('width', Math.max(xb - xa, 1)).attr('height', fh - 8)
      .attr('fill', f.color || P.final).attr('rx', 2)
      .on('mousemove', ev => mostrarTip(ev, f.tip || `${esc(f.nombre)}: <b>${o.fv ? o.fv(f.valor) : f.valor}</b>`)).on('mouseleave', ocultarTip);
    if (f.error) svg.append('line').attr('x1', sx(f.valor - f.error)).attr('x2', sx(f.valor + f.error))
      .attr('y1', y + fh / 2).attr('y2', y + fh / 2).attr('stroke', '#fff').attr('stroke-width', 1.2);
    svg.append('text').attr('x', W - m.r + 4).attr('y', y + fh / 2 + 3).attr('fill', '#8D97C9').attr('font-size', 9.5)
      .text(o.fv ? o.fv(f.valor) : f.valor);
  });
  for (const v of o.v || []) {
    svg.append('line').attr('x1', sx(v.x)).attr('x2', sx(v.x)).attr('y1', m.t).attr('y2', H - m.b).attr('stroke', v.color).attr('stroke-dasharray', '4 3');
    svg.append('text').attr('x', sx(v.x)).attr('y', H - m.b + 18).attr('text-anchor', 'middle').attr('fill', v.color).attr('font-size', 9).text(v.txt || '');
  }
}

function barrasAgrupadas(cont, grupos, series, o) {
  cont.innerHTML = '';
  const W = Math.max(cont.clientWidth, 200), H = o.alto || 170, m = {t: 8, r: 8, b: 30, l: 42};
  const svg = d3.select(cont).append('svg').attr('class', 'graf').attr('width', W).attr('height', H);
  const x0 = d3.scaleBand(grupos, [m.l, W - m.r]).padding(0.25), x1 = d3.scaleBand(series.map(s => s.nombre), [0, x0.bandwidth()]).padding(0.08);
  const sy = d3.scaleLinear(o.y, [H - m.b, m.t]).clamp(true);
  svg.append('g').attr('class', 'rej').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(sy).ticks(4).tickSize(-(W - m.l - m.r)).tickFormat(''));
  svg.append('g').attr('class', 'eje').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x0).tickSizeOuter(0));
  svg.append('g').attr('class', 'eje').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(sy).ticks(4).tickFormat(o.fy || null));
  if (o.ejeX) svg.append('text').attr('class', 'tit-eje').attr('x', W - m.r).attr('y', H - 2).attr('text-anchor', 'end').text(o.ejeX);
  series.forEach(s => s.valores.forEach((v, i) => {
    svg.append('rect').attr('x', x0(grupos[i]) + x1(s.nombre)).attr('width', x1.bandwidth()).attr('y', sy(v))
      .attr('height', Math.max(sy(o.y[0]) - sy(v), 0)).attr('fill', s.color).attr('rx', 1.5)
      .on('mousemove', ev => mostrarTip(ev, `${esc(grupos[i])} · ${esc(s.nombre)}<br><b>${fx(v, 4)}</b>${s.tips ? '<br>' + esc(s.tips[i]) : ''}`))
      .on('mouseleave', ocultarTip);
  }));
  const l = document.createElement('div'); l.className = 'leyenda-g';
  l.innerHTML = series.map(s => `<span><i style="background:${s.color}"></i>${esc(s.nombre)}</span>`).join('');
  cont.appendChild(l);
}

// ---------------------------------------------------------------- cabecera, regiones, satélites
function llenarSelector() {
  const sel = $('#vista'), grupos = {};
  D.vistas.forEach(v => (grupos[v.grupo] = grupos[v.grupo] || []).push(v));
  sel.innerHTML = Object.entries(grupos).map(([g, vs]) => `<optgroup label="${esc(g)}">` +
    vs.map(v => `<option value="${esc(v.id)}">${esc(v.titulo)}</option>`).join('') + '</optgroup>').join('');
  sel.value = E.vista.id;
  sel.onchange = () => seleccionarVista(sel.value, false);
}

function renderKPIs(c, sc) {
  const cr = criterios(c, sc), cumple = cr.filter(x => x[2]).length;
  const k = (t, v, cls = '', tit = '') => `<div class="kpi" title="${esc(tit)}"><small>${t}</small><b class="${cls}">${v}</b></div>`;
  $('#kpis').innerHTML =
    k('FITNESS', f4(c.f), 'cian', 'Calidad de la configuración, de 0 a 1') +
    k('% DE LA COTA', sc.cota ? fx(100 * c.f / sc.cota, 1) + '%' : '—', '', `Cota de referencia ${f4(sc.cota)}`) +
    k('REGIONES', `${c.c}/${sc.regiones.length}`, c.c === sc.regiones.length ? 'ok' : 'mal', 'Regiones cubiertas (≥ 95% de sus puntos)') +
    k('VIOLACIONES', c.ok ? '0' : `${c.x.length} · ${fx(c.v, 1)}°`, c.ok ? 'ok' : 'mal', c.ok ? 'Configuración válida' : c.x.join('\n')) +
    k('CRITERIOS', `${cumple}/4 ${cumple === 4 ? 'ACEPTADA' : 'NO ACEPTADA'}`, cumple === 4 ? 'ok' : 'mal',
      cr.map(x => `${x[0]} ${x[1]}: ${x[2] ? 'sí' : 'no'}`).join('\n'));
}

function renderRegiones(c, sc) {
  $('#regiones').innerHTML = sc.regiones.map((r, i) => {
    const [cob, red, , cub, sats] = c.r[i], col = colorRegion(cub);
    return `<div class="region${E.region === i ? ' activa' : ''}" data-i="${i}">
      <div class="fila"><span class="nom"><span class="punto" style="background:${col}"></span>${esc(r.nombre)}</span>
      <span class="prio ${r.prioridad}">${r.prioridad.toUpperCase()}</span></div>
      <div class="barra"><i style="width:${100 * cob}%;background:${col}"></i><i class="red" style="width:${100 * red}%"></i></div>
      <small>cobertura <b style="color:${col}">${pct(cob)}</b> · redund. ${pct(red)} · ${sats.length ? sats.map(s => 'S' + s).join(' ') : 'sin satélites'}</small></div>`;
  }).join('');
  document.querySelectorAll('.region').forEach(el => el.onclick = () => {
    const i = +el.dataset.i; E.region = E.region === i ? null : i; render();
    if (E.region != null) enfocar(sc.regiones[i].lat, sc.regiones[i].lon);
  });
  const det = $('#detalle-region');
  if (E.region == null || E.region >= sc.regiones.length) {
    det.innerHTML = '<span class="tenue">Haz clic en una región para ver su detalle y centrarla en el mapa.</span>'; return;
  }
  const r = sc.regiones[E.region], [cob, red, res, cub, sats] = c.r[E.region], w = sc.pesos_fitness;
  det.innerHTML = `<h2>${esc(r.nombre.toUpperCase())}</h2>
    Prioridad <b>${r.prioridad}</b> (peso ${r.peso}) · centro ${fx(r.lat, 1)}°, ${fx(r.lon, 1)}° · radio ${r.radio_km} km<br>
    Cobertura <b>${pct(cob, 1)}</b> · redundancia <b>${pct(red, 1)}</b> · resolución <b>${fx(res, 3)}</b><br>
    Puntaje = ${w[0]}·${fx(cob, 3)} + ${w[1]}·${fx(red, 3)} + ${w[2]}·${fx(res, 3)} = <b>${fx(w[0] * cob + w[1] * red + w[2] * res, 4)}</b><br>
    Estado: ${cub ? '<b class="ok">CUBIERTA</b>' : '<b class="mal">NO CUBIERTA</b>'} · satélites: ${sats.map(s => 'S' + s).join(', ') || 'ninguno'}`;
}

function renderSatelites(c, ini) {
  const filas = c.s.map((s, i) => {
    const mov = ini && ini.s[i] ? distAng(ini.s[i][0], ini.s[i][1], s[0], s[1]) : null;
    return `<tr title="${s[4] ? 'Viola una restricción' : ''}"><td><span class="punto" style="background:${s[4] ? P.no_cubierta : P.final}"></span>S${i}</td>
      <td>${fx(s[0], 2)}</td><td>${fx(s[1], 2)}</td><td>${fx(s[2], 0)}</td>
      <td>${mov == null ? fx(s[3] * Math.PI / 180 * RT, 0) : fx(mov, 1) + '°'}</td></tr>`;
  }).join('');
  $('#satelites').innerHTML = `<tr><th>SAT</th><th>LAT</th><th>LON</th><th title="Altitud en km">ALT</th>${ini
    ? '<th title="Distancia desde la posición inicial">MOVIDO</th>' : '<th title="Radio de la huella del sensor, en km">HUELLA</th>'}</tr>` + filas;
}

let minis = null;
function renderMinis() {
  const v = E.vista, h = v.hist;
  if (!h) {
    ['#mini-fitness', '#mini-fact', '#mini-div'].forEach(s => { $(s).innerHTML = '<div class="tenue" style="padding:10px 0">Configuración fija: sin historial de evolución.</div>'; });
    ['#m-fit', '#m-fact', '#m-div'].forEach(s => { $(s).textContent = ''; }); minis = null; return;
  }
  const n = h.mejor.length - 1, nf = 'generación';
  minis = [
    grafica($('#mini-fitness'), {alto: 92, x: [0, n], y: [0, 1], margenIzq: 30, nombreX: nf, leyenda: false,
      series: [{y: h.media, color: P.media, ancho: 1.1, nombre: 'media'}, {y: h.mejor, color: P.final, ancho: 1.8, nombre: 'mejor histórico'}],
      h: [{y: D.escenarios[v.escenario].cota, color: rgba(P.cubierta, .7)}]}),
    grafica($('#mini-fact'), {alto: 70, x: [0, n], y: [0, 1], margenIzq: 30, nombreX: nf, ticksY: 2, fy: d3.format('.0%'),
      series: [{y: h.fact, color: P.cubierta, nombre: 'fracción válida'}]}),
    grafica($('#mini-div'), {alto: 70, x: [0, n], y: [0, Math.max(5, d3.max(h.div))], margenIzq: 30, nombreX: nf, ticksY: 2,
      series: [{y: h.div, color: P.ocupada, nombre: 'diversidad (°)'}], fy: d3.format('.0f')})];
}
function cursorMinis() {
  const h = E.vista.hist; if (!minis || !h) return;
  const g = Math.min(E.gen, h.mejor.length - 1);
  minis.forEach(m => m.cursor(g));
  $('#m-fit').textContent = f4(h.mejor[g]); $('#m-fact').textContent = pct(h.fact[g]); $('#m-div').textContent = fx(h.div[g], 1) + '°';
}

// ---------------------------------------------------------------- globo 3D
function hayWebGL() {
  try { const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl'))); }
  catch (e) { return false; }
}
let G = null, etiquetas = [];
function iniciarGlobo() {
  if (typeof Globe === 'undefined' || !hayWebGL()) return null;
  const el = $('#globo'), cont = $('#centro');
  const g = Globe({animateIn: false})(el).width(cont.clientWidth).height(cont.clientHeight)
    .backgroundColor('rgba(0,0,0,0)').globeImageUrl(TEXTURA).bumpImageUrl(IMG + 'earth-topology.png')
    .showAtmosphere(true).atmosphereColor(P.final).atmosphereAltitude(0.16)
    .polygonGeoJsonGeometry('geom').polygonCapCurvatureResolution(2).polygonSideColor(() => 'rgba(0,0,0,0)')
    .polygonStrokeColor('borde').polygonCapColor('relleno').polygonAltitude('alt').polygonLabel('tip').polygonsTransitionDuration(0)
    .pointLat('lat').pointLng('lng').pointAltitude('alt').pointRadius('r').pointColor('color').pointLabel('tip').pointsMerge(false)
    .pointsTransitionDuration(300)
    .arcStartLat('a0').arcStartLng('o0').arcEndLat('a1').arcEndLng('o1').arcColor('color').arcStroke(0.45)
    .arcDashLength(0.5).arcDashGap(0.15).arcDashAnimateTime(2200).arcAltitudeAutoScale(0.35)
    .htmlLat('lat').htmlLng('lng').htmlAltitude(d => d.alt || 0.012)
    .htmlElement(d => { const s = document.createElement('span'); s.textContent = d.texto;
      Object.assign(s.style, {color: d.color, fontFamily: 'JetBrains Mono, monospace', fontSize: Math.round(15 * d.tam) + 'px',
        whiteSpace: 'nowrap', pointerEvents: 'none', textShadow: '0 1px 3px #000', transition: 'opacity .2s'});
      d.el = s; return s; })
    .ringLat('lat').ringLng('lng').ringColor(d => t => rgba(d.color, 1 - t)).ringMaxRadius(4).ringPropagationSpeed(1.2).ringRepeatPeriod(1700);
  g.pointOfView({lat: 15, lng: -60, altitude: 2.4});
  g.controls().autoRotate = true; g.controls().autoRotateSpeed = 0.4;
  g.controls().addEventListener('change', visibilidadEtiquetas);
  return g;
}
function visibilidadEtiquetas() {
  if (!G) return;
  const cam = G.camera().position;
  etiquetas.forEach(d => { if (!d.el) return; const p = G.getCoords(d.lat, d.lng, d.alt || 0.012);
    d.el.style.opacity = (p.x * cam.x + p.y * cam.y + p.z * cam.z) > 0 ? 1 : 0; });
}
function renderGlobo(c, sc, ini) {
  const pol = [];
  sc.zonas.forEach(z => {
    const des = z.tipo === 'desechos'; if (des ? !E.capas.desechos : !E.capas.ocupadas) return;
    const col = des ? P.desechos : P.ocupada;
    pol.push({geom: casquete(z.lat, z.lon, z.radio), relleno: rgba(col, .26), borde: col, alt: .006,
      tip: `<b>${esc(z.nombre)}</b><br>${des ? 'Zona de desechos' : 'Posición ocupada'} · radio ${z.radio}°`});
  });
  sc.regiones.forEach((r, i) => { const col = colorRegion(c.r[i][3]);
    pol.push({geom: casquete(r.lat, r.lon, r.radio_km / RT * 180 / Math.PI), relleno: rgba(col, E.region === i ? .85 : .55), borde: col, alt: .009,
      tip: `<b>${esc(r.nombre)}</b> (${r.prioridad})<br>cobertura ${pct(c.r[i][0])} · redundancia ${pct(c.r[i][1])}`}); });
  if (E.capas.huellas) c.s.forEach((s, i) => pol.push({geom: casquete(s[0], s[1], s[3]), relleno: rgba(s[4] ? P.no_cubierta : P.final, .1),
    borde: rgba(s[4] ? P.no_cubierta : P.final, .9), alt: .003, tip: `Huella de S${i} · radio ${fx(s[3] * Math.PI / 180 * RT, 0)} km`}));
  if (ini && E.capas.huellas) ini.s.forEach((s, i) => pol.push({geom: casquete(s[0], s[1], s[3]), relleno: 'rgba(0,0,0,0)',
    borde: rgba(P.inicial, .85), alt: .002, tip: `Huella inicial de S${i}`}));
  G.polygonsData(pol);
  const pts = c.s.map((s, i) => ({lat: s[0], lng: s[1], alt: s[2] / RT, r: .5, color: s[4] ? P.no_cubierta : P.final,
    tip: `<b>S${i}</b><br>${fx(s[0], 2)}°, ${fx(s[1], 2)}°<br>altitud ${fx(s[2], 0)} km · huella ${fx(s[3] * Math.PI / 180 * RT, 0)} km${s[4] ? '<br><b>¡viola una restricción!</b>' : ''}`}));
  if (ini) ini.s.forEach((s, i) => pts.push({lat: s[0], lng: s[1], alt: s[2] / RT, r: .3, color: P.inicial, tip: `S${i} inicial · ${fx(s[2], 0)} km`}));
  G.pointsData(pts);
  G.arcsData(ini ? c.s.map((s, i) => ({a0: ini.s[i][0], o0: ini.s[i][1], a1: s[0], o1: s[1], color: [P.inicial, P.final]})) : []);
  etiquetas = c.s.map((s, i) => ({lat: s[0], lng: s[1], alt: s[2] / RT + .012, texto: 'S' + i, tam: 1, color: s[4] ? P.no_cubierta : P.final}))
    .concat(sc.regiones.map((r, i) => ({lat: r.lat, lng: r.lon, texto: r.nombre, tam: .78, color: colorRegion(c.r[i][3])})))
    .concat(sc.zonas.filter(z => z.tipo === 'desechos' ? E.capas.desechos : E.capas.ocupadas)
      .map(z => ({lat: z.lat, lng: z.lon, texto: z.nombre, tam: .7, color: z.tipo === 'desechos' ? P.desechos : P.ocupada})));
  G.htmlElementsData(etiquetas);
  requestAnimationFrame(visibilidadEtiquetas);
  G.ringsData(sc.regiones.map((r, i) => ({lat: r.lat, lng: r.lon, color: colorRegion(c.r[i][3])})));
  G.controls().autoRotate = E.capas.giro && E.reproduciendo == null;
}

// ---------------------------------------------------------------- mapa 2D
const MAPA = {listo: false};
function iniciarMapa() {
  const svg = d3.select('#mapa');
  MAPA.svg = svg; MAPA.g = svg.append('g');
  ['esfera', 'ret', 'tierra', 'zonas', 'regiones', 'huellas', 'fantasma', 'arcos', 'sats', 'etiq'].forEach(k => { MAPA[k] = MAPA.g.append('g'); });
  MAPA.zoom = d3.zoom().scaleExtent([1, 10]).on('zoom', ev => { MAPA.g.attr('transform', ev.transform); MAPA.k = ev.transform.k; escalarTextos(); });
  svg.call(MAPA.zoom); MAPA.k = 1;
  ajustarMapa();
  fetch('https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json').then(r => r.json()).then(t => {
    MAPA.tierraGeo = topojson.feature(t, t.objects.land); dibujarFondo();
  }).catch(() => { MAPA.sinTierra = true; });
  MAPA.listo = true;
}
function ajustarMapa() {
  const el = $('#centro'), w = el.clientWidth, h = el.clientHeight;
  MAPA.svg.attr('viewBox', `0 0 ${w} ${h}`);
  MAPA.proy = d3.geoEquirectangular().fitExtent([[8, 62], [w - 8, h - 50]], {type: 'Sphere'});
  MAPA.ruta = d3.geoPath(MAPA.proy);
  dibujarFondo();
}
function dibujarFondo() {
  if (!MAPA.ruta) return;
  MAPA.esfera.selectAll('*').remove(); MAPA.ret.selectAll('*').remove(); MAPA.tierra.selectAll('*').remove();
  MAPA.esfera.append('path').attr('class', 'mapa-esfera').attr('d', MAPA.ruta({type: 'Sphere'}));
  // La proyección es equirectangular, igual que la imagen: encaja exacta en el rectángulo de la esfera.
  const [[x0, y0], [x1, y1]] = MAPA.ruta.bounds({type: 'Sphere'});
  if (!MAPA.sinImagen) MAPA.esfera.append('image').attr('href', TEXTURA).attr('x', x0).attr('y', y0)
    .attr('width', x1 - x0).attr('height', y1 - y0).attr('preserveAspectRatio', 'none')
    .on('error', () => { MAPA.sinImagen = true; dibujarFondo(); });
  MAPA.ret.append('path').attr('class', 'mapa-ret').attr('d', MAPA.ruta(d3.geoGraticule10()));
  if (MAPA.tierraGeo) MAPA.tierra.append('path').attr('class', MAPA.sinImagen ? 'mapa-tierra' : 'mapa-costa')
    .attr('vector-effect', 'non-scaling-stroke').attr('d', MAPA.ruta(MAPA.tierraGeo));
}
function escalarTextos() { const k = MAPA.k || 1;
  MAPA.etiq.selectAll('text').attr('font-size', d => (d.tam || 10) / k).attr('stroke-width', 2.5 / k);
  MAPA.sats.selectAll('circle').attr('r', d => d.r / k); }
function renderMapa(c, sc, ini) {
  if (!MAPA.listo) return;
  const ruta = MAPA.ruta, pr = MAPA.proy;
  const capa = (g, datos, attrs) => { g.selectAll('*').remove();
    datos.forEach(d => { const p = g.append('path').attr('d', ruta(d.geom)).attr('vector-effect', 'non-scaling-stroke');
      Object.entries(attrs(d)).forEach(([k, v]) => p.attr(k, v));
      if (d.tip) p.on('mousemove', ev => mostrarTip(ev, d.tip)).on('mouseleave', ocultarTip); }); };
  capa(MAPA.zonas, sc.zonas.filter(z => z.tipo === 'desechos' ? E.capas.desechos : E.capas.ocupadas).map(z => ({z, geom: casquete(z.lat, z.lon, z.radio),
    tip: `<b>${esc(z.nombre)}</b><br>${z.tipo === 'desechos' ? 'Zona de desechos' : 'Posición ocupada'} · radio ${z.radio}°`})),
    d => { const col = d.z.tipo === 'desechos' ? P.desechos : P.ocupada;
      return {fill: rgba(col, .22), stroke: col, 'stroke-width': 1.3, 'stroke-dasharray': d.z.tipo === 'desechos' ? '5 3' : null}; });
  capa(MAPA.regiones, sc.regiones.map((r, i) => ({i, geom: casquete(r.lat, r.lon, r.radio_km / RT * 180 / Math.PI),
    tip: `<b>${esc(r.nombre)}</b> (${r.prioridad})<br>cobertura ${pct(c.r[i][0])} · redundancia ${pct(c.r[i][1])}`})),
    d => { const col = colorRegion(c.r[d.i][3]); return {fill: rgba(col, E.region === d.i ? .9 : .6), stroke: col, 'stroke-width': 1.5}; });
  capa(MAPA.huellas, E.capas.huellas ? c.s.map((s, i) => ({s, geom: casquete(s[0], s[1], s[3]), tip: `Huella de S${i}`})) : [],
    d => ({fill: rgba(d.s[4] ? P.no_cubierta : P.final, .1), stroke: rgba(d.s[4] ? P.no_cubierta : P.final, .9), 'stroke-width': 1}));
  capa(MAPA.fantasma, ini && E.capas.huellas ? ini.s.map(s => ({geom: casquete(s[0], s[1], s[3])})) : [],
    () => ({fill: 'none', stroke: rgba(P.inicial, .8), 'stroke-width': 1, 'stroke-dasharray': '3 3'}));
  capa(MAPA.arcos, ini ? c.s.map((s, i) => ({geom: {type: 'LineString', coordinates: [[ini.s[i][1], ini.s[i][0]], [s[1], s[0]]]}})) : [],
    () => ({fill: 'none', stroke: rgba(P.inicial, .9), 'stroke-width': 1.2}));
  MAPA.sats.selectAll('*').remove(); MAPA.etiq.selectAll('*').remove();
  const puntos = c.s.map((s, i) => ({s, i, r: 4.5, color: s[4] ? P.no_cubierta : P.final, xy: pr([s[1], s[0]])}));
  if (ini) ini.s.forEach((s, i) => puntos.push({s, i, r: 2.8, color: P.inicial, xy: pr([s[1], s[0]]), ini: true}));
  MAPA.sats.selectAll('circle').data(puntos).join('circle').attr('cx', d => d.xy[0]).attr('cy', d => d.xy[1]).attr('r', d => d.r)
    .attr('fill', d => d.color).attr('stroke', '#04121a').attr('stroke-width', 1).attr('vector-effect', 'non-scaling-stroke')
    .on('mousemove', (ev, d) => mostrarTip(ev, `<b>S${d.i}</b>${d.ini ? ' (inicial)' : ''}<br>${fx(d.s[0], 2)}°, ${fx(d.s[1], 2)}° · ${fx(d.s[2], 0)} km`))
    .on('mouseleave', ocultarTip);
  const textos = c.s.map((s, i) => ({texto: 'S' + i, xy: pr([s[1], s[0]]), dx: 6, dy: -5, color: s[4] ? P.no_cubierta : P.final, tam: 10}))
    .concat(sc.regiones.map((r, i) => ({texto: r.nombre, xy: pr([r.lon, r.lat]), dx: 0, dy: 16, color: colorRegion(c.r[i][3]), tam: 9.5, centro: true})))
    .concat(sc.zonas.filter(z => z.tipo === 'desechos' ? E.capas.desechos : E.capas.ocupadas)
      .map(z => ({texto: z.nombre, xy: pr([z.lon, z.lat]), dx: 0, dy: 3, color: z.tipo === 'desechos' ? P.desechos : P.ocupada, tam: 9, centro: true})));
  MAPA.etiq.selectAll('text').data(textos).join('text').attr('x', d => d.xy[0] + d.dx).attr('y', d => d.xy[1] + d.dy)
    .attr('text-anchor', d => d.centro ? 'middle' : 'start').attr('fill', d => d.color).attr('font-family', 'JetBrains Mono, monospace')
    .attr('paint-order', 'stroke').attr('stroke', '#070B1A').attr('pointer-events', 'none').text(d => d.texto);
  escalarTextos();
}

// ---------------------------------------------------------------- estrellas
// Campo de estrellas que titila y se desplaza con el giro del globo, como en Google Earth (solo en 3D).
const CIELO = {visible: true, quieto: window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches};
function iniciarEstrellas() {
  const cv = $('#estrellas'), ctx = cv.getContext('2d');
  const tintes = ['255,255,255', '255,255,255', '255,255,255', '200,220,255', '255,225,205', '225,205,255'];
  const crear = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2), w = cv.clientWidth, h = cv.clientHeight;
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    CIELO.w = w; CIELO.h = h;
    CIELO.estrellas = d3.range(Math.round(w * h / 260)).map(() => {
      const brillante = Math.random() < 0.06;
      return {x: Math.random(), y: Math.random(), r: brillante ? 0.9 + Math.random() * 0.9 : 0.25 + Math.random() * 0.65,
        a: brillante ? 0.8 + Math.random() * 0.2 : 0.25 + Math.random() * 0.6, f: 0.4 + Math.random() * 1.6,
        fase: Math.random() * 6.283, prof: 0.3 + Math.random() * 0.7, color: tintes[Math.floor(Math.random() * tintes.length)]};
    });
  };
  const dibujar = t => {
    const {w, h} = CIELO; ctx.clearRect(0, 0, w, h);
    const giro = E.modo3d && G ? G.pointOfView() : {lng: 0, lat: 0};
    const dx = -giro.lng / 360 * w * 0.6 + t * 0.004, dy = giro.lat / 180 * h * 0.3;
    for (const s of CIELO.estrellas) {
      const x = ((s.x * w + dx * s.prof) % w + w) % w, y = ((s.y * h + dy * s.prof) % h + h) % h;
      const a = CIELO.quieto ? s.a : s.a * (0.65 + 0.35 * Math.sin(t * 0.001 * s.f + s.fase));
      ctx.fillStyle = `rgba(${s.color},${a.toFixed(3)})`; ctx.beginPath(); ctx.arc(x, y, s.r, 0, 6.283); ctx.fill();
      if (s.r > 1.2) { ctx.fillStyle = `rgba(${s.color},${(a * 0.18).toFixed(3)})`; ctx.beginPath(); ctx.arc(x, y, s.r * 3, 0, 6.283); ctx.fill(); }
    }
  };
  const ciclo = t => { if (CIELO.visible && E.modo3d) dibujar(t); if (!CIELO.quieto) requestAnimationFrame(ciclo); };
  crear(); requestAnimationFrame(ciclo);
  new ResizeObserver(() => { crear(); dibujar(performance.now()); }).observe(cv);
}

// ---------------------------------------------------------------- render principal
function render() {
  const v = E.vista, sc = escDe(v), c = cuadroEn(v, E.gen);
  const ini = E.comparar && v.cuadros.length > 1 ? v.cuadros[0] : null;
  renderKPIs(c, sc); renderRegiones(c, sc); renderSatelites(c, ini);
  if (E.modo3d && G) renderGlobo(c, sc, ini); else renderMapa(c, sc, ini);
  $('#nota-vista').innerHTML = `<b>${esc(v.titulo)}</b>${esc(sc.nombre)}${v.semilla != null ? ' · semilla ' + v.semilla : ''}` +
    (v.nota ? '<br>' + md(v.nota) : '') + (c.x.length ? `<br><span class="mal">Violaciones: ${esc(c.x.join(' · '))}</span>` : '');
  const fija = v.gen_total == null;
  $('#gen').disabled = fija; $('#play').disabled = fija; $('#b-ini').disabled = fija; $('#comparar').disabled = fija || v.cuadros.length < 2;
  $('#gen-txt').innerHTML = fija ? 'CONFIGURACIÓN FIJA' : `GEN <span class="cian">${E.gen}</span> / ${v.gen_total} <span class="tenue">· cuadro ${v.cuadros.indexOf(c) + 1}/${v.cuadros.length}</span>`;
  $('#b-ini').classList.toggle('on', !fija && E.gen === 0); $('#b-fin').classList.toggle('on', fija || E.gen === v.gen_total);
  cursorMinis(); if (graficaEvolucion && v.id === 'base') graficaEvolucion.forEach(g => g.cursor(E.gen));
}
let pendiente = false;
const pedirRender = () => { if (!pendiente) { pendiente = true; requestAnimationFrame(() => { pendiente = false; render(); }); } };

function seleccionarVista(id, irAlMapa = true) {
  const v = VISTAS[id]; if (!v) return;
  detener(); E.vista = v; E.gen = v.gen_total == null ? 0 : v.gen_total;
  if (E.region != null && E.region >= escDe(v).regiones.length) E.region = null;
  $('#vista').value = id; const s = $('#gen'); s.max = v.gen_total || 0; s.value = E.gen;
  renderMinis(); render();
  if (irAlMapa) { const m = $('#mision'); m.animate([{boxShadow: '0 0 0 2px #22D3EE'}, {boxShadow: '0 0 0 0 transparent'}], 900);
    m.scrollIntoView({behavior: 'smooth', block: 'start'}); }
}
function enfocar(lat, lon) {
  if (E.modo3d && G) { G.controls().autoRotate = false; $('#c-giro').checked = false; E.capas.giro = false; G.pointOfView({lat, lng: lon, altitude: 1.5}, 900); }
  else if (MAPA.listo) { const [x, y] = MAPA.proy([lon, lat]), el = $('#centro');
    MAPA.svg.transition().duration(700).call(MAPA.zoom.transform, d3.zoomIdentity.translate(el.clientWidth / 2, el.clientHeight / 2).scale(3).translate(-x, -y)); }
}
function detener() { if (E.reproduciendo != null) { clearInterval(E.reproduciendo); E.reproduciendo = null; $('#play').textContent = '▶'; } }
function reproducir() {
  const v = E.vista; if (v.gen_total == null) return;
  if (E.reproduciendo != null) { detener(); render(); return; }
  if (E.gen >= v.gen_total) E.gen = 0;
  const paso = Math.max(1, Math.round(v.gen_total / 240));
  $('#play').textContent = '⏸';
  E.reproduciendo = setInterval(() => { E.gen = Math.min(v.gen_total, E.gen + paso); $('#gen').value = E.gen; pedirRender();
    if (E.gen >= v.gen_total) { detener(); pedirRender(); } }, 45);
}
function fijarModo(tres) {
  E.modo3d = tres && !!G;
  const b = $('#modo3d'); b.setAttribute('aria-checked', String(E.modo3d));
  b.setAttribute('aria-label', E.modo3d ? 'Vista 3D activada; pulsa para cambiar a 2D' : 'Vista 2D activada; pulsa para cambiar a 3D');
  $('#et3d').classList.toggle('on', E.modo3d); $('#et2d').classList.toggle('on', !E.modo3d);
  $('#globo').style.display = E.modo3d ? 'block' : 'none'; $('#mapa').style.display = E.modo3d ? 'none' : 'block';
  $('#estrellas').style.display = E.modo3d ? 'block' : 'none';
  if (G) { if (E.modo3d) G.resumeAnimation(); else G.pauseAnimation(); }
  if (!E.modo3d && !MAPA.listo) iniciarMapa();
  render();
}

// ---------------------------------------------------------------- pestañas
const bloque = t => `<div class="prueba"><span class="etq">CONDICIONES</span>${md(t.condiciones)}
  <span class="etq">RESULTADO</span>${md(t.resultado)}
  <span class="etq">INTERPRETACIÓN</span><ul>${t.interpretacion.map(x => `<li>${md(x)}</li>`).join('')}</ul></div>`;
const botonVer = (id, txt = 'Ver en el mapa') => VISTAS[id] ? `<button class="ver" data-vista="${esc(id)}">${esc(txt)}</button>` : '';
let graficaEvolucion = null;

const PESTANAS = [
  ['evolucion', 'Evolución', pEvolucion], ['ejecuciones', 'Ejecuciones', pEjecuciones], ['restricciones', 'Restricciones', pRestricciones],
  ['limite', 'Escenarios límite', pLimite], ['propia', 'Prueba propia', pPropia], ['calibracion', 'Calibración', pCalibracion],
  ['modelo', 'Modelo y verificación', pModelo]];

function pEvolucion(el) {
  const ev = D.evolucion, n = ev.fitness_media.length - 1, sup = ev.fitness_media.map((m, i) => m == null ? null : Math.min(1, m + ev.fitness_desv[i])),
    inf = ev.fitness_media.map((m, i) => m == null ? null : Math.max(0, m - ev.fitness_desv[i]));
  el.innerHTML = `<div class="rejilla" style="grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)">
    <div class="caja"><h3>E2 · CALIDAD POR GENERACIÓN ${botonVer('base', 'Reproducir en el mapa')}</h3><div id="g-ev1"></div></div>
    <div class="caja"><h3>FACTIBILIDAD, DIVERSIDAD Y MUTACIÓN</h3><div id="g-ev2"></div><div id="g-ev3"></div></div></div>
    <div class="caja" style="margin-top:10px">${bloque(ev.texto)}</div>`;
  const v = [];
  if (ev.gen_cobertura_completa != null) v.push({x: ev.gen_cobertura_completa, color: P.cubierta, txt: 'todas cubiertas'});
  if (ev.gen_convergencia != null) v.push({x: ev.gen_convergencia, color: P.media, txt: '99%'});
  graficaEvolucion = [
    grafica($('#g-ev1'), {alto: 205, x: [0, n], y: [0, 1], ejeX: 'generación', nombreX: 'generación', v,
      bandas: [{y0: inf, y1: sup, color: rgba(P.media, .14)}],
      series: [{y: ev.fitness_peor, color: P.tenue, ancho: .8, guion: '2 3', nombre: 'peor'},
        {y: ev.fitness_media, color: P.media, ancho: 1.3, nombre: 'media (± desv.)'},
        {y: ev.fitness_mejor, color: P.final, ancho: 2.2, nombre: 'mejor válida de la generación'}],
      h: [{y: ev.cota, color: P.cubierta, txt: `cota ${f4(ev.cota)}`, nombre: 'cota de referencia'}]}),
    grafica($('#g-ev2'), {alto: 110, x: [0, n], y: [0, Math.max(5, d3.max(ev.div))], nombreX: 'generación',
      series: [{y: ev.div, color: P.ocupada, nombre: 'diversidad (°)'}, {y: ev.fact.map(x => x * Math.max(5, d3.max(ev.div))), color: P.cubierta, nombre: 'fracción válida (escalada)'}]}),
    grafica($('#g-ev3'), {alto: 92, x: [0, n], y: [0, d3.max(ev.sigma)], ejeX: 'generación', nombreX: 'generación', ticksY: 3,
      series: [{y: ev.sigma, color: P.inicial, nombre: 'σ de mutación (°)'}]})];
  if (E.vista.id === 'base') graficaEvolucion.forEach(g => g.cursor(E.gen));
}

function pEjecuciones(el) {
  const ej = D.ejecuciones, r = ej.resumen;
  el.innerHTML = `<div class="rejilla r3">
    <div class="caja"><h3>E7 · CONVERGENCIA DE ${r.n_ejecuciones} SEMILLAS</h3><div id="g-e7a"></div></div>
    <div class="caja"><h3>MISMO PRESUPUESTO: AG CONTRA ALEATORIA</h3><div id="g-e7b"></div></div>
    <div class="caja"><h3>DISTANCIA ENTRE SOLUCIONES (°)</h3><div id="g-e7c"></div></div></div>
    <div class="rejilla r2" style="margin-top:10px"><div class="caja" style="overflow:auto"><h3>TABLA POR SEMILLA</h3><table id="t-e7"></table></div>
    <div class="caja">${bloque(ej.texto)}</div></div>`;
  const curvas = ej.filas.map(f => VISTAS[f.vista].hist.mejor), n = curvas[0].length - 1;
  const media = curvas[0].map((_, i) => d3.mean(curvas, c => c[i]));
  grafica($('#g-e7a'), {alto: 170, x: [0, n], y: [0, 1], ejeX: 'generación', nombreX: 'generación', leyenda: false,
    series: curvas.map((c, k) => ({y: c, color: d3.schemeTableau10[k % 10], ancho: 1, opacidad: .55})).concat([{y: media, color: '#fff', ancho: 2.2, nombre: 'media'}]),
    h: [{y: r.cota, color: P.cubierta, txt: 'cota'}]});
  const c2 = $('#g-e7b'); c2.innerHTML = '';
  const W = Math.max(c2.clientWidth, 200), H = 170, m = {t: 8, r: 70, b: 22, l: 42};
  const todos = ej.filas.map(f => f.fitness).concat(ej.aleatoria);
  const sy = d3.scaleLinear([Math.max(0, d3.min(todos) - .05), Math.min(1, Math.max(r.cota, d3.max(todos)) + .02)], [H - m.b, m.t]);
  const sx = d3.scaleBand(['AG', 'Aleatoria'], [m.l, W - m.r]).padding(.4);
  const svg = d3.select(c2).append('svg').attr('class', 'graf').attr('width', W).attr('height', H);
  svg.append('g').attr('class', 'rej').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(sy).ticks(5).tickSize(-(W - m.l - m.r)).tickFormat(''));
  svg.append('g').attr('class', 'eje').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(sy).ticks(5));
  svg.append('g').attr('class', 'eje').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(sx).tickSizeOuter(0));
  [[r.cota, P.cubierta, `cota ${f4(r.cota)}`, -4], [r.voraz, P.media, `voraz ${f4(r.voraz)}`, 11]].forEach(([y, col, t, dy]) => {
    svg.append('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', sy(y)).attr('y2', sy(y)).attr('stroke', col).attr('stroke-dasharray', '5 4');
    svg.append('text').attr('x', W - m.r + 4).attr('y', sy(y) + dy).attr('fill', col).attr('font-size', 9.5).text(t); });
  const pts = ej.filas.map((f, i) => ({g: 'AG', y: f.fitness, t: `semilla ${f.semilla}: ${f4(f.fitness)}`, vista: f.vista, j: i}))
    .concat(ej.aleatoria.map((y, i) => ({g: 'Aleatoria', y, t: `aleatoria ${i}: ${f4(y)}`, j: i})));
  svg.selectAll('circle').data(pts).join('circle').attr('cx', d => sx(d.g) + sx.bandwidth() * (.2 + .6 * ((d.j * 37) % 10) / 10))
    .attr('cy', d => sy(d.y)).attr('r', 4).attr('fill', d => d.g === 'AG' ? P.final : P.inicial).attr('opacity', .85)
    .style('cursor', d => d.vista ? 'pointer' : null)
    .on('mousemove', (ev, d) => mostrarTip(ev, esc(d.t) + (d.vista ? '<br><span class="tenue">clic: ver en el mapa</span>' : '')))
    .on('mouseleave', ocultarTip).on('click', (ev, d) => d.vista && seleccionarVista(d.vista));
  [['AG', d3.mean(ej.filas, f => f.fitness)], ['Aleatoria', d3.mean(ej.aleatoria)]].forEach(([g, y]) =>
    svg.append('line').attr('x1', sx(g)).attr('x2', sx(g) + sx.bandwidth()).attr('y1', sy(y)).attr('y2', sy(y)).attr('stroke', '#fff').attr('stroke-width', 2));
  const n2 = ej.distancias.length, maxd = d3.max(ej.distancias.flat()) || 1, col = d3.scaleSequential([0, maxd], d3.interpolateViridis);
  $('#g-e7c').innerHTML = `<table style="table-layout:fixed">${'<tr><th></th>' + ej.filas.map(f => `<th>s${f.semilla}</th>`).join('') + '</tr>'}${ej.distancias.map((fila, i) =>
    `<tr><th>s${ej.filas[i].semilla}</th>${fila.map((d, j) => `<td title="s${ej.filas[i].semilla} ↔ s${ej.filas[j].semilla}: ${fx(d, 1)}°" style="background:${i === j ? 'transparent' : col(d)};color:${d > maxd * .6 ? '#04121a' : '#E6ECFF'};text-align:center;font-size:9px;padding:2px">${i === j ? '' : fx(d, 0)}</td>`).join('')}</tr>`).join('')}</table>
    <div class="leyenda-g">Distancia media entre satélites emparejados de dos soluciones (${n2}×${n2}).</div>`;
  $('#t-e7').innerHTML = '<tr><th>SEMILLA</th><th>FITNESS</th><th>INICIAL</th><th>REG.</th><th>ACEPTADA</th><th>GEN 6/6</th><th>GEN 99%</th><th></th></tr>' +
    ej.filas.map(f => `<tr><td>${f.semilla}</td><td>${f4(f.fitness)}</td><td>${f4(f.fitness_inicial)}</td><td>${f.regiones_cubiertas}</td>
    <td>${f.aceptada ? marca(true) : marca(false) + ' ' + f.fallidos.join(', ')}</td><td>${f.gen_cobertura_completa ?? '—'}</td><td>${f.gen_convergencia ?? '—'}</td>
    <td>${botonVer(f.vista, 'Ver')}</td></tr>`).join('');
}

function pRestricciones(el) {
  const R = D.restricciones, T = R.texto;
  el.innerHTML = `<div class="rejilla" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr)">
    <div class="caja"><h3>E3/E4 · MARGEN MÍNIMO POR ZONA EN TODAS LAS SEMILLAS</h3><div id="g-zonas"></div>
      <div class="chips" style="margin-top:6px"><div class="chip"><small>VÁLIDAS AL INICIO</small><b class="grande">${pct(R.fact_inicial)}</b></div>
      <div class="chip"><small>VÁLIDAS AL FINAL</small><b class="grande ok">${pct(R.fact_final)}</b></div>
      <div class="chip"><small>OBJETO JUNTO AL SAHEL</small><b class="grande">${f4(R.junto.fitness)}</b> <span class="tenue">vs ${f4(R.junto.fitness_base)}</span> ${botonVer('e4')}</div></div></div>
    <div class="caja">${bloque(T.auditoria)}</div>
    <div class="caja"><h3>E5 · ESPACIO REDUCIDO: FITNESS Y COBERTURA POR NIVEL</h3><div id="g-e5"></div><table id="t-e5" style="margin-top:6px"></table>
      <h3>R1 SIN MANEJO DE RESTRICCIONES ${botonVer('e5-R1-sin')}</h3>
      <div>Fitness aparente <b>${f4(R.sin_manejo.fitness)}</b> · intrusión <b class="mal">${fx(R.sin_manejo.violacion, 2)}°</b><br>
      <span class="mal">${R.sin_manejo.violaciones.map(esc).join('<br>') || 'sin violaciones'}</span></div></div>
    <div class="caja">${bloque(T.e5)}</div></div>`;
  barrasH($('#g-zonas'), R.zonas.map(z => ({nombre: `${z.zona} (${z.radio}°)`, valor: z.margen_min, color: z.todas ? (z.tipo === 'desechos' ? P.desechos : P.ocupada) : P.no_cubierta,
    tip: `<b>${esc(z.zona)}</b><br>distancia mínima ${fx(z.distancia_min, 2)}° · margen ${fx(z.margen_min, 2)}°<br>${z.todas ? 'todas las semillas la respetan' : '¡alguna semilla la invade!'}`})),
    {x: [Math.min(0, d3.min(R.zonas, z => z.margen_min)), d3.max(R.zonas, z => z.margen_min) * 1.05], fv: v => fx(v, 1) + '°', margenIzq: 160,
     v: [{x: 0, color: P.no_cubierta}]});
  barrasH($('#g-e5'), R.niveles.map(n => ({nombre: n.nombre, valor: n.fitness, color: n.factible ? P.final : P.no_cubierta,
    tip: `<b>${esc(n.nombre)}</b><br>fitness ${f4(n.fitness)} · cota ${f4(n.cota)}<br>altitudes: ${n.altitudes.join(', ')} km`})),
    {x: [Math.max(0, d3.min(R.niveles, n => n.fitness) - .1), 1], fv: f4, margenIzq: 190});
  const regiones = D.escenarios[VISTAS[R.niveles[0].vista].escenario].regiones;
  const col = d3.scaleLinear([0, .95, 1], [P.no_cubierta, P.media, P.cubierta]);
  $('#t-e5').innerHTML = `<tr><th>NIVEL</th>${regiones.map(r => `<th title="${esc(r.nombre)}">${esc(r.nombre.split(' ').slice(-1)[0].slice(0, 9))}</th>`).join('')}<th></th></tr>` +
    R.niveles.map(n => `<tr><td>${esc(n.nombre.split(' ')[0])}</td>${n.cobertura.map(c => `<td style="color:${col(c)}">${pct(c)}</td>`).join('')}<td>${botonVer(n.vista, 'Ver')}</td></tr>`).join('');
}

function pLimite(el) {
  const L = D.limite, e9 = L.e9;
  const fila = (t, a, b) => `<tr><td>${t}</td><td>${a}</td><td>${b}</td></tr>`;
  el.innerHTML = `<div class="rejilla r3">${L.casos.map(c => `<div class="caja"><h3>E6 · ${esc(c.clave.toUpperCase())} ${botonVer(c.vista)}</h3>
      <div class="prueba">${md(c.dificultad)}</div>
      <div class="chips" style="margin:6px 0"><div class="chip"><small>FITNESS</small><b>${f4(c.fitness)}</b></div>
      <div class="chip"><small>VÁLIDA</small><b>${sino(c.factible)}</b></div><div class="chip"><small>REGIONES</small><b>${c.cubiertas}/${c.regiones}</b></div>
      <div class="chip"><small>VIOLACIONES</small><b>${c.n_violaciones}</b></div></div>
      <div class="prueba">${md(c.texto)}</div></div>`).join('')}</div>
    <div class="rejilla" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1.2fr);margin-top:10px">
      <div class="caja"><h3>E9 · ¿SIGUE SIENDO VÁLIDA LA SOLUCIÓN ANTERIOR?</h3><table>
        <tr><th></th><th>(a) PRIORIDAD</th><th>(b) ZONA NUEVA</th></tr>
        ${fila('Válida antes', sino(e9.a.valida_antes), sino(e9.b.valida_antes))}${fila('Válida ahora', sino(e9.a.valida_ahora), sino(e9.b.valida_ahora))}
        ${fila('Fitness antes', f4(e9.a.fitness_antes), f4(e9.b.fitness_antes))}${fila('Fitness ahora', f4(e9.a.fitness_ahora), f4(e9.b.fitness_ahora))}
        ${fila('Aceptada ahora', sino(e9.a.aceptada_ahora), sino(e9.b.aceptada_ahora))}
        ${fila('Reoptimizada', f4(e9.a.reoptimizado), `${f4(e9.b.previa)} / ${f4(e9.b.cero)}`)}
        ${fila('', botonVer('e9-a-anterior', 'Anterior') + ' ' + botonVer('e9-a-reopt', 'Nueva'), botonVer('e9-b-anterior', 'Anterior') + ' ' + botonVer('e9-b-previa', 'Previa') + ' ' + botonVer('e9-b-cero', 'Cero'))}</table>
        <div class="mal" style="margin-top:6px">${e9.b.violaciones.map(esc).join('<br>')}</div></div>
      <div class="caja"><h3>E9b · REOPTIMIZACIÓN TRAS LA ZONA NUEVA</h3><div id="g-e9"></div></div>
      <div class="caja">${bloque(e9.texto)}</div></div>`;
  const hp = VISTAS['e9-b-previa'].hist.mejor, hc = VISTAS['e9-b-cero'].hist.mejor;
  grafica($('#g-e9'), {alto: 170, x: [0, Math.max(hp.length, hc.length) - 1], y: [0, 1], ejeX: 'generación', nombreX: 'generación',
    series: [{y: hc, color: P.inicial, nombre: 'desde cero'}, {y: hp, color: P.final, ancho: 2, nombre: 'desde la población previa'}]});
}

function pPropia(el) {
  const Pr = D.propia;
  el.innerHTML = `<div class="rejilla" style="grid-template-columns:minmax(0,1.3fr) minmax(0,1fr)">
    <div class="caja"><h3>E8 · FITNESS SI FALLA CADA SATÉLITE (N-1) ${botonVer('base', 'Con redundancia')} ${botonVer('e8-sin', 'Sin redundancia')}</h3><div id="g-e8"></div>
      <table style="margin-top:6px"><tr><th>FALLA</th><th>CON: REGIONES PERDIDAS</th><th>SIN: REGIONES PERDIDAS</th></tr>
      ${Pr.con.map((f, i) => `<tr><td>S${f.satelite_fallado}</td><td class="${f.regiones_perdidas === 'ninguna' ? 'ok' : 'mal'}" style="text-align:left">${esc(f.regiones_perdidas)}</td>
        <td class="${Pr.sin[i].regiones_perdidas === 'ninguna' ? 'ok' : 'mal'}" style="text-align:left">${esc(Pr.sin[i].regiones_perdidas)}</td></tr>`).join('')}</table></div>
    <div class="caja">${bloque(Pr.texto)}</div></div>`;
  barrasAgrupadas($('#g-e8'), Pr.con.map(f => 'S' + f.satelite_fallado), [
    {nombre: 'con término de redundancia', color: P.final, valores: Pr.con.map(f => f.fitness), tips: Pr.con.map(f => 'perdidas: ' + f.regiones_perdidas)},
    {nombre: 'sin término de redundancia', color: P.inicial, valores: Pr.sin.map(f => f.fitness), tips: Pr.sin.map(f => 'perdidas: ' + f.regiones_perdidas)}],
    {y: [Math.max(0, d3.min(Pr.con.concat(Pr.sin), f => f.fitness) - .1), 1], alto: 165, ejeX: 'satélite que falla'});
}

function pCalibracion(el) {
  const C = D.calibracion;
  el.innerHTML = `<div class="rejilla" style="grid-template-columns:minmax(0,1.3fr) minmax(0,1fr)">
    <div class="caja"><h3>E10 · ABLACIÓN DE OPERADORES (${C.n_semillas} SEMILLAS, ESCENARIO R1)</h3><div id="g-e10"></div>
      <table style="margin-top:6px"><tr><th>VARIANTE</th><th>FITNESS</th><th>DESV.</th><th>VÁLIDAS</th><th>GEN 99%</th></tr>
      ${C.filas.map(f => `<tr><td>${esc(f.variante)}</td><td>${f4(f.fitness_media)}</td><td>${f4(f.fitness_desv)}</td><td>${f.validas}/${C.n_semillas}</td><td>${fx(f.gen_convergencia_media, 0)}</td></tr>`).join('')}</table></div>
    <div class="caja">${bloque(C.texto)}</div></div>`;
  const ref = C.filas[0].fitness_media;
  barrasH($('#g-e10'), C.filas.map((f, i) => ({nombre: f.variante, valor: f.fitness_media, error: f.fitness_desv || 0,
    color: i === 0 ? P.cubierta : (f.fitness_media < ref ? P.final : P.media)})),
    {x: [Math.max(0, d3.min(C.filas, f => f.fitness_media - (f.fitness_desv || 0)) - .01), Math.min(1, d3.max(C.filas, f => f.fitness_media + (f.fitness_desv || 0)) + .005)],
     fv: f4, margenIzq: 170, v: [{x: ref, color: P.cubierta, txt: 'final'}]});
}

function verificarEnNavegador() {
  // Recalcula la cobertura del cuadro final con los datos dibujados, de forma independiente a Python.
  const v = VISTAS.base, c = v.cuadros[v.cuadros.length - 1], sc = escDe(v), rad_r = 180 / Math.PI / RT;
  const res = sc.regiones.map((r, i) => {
    const pts = muestrasDisco(r.lat, r.lon, r.radio_km * rad_r, sc.anillos);
    const vistos = pts.filter(p => c.s.some(s => distAng(p[0], p[1], s[0], s[1]) <= s[3] + 1e-9)).length;
    return {js: vistos / pts.length, py: c.r[i][0]};
  });
  const crJs = criterios(c, sc).map(x => x[2]), crPy = Object.entries(D.modelo.aceptacion).filter(([k]) => k !== 'ACEPTADA').map(([, v]) => v);
  return {res, maxDif: d3.max(res, x => Math.abs(x.js - x.py)), criteriosIguales: crJs.every((x, i) => x === crPy[i])};
}

function pModelo(el) {
  const M = D.modelo, V = D.verificacion, U = D.pruebas_unitarias, js = verificarEnNavegador(), pa = M.parametros_ag;
  const w = M.pesos_fitness;
  el.innerHTML = `<div class="rejilla r3">
    <div class="caja prueba"><h3>FUNCIÓN DE EVALUACIÓN</h3>
      Por región: <code>puntaje = ${w[0]}·cobertura + ${w[1]}·redundancia + ${w[2]}·resolución</code><br>
      Total: <code>fitness = Σ peso·puntaje / Σ pesos</code> ∈ [0, 1]<br>
      Pesos por prioridad: ${Object.entries(M.pesos_prioridad).map(([k, v]) => `<b>${k}</b> = ${v}`).join(' · ')}<br>
      Cota de referencia (relajación sin zonas): <b>${f4(M.cota.fitness)}</b>
      <h3>SUPUESTOS DEL MODELO</h3><ul>${M.supuestos.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>
    <div class="caja"><h3>HUELLA DEL SENSOR CONTRA ALTITUD</h3><table><tr><th>ALTITUD km</th><th>RADIO HUELLA km</th><th>CALIDAD RESOL.</th></tr>
      ${M.huella.map(h => `<tr><td>${fx(h.alt_km, 0)}</td><td>${fx(h.radio_km, 0)}</td><td>${fx(h.calidad, 3)}</td></tr>`).join('')}</table>
      <h3>PARÁMETROS DEL AG</h3><table>${[['Población', pa.tam_poblacion], ['Generaciones', pa.generaciones], ['Torneo / élite', `${pa.tam_torneo} / ${pa.tam_elite}`],
        ['Prob. cruce / mezcla', `${pa.prob_cruce} / ${pa.prob_mezcla}`], ['Cruce alineado', pa.cruce_alineado ? 'sí' : 'no'], ['Prob. mutación', pa.prob_mutacion],
        ['σ posición', `${pa.sigma_inicial_grados}° → ${pa.sigma_final_grados}°`], ['σ altitud', `${pa.sigma_alt_inicial_km} → ${pa.sigma_alt_final_km} km`],
        ['Reubicación / reparación', `${pa.prob_reubicacion} / ${pa.prob_reparacion}`], ['Restricciones', pa.manejo_restricciones]]
        .map(([k, v]) => `<tr><td>${k}</td><td>${esc(v)}</td></tr>`).join('')}</table></div>
    <div class="caja"><h3>CRITERIOS DE ACEPTACIÓN (SOLUCIÓN PRINCIPAL)</h3><table>
      ${Object.entries(M.aceptacion).map(([k, v]) => `<tr><td style="white-space:normal">${esc(k)}</td><td>${marca(v)}</td></tr>`).join('')}</table>
      <h3>VERIFICACIÓN DE CORRESPONDENCIA</h3><table>
      <tr><td style="white-space:normal">Configuración dibujada = resultado del AG (dif. máx. ${V.max_dif_configuracion.toExponential(1)})</td><td>${marca(V.max_dif_configuracion < 1e-3)}</td></tr>
      <tr><td style="white-space:normal">Fitness y regiones cubiertas iguales a Python</td><td>${marca(V.fitness_igual && V.cobertura_igual)}</td></tr>
      <tr><td style="white-space:normal">Cobertura recalculada en el navegador (dif. máx. ${fx(js.maxDif, 4)})</td><td>${marca(js.maxDif < 1e-9)}</td></tr>
      <tr><td style="white-space:normal">Criterios C1–C4 del navegador = Python</td><td>${marca(js.criteriosIguales)}</td></tr>
      <tr><td style="white-space:normal">Pruebas unitarias (pytest)</td><td>${U ? `${marca(U.fallidas === 0 && U.aprobadas > 0)} ${U.aprobadas} aprobadas${U.fallidas ? `, <span class="mal">${U.fallidas} fallidas</span>` : ''}` : '<span class="tenue">no se ejecutaron</span>'}</td></tr></table>
      <div class="leyenda-g">El navegador vuelve a muestrear los 49 puntos de cada región y comprueba qué huellas los cubren, sin usar los valores de Python.</div>
      <div class="leyenda-g">Datos: modo <b>${esc(D.modo)}</b> · generado ${esc(D.generado)} · AstroShield ${esc(D.version)}${D.tiempo_s != null ? ` · ${D.tiempo_s} s de cómputo` : ''}</div></div></div>`;
}

function abrirPestana(id) {
  document.querySelectorAll('#pestanas button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.id === id)));
  const p = PESTANAS.find(x => x[0] === id), el = $('#detalle');
  graficaEvolucion = null;
  try { p[2](el); } catch (e) { el.innerHTML = `<span class="mal">No se pudo dibujar esta pestaña: ${esc(e.message)}</span>`; console.error(e); }
  el.querySelectorAll('.ver').forEach(b => b.onclick = () => seleccionarVista(b.dataset.vista));
  el.scrollTop = 0;
}

// ---------------------------------------------------------------- arranque
function iniciar() {
  if (typeof d3 === 'undefined') {
    document.getElementById('app').innerHTML = '<div class="panel" style="padding:20px;margin:20px">No se pudo cargar la librería de gráficas (d3). ' +
      'Revisa tu conexión a internet y vuelve a ejecutar la celda.</div>'; return;
  }
  llenarSelector();
  $('#pestanas').innerHTML = PESTANAS.map(([id, t]) => `<button role="tab" data-id="${id}" aria-selected="false">${t}</button>`).join('');
  document.querySelectorAll('#pestanas button').forEach(b => b.onclick = () => abrirPestana(b.dataset.id));
  G = iniciarGlobo();
  if (!G) {
    const b = $('#modo3d'); b.disabled = true; b.title = 'Vista 3D no disponible';
    const aviso = $('#aviso'); aviso.style.display = 'block';
    aviso.textContent = typeof Globe === 'undefined' ? 'No se pudo cargar el globo 3D (globe.gl): se muestra el mapa 2D.'
      : 'Tu navegador no tiene WebGL: se muestra el mapa 2D.';
  }
  $('#modo3d').onclick = () => fijarModo(!E.modo3d);
  $('#gen').oninput = e => { detener(); E.gen = +e.target.value; pedirRender(); };
  $('#play').onclick = reproducir;
  $('#b-ini').onclick = () => { detener(); E.gen = 0; $('#gen').value = 0; render(); };
  $('#b-fin').onclick = () => { detener(); E.gen = E.vista.gen_total || 0; $('#gen').value = E.gen; render(); };
  $('#comparar').onchange = e => { E.comparar = e.target.checked; render(); };
  [['huellas', 'c-huellas'], ['desechos', 'c-desechos'], ['ocupadas', 'c-ocupadas'], ['giro', 'c-giro']].forEach(([k, id]) =>
    $('#' + id).onchange = e => { E.capas[k] = e.target.checked; render(); });
  $('#descargar').onclick = () => {
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([FUENTE], {type: 'text/html'}));
    a.download = 'astroshield_centro_control.html'; document.body.appendChild(a); a.click(); a.remove();
  };
  new ResizeObserver(() => { const el = $('#centro'); if (G) G.width(el.clientWidth).height(el.clientHeight); if (MAPA.listo) { ajustarMapa(); render(); } }).observe($('#centro'));
  // El globo deja de dibujar cuando el panel no está a la vista (Colab tiene muchas salidas en la misma pestaña).
  if ('IntersectionObserver' in window) new IntersectionObserver(es => es.forEach(e => {
    CIELO.visible = e.isIntersecting;
    if (!G || !E.modo3d) return; if (e.isIntersecting) G.resumeAnimation(); else G.pauseAnimation(); })).observe($('#centro'));
  iniciarEstrellas();
  fijarModo(!!G);
  seleccionarVista(E.vista.id, false);
  abrirPestana('evolucion');
  if (FALLAS.length && FALLAS.some(f => f !== 'globe.gl')) console.warn('Librerías que no cargaron:', FALLAS);
}
iniciar();
</script>
</body>
</html>
"""
