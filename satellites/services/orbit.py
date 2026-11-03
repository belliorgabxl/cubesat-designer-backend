"""Circular-orbit geometry for the beta = 0 case."""

import math

EARTH_RADIUS_KM = 6371.0
EARTH_MU_KM3_S2 = 398600.0


def orbital_period_s(altitude_km):
    """T = 2*pi*sqrt((R + h)^3 / mu)."""
    return 2 * math.pi * math.sqrt((EARTH_RADIUS_KM + altitude_km) ** 3 / EARTH_MU_KM3_S2)


def eclipse_fraction(altitude_km):
    """Share of the orbit in Earth's shadow: asin(R / (R + h)) / pi."""
    return math.asin(EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude_km)) / math.pi


def in_eclipse(t_s, period_s, fraction):
    """True while in shadow; t = 0 is the sub-solar point, so the eclipse is centred on half an orbit."""
    phase = (t_s % period_s) / period_s
    return abs(phase - 0.5) < fraction / 2


def orbit_summary(altitude_km):
    return {
        "altitude_km": altitude_km,
        "period_min": round(orbital_period_s(altitude_km) / 60, 1),
        "eclipse_fraction": round(eclipse_fraction(altitude_km), 3),
    }
