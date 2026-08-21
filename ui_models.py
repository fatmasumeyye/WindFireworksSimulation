"""UI state models and the existing slider definitions."""

from dataclasses import dataclass

import pygame

from common import clamp
from config import *

@dataclass
class Slider:
    name: str
    label: str
    rect: pygame.Rect
    minimum: float
    maximum: float
    value: float
    step: float
    suffix: str = ""

    def normalized(self) -> float:
        return clamp(
            (self.value - self.minimum)
            / max(0.0001, self.maximum - self.minimum),
            0.0,
            1.0,
        )

    def set_from_x(self, mouse_x: int) -> None:
        ratio = clamp(
            (mouse_x - self.rect.left)
            / max(1, self.rect.width),
            0.0,
            1.0,
        )
        raw = self.minimum + ratio * (self.maximum - self.minimum)
        self.value = clamp(
            round(raw / self.step) * self.step,
            self.minimum,
            self.maximum,
        )

    def handle_x(self) -> int:
        return int(self.rect.left + self.normalized() * self.rect.width)


SLIDERS = {
    "height": Slider(
        "height",
        "Patlama yüksekliği",
        pygame.Rect(952, 202, 270, 7),
        MIN_HEIGHT_M,
        MAX_HEIGHT_M,
        52.0,
        1.0,
        " m",
    ),
    "angle": Slider(
        "angle",
        "Fırlatma açısı",
        pygame.Rect(952, 258, 270, 7),
        MIN_ANGLE_DEG,
        MAX_ANGLE_DEG,
        90.0,
        1.0,
        "°",
    ),
    "power": Slider(
        "power",
        "Patlama gücü",
        pygame.Rect(952, 314, 270, 7),
        MIN_EXPLOSION_POWER,
        MAX_EXPLOSION_POWER,
        1.00,
        0.05,
        "",
    ),
    "wind": Slider(
        "wind",
        "Rüzgâr hızı",
        pygame.Rect(952, 202, 270, 7),
        MIN_WIND_MPS,
        MAX_WIND_MPS,
        0.0,
        0.5,
        " m/sn",
    ),
    "precipitation": Slider(
        "precipitation",
        "Yağış şiddeti",
        pygame.Rect(952, 362, 270, 7),
        0.0,
        1.0,
        0.35,
        0.05,
        "",
    ),
}


# ============================================================
# FİZİK
# ============================================================

