"""Rocket flight and explosion-pattern behavior."""

import math
import random

import pygame

from common import clamp, px_to_m
from config import *
from graphics import draw_radial_glow
from particles import FireworkStar, Flash, ShellSpark, Smoke, make_star, spherical_direction
from physics import Body


class Shell:
    PATTERNS = (
        "Şakayık",
        "Krizantem",
        "Halka",
        "Altın Söğüt",
        "Palmiye",
        "Çift Renk",
    )

    def __init__(
        self,
        launch_x_px: float,
        palette: tuple[
            tuple[int, int, int],
            tuple[int, int, int],
            tuple[int, int, int],
        ],
        palette_name: str,
        pattern: str,
        power: float,
        angle_deg: float,
        target_height_m: float,
    ) -> None:
        diameter = 0.045
        area = math.pi * (diameter / 2.0) ** 2

        angle_radians = math.radians(angle_deg)
        vertical_component = max(0.25, math.sin(angle_radians))

        # H = v_y² / (2g) denkleminden başlangıç hızı.
        # Sürükleme kaybı için 1.18 düzeltme katsayısı uygulanır.
        launch_speed = (
            math.sqrt(2.0 * GRAVITY_MPS2 * target_height_m)
            / vertical_component
            * 1.18
        )

        self.body = Body(
            px_to_m(launch_x_px),
            px_to_m(LAUNCH_Y),
            launch_speed * math.cos(angle_radians),
            -launch_speed * math.sin(angle_radians),
            0.18,
            area,
            0.47,
        )

        self.palette = palette
        self.palette_name = palette_name
        self.pattern = pattern
        self.power = clamp(
            power,
            MIN_EXPLOSION_POWER,
            MAX_EXPLOSION_POWER,
        )
        self.angle_deg = angle_deg
        self.target_height_m = target_height_m
        self.spark_timer = 0.0
        self.smoke_timer = 0.0
        self.history: list[tuple[float, float]] = []
        self.alive = True

    @property
    def altitude_m(self) -> float:
        return max(
            0.0,
            (LAUNCH_Y - self.body.y_px) / PIXELS_PER_METER,
        )

    def speed(self, base_speed: float) -> float:
        return base_speed * self.power

    def burn(self, base_burn: float) -> float:
        return base_burn * (0.92 + 0.12 * self.power)

    def update(
        self,
        dt: float,
        wind_mps: float,
        density_multiplier: float,
        precipitation_loss: float,
        sparks: list[ShellSpark],
        smoke_particles: list[Smoke],
    ) -> bool:
        self.history.append(
            (self.body.x_px, self.body.y_px)
        )
        if len(self.history) > 14:
            self.history.pop(0)

        self.body.integrate(
            dt,
            wind_mps,
            density_multiplier,
        )
        self.spark_timer += dt
        self.smoke_timer += dt

        while self.spark_timer >= 0.016:
            self.spark_timer -= 0.016
            life = random.uniform(0.24, 0.42)
            sparks.append(
                ShellSpark(
                    self.body.x_px + random.uniform(-1.2, 1.2),
                    self.body.y_px + random.uniform(4.0, 7.0),
                    random.uniform(-7.0, 7.0),
                    random.uniform(20.0, 42.0),
                    random.choice(
                        (
                            self.palette[2],
                            (255, 208, 100),
                            (255, 150, 60),
                        )
                    ),
                    life,
                    life,
                )
            )

        if self.smoke_timer >= 0.10:
            self.smoke_timer = 0.0
            life = random.uniform(0.6, 0.9)
            smoke_particles.append(
                Smoke(
                    self.body.x_px + random.uniform(-1.0, 1.0),
                    self.body.y_px + 7.0,
                    random.uniform(-2.0, 2.0),
                    random.uniform(-3.0, 1.0),
                    life,
                    life,
                    random.uniform(1.5, 2.4),
                )
            )

        reached_height = self.altitude_m >= self.target_height_m
        reached_apex = self.body.vy_mps >= -0.45
        left_screen = (
            self.body.x_px < -35.0
            or self.body.x_px > FIREWORK_AREA_RIGHT + 35.0
        )

        if reached_height or reached_apex or left_screen:
            self.alive = False
            return True

        return False

    def draw(
        self,
        effects: pygame.Surface,
        glow: pygame.Surface,
        visibility: float,
    ) -> None:
        if len(self.history) >= 2:
            for index in range(1, len(self.history)):
                ratio = index / max(1, len(self.history) - 1)
                pygame.draw.aaline(
                    effects,
                    (
                        255,
                        190,
                        95,
                        int(150 * ratio * ratio * visibility),
                    ),
                    self.history[index - 1],
                    self.history[index],
                )

        draw_radial_glow(
            glow,
            self.body.x_px,
            self.body.y_px,
            self.palette[2],
            6.0,
            int(210 * visibility),
        )
        pygame.draw.circle(
            effects,
            (255, 252, 235, int(230 * visibility)),
            (int(self.body.x_px), int(self.body.y_px)),
            2,
        )

    def burst(self) -> tuple[list[FireworkStar], Flash]:
        factory = {
            "Şakayık": self._peony,
            "Krizantem": self._chrysanthemum,
            "Halka": self._ring,
            "Altın Söğüt": self._willow,
            "Palmiye": self._palm,
            "Çift Renk": self._two_tone,
        }
        return (
            factory[self.pattern](),
            Flash(
                self.body.x_px,
                self.body.y_px,
                self.palette[0],
            ),
        )

    def _peony(self) -> list[FireworkStar]:
        stars: list[FireworkStar] = []
        for index in range(random.randint(135, 165)):
            dx, dy = spherical_direction()
            speed = self.speed(random.uniform(13.0, 20.0))
            stars.append(
                make_star(
                    self.body.x_px,
                    self.body.y_px,
                    dx * speed,
                    dy * speed,
                    self.palette,
                    burn=self.burn(random.uniform(1.45, 1.90)),
                    trail=8,
                    glitter=random.random() < 0.10,
                    color_index=(index // 14) % 2,
                )
            )
        return stars

    def _chrysanthemum(self) -> list[FireworkStar]:
        stars: list[FireworkStar] = []
        for index in range(random.randint(150, 185)):
            dx, dy = spherical_direction()
            speed = self.speed(random.uniform(13.5, 20.5))
            stars.append(
                make_star(
                    self.body.x_px,
                    self.body.y_px,
                    dx * speed,
                    dy * speed,
                    self.palette,
                    burn=self.burn(random.uniform(2.0, 2.55)),
                    trail=14,
                    glitter=True,
                    color_index=1 if index % 3 == 0 else 0,
                )
            )
        return stars

    def _ring(self) -> list[FireworkStar]:
        stars: list[FireworkStar] = []
        count = random.randint(90, 115)
        tilt = random.uniform(0.35, 1.05)

        for index in range(count):
            angle = (
                math.tau * index / count
                + random.uniform(-0.018, 0.018)
            )
            x_direction = math.cos(angle)
            y_direction = math.sin(angle) * math.cos(tilt)
            speed = self.speed(random.uniform(15.0, 18.5))

            stars.append(
                make_star(
                    self.body.x_px,
                    self.body.y_px,
                    x_direction * speed,
                    y_direction * speed,
                    self.palette,
                    burn=self.burn(random.uniform(1.45, 1.80)),
                    trail=8,
                    glitter=random.random() < 0.16,
                    color_index=(index // 10) % 2,
                )
            )

        return stars

    def _willow(self) -> list[FireworkStar]:
        gold = (
            (255, 218, 105),
            (255, 130, 55),
            (255, 252, 222),
        )
        stars: list[FireworkStar] = []

        for index in range(random.randint(120, 145)):
            dx, dy = spherical_direction()
            speed = self.speed(random.uniform(9.5, 15.5))
            stars.append(
                make_star(
                    self.body.x_px,
                    self.body.y_px,
                    dx * speed,
                    dy * speed,
                    gold,
                    burn=self.burn(random.uniform(2.70, 3.25)),
                    mass=0.0045,
                    diameter=0.013,
                    drag_coefficient=0.83,
                    trail=18,
                    glitter=True,
                    color_index=1 if index % 7 == 0 else 0,
                )
            )
        return stars

    def _palm(self) -> list[FireworkStar]:
        stars: list[FireworkStar] = []
        arms = random.randint(9, 12)
        phase = random.uniform(0.0, math.tau)

        for arm in range(arms):
            angle = phase + math.tau * arm / arms
            for step in range(8, 14):
                speed = self.speed(6.5 + step * 1.15)
                jitter = random.uniform(-0.025, 0.025)
                stars.append(
                    make_star(
                        self.body.x_px,
                        self.body.y_px,
                        math.cos(angle + jitter) * speed,
                        math.sin(angle + jitter) * speed,
                        self.palette,
                        burn=self.burn(random.uniform(2.0, 2.55)),
                        trail=15,
                        glitter=True,
                        color_index=arm % 2,
                    )
                )
        return stars

    def _two_tone(self) -> list[FireworkStar]:
        stars: list[FireworkStar] = []
        phase = random.uniform(0.0, math.tau)
        count = random.randint(140, 170)

        for index in range(count):
            angle = (
                math.tau * index / count
                + random.uniform(-0.03, 0.03)
            )
            speed = self.speed(random.uniform(13.0, 20.0))
            side = 0 if math.cos(angle - phase) >= 0 else 1
            stars.append(
                make_star(
                    self.body.x_px,
                    self.body.y_px,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    self.palette,
                    burn=self.burn(random.uniform(1.65, 2.05)),
                    trail=10,
                    glitter=random.random() < 0.18,
                    color_index=side,
                )
            )
        return stars


