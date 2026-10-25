import numpy as np
import pytest

from astroshield.escenario import Zona, escenario_base, escenario_inicial
from astroshield.evaluacion import (
    Evaluador,
    aceptacion,
    altitud_minima_vista_completa,
    cota_referencia,
    listar_violaciones,
    semiangulo_huella,
)
from astroshield.geometria import destino, distancia_angular, km_a_grados, muestras_disco, normalizar_lon


def configuracion_encima(escenario, alt=900.0):
    """Un satélite sobre el centro de cada región; los sobrantes, lejos, sobre océanos."""
    filas = [(r.lat, r.lon, alt) for r in escenario.regiones]
    sobrantes = [(-60.0, -150.0, alt), (-60.0, 60.0, alt)]
    return np.array((filas + sobrantes)[: escenario.n_satelites])


# ---------------------------------------------------------------- geometría
def test_distancia_angular_valores_conocidos():
    assert distancia_angular(0, 0, 0, 90) == pytest.approx(90)
    assert distancia_angular(90, 0, -90, 0) == pytest.approx(180)
    assert distancia_angular(10, 179, 10, -179) == pytest.approx(2 * np.cos(np.radians(10)), rel=1e-3)


def test_destino_recorre_la_distancia_pedida():
    lat, lon = destino(20.5, -89.0, np.arange(0, 360, 30), 7.0)
    assert np.allclose(distancia_angular(20.5, -89.0, lat, lon), 7.0)


def test_normalizar_lon_rango():
    assert normalizar_lon(190) == pytest.approx(-170)
    assert normalizar_lon(-180) == pytest.approx(-180)


@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        (180, -180),
        (-181, 179),
        (360, 0),
        (540, -180),
        (-540, -180),
    ],
)
def test_normalizar_lon_casos_limite(entrada, esperada):
    assert normalizar_lon(entrada) == pytest.approx(esperada)



def test_muestras_disco_cubren_exactamente_la_region():
    pts = muestras_disco(0, 0, 3.0, anillos=3)
    assert len(pts) == 1 + 8 + 16 + 24
    d = distancia_angular(0, 0, pts[:, 0], pts[:, 1])
    assert d.max() == pytest.approx(3.0)


# ---------------------------------------------------------------- cobertura
def test_huella_crece_con_la_altitud():
    lam = semiangulo_huella(np.linspace(500, 2000, 20), 30)
    assert np.all(np.diff(lam) > 0)


def test_altitud_minima_no_ve_la_region_completa():
    sc = escenario_inicial()
    assert semiangulo_huella(500, 30) < km_a_grados(300)
    assert 500 < altitud_minima_vista_completa(300, sc) < 600


def test_satelite_encima_cubre_toda_su_region():
    sc = escenario_inicial()
    ev = Evaluador(sc).evaluar(configuracion_encima(sc))
    assert all(r.cobertura == 1.0 and r.cubierta for r in ev.regiones)
    assert 0 < ev.fitness <= 1


def test_satelites_lejanos_no_cubren_nada():
    sc = escenario_inicial()
    cfg = np.tile([-80.0, 0.0, 2000.0], (8, 1))
    cfg[:, 1] = np.arange(8) * 45
    ev = Evaluador(sc).evaluar(cfg)
    assert ev.n_cubiertas == 0 and ev.fitness == 0


def test_pesos_de_prioridad_cambian_el_fitness():
    sc = escenario_inicial()
    cfg = configuracion_encima(sc)
    cfg[0] = (-60, 170, 900)  # deja sin cubrir Yucatán (alta)
    base = Evaluador(sc).evaluar(cfg).fitness
    menor = Evaluador(sc.con_prioridad("Península de Yucatán", "normal")).evaluar(cfg).fitness
    assert menor > base  # perder una región Normal cuesta menos que perder una Alta


