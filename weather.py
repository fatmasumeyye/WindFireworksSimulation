"""Rain, snow, and weather-related simulation effects."""

import math
import random
from dataclasses import dataclass

import pygame

from common import clamp
from config import *

@dataclass
class WeatherParticle:
    kind: str
    x: float
    y: float
    speed: float
    size: float
    phase: float

    @property
    def alive(self) -> bool:
        return (
            -50.0 <= self.x <= WIDTH + 50.0
            and self.y <= HEIGHT + 40.0
        )

    def update(
        self,
        dt: float,
        wind_mps: float,
    ) -> None:
        if self.kind == "Yağmur":
            self.x += wind_mps * 11.0 * dt
            self.y += self.speed * dt
        else:
            self.phase += dt * 1.8
            self.x += (
                wind_mps * 7.0
                + math.sin(self.phase) * 13.0
            ) * dt
            self.y += self.speed * dt

    def draw(
        self,
        surface: pygame.Surface,
        intensity: float,
    ) -> None:
        if self.kind == "Yağmur":
            slant = int(clamp(self.speed / 55.0, 7.0, 15.0))
            alpha = int(70 + 90 * intensity)
            pygame.draw.aaline(
                surface,
                (160, 192, 225, alpha),
                (int(self.x), int(self.y)),
                (int(self.x - slant * 0.28), int(self.y - slant)),
            )
        else:
            alpha = int(130 + 100 * intensity)
            radius = max(1, int(self.size))
            pygame.draw.circle(
                surface,
                (244, 248, 255, alpha),
                (int(self.x), int(self.y)),
                radius,
            )
            if radius >= 2:
                pygame.draw.aaline(
                    surface,
                    (220, 234, 255, alpha),
                    (int(self.x - radius - 1), int(self.y)),
                    (int(self.x + radius + 1), int(self.y)),
                )


# ============================================================
# SEÇİM VE FIRLATMA YARDIMCILARI
# ============================================================

def effective_density_multiplier(
    air_level: str,
    weather_name: str,
    precipitation_intensity: float,
) -> float:
    multiplier = AIR_RESISTANCE_LEVELS[air_level]

    if weather_name == "Yağmur":
        multiplier *= 1.0 + 0.20 * precipitation_intensity
    elif weather_name == "Kar":
        multiplier *= 1.0 + 0.10 * precipitation_intensity

    return multiplier


def weather_visibility_multiplier(
    weather_name: str,
    precipitation_intensity: float,
) -> float:
    if weather_name == "Yağmur":
        return 1.0 - 0.34 * precipitation_intensity
    if weather_name == "Kar":
        return 1.0 - 0.20 * precipitation_intensity
    return 1.0


def precipitation_burn_loss(
    weather_name: str,
    precipitation_intensity: float,
) -> float:
    if weather_name == "Yağmur":
        return 0.18 * precipitation_intensity
    if weather_name == "Kar":
        return 0.06 * precipitation_intensity
    return 0.0


def update_weather_particles(
    particles: list[WeatherParticle],
    weather_name: str,
    intensity: float,
    dt: float,
    wind_mps: float,
    spawn_accumulator: float,
) -> float:
    if weather_name == "Açık" or intensity <= 0.0:
        particles.clear()
        return 0.0

    spawn_rate = (
        430.0 * intensity
        if weather_name == "Yağmur"
        else 115.0 * intensity
    )
    spawn_accumulator += spawn_rate * dt

    while (
        spawn_accumulator >= 1.0
        and len(particles) < MAX_WEATHER_PARTICLES
    ):
        spawn_accumulator -= 1.0

        if weather_name == "Yağmur":
            particles.append(
                WeatherParticle(
                    "Yağmur",
                    random.uniform(-20.0, WIDTH + 20.0),
                    random.uniform(-35.0, -5.0),
                    random.uniform(420.0, 650.0),
                    1.0,
                    random.uniform(0.0, math.tau),
                )
            )
        else:
            particles.append(
                WeatherParticle(
                    "Kar",
                    random.uniform(-20.0, WIDTH + 20.0),
                    random.uniform(-35.0, -5.0),
                    random.uniform(30.0, 72.0),
                    random.choice((1.0, 1.0, 1.5, 2.0)),
                    random.uniform(0.0, math.tau),
                )
            )

    for particle in particles:
        particle.update(dt, wind_mps)

    particles[:] = [
        particle
        for particle in particles
        if particle.alive
    ]

    return spawn_accumulator


def draw_weather(
    screen: pygame.Surface,
    particles: list[WeatherParticle],
    weather_name: str,
    intensity: float,
) -> None:
    if weather_name == "Açık" or intensity <= 0.0:
        return

    weather_surface = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA,
    )

    if weather_name == "Yağmur":
        veil_alpha = int(22 * intensity)
        weather_surface.fill((40, 61, 88, veil_alpha))
    else:
        veil_alpha = int(12 * intensity)
        weather_surface.fill((190, 205, 226, veil_alpha))

    for particle in particles:
        particle.draw(weather_surface, intensity)

    screen.blit(weather_surface, (0, 0))


