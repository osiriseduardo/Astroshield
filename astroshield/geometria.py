"""Funciones de geometría esférica.

Todos los ángulos están en grados, salvo que el nombre diga lo contrario. La
Tierra es una esfera perfecta de radio RADIO_TIERRA_KM (modelo educativo).
"""
from __future__ import annotations

import numpy as np

RADIO_TIERRA_KM = 6371.0


def normalizar_lon(lon):
    """Lleva la(s) longitud(es) al intervalo [-180, 180)."""
    return (np.asarray(lon) + 180.0) % 360.0 - 180.0


def km_a_grados(km):
    """Distancia sobre la superficie (km) -> ángulo central (grados)."""
    return np.degrees(np.asarray(km) / RADIO_TIERRA_KM)


def grados_a_km(grados):
    """Ángulo central (grados) -> distancia sobre la superficie (km)."""
    return np.radians(np.asarray(grados)) * RADIO_TIERRA_KM


def a_unitario(lat, lon):
    """Lat/lon (grados) -> vectores unitarios con forma (..., 3)."""
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    cos_lat = np.cos(lat_r)
    return np.stack(
        [cos_lat * np.cos(lon_r), cos_lat * np.sin(lon_r), np.sin(lat_r)], axis=-1
    )


def desde_unitario(v):
    """Vectores unitarios (o cualquiera no nulo) (..., 3) -> (lat, lon) en grados."""
    v = np.asarray(v, dtype=float)
    v = v / np.linalg.norm(v, axis=-1, keepdims=True)
    lat = np.degrees(np.arcsin(np.clip(v[..., 2], -1.0, 1.0)))
    lon = np.degrees(np.arctan2(v[..., 1], v[..., 0]))
    return lat, lon


def distancia_angular(lat1, lon1, lat2, lon2):
    """Ángulo central de gran círculo (grados) con la fórmula de haversine."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return np.degrees(2 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0))))


def rumbo_inicial(lat1, lon1, lat2, lon2):
    """Rumbo inicial (grados, en sentido horario desde el norte) del punto 1 al punto 2."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    x = np.sin(dl) * np.cos(p2)
    y = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl)
    return np.degrees(np.arctan2(x, y)) % 360.0


def destino(lat, lon, rumbo, distancia):
    """Punto al que se llega recorriendo `distancia` (grados) desde (lat, lon) con `rumbo`."""
    p1 = np.radians(lat)
    l1 = np.radians(lon)
    b = np.radians(rumbo)
    d = np.radians(distancia)
    p2 = np.arcsin(np.sin(p1) * np.cos(d) + np.cos(p1) * np.sin(d) * np.cos(b))
    l2 = l1 + np.arctan2(
        np.sin(b) * np.sin(d) * np.cos(p1), np.cos(d) - np.sin(p1) * np.sin(p2)
    )
    return np.degrees(p2), normalizar_lon(np.degrees(l2))


def circulo(lat, lon, radio, n=72):
    """Borde de un casquete esférico como (lats, lons), antihorario y cerrado."""
    rumbos = np.linspace(360.0, 0.0, n + 1)  # rumbo decreciente => antihorario en un mapa
    return destino(lat, lon, rumbos, radio)


def muestras_disco(lat, lon, radio, anillos=3):
    """Puntos de muestra (N, 2) que cubren un disco esférico: centro + anillos concéntricos.

    El anillo k (1..anillos) está a radio*k/anillos y tiene 8*k puntos, así que el
    anillo exterior queda exactamente sobre el borde de la región.
    """
    puntos = [(lat, lon)]
    for k in range(1, anillos + 1):
        n = 8 * k
        desfase = 0.0 if k % 2 else 180.0 / n  # alterna los anillos
        rumbos = desfase + np.arange(n) * 360.0 / n
        la, lo = destino(lat, lon, rumbos, radio * k / anillos)
        puntos.extend(zip(la, lo))
    return np.array(puntos, dtype=float)


def puntos_aleatorios(rng, n):
    """`n` puntos distribuidos uniformemente sobre la esfera -> arreglos (lat, lon)."""
    lat = np.degrees(np.arcsin(rng.uniform(-1.0, 1.0, n)))
    lon = rng.uniform(-180.0, 180.0, n)
    return lat, lon


def paso_gaussiano(rng, lat, lon, sigma):
    """Mueve cada punto un paso gaussiano 2-D (sigma en grados) sobre la esfera."""
    lat = np.asarray(lat, dtype=float)
    dx = rng.normal(0.0, sigma, lat.shape)
    dy = rng.normal(0.0, sigma, lat.shape)
    dist = np.hypot(dx, dy)
    rumbo = np.degrees(np.arctan2(dx, dy))
    return destino(lat, lon, rumbo, dist)