def test_evaluacion_por_lote_e_individual_coinciden():
    sc = escenario_base()
    rng = np.random.default_rng(3)
    pob = np.stack([configuracion_encima(sc) + rng.normal(0, [1, 1, 10], (8, 3)) for _ in range(5)])
    ev = Evaluador(sc)
    lote = ev.evaluar_poblacion(pob)
    for i in range(5):
        individual = ev.evaluar(pob[i])
        assert individual.fitness == pytest.approx(lote["fitness"][i])
        assert individual.factible == bool(lote["factible"][i])


# -------------------------------------------------------------- restricciones
@pytest.mark.parametrize("nombre_zona", ["Atlántico Norte", "Pacífico Sur", "Polar Norte", "Objeto A", "Objeto B"])
def test_satelite_dentro_de_cada_zona_es_invalido(nombre_zona):
    sc = escenario_base()
    z = next(z for z in sc.zonas if z.nombre == nombre_zona)
    cfg = configuracion_encima(sc)
    cfg[7, :2] = destino(z.lat, z.lon, 45, z.radio_grados * 0.9)
    ev = Evaluador(sc).evaluar(cfg)
    assert not ev.factible
    assert [v.objetivo for v in ev.violaciones] == [nombre_zona]
    assert ev.violacion == pytest.approx(z.radio_grados * 0.1, rel=1e-6)


def test_satelite_justo_fuera_de_la_zona_es_valido():
    sc = escenario_base()
    z = sc.zonas[0]
    cfg = configuracion_encima(sc)
    cfg[7, :2] = destino(z.lat, z.lon, 90, z.radio_grados + 0.01)
    assert Evaluador(sc).evaluar(cfg).factible


def test_se_exige_la_separacion_minima():
    sc = escenario_base()
    cfg = configuracion_encima(sc)
    cfg[7] = (cfg[0, 0] + 1.0, cfg[0, 1], 900)  # a 1° del satélite 0 (< 2°)
    v = listar_violaciones(cfg, sc)
    assert len(v) == 1 and v[0].restriccion == "separacion"


def test_zona_nueva_invalida_la_configuracion_anterior():
    sc = escenario_base()
    cfg = configuracion_encima(sc)
    assert Evaluador(sc).evaluar(cfg).factible
    cambiado = sc.con_zona(Zona("Nueva", cfg[3, 0], cfg[3, 1], 3.0))
    ev = Evaluador(cambiado).evaluar(cfg)
    assert not ev.factible and ev.violaciones[0].satelite == 3


def test_con_zona_conserva_el_escenario_original():
    sc = escenario_base()
    zonas_originales = sc.zonas

    cambiado = sc.con_zona(
        Zona("Zona de prueba", 0.0, 0.0, 4.0)
    )

    assert sc.zonas == zonas_originales
    assert len(cambiado.zonas) == len(zonas_originales) + 1
    assert cambiado.zonas[-1].nombre == "Zona de prueba"



def test_cota_de_referencia_supera_una_solucion_conocida():
    sc = escenario_base()
    ev = Evaluador(sc).evaluar(configuracion_encima(sc, alt=520))
    assert ev.fitness <= cota_referencia(sc)["fitness"]
    assert set(aceptacion(ev, sc)) >= {"C1 válida (sin violaciones)", "ACEPTADA"}


def test_redundancia_exigida_se_adapta_a_los_satelites_sobrantes():
    # Tres regiones Alta pero solo dos satélites sobrantes: dos regiones Alta
    # con redundancia deben bastar para cumplir C3.
    sc = escenario_base().con_prioridad("Interior de Australia", "alta")
    cfg = configuracion_encima(sc, alt=520)
    cfg[6] = (sc.regiones[0].lat + 2.5, sc.regiones[0].lon, 1300)  # 2.º satélite sobre Yucatán
    cfg[7] = (sc.regiones[1].lat + 2.5, sc.regiones[1].lon, 1300)  # 2.º satélite sobre la Amazonía
    criterios = aceptacion(Evaluador(sc).evaluar(cfg), sc)
    c3 = next(k for k in criterios if k.startswith("C3"))
    assert "≥2" in c3 and criterios[c3]
