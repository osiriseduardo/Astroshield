"""Regression checks for Unicode globe labels."""
import numpy as np
from astroshield.scenario import default_scenario
from astroshield.viz import globe_html


def test_globe_uses_unicode_html_labels():
    sc = default_scenario()
    config = np.array([[r.lat, r.lon, 800] for r in sc.regions] + [[0, 90, 800], [0, -90, 800]])
    html = globe_html(sc, {"Configuración final": config})
    assert "Península de Yucatán" in html
    assert "Amazonía brasileña" in html
    assert "Japón" in html
    assert "G.htmlElementsData(labels)" in html
    assert "label.textContent = d.text" in html
    assert "G.labelsData(labels)" not in html
