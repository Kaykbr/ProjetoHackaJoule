"""Distância geográfica. Haversine basta para o MVP (dispensa PostGIS)."""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

RAIO_TERRA_KM = 6371.0


def distancia_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * RAIO_TERRA_KM * asin(sqrt(a))
