"""Physical body model and integration."""

import math
from dataclasses import dataclass

from common import m_to_px
from config import AIR_DENSITY, GRAVITY_MPS2

@dataclass
class Body:
    x_m: float
    y_m: float
    vx_mps: float
    vy_mps: float
    mass_kg: float
    area_m2: float
    drag_coefficient: float

    def integrate(
        self,
        dt: float,
        wind_mps: float,
        density_multiplier: float,
        gravity_scale: float = 1.0,
    ) -> None:
        rel_vx = self.vx_mps - wind_mps
        rel_vy = self.vy_mps
        speed = math.hypot(rel_vx, rel_vy)

        if speed > 0.0001:
            effective_density = AIR_DENSITY * density_multiplier
            drag_force = (
                0.5
                * effective_density
                * self.drag_coefficient
                * self.area_m2
                * speed
                * speed
            )
            drag_acceleration = drag_force / max(0.0001, self.mass_kg)
            ax = -drag_acceleration * rel_vx / speed
            ay = (
                GRAVITY_MPS2 * gravity_scale
                - drag_acceleration * rel_vy / speed
            )
        else:
            ax = 0.0
            ay = GRAVITY_MPS2 * gravity_scale

        # Yarı örtük Euler yöntemi
        self.vx_mps += ax * dt
        self.vy_mps += ay * dt
        self.x_m += self.vx_mps * dt
        self.y_m += self.vy_mps * dt

    @property
    def x_px(self) -> float:
        return m_to_px(self.x_m)

    @property
    def y_px(self) -> float:
        return m_to_px(self.y_m)


