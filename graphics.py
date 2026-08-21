"""Shared low-level drawing helpers."""

import pygame

from common import clamp, mix
from config import HEIGHT, WIDTH

def draw_gradient(
    surface: pygame.Surface,
    stops: list[tuple[float, tuple[int, int, int]]],
) -> None:
    for y in range(HEIGHT):
        p = y / max(1, HEIGHT - 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= p <= p1:
                t = (p - p0) / max(0.0001, p1 - p0)
                pygame.draw.line(surface, mix(c0, c1, t), (0, y), (WIDTH, y))
                break


def draw_radial_glow(
    target: pygame.Surface,
    x: float,
    y: float,
    color: tuple[int, int, int],
    radius: float,
    alpha: int,
) -> None:
    radius_i = max(1, int(radius))
    if alpha <= 0:
        return
    temp = pygame.Surface((radius_i * 2, radius_i * 2), pygame.SRCALPHA)
    center = (radius_i, radius_i)
    for ratio, factor in ((1.0, 0.035), (0.62, 0.09), (0.30, 0.24), (0.12, 0.62)):
        pygame.draw.circle(
            temp,
            (*color, int(alpha * factor)),
            center,
            max(1, int(radius_i * ratio)),
        )
    target.blit(temp, (int(x) - radius_i, int(y) - radius_i))


