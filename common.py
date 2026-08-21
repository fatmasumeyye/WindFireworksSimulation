"""Shared numeric and coordinate helpers."""

from config import PIXELS_PER_METER

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = clamp(t, 0.0, 1.0)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def px_to_m(value: float) -> float:
    return value / PIXELS_PER_METER


def m_to_px(value: float) -> float:
    return value * PIXELS_PER_METER


