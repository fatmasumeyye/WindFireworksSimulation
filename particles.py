"""Firework sparks, stars, smoke, and flash effects."""

import math
import random
from dataclasses import dataclass, field

import pygame

from common import clamp, mix, px_to_m
from config import *
from graphics import draw_radial_glow
from physics import Body

@dataclass
class TrailPoint:
    x: float
    y: float


@dataclass
class FireworkStar:
    body: Body
    primary: tuple[int, int, int]
    secondary: tuple[int, int, int]
    hot: tuple[int, int, int]
    burn_time: float
    max_burn_time: float
    trail_length: int
    glitter: bool = False
    twinkle_phase: float = field(
        default_factory=lambda: random.uniform(0.0, math.tau)
    )
    history: list[TrailPoint] = field(default_factory=list)

    @property
    def alive(self) -> bool:
        return (
            self.burn_time > 0.0
            and -120.0 < self.body.x_px < WIDTH + 120.0
            and -120.0 < self.body.y_px < HEIGHT + 160.0
        )

    def update(
        self,
        dt: float,
        wind_mps: float,
        density_multiplier: float,
        precipitation_loss: float,
    ) -> None:
        self.history.append(
            TrailPoint(self.body.x_px, self.body.y_px)
        )
        if len(self.history) > self.trail_length:
            self.history.pop(0)

        self.body.integrate(
            dt,
            wind_mps,
            density_multiplier,
        )
        self.burn_time -= dt * (1.0 + precipitation_loss)

    def age_ratio(self) -> float:
        return 1.0 - clamp(
            self.burn_time / self.max_burn_time,
            0.0,
            1.0,
        )

    def color(self) -> tuple[int, int, int]:
        age = self.age_ratio()
        if age < 0.07:
            return mix(self.hot, self.primary, age / 0.07)
        if age < 0.70:
            return mix(
                self.primary,
                self.secondary,
                (age - 0.07) / 0.63,
            )
        return self.secondary

    def brightness(self) -> float:
        age = self.age_ratio()
        ignition = min(1.0, age / 0.035)
        fade = (
            1.0
            if age < 0.68
            else max(0.0, 1.0 - (age - 0.68) / 0.32)
        )
        flicker = 1.0
        if self.glitter and age > 0.42:
            flicker = 0.35 + 0.65 * abs(
                math.sin(self.twinkle_phase + age * 38.0)
            )
        return ignition * fade * flicker

    def draw(
        self,
        effects: pygame.Surface,
        glow: pygame.Surface,
        visibility: float,
    ) -> None:
        if not self.alive:
            return

        brightness = self.brightness() * visibility
        if brightness <= 0.02:
            return

        color = self.color()
        alpha = int(235 * brightness)

        if len(self.history) >= 2:
            segment_total = len(self.history) - 1
            for index in range(1, len(self.history)):
                ratio = index / max(1, segment_total)
                segment_alpha = int(
                    alpha * (ratio ** 1.8) * 0.76
                )
                pygame.draw.aaline(
                    effects,
                    (*color, segment_alpha),
                    (
                        int(self.history[index - 1].x),
                        int(self.history[index - 1].y),
                    ),
                    (
                        int(self.history[index].x),
                        int(self.history[index].y),
                    ),
                )

        draw_radial_glow(
            glow,
            self.body.x_px,
            self.body.y_px,
            color,
            3.0,
            alpha,
        )
        pygame.draw.circle(
            effects,
            (*color, alpha),
            (int(self.body.x_px), int(self.body.y_px)),
            1,
        )


