"""Comprobaciones de las gráficas estáticas con nombres en español."""
import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402

from astroshield.escenario import escenario_base  # noqa: E402
from astroshield.visualizacion import graficar_mapa_mision  # noqa: E402


def test_mapa_de_mision_muestra_regiones_con_acentos():
    sc = escenario_base()
    configuracion = np.array([[r.lat, r.lon, 800] for r in sc.regiones] + [[0, 90, 800], [0, -90, 800]])
    fig = graficar_mapa_mision(sc, configuracion)
    textos = [t.get_text() for t in fig.axes[0].texts]
    assert any("Península de Yucatán" in t for t in textos)
    assert any("Japón" in t for t in textos)
    assert "6/6 regiones cubiertas" in fig.axes[0].get_title()
