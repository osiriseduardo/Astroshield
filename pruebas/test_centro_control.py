"""El centro de control debe mostrar exactamente lo que produjo el AG."""
import json
import re

import numpy as np
import pytest

from astroshield import centro_control as C
from astroshield import experimentos as X
from astroshield.algoritmo_genetico import ParametrosAG, ejecutar_ag
from astroshield.escenario import escenario_base

RAPIDO = ParametrosAG(tam_poblacion=24, generaciones=12)


@pytest.fixture(scope="module")
def todo():
    return X.ejecutar_todo(RAPIDO, n_semillas=2, n_ablacion=1)


@pytest.fixture(scope="module")
def datos(todo):
    return C.datos_centro_control(todo, {"aprobadas": 1, "fallidas": 0, "resumen": "1 passed", "codigo_salida": 0})


def _datos_incrustados(html):
    return json.loads(re.search(r'<script id="datos" type="application/json">(.*?)</script>', html, re.S).group(1))


def test_instantaneas_en_la_generacion_0_y_en_cada_mejora():
    r = ejecutar_ag(escenario_base(), RAPIDO, semilla=3)
    curva = [h["mejor_rango_historico"] for h in r.historial]
    mejoras = {g for g in range(1, len(curva)) if curva[g] > curva[g - 1]}
    assert set(r.instantaneas) == {0, len(curva) - 1} | mejoras
    assert np.array_equal(r.instantaneas[len(curva) - 1], r.mejor)


def test_el_panel_dibuja_la_configuracion_real_del_ag(todo, datos):
    base = todo["base"]
    final = next(v for v in datos["vistas"] if v["id"] == "base")["cuadros"][-1]
    dibujada = np.array([s[:3] for s in final["s"]])
    assert np.abs(dibujada - base.mejor).max() < 1e-3
    assert final["f"] == round(base.eval_mejor.fitness, 4)
    assert [r[3] for r in final["r"]] == [int(x.cubierta) for x in base.eval_mejor.regiones]
    assert datos["verificacion"]["fitness_igual"] and datos["verificacion"]["cobertura_igual"]


def test_la_vista_principal_tiene_un_cuadro_por_mejora(todo, datos):
    base = todo["base"]
    vista = next(v for v in datos["vistas"] if v["id"] == "base")
    assert [c["g"] for c in vista["cuadros"]] == sorted(base.instantaneas)
    assert len(vista["hist"]["mejor"]) == len(base.historial)


def test_cada_prueba_tiene_condiciones_resultado_e_interpretacion(datos):
    textos = [datos["evolucion"]["texto"], datos["ejecuciones"]["texto"], datos["restricciones"]["texto"]["auditoria"],
              datos["restricciones"]["texto"]["e5"], datos["limite"]["e9"]["texto"], datos["propia"]["texto"],
              datos["calibracion"]["texto"]]
    for t in textos:
        assert t["condiciones"] and t["resultado"] and t["interpretacion"]
    assert all(c["texto"] for c in datos["limite"]["casos"])


def test_html_autocontenido_en_espanol_con_interruptor_en_3d(datos):
    html = C.html_centro_control(datos)
    assert '<html lang="es">' in html and "CENTRO DE CONTROL" in html
    assert 'role="switch" aria-checked="true"' in html  # 3D por defecto
    assert "d3/7.8.5/d3.min.js" in html and "globe.gl@2.33.1" in html
    assert html.count("</script>") == html.count("<script")  # los datos no cierran la etiqueta antes de tiempo
    incrustados = _datos_incrustados(html)
    assert incrustados["vistas"][0]["cuadros"][-1] == datos["vistas"][0]["cuadros"][-1]


def test_vistas_cubren_todas_las_pruebas(datos):
    ids = {v["id"] for v in datos["vistas"]}
    assert {"base", "e1", "e4", "e5-R1-sin", "e6-I1", "e6-I2", "e6-I3", "e9-b-anterior", "e8-sin"} <= ids
    assert all(v["escenario"] in datos["escenarios"] for v in datos["vistas"])


def test_solucion_anterior_bajo_zona_nueva_se_marca_como_invalida(datos):
    anterior = next(v for v in datos["vistas"] if v["id"] == "e9-b-anterior")["cuadros"][0]
    assert anterior["ok"] == 0 and any(s[4] for s in anterior["s"]) and anterior["x"]


def test_laboratorio_reemplaza_sus_vistas_sin_duplicarlas(todo, datos):
    base = todo["base"]
    lab = escenario_base().con_prioridad("Interior de Australia", "alta", nombre="Laboratorio")
    r = ejecutar_ag(lab, RAPIDO, semilla=1)
    una = C.agregar_laboratorio(datos, r, base.mejor, base.escenario)
    dos = C.agregar_laboratorio(una, r, base.mejor, base.escenario)
    ids = [v["id"] for v in dos["vistas"]]
    assert ids.count("lab") == 1 and ids.count("lab-anterior") == 1 and dos["vista_inicial"] == "lab"
    assert len(dos["vistas"]) == len(datos["vistas"]) + 2
