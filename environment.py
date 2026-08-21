"""Sky, city, scenery, and day/night cycle rendering."""

import math
import random

import pygame

from common import clamp, mix
from config import *
from graphics import draw_gradient, draw_radial_glow

def create_stars(count: int) -> list[dict[str, float]]:
    rng = random.Random(42)
    return [
        {
            "x": rng.randint(15, WIDTH - 15),
            "y": rng.randint(90, 510),
            "radius": rng.choice((1, 1, 1, 1, 2)),
            "phase": rng.uniform(0.0, math.tau),
            "speed": rng.uniform(0.4, 1.4),
            "cross": rng.random() > 0.92,
        }
        for _ in range(count)
    ]


def draw_stars(surface: pygame.Surface, stars: list[dict[str, float]], time_s: float) -> None:
    for star in stars:
        pulse = (math.sin(time_s * star["speed"] + star["phase"]) + 1.0) * 0.5
        brightness = int(150 + 95 * pulse)
        x, y = int(star["x"]), int(star["y"])
        pygame.draw.circle(
            surface,
            (brightness, brightness, min(255, brightness + 10)),
            (x, y),
            int(star["radius"]),
        )
        if star["cross"] and pulse > 0.68:
            a = int(75 + 90 * pulse)
            layer = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.aaline(layer, (220, 230, 255, a), (7, 1), (7, 13))
            pygame.draw.aaline(layer, (220, 230, 255, a), (1, 7), (13, 7))
            surface.blit(layer, (x - 7, y - 7))


def draw_cloud(
    surface: pygame.Surface,
    x: float,
    y: float,
    scale: float,
    top: tuple[int, int, int, int],
    shadow: tuple[int, int, int, int],
) -> None:
    cloud = pygame.Surface((int(220 * scale), int(105 * scale)), pygame.SRCALPHA)
    pygame.draw.ellipse(cloud, shadow, (int(25*scale), int(56*scale), int(168*scale), int(32*scale)))
    pygame.draw.circle(cloud, top, (int(53*scale), int(57*scale)), int(31*scale))
    pygame.draw.circle(cloud, top, (int(91*scale), int(39*scale)), int(41*scale))
    pygame.draw.circle(cloud, top, (int(136*scale), int(46*scale)), int(36*scale))
    pygame.draw.circle(cloud, top, (int(171*scale), int(60*scale)), int(27*scale))
    pygame.draw.ellipse(cloud, top, (int(33*scale), int(52*scale), int(158*scale), int(39*scale)))
    surface.blit(cloud, (int(x), int(y)))


def draw_bird(
    surface: pygame.Surface,
    x: float,
    y: float,
    scale: float,
    color: tuple[int, int, int],
    flap: float,
) -> None:
    q = 3
    bird = pygame.Surface((92*q, 54*q), pygame.SRCALPHA)
    def p(px: float, py: float) -> tuple[int, int]:
        return int(px*q), int(py*q)
    body = (*color, 255)
    dark = (max(0,color[0]-16), max(0,color[1]-16), max(0,color[2]-16), 235)
    pygame.draw.polygon(bird, dark, [p(39,25), p(24,34+flap*4), p(16,42+flap*3), p(35,35), p(51,27)])
    pygame.draw.polygon(bird, body, [p(37,24), p(25,8-flap*7), p(38,13+flap*2), p(55,23), p(49,28)])
    pygame.draw.polygon(bird, body, [p(27,25), p(12,18), p(19,26), p(11,34), p(30,29)])
    pygame.draw.ellipse(bird, body, (25*q,21*q,40*q,13*q))
    pygame.draw.circle(bird, body, p(65,24), 6*q)
    pygame.draw.polygon(bird, body, [p(69,22), p(79,25), p(69,27)])
    bird = pygame.transform.smoothscale(bird, (max(1,int(92*scale)), max(1,int(54*scale))))
    surface.blit(bird, bird.get_rect(center=(int(x), int(y))))


def draw_birds(
    surface: pygame.Surface,
    data: list[tuple[float, float, float, float, float]],
    color: tuple[int, int, int],
    time_s: float,
) -> None:
    travel = WIDTH + 300
    for start_x, start_y, scale, speed, phase in data:
        x = ((start_x + time_s * speed + 150) % travel) - 150
        y = start_y + math.sin(time_s * 0.75 + phase) * 3.0
        draw_bird(surface, x, y, scale, color, math.sin(time_s * 4.1 + phase))


def draw_haze(
    surface: pygame.Surface,
    y: int,
    color: tuple[int, int, int],
    height: int,
    max_alpha: int,
) -> None:
    layer = pygame.Surface((WIDTH, height), pygame.SRCALPHA)
    for py in range(height):
        d = abs(py - height / 2)
        ratio = max(0.0, 1.0 - d / max(1.0, height / 2))
        pygame.draw.line(layer, (*color, int(max_alpha * ratio)), (0, py), (WIDTH, py))
    surface.blit(layer, (0, y))


