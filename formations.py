"""Launch requests, selectable options, and show formations."""

import math
import random
from dataclasses import dataclass

from common import clamp
from config import *
from fireworks import Shell

@dataclass
class LaunchRequest:
    delay: float
    x_px: float
    angle_deg: float
    height_m: float
    power: float
    pattern_name: str
    palette_name: str



def cycle_option(
    options: tuple[str, ...],
    current: str,
    direction: int = 1,
) -> str:
    index = options.index(current)
    return options[(index + direction) % len(options)]


def resolve_pattern(selected: str) -> str:
    return (
        random.choice(Shell.PATTERNS)
        if selected == "Rastgele"
        else selected
    )


def resolve_palette(selected: str) -> tuple[
    tuple[
        tuple[int, int, int],
        tuple[int, int, int],
        tuple[int, int, int],
    ],
    str,
]:
    if selected == "Rastgele":
        name = random.choice(PALETTE_OPTIONS[1:])
        palette = PALETTE_MAP[name]
        assert palette is not None
        return palette, name

    palette = PALETTE_MAP[selected]
    assert palette is not None
    return palette, selected


def create_launch_requests(
    formation: str,
    angle_deg: float,
    height_m: float,
    power: float,
    pattern_selected: str,
    palette_selected: str,
) -> list[LaunchRequest]:
    requests: list[LaunchRequest] = []

    def add(
        delay: float,
        x_px: float,
        angle: float,
        height: float,
        pattern_name: str | None = None,
        palette_name: str | None = None,
    ) -> None:
        requests.append(
            LaunchRequest(
                delay=max(0.0, delay),
                x_px=clamp(x_px, 100.0, FIREWORK_AREA_RIGHT - 70.0),
                angle_deg=clamp(angle, MIN_ANGLE_DEG, MAX_ANGLE_DEG),
                height_m=clamp(height, MIN_HEIGHT_M, MAX_HEIGHT_M),
                power=clamp(power, MIN_EXPLOSION_POWER, MAX_EXPLOSION_POWER),
                pattern_name=pattern_name or pattern_selected,
                palette_name=palette_name or palette_selected,
            )
        )

    if formation == "Tekli":
        add(
            0.0,
            random.uniform(180.0, FIREWORK_AREA_RIGHT - 150.0),
            angle_deg,
            height_m,
        )

    elif formation == "İkili":
        center = random.uniform(350.0, 560.0)
        add(0.0, center - 125.0, angle_deg - 5.0, height_m - 3.0)
        add(0.0, center + 125.0, angle_deg + 5.0, height_m + 3.0)

    elif formation == "Yelpaze":
        center = random.uniform(390.0, 505.0)
        for index, angle_offset in enumerate((-18.0, -9.0, 0.0, 9.0, 18.0)):
            add(
                index * 0.035,
                center + (index - 2) * 16.0,
                angle_deg + angle_offset,
                height_m + (2 - abs(index - 2)) * 2.0,
            )

    elif formation == "Dalga":
        for index in range(6):
            x = 130.0 + index * 130.0
            add(
                index * 0.16,
                x,
                angle_deg + (index - 2.5) * 2.0,
                height_m + math.sin(index * 0.85) * 6.0,
            )

    else:  # Final
        for index in range(8):
            x = 110.0 + index * 100.0
            add(
                (index % 4) * 0.10,
                x,
                angle_deg + random.uniform(-13.0, 13.0),
                height_m + random.uniform(-10.0, 10.0),
                random.choice(PATTERN_OPTIONS[1:]),
                random.choice(PALETTE_OPTIONS[1:]),
            )

        for index in range(3):
            add(
                0.58 + index * 0.12,
                300.0 + index * 145.0,
                angle_deg + (index - 1) * 8.0,
                min(MAX_HEIGHT_M, height_m + 10.0),
                "Krizantem",
                random.choice(PALETTE_OPTIONS[1:]),
            )

    return requests


def spawn_shell_from_request(
    request: LaunchRequest,
    shells: list[Shell],
) -> tuple[bool, dict[str, object]]:
    if len(shells) >= MAX_SHELLS:
        return False, {}

    pattern = resolve_pattern(request.pattern_name)
    palette, palette_name = resolve_palette(request.palette_name)

    shells.append(
        Shell(
            request.x_px,
            palette,
            palette_name,
            pattern,
            request.power,
            request.angle_deg,
            request.height_m,
        )
    )

    return True, {
        "pattern": pattern,
        "palette": palette_name,
        "height": request.height_m,
        "angle": request.angle_deg,
        "power": request.power,
    }


