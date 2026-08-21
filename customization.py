"""Card-based selection UI for the existing simulation content."""

from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame

from config import (
    COMPACT_VIEW_RECT,
    CYCLE_PHASE_LABELS,
    FORMATION_OPTIONS,
    HEIGHT,
    MODE_BUTTONS,
    PALETTE_MAP,
    PALETTE_OPTIONS,
    PATTERN_OPTIONS,
    WIDTH,
)
from environment import create_stars, render_scene
from fireworks import Shell
from formations import create_launch_requests


CUSTOMIZE_WIDTH = 900
CUSTOMIZE_HEIGHT = 600
CUSTOMIZE_SIZE = (CUSTOMIZE_WIDTH, CUSTOMIZE_HEIGHT)

CUSTOMIZE_TABS = (
    ("environments", "Ortamlar"),
    ("patterns", "Havai Fişekler"),
    ("palettes", "Paletler"),
    ("formations", "Formasyonlar"),
)

TAB_RECTS = {
    key: pygame.Rect(34 + index * 207, 102, 190, 42)
    for index, (key, _) in enumerate(CUSTOMIZE_TABS)
}
RETURN_RECT = pygame.Rect(698, 536, 168, 42)

CARD_WIDTH = 196
CARD_HEIGHT = 146
CARD_GAP_X = 16
CARD_GAP_Y = 16
CARD_COLUMNS = 4
CARD_START_X = 34
CARD_START_Y = 164


def options_for_tab(tab: str) -> tuple[tuple[str, str], ...]:
    """Return selectable values and labels from the existing config sources."""
    if tab == "environments":
        return tuple(
            (key, CYCLE_PHASE_LABELS[key])
            for key in MODE_BUTTONS
        )
    if tab == "patterns":
        return tuple((name, name) for name in PATTERN_OPTIONS)
    if tab == "palettes":
        return tuple((name, name) for name in PALETTE_OPTIONS)
    return tuple((name, name) for name in FORMATION_OPTIONS)