def draw_mountains(surface: pygame.Surface, mode: str) -> None:
    colors = {
        "day": ((112,153,178), (76,117,139), (45,76,91)),
        "sunset": ((117,68,126), (74,48,91), (43,34,62)),
        "night": ((28,35,67), (19,26,49), (11,17,31)),
    }[mode]
    far = [(0,565),(80,520),(160,550),(260,472),(360,545),(465,490),(560,552),(670,478),(780,552),(900,486),(1010,548),(1130,472),(1280,550),(1280,720),(0,720)]
    mid = [(0,600),(125,535),(245,595),(375,515),(510,600),(645,525),(785,595),(930,515),(1070,600),(1190,530),(1280,585),(1280,720),(0,720)]
    near = [(0,630),(150,570),(310,630),(475,555),(650,635),(825,565),(1000,630),(1165,550),(1280,610),(1280,720),(0,720)]
    pygame.draw.polygon(surface, colors[0], far)
    pygame.draw.polygon(surface, colors[1], mid)
    pygame.draw.polygon(surface, colors[2], near)


def draw_day(surface: pygame.Surface, time_s: float) -> None:
    draw_gradient(surface, [(0,(24,91,182)),(.28,(45,135,215)),(.58,(105,187,234)),(.82,(181,223,244)),(1,(228,241,245))])
    draw_radial_glow(surface, 1065, 142, (255,226,139), 145, 72)
    pygame.draw.circle(surface, (255,230,132), (1065,142), 48)
    for raw_x, y, scale in [(-180+time_s*13,135,.92),(290+time_s*8,225,.65),(720+time_s*6,105,.72)]:
        x = (raw_x % (WIDTH+300)) - 220
        draw_cloud(surface, x, y, scale, (247,251,255,225), (124,170,199,105))
    draw_birds(surface, DAY_BIRDS, (31,43,52), time_s)
    draw_haze(surface, 450, (211,232,239), 150, 75)
    draw_mountains(surface, "day")


def draw_sunset(surface: pygame.Surface, time_s: float) -> None:
    draw_gradient(surface, [(0,(28,20,72)),(.18,(57,31,105)),(.38,(120,52,135)),(.57,(202,76,128)),(.76,(247,123,89)),(.90,(255,177,101)),(1,(255,216,148))])
    draw_radial_glow(surface, 1045, 447, (255,121,74), 210, 78)
    draw_radial_glow(surface, 1045, 447, (255,221,145), 112, 92)
    pygame.draw.circle(surface, (255,219,133), (1045,447), 55)
    draw_haze(surface, 370, (255,184,131), 190, 88)
    for raw_x, y, scale in [(-170+time_s*8,125,.95),(340+time_s*5,235,.70),(760+time_s*4,105,.78)]:
        x = (raw_x % (WIDTH+320)) - 230
        draw_cloud(surface, x, y, scale, (174,90,147,170), (65,39,96,130))
    streaks = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.ellipse(streaks, (255,164,142,85), (65,315,360,24))
    pygame.draw.ellipse(streaks, (251,135,142,68), (555,345,445,28))
    surface.blit(streaks, (0,0))
    draw_birds(surface, SUNSET_BIRDS, (45,28,51), time_s)
    draw_mountains(surface, "sunset")


def draw_night(surface: pygame.Surface, stars: list[dict[str,float]], time_s: float) -> None:
    draw_gradient(surface, [(0,(3,6,25)),(.45,(7,12,43)),(.78,(12,18,58)),(1,(20,27,70))])
    draw_stars(surface, stars, time_s)
    draw_radial_glow(surface, 1080, 135, (180,195,255), 110, 42)
    pygame.draw.circle(surface, (250,244,207), (1080,135), 48)
    pygame.draw.circle(surface, (8,13,44), (1101,117), 46)
    draw_haze(surface, 470, (76,92,149), 120, 35)
    draw_mountains(surface, "night")



def draw_dawn(surface: pygame.Surface, time_s: float) -> None:
    """Gece ile gündüz arasında serin tonlu gün doğumu sahnesi çizer."""
    draw_gradient(
        surface,
        [
            (0.00, (19, 25, 67)),
            (0.22, (48, 58, 111)),
            (0.48, (128, 90, 142)),
            (0.70, (227, 132, 128)),
            (0.88, (255, 184, 128)),
            (1.00, (255, 224, 174)),
        ],
    )

    sun_x = 220
    sun_y = 455
    draw_radial_glow(surface, sun_x, sun_y, (255, 177, 112), 205, 72)
    draw_radial_glow(surface, sun_x, sun_y, (255, 226, 162), 108, 88)
    pygame.draw.circle(surface, (255, 221, 151), (sun_x, sun_y), 50)

    draw_haze(surface, 372, (255, 194, 151), 190, 78)

    for raw_x, y, scale in [
        (-220 + time_s * 7, 132, .88),
        (290 + time_s * 4.5, 220, .66),
        (760 + time_s * 3.5, 108, .74),
    ]:
        x = (raw_x % (WIDTH + 330)) - 235
        draw_cloud(
            surface,
            x,
            y,
            scale,
            (184, 147, 185, 155),
            (71, 66, 119, 115),
        )

    streaks = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.ellipse(streaks, (255, 176, 151, 72), (120, 330, 360, 22))
    pygame.draw.ellipse(streaks, (194, 142, 186, 58), (650, 290, 380, 25))
    surface.blit(streaks, (0, 0))

    draw_birds(surface, DAY_BIRDS, (47, 43, 61), time_s)
    draw_mountains(surface, "sunset")