@dataclass
class ShellSpark:
    x_px: float
    y_px: float
    vx_px: float
    vy_px: float
    color: tuple[int, int, int]
    life: float
    max_life: float

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    def update(
        self,
        dt: float,
        wind_mps: float,
        precipitation_loss: float,
    ) -> None:
        self.vx_px += wind_mps * PIXELS_PER_METER * 0.08 * dt
        self.vy_px += GRAVITY_MPS2 * PIXELS_PER_METER * 0.35 * dt
        self.x_px += self.vx_px * dt
        self.y_px += self.vy_px * dt
        self.life -= dt * (1.0 + precipitation_loss * 1.5)

    def draw(
        self,
        effects: pygame.Surface,
        glow: pygame.Surface,
        visibility: float,
    ) -> None:
        ratio = clamp(self.life / self.max_life, 0.0, 1.0)
        alpha = int(190 * ratio * visibility)
        if alpha <= 0:
            return
        draw_radial_glow(
            glow,
            self.x_px,
            self.y_px,
            self.color,
            3.6,
            alpha,
        )
        pygame.draw.circle(
            effects,
            (*self.color, alpha),
            (int(self.x_px), int(self.y_px)),
            1,
        )


@dataclass
class Smoke:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    radius: float

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    def update(
        self,
        dt: float,
        wind_mps: float,
        weather_name: str,
        precipitation_intensity: float,
    ) -> None:
        self.vx += wind_mps * PIXELS_PER_METER * 0.02 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.radius += 4.0 * dt

        weather_decay = 1.0
        if weather_name == "Yağmur":
            weather_decay += 0.75 * precipitation_intensity
        elif weather_name == "Kar":
            weather_decay += 0.18 * precipitation_intensity

        self.life -= dt * weather_decay

    def draw(
        self,
        effects: pygame.Surface,
        visibility: float,
    ) -> None:
        ratio = clamp(self.life / self.max_life, 0.0, 1.0)
        alpha = int(18 * ratio * visibility)
        pygame.draw.circle(
            effects,
            (130, 138, 153, alpha),
            (int(self.x), int(self.y)),
            max(1, int(self.radius)),
        )


@dataclass
class Flash:
    x: float
    y: float
    color: tuple[int, int, int]
    life: float = 0.12
    max_life: float = 0.12

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float) -> None:
        self.life -= dt

    def draw(
        self,
        effects: pygame.Surface,
        glow: pygame.Surface,
        visibility: float,
    ) -> None:
        progress = 1.0 - clamp(
            self.life / self.max_life,
            0.0,
            1.0,
        )
        fade = 1.0 - progress
        alpha = int(118 * fade * visibility)
        draw_radial_glow(
            glow,
            self.x,
            self.y,
            self.color,
            10.0 + progress * 14.0,
            alpha,
        )
        pygame.draw.circle(
            effects,
            (255, 255, 245, min(220, alpha + 70)),
            (int(self.x), int(self.y)),
            2 if progress < 0.30 else 1,
        )


def spherical_direction() -> tuple[float, float]:
    z_axis = random.uniform(-1.0, 1.0)
    azimuth = random.uniform(0.0, math.tau)
    radial = math.sqrt(max(0.0, 1.0 - z_axis * z_axis))
    return math.cos(azimuth) * radial, z_axis


def make_star(
    x_px: float,
    y_px: float,
    vx: float,
    vy: float,
    palette: tuple[
        tuple[int, int, int],
        tuple[int, int, int],
        tuple[int, int, int],
    ],
    *,
    burn: float,
    mass: float = 0.004,
    diameter: float = 0.012,
    drag_coefficient: float = 0.80,
    trail: int = 10,
    glitter: bool = False,
    color_index: int = 0,
) -> FireworkStar:
    area = math.pi * (diameter / 2.0) ** 2
    primary = palette[color_index % 2]
    secondary = palette[(color_index + 1) % 2]

    return FireworkStar(
        body=Body(
            px_to_m(x_px),
            px_to_m(y_px),
            vx,
            vy,
            mass,
            area,
            drag_coefficient,
        ),
        primary=primary,
        secondary=secondary,
        hot=palette[2],
        burn_time=burn,
        max_burn_time=burn,
        trail_length=trail,
        glitter=glitter,
    )