def card_rects(tab: str) -> dict[str, pygame.Rect]:
    """Calculate the compact two-row grid for a tab's real options."""
    return {
        value: pygame.Rect(
            CARD_START_X + (index % CARD_COLUMNS) * (CARD_WIDTH + CARD_GAP_X),
            CARD_START_Y + (index // CARD_COLUMNS) * (CARD_HEIGHT + CARD_GAP_Y),
            CARD_WIDTH,
            CARD_HEIGHT,
        )
        for index, (value, _) in enumerate(options_for_tab(tab))
    }


@lru_cache(maxsize=None)
def _environment_preview_surface(
    value: str,
    size: tuple[int, int],
) -> pygame.Surface:
    """Render one fixed snapshot through the real environment pipeline."""
    logical_scene = pygame.Surface((WIDTH, HEIGHT))
    render_scene(logical_scene, value, create_stars(165), 4.0)
    compact_view = logical_scene.subsurface(COMPACT_VIEW_RECT)
    return pygame.transform.smoothscale(compact_view, size)


def _draw_environment_preview(
    surface: pygame.Surface,
    rect: pygame.Rect,
    value: str,
) -> None:
    surface.blit(_environment_preview_surface(value, rect.size), rect)


@lru_cache(maxsize=None)
def _pattern_preview_surface(
    value: str,
    size: tuple[int, int],
) -> pygame.Surface:
    """Build a deterministic static snapshot from the real burst factories."""
    preview = pygame.Surface(size, pygame.SRCALPHA)
    if value == "Rastgele":
        samples = ("Şakayık", "Halka", "Palmiye")
        sample_width = (size[0] - 8) // len(samples)
        for index, sample in enumerate(samples):
            sample_surface = _pattern_preview_surface(
                sample,
                (sample_width, size[1] - 8),
            )
            preview.blit(sample_surface, (4 + index * sample_width, 4))
        return preview

    palette = PALETTE_MAP["Safir"]
    assert palette is not None
    random_state = random.getstate()
    try:
        random.seed(4100 + PATTERN_OPTIONS.index(value))
        shell = Shell(450.0, palette, "Safir", value, 1.0, 90.0, 52.0)
        stars, _ = shell.burst()
    finally:
        random.setstate(random_state)

    for _ in range(18):
        for star in stars:
            star.update(0.05, 0.0, 1.0, 0.0)

    all_points = [
        (point.x, point.y)
        for star in stars
        for point in star.history
    ] + [
        (star.body.x_px, star.body.y_px)
        for star in stars
    ]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    scale = min(
        (size[0] - 12) / max(1.0, max_x - min_x),
        (size[1] - 12) / max(1.0, max_y - min_y),
    )
    offset_x = (size[0] - (max_x - min_x) * scale) * 0.5
    offset_y = (size[1] - (max_y - min_y) * scale) * 0.5

    for star in stars:
        raw_points = [
            (point.x, point.y)
            for point in star.history
        ] + [(star.body.x_px, star.body.y_px)]
        points = [
            (
                offset_x + (x - min_x) * scale,
                offset_y + (y - min_y) * scale,
            )
            for x, y in raw_points
        ]
        color = star.color()
        if len(points) >= 2:
            pygame.draw.aalines(preview, (*color, 150), False, points)
        pygame.draw.circle(preview, (*color, 235), points[-1], 1)
    return preview


def _draw_pattern_preview(
    surface: pygame.Surface,
    rect: pygame.Rect,
    value: str,
) -> None:
    surface.blit(_pattern_preview_surface(value, rect.size), rect)


def _draw_palette_preview(
    surface: pygame.Surface,
    rect: pygame.Rect,
    value: str,
) -> None:
    palette = PALETTE_MAP[value]
    if palette is None:
        palette = tuple(
            PALETTE_MAP[name][index % 3]
            for index, name in enumerate(PALETTE_OPTIONS[1:])
            if PALETTE_MAP[name] is not None
        )
    swatch_count = len(palette)
    swatch_width = 20 if swatch_count > 3 else 42
    gap = 5 if swatch_count > 3 else 8
    total_width = swatch_width * swatch_count + gap * (swatch_count - 1)
    x = rect.centerx - total_width // 2
    for color in palette:
        swatch = pygame.Rect(x, rect.centery - 18, swatch_width, 36)
        pygame.draw.rect(surface, color, swatch, border_radius=9)
        pygame.draw.rect(surface, (255, 255, 255, 35), swatch, 1, border_radius=9)
        x += swatch_width + gap


@lru_cache(maxsize=None)
def _formation_preview_data(
    value: str,
) -> tuple[tuple[float, float, float, float], ...]:
    """Sample the real request builder without retaining random state changes."""
    random_state = random.getstate()
    try:
        random.seed(7300 + FORMATION_OPTIONS.index(value))
        requests = create_launch_requests(
            value,
            90.0,
            52.0,
            1.0,
            "Şakayık",
            "Safir",
        )
    finally:
        random.setstate(random_state)
    return tuple(
        (request.x_px, request.angle_deg, request.height_m, request.delay)
        for request in requests
    )


def _draw_formation_preview(
    surface: pygame.Surface,
    rect: pygame.Rect,
    value: str,
) -> None:
    bottom = rect.bottom - 10
    if value == "Yelpaze":
        center_x = rect.centerx
        launch_offsets = (-12, -6, 0, 6, 12)
        endpoint_offsets = (-62, -34, 0, 34, 62)
        endpoint_heights = (42, 26, 18, 26, 42)
        for index, (launch_offset, endpoint_offset, endpoint_height) in enumerate(
            zip(launch_offsets, endpoint_offsets, endpoint_heights)
        ):
            start = (center_x + launch_offset, bottom)
            end = (center_x + endpoint_offset, rect.top + endpoint_height)
            distance_from_center = abs(index - 2)
            color = (
                194 - distance_from_center * 8,
                200 - distance_from_center * 4,
                218,
            )
            pygame.draw.aaline(surface, color, start, end)
            pygame.draw.circle(surface, (236, 201, 126), end, 3)
            pygame.draw.circle(surface, color, start, 2)
        return

    requests = _formation_preview_data(value)
    max_delay = max((request[3] for request in requests), default=0.0)
    for x_px, angle_deg, height_m, delay in requests:
        start_x = rect.left + 12 + (x_px - 100.0) / 730.0 * (rect.width - 24)
        length = 38.0 + (height_m - 30.0) / 45.0 * 22.0
        angle = math.radians(angle_deg)
        end = (
            start_x + math.cos(angle) * length,
            bottom - math.sin(angle) * length,
        )
        delay_ratio = delay / max(0.01, max_delay)
        color = (
            int(116 + 78 * (1.0 - delay_ratio)),
            int(145 + 55 * (1.0 - delay_ratio)),
            218,
        )
        pygame.draw.aaline(surface, color, (start_x, bottom), end)
        pygame.draw.circle(surface, (236, 201, 126), end, 3)
        pygame.draw.circle(surface, color, (start_x, bottom), 2)


def _draw_preview(
    surface: pygame.Surface,
    tab: str,
    value: str,
    rect: pygame.Rect,
) -> None:
    preview = pygame.Rect(rect.left + 12, rect.top + 12, rect.width - 24, 84)
    pygame.draw.rect(surface, (8, 13, 27), preview, border_radius=9)
    if tab == "environments":
        _draw_environment_preview(surface, preview, value)
    elif tab == "patterns":
        _draw_pattern_preview(surface, preview, value)
    elif tab == "palettes":
        _draw_palette_preview(surface, preview, value)
    else:
        _draw_formation_preview(surface, preview, value)


def draw_customization_screen(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    mouse: tuple[int, int],
    active_tab: str,
    selected_environment: str,
    selected_pattern: str,
    selected_palette: str,
    selected_formation: str,
) -> None:
    """Draw the customization screen without running card simulations."""
    surface.fill((8, 12, 24))
    pygame.draw.circle(surface, (20, 36, 67), (790, 55), 180)

    title = fonts["custom_title"].render("Gökyüzünü Özelleştir", True, (239, 243, 252))
    surface.blit(title, (34, 27))
    subtitle = fonts["small"].render(
        "Gösterinin görünümünü ve davranışını seç.",
        True,
        (148, 163, 190),
    )
    surface.blit(subtitle, (35, 67))

    for key, label in CUSTOMIZE_TABS:
        rect = TAB_RECTS[key]
        active = key == active_tab
        hovered = rect.collidepoint(mouse)
        pygame.draw.rect(
            surface,
            (29, 40, 64) if active else (17, 25, 43) if hovered else (13, 20, 36),
            rect,
            border_radius=10,
        )
        pygame.draw.rect(
            surface,
            (88, 112, 157) if active else (42, 55, 81),
            rect,
            1,
            border_radius=10,
        )
        text = fonts["small_bold"].render(label, True, (223, 230, 243))
        surface.blit(text, text.get_rect(center=rect.center))

    selected_by_tab = {
        "environments": selected_environment,
        "patterns": selected_pattern,
        "palettes": selected_palette,
        "formations": selected_formation,
    }
    selected = selected_by_tab[active_tab]
    rects = card_rects(active_tab)
    labels = dict(options_for_tab(active_tab))

    for value, rect in rects.items():
        is_selected = value == selected
        hovered = rect.collidepoint(mouse)
        pygame.draw.rect(
            surface,
            (24, 34, 54) if is_selected else (18, 27, 44) if hovered else (14, 22, 38),
            rect,
            border_radius=13,
        )
        pygame.draw.rect(
            surface,
            (100, 126, 172) if is_selected else (39, 53, 79),
            rect,
            2 if is_selected else 1,
            border_radius=13,
        )
        _draw_preview(surface, active_tab, value, rect)
        label = fonts["button"].render(labels[value], True, (224, 231, 243))
        surface.blit(label, (rect.left + 14, rect.bottom - 37))
        if is_selected:
            check = fonts["small_bold"].render("✓", True, (178, 203, 239))
            surface.blit(check, check.get_rect(center=(rect.right - 19, rect.bottom - 25)))

    hovered = RETURN_RECT.collidepoint(mouse)
    pygame.draw.rect(
        surface,
        (45, 70, 111) if hovered else (35, 56, 91),
        RETURN_RECT,
        border_radius=11,
    )
    pygame.draw.rect(surface, (92, 119, 166), RETURN_RECT, 1, border_radius=11)
    text = fonts["small_bold"].render("Gökyüzüne Dön", True, (236, 241, 250))
    surface.blit(text, text.get_rect(center=RETURN_RECT.center))