def render_scene(
    target: pygame.Surface,
    mode: str,
    stars: list[dict[str, float]],
    time_s: float,
) -> None:
    """Seçilen gökyüzü ve şehir katmanını tek yüzeye çizer."""
    if mode == "day":
        draw_day(target, time_s)
    elif mode == "sunset":
        draw_sunset(target, time_s)
    elif mode == "night":
        draw_night(target, stars, time_s)
    else:
        draw_dawn(target, time_s)

    draw_city(target, mode)


def smoothstep(value: float) -> float:
    value = clamp(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def scene_visibility(mode: str) -> float:
    if mode == "day":
        return 0.50
    if mode == "sunset":
        return 0.80
    if mode == "dawn":
        return 0.66
    return 1.0


def cycle_state(
    elapsed: float,
    total_duration: float,
) -> tuple[str, str, float]:
    """Zaman döngüsündeki mevcut ve sonraki sahneyi hesaplar."""
    total_duration = max(4.0, total_duration)
    phase_duration = total_duration / len(CYCLE_PHASES)
    phase_position = (elapsed % total_duration) / phase_duration
    phase_index = int(phase_position) % len(CYCLE_PHASES)
    local_progress = phase_position - math.floor(phase_position)

    current_mode = CYCLE_PHASES[phase_index]
    next_mode = CYCLE_PHASES[(phase_index + 1) % len(CYCLE_PHASES)]

    return current_mode, next_mode, smoothstep(local_progress)


def draw_cycle_scene(
    screen: pygame.Surface,
    first_scene: pygame.Surface,
    second_scene: pygame.Surface,
    stars: list[dict[str, float]],
    time_s: float,
    cycle_elapsed: float,
    cycle_duration: float,
) -> tuple[str, float]:
    """Sahneleri yumuşak alfa geçişiyle birbirine bağlar."""
    current_mode, next_mode, blend = cycle_state(
        cycle_elapsed,
        cycle_duration,
    )

    render_scene(first_scene, current_mode, stars, time_s)
    render_scene(second_scene, next_mode, stars, time_s)

    screen.blit(first_scene, (0, 0))

    second_scene.set_alpha(int(255 * blend))
    screen.blit(second_scene, (0, 0))
    second_scene.set_alpha(255)

    current_visibility = scene_visibility(current_mode)
    next_visibility = scene_visibility(next_mode)
    visibility = current_visibility + (
        next_visibility - current_visibility
    ) * blend

    visible_mode = current_mode if blend < 0.5 else next_mode
    return visible_mode, visibility

def draw_city(surface: pygame.Surface, mode: str) -> None:
    if mode == "day":
        building, top, ground, window, lights = (47,68,86), (77,101,120), (28,40,50), (92,123,143), False
    elif mode == "sunset":
        building, top, ground, window, lights = (28,24,44), (53,43,69), (17,15,28), (255,184,82), True
    elif mode == "dawn":
        building, top, ground, window, lights = (36,38,60), (67,67,91), (24,25,40), (244,169,91), True
    else:
        building, top, ground, window, lights = (6,8,16), (21,26,42), (2,4,10), (241,190,72), True

    for idx, (x,y,w,h) in enumerate(BUILDINGS):
        pygame.draw.rect(surface, building, (x,y,w,h))
        pygame.draw.line(surface, top, (x,y), (x+w,y), 2)
        if idx in (3,7,10):
            ax = x+w//2
            pygame.draw.line(surface, top, (ax,y), (ax,y-26), 2)
            pygame.draw.circle(surface, (218,63,73), (ax,y-28), 3)
        for wx in range(x+14, x+w-10, 24):
            for wy in range(y+18, y+h-10, 28):
                n = wx//24 + wy//28 + idx
                if (n%3 != 0 if lights else n%2 == 0):
                    pygame.draw.rect(surface, window, (wx,wy,7,11), border_radius=1)

    pygame.draw.rect(surface, ground, (0,CITY_BASE_Y,WIDTH,HEIGHT-CITY_BASE_Y))


# ============================================================
# GELİŞMİŞ SİMÜLASYON AYARLARI
# ============================================================

