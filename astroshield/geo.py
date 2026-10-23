"""Spherical geometry helpers.

All angles are in degrees unless the name says otherwise. The Earth is a
perfect sphere of radius EARTH_RADIUS_KM (educational model).
"""
from __future__ import annotations

import numpy as np

EARTH_RADIUS_KM = 6371.0


def wrap_lon(lon):
    """Wrap longitude(s) into [-180, 180)."""
    return (np.asarray(lon) + 180.0) % 360.0 - 180.0


def km_to_deg(km):
    """Ground distance (km) -> central angle (deg)."""
    return np.degrees(np.asarray(km) / EARTH_RADIUS_KM)


def deg_to_km(deg):
    """Central angle (deg) -> ground distance (km)."""
    return np.radians(np.asarray(deg)) * EARTH_RADIUS_KM


def to_unit(lat, lon):
    """Lat/lon (deg) -> unit vectors with shape (..., 3)."""
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    cos_lat = np.cos(lat_r)
    return np.stack(
        [cos_lat * np.cos(lon_r), cos_lat * np.sin(lon_r), np.sin(lat_r)], axis=-1
    )


def from_unit(v):
    """Unit (or any non-zero) vectors (..., 3) -> (lat, lon) in degrees."""
    v = np.asarray(v, dtype=float)
    v = v / np.linalg.norm(v, axis=-1, keepdims=True)
    lat = np.degrees(np.arcsin(np.clip(v[..., 2], -1.0, 1.0)))
    lon = np.degrees(np.arctan2(v[..., 1], v[..., 0]))
    return lat, lon


def angular_distance(lat1, lon1, lat2, lon2):
    """Great-circle central angle (deg) using the haversine formula."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return np.degrees(2 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0))))


def initial_bearing(lat1, lon1, lat2, lon2):
    """Initial bearing (deg, clockwise from north) from point 1 to point 2."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    x = np.sin(dl) * np.cos(p2)
    y = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl)
    return np.degrees(np.arctan2(x, y)) % 360.0


def destination(lat, lon, bearing, distance):
    """Point reached travelling `distance` (deg) from (lat, lon) along `bearing`."""
    p1 = np.radians(lat)
    l1 = np.radians(lon)
    b = np.radians(bearing)
    d = np.radians(distance)
    p2 = np.arcsin(np.sin(p1) * np.cos(d) + np.cos(p1) * np.sin(d) * np.cos(b))
    l2 = l1 + np.arctan2(
        np.sin(b) * np.sin(d) * np.cos(p1), np.cos(d) - np.sin(p1) * np.sin(p2)
    )
    return np.degrees(p2), wrap_lon(np.degrees(l2))


def circle(lat, lon, radius, n=72):
    """Boundary of a spherical cap as (lats, lons), counter-clockwise, closed."""
    bearings = np.linspace(360.0, 0.0, n + 1)  # decreasing bearing => CCW on a map
    return destination(lat, lon, bearings, radius)


def disk_samples(lat, lon, radius, rings=3):
    """Sample points (N, 2) covering a spherical disk: centre + concentric rings.

    Ring k (1..rings) sits at radius*k/rings and holds 8*k points, so the
    outer ring lies exactly on the region border.
    """
    pts = [(lat, lon)]
    for k in range(1, rings + 1):
        n = 8 * k
        offset = 0.0 if k % 2 else 180.0 / n  # stagger rings
        bearings = offset + np.arange(n) * 360.0 / n
        la, lo = destination(lat, lon, bearings, radius * k / rings)
        pts.extend(zip(la, lo))
    return np.array(pts, dtype=float)


def random_points(rng, n):
    """`n` points uniformly distributed on the sphere -> (lat, lon) arrays."""
    lat = np.degrees(np.arcsin(rng.uniform(-1.0, 1.0, n)))
    lon = rng.uniform(-180.0, 180.0, n)
    return lat, lon


def gaussian_step(rng, lat, lon, sigma):
    """Move each point a 2-D Gaussian step (sigma in deg) on the sphere."""
    lat = np.asarray(lat, dtype=float)
    dx = rng.normal(0.0, sigma, lat.shape)
    dy = rng.normal(0.0, sigma, lat.shape)
    dist = np.hypot(dx, dy)
    bearing = np.degrees(np.arctan2(dx, dy))
    return destination(lat, lon, bearing, dist)
