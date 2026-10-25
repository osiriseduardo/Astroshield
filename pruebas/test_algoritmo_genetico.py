import numpy as np
import pytest

from astroshield.algoritmo_genetico import (
    ParametrosAG,
    alinear,
    ejecutar_ag,
    poblacion_aleatoria,
    reflejar_altitud,
    reparar,
)
from astroshield.escenario import Zona, escenario_base
from astroshield.evaluacion import Evaluador, cota_referencia
from astroshield.geometria import distancia_angular
from astroshield.referencias import busqueda_aleatoria, colocacion_voraz

RAPIDO = ParametrosAG(tam_poblacion=40, generaciones=60)


@pytest.fixture(scope="module")
def ejecucion_base():
    return ejecutar_ag(escenario_base(), RAPIDO, semilla=1)


def test_ag_mejora_sobre_la_poblacion_inicial(ejecucion_base):
    assert ejecucion_base.eval_mejor.fitness > ejecucion_base.eval_inicial.fitness + 0.2
    assert len(ejecucion_base.historial) == RAPIDO.generaciones + 1


def test_mejor_historico_nunca_disminuye(ejecucion_base):
    curva = [h["mejor_rango_historico"] for h in ejecucion_base.historial]
    assert all(b >= a - 1e-12 for a, b in zip(curva, curva[1:]))


def test_solucion_final_respeta_todas_las_zonas(ejecucion_base):
    sc = ejecucion_base.escenario
    mejor = ejecucion_base.mejor
    assert ejecucion_base.eval_mejor.factible
    for z in sc.zonas:
        assert distancia_angular(mejor[:, 0], mejor[:, 1], z.lat, z.lon).min() >= z.radio_grados


def test_altitudes_dentro_de_limites(ejecucion_base):
    sc = ejecucion_base.escenario
    pob = ejecucion_base.poblacion_final
    assert pob[..., 2].min() >= sc.alt_min_km and pob[..., 2].max() <= sc.alt_max_km


def test_misma_semilla_es_reproducible():
    sc = escenario_base()
    a = ejecutar_ag(sc, ParametrosAG(tam_poblacion=20, generaciones=10), semilla=7)
    b = ejecutar_ag(sc, ParametrosAG(tam_poblacion=20, generaciones=10), semilla=7)
    assert np.array_equal(a.mejor, b.mejor)


def test_restricciones_imposibles_se_reportan_no_se_ocultan():
    # 8 puntos en una esfera no pueden estar todos a 80° (cota de Tammes ~74.9°).
    sc = escenario_base().con_parametros(separacion_min_grados=80.0)
    r = ejecutar_ag(sc, ParametrosAG(tam_poblacion=30, generaciones=20), semilla=0)
    assert not r.encontro_factible
    assert r.eval_mejor.violacion > 0 and r.eval_mejor.violaciones
    assert np.isnan(r.historial[-1]["fitness_mejor"])


def test_region_inalcanzable_queda_sin_cubrir_pero_la_solucion_es_valida():
    sc = escenario_base().con_zona(Zona("Bloqueo Amazonía", -3.5, -62.0, 15.0))
    r = ejecutar_ag(sc, RAPIDO, semilla=0)
    amazonia = next(x for x in r.eval_mejor.regiones if x.nombre == "Amazonía brasileña")
    assert r.encontro_factible and amazonia.cobertura == 0.0


def test_arranque_en_caliente_conserva_la_solucion_semilla(ejecucion_base):
    r = ejecutar_ag(ejecucion_base.escenario, ParametrosAG(tam_poblacion=40, generaciones=1), semilla=5,
                    poblacion_inicial=ejecucion_base.mejor[None])
    assert r.eval_inicial.fitness == pytest.approx(ejecucion_base.eval_mejor.fitness)


def test_ag_supera_busqueda_aleatoria_con_el_mismo_presupuesto(ejecucion_base):
    _, curva = busqueda_aleatoria(ejecucion_base.escenario, ejecucion_base.evaluaciones, semilla=1)
    assert ejecucion_base.eval_mejor.fitness > curva[-1][1]


def test_voraz_y_ag_bajo_la_cota_de_referencia(ejecucion_base):
    sc = ejecucion_base.escenario
    cota = cota_referencia(sc)["fitness"]
    _, g = colocacion_voraz(sc)
    assert g.factible and g.fitness <= cota and ejecucion_base.eval_mejor.fitness <= cota


# ---------------------------------------------------------------- operadores
def test_reparar_saca_al_satelite_de_la_zona():
    sc = escenario_base()
    individuo = np.array([[45.0, -35.0, 800.0], [44.0, -30.0, 800.0]])
    reparar(np.random.default_rng(0), individuo, sc)
    assert Evaluador(sc.con_parametros(n_satelites=2)).evaluar(individuo).factible


def test_alinear_empareja_los_satelites_mas_cercanos():
    a = np.array([[0, 0, 1000], [0, 90, 1000], [45, 180, 1000]], float)
    b = a[[2, 0, 1]] + [0.5, 0.5, 0]
    assert np.allclose(alinear(a, b)[:, :2], a[:, :2] + 0.5)


def test_reflejar_altitud_se_queda_dentro():
    x = reflejar_altitud(np.array([400.0, 2100.0, 4100.0, 1000.0]), 500, 2000)
    assert np.all((x >= 500) & (x <= 2000)) and x[3] == 1000


def test_modo_de_restriccion_invalido_se_rechaza():
    with pytest.raises(ValueError):
        ParametrosAG(manejo_restricciones="magia")


def test_forma_de_la_poblacion_aleatoria():
    pob = poblacion_aleatoria(np.random.default_rng(0), escenario_base(), 5)
    assert pob.shape == (5, 8, 3)

def test_con_ocho_satelites_se_cubren_todas_las_regiones():
    sc = escenario_base()
    r = ejecutar_ag(sc, ParametrosAG(), semilla=0)

    assert len(r.mejor) == 8
    assert r.encontro_factible
    assert all(region.cobertura == pytest.approx(1.0) for region in r.eval_mejor.regiones)
