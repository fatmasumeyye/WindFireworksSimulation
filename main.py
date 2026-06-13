"""
Rüzgâr, yer çekimi ve parçacık hareketlerine bağlı etkileşimli
havai fişek gösterisi simülasyonu.

Program; yarı örtük Euler integrasyonu, karesel hava sürükleme modeli,
rüzgâr, yağış, zaman döngüsü ve kullanıcı tarafından değiştirilebilen
fırlatma parametrelerini tek bir Pygame uygulamasında birleştirir.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass, field

try:
    import pygame
except ModuleNotFoundError as error:
    if error.name != "pygame":
        raise

    print(
        "Program başlatılamadı: pygame-ce kütüphanesi bulunamadı.\n"
        "Proje klasöründe şu komutu çalıştırın:\n"
        "python -m pip install -r requirements.txt"
    )
    raise SystemExit(1) from None


# ============================================================
# PENCERE VE FİZİK SABİTLERİ
# ============================================================

WIDTH = 1280
HEIGHT = 720
FPS = 60
CITY_BASE_Y = HEIGHT - 36
LAUNCH_Y = CITY_BASE_Y - 6

# Simülasyon iç hesaplarını metre ve saniye ile yapar.
PIXELS_PER_METER = 7.5
GRAVITY_MPS2 = 9.81
AIR_DENSITY = 1.225

MIN_WIND_MPS = -8.0
MAX_WIND_MPS = 8.0
WIND_STEP_MPS = 1.0

MIN_EXPLOSION_POWER = 0.60
MAX_EXPLOSION_POWER = 1.40
DEFAULT_EXPLOSION_POWER = 1.00

CYCLE_SPEEDS = {
    "slow": 120.0,
    "normal": 60.0,
    "fast": 30.0,
}
CYCLE_PHASES = ("day", "sunset", "night", "dawn")
CYCLE_PHASE_LABELS = {
    "day": "Gündüz",
    "sunset": "Gün Batımı",
    "night": "Gece",
    "dawn": "Gün Doğumu",
}

MAX_SHELLS = 8
MAX_STARS = 3200

WHITE = (244, 247, 255)
PANEL = (12, 17, 32)
PANEL_BORDER = (58, 75, 111)
ACTIVE = (44, 128, 214)
PASSIVE = (28, 36, 58)
HOVER = (49, 64, 94)
DANGER = (160, 64, 76)

PALETTES = [
    ((255, 74, 92), (255, 188, 80), (255, 250, 224)),
    ((76, 177, 255), (125, 98, 255), (238, 248, 255)),
    ((255, 83, 185), (181, 94, 255), (255, 236, 250)),
    ((76, 232, 164), (63, 181, 255), (235, 255, 245)),
    ((255, 216, 91), (255, 135, 57), (255, 250, 220)),
    ((239, 246, 255), (155, 202, 255), (255, 255, 255)),
]

BUILDINGS = [
    (0, 620, 90, 65), (90, 580, 110, 105), (200, 605, 80, 80),
    (280, 540, 115, 145), (395, 585, 95, 100), (490, 560, 130, 125),
    (620, 610, 90, 75), (710, 530, 105, 155), (815, 575, 125, 110),
    (940, 615, 85, 70), (1025, 550, 120, 135), (1145, 590, 135, 95),
]

MODE_BUTTONS = {
    "day": pygame.Rect(748, 28, 145, 50),
    "sunset": pygame.Rect(903, 28, 170, 50),
    "night": pygame.Rect(1083, 28, 145, 50),
}

CONTROL_PANEL_RECT = pygame.Rect(16, 592, 1248, 112)

CONTROL_BUTTONS = {
    "launch": pygame.Rect(30, 610, 110, 38),
    "show": pygame.Rect(148, 610, 150, 38),
    "pause": pygame.Rect(306, 610, 105, 38),
    "reset": pygame.Rect(419, 610, 95, 38),
    "wind_down": pygame.Rect(536, 610, 42, 38),
    "wind_up": pygame.Rect(686, 610, 42, 38),
}

POWER_SLIDER = pygame.Rect(790, 625, 190, 8)
POWER_SLIDER_HITBOX = pygame.Rect(760, 603, 245, 42)

CYCLE_BUTTON = pygame.Rect(30, 658, 170, 32)
CYCLE_SPEED_BUTTONS = {
    "slow": pygame.Rect(210, 658, 76, 32),
    "normal": pygame.Rect(294, 658, 82, 32),
    "fast": pygame.Rect(384, 658, 76, 32),
}

DAY_BIRDS = [
    (350, 185, 0.50, 16, 0.0),
    (410, 158, 0.64, 14, 1.3),
    (475, 195, 0.44, 18, 2.5),
]

SUNSET_BIRDS = [
    (300, 235, 0.45, 12, 0.4),
    (365, 205, 0.58, 11, 1.7),
    (430, 238, 0.40, 14, 2.9),
]


# ============================================================
# TEMEL YARDIMCILAR
# ============================================================

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = clamp(t, 0.0, 1.0)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def px_to_m(value: float) -> float:
    return value / PIXELS_PER_METER


def m_to_px(value: float) -> float:
    return value * PIXELS_PER_METER


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

FIREWORK_AREA_RIGHT = 900
RIGHT_PANEL = pygame.Rect(918, 96, 346, 480)

# Alt araç çubuğu daha ince tutulur; böylece şehir ve gösteri alanı kapanmaz.
BOTTOM_BAR = pygame.Rect(16, 638, 888, 66)

# Karşılama ekranı ve gezinme düğmeleri.
WELCOME_BUTTONS = {
    "start": pygame.Rect(470, 332, 340, 50),
    "help": pygame.Rect(470, 394, 340, 46),
    "physics": pygame.Rect(470, 450, 340, 46),
    "exit": pygame.Rect(470, 506, 340, 46),
}
WELCOME_MODAL_RECT = pygame.Rect(305, 154, 670, 410)
WELCOME_MODAL_CLOSE = pygame.Rect(565, 514, 150, 38)

HOME_BUTTON = pygame.Rect(24, 100, 118, 36)
PANEL_OPEN_BUTTON = pygame.Rect(1222, 100, 42, 42)
PANEL_CLOSE_BUTTON = pygame.Rect(868, 100, 42, 42)

HOME_CONFIRM_RECT = pygame.Rect(390, 245, 500, 220)
HOME_CONFIRM_CANCEL = pygame.Rect(462, 394, 150, 42)
HOME_CONFIRM_ACCEPT = pygame.Rect(628, 394, 190, 42)

TAB_BUTTONS = {
    "launch": pygame.Rect(932, 108, 96, 34),
    "environment": pygame.Rect(1036, 108, 104, 34),
    "info": pygame.Rect(1148, 108, 96, 34),
}

BOTTOM_BUTTONS = {
    "launch": pygame.Rect(30, 651, 112, 40),
    "show": pygame.Rect(150, 651, 150, 40),
    "pause": pygame.Rect(308, 651, 112, 40),
    "reset": pygame.Rect(428, 651, 102, 40),
}

FORMULA_BUTTON = pygame.Rect(752, 655, 132, 32)
TRAJECTORY_BUTTON = pygame.Rect(938, 502, 302, 34)
TIME_CYCLE_BUTTON = pygame.Rect(938, 408, 302, 34)

CYCLE_SPEED_BUTTONS = {
    "slow": pygame.Rect(938, 454, 92, 32),
    "normal": pygame.Rect(1037, 454, 96, 32),
    "fast": pygame.Rect(1140, 454, 100, 32),
}

SIMULATION_SPEED_BUTTONS = {
    "half": pygame.Rect(938, 536, 92, 30),
    "normal": pygame.Rect(1037, 536, 96, 30),
    "double": pygame.Rect(1140, 536, 100, 30),
}

SIMULATION_SPEEDS = {
    "half": 0.50,
    "normal": 1.00,
    "double": 2.00,
}

SIMULATION_SPEED_LABELS = {
    "half": "0.5x",
    "normal": "1x",
    "double": "2x",
}

CYCLE_SPEEDS = {
    "slow": 120.0,
    "normal": 60.0,
    "fast": 30.0,
}
CYCLE_PHASES = ("day", "sunset", "night", "dawn")
CYCLE_PHASE_LABELS = {
    "day": "Gündüz",
    "sunset": "Gün Batımı",
    "night": "Gece",
    "dawn": "Gün Doğumu",
}

PATTERN_OPTIONS = (
    "Rastgele",
    "Şakayık",
    "Krizantem",
    "Halka",
    "Altın Söğüt",
    "Palmiye",
    "Çift Renk",
)

PALETTE_MAP = {
    "Rastgele": None,
    "Yakut": ((255, 74, 92), (255, 188, 80), (255, 250, 224)),
    "Safir": ((76, 177, 255), (125, 98, 255), (238, 248, 255)),
    "Ametist": ((255, 83, 185), (181, 94, 255), (255, 236, 250)),
    "Zümrüt": ((76, 232, 164), (63, 181, 255), (235, 255, 245)),
    "Altın": ((255, 216, 91), (255, 135, 57), (255, 250, 220)),
    "Kutup": ((239, 246, 255), (155, 202, 255), (255, 255, 255)),
}
PALETTE_OPTIONS = tuple(PALETTE_MAP.keys())

FORMATION_OPTIONS = (
    "Tekli",
    "İkili",
    "Yelpaze",
    "Dalga",
    "Final",
)

AIR_RESISTANCE_LEVELS = {
    "Düşük": 0.72,
    "Normal": 1.00,
    "Yüksek": 1.35,
}
AIR_RESISTANCE_OPTIONS = tuple(AIR_RESISTANCE_LEVELS.keys())

WEATHER_OPTIONS = (
    "Açık",
    "Yağmur",
    "Kar",
)

MAX_SHELLS = 14
MAX_STARS = 4300
MAX_WEATHER_PARTICLES = 700

MIN_WIND_MPS = -8.0
MAX_WIND_MPS = 8.0
MIN_EXPLOSION_POWER = 0.60
MAX_EXPLOSION_POWER = 1.40
MIN_HEIGHT_M = 30.0
MAX_HEIGHT_M = 75.0
MIN_ANGLE_DEG = 70.0
MAX_ANGLE_DEG = 110.0


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


@dataclass
class LaunchRequest:
    delay: float
    x_px: float
    angle_deg: float
    height_m: float
    power: float
    pattern_name: str
    palette_name: str


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


def draw_trajectory_preview(
    screen: pygame.Surface,
    launch_angle_deg: float,
    target_height_m: float,
    wind_mps: float,
    density_multiplier: float,
) -> None:
    angle = math.radians(launch_angle_deg)
    vertical_component = max(0.25, math.sin(angle))
    launch_speed = (
        math.sqrt(2.0 * GRAVITY_MPS2 * target_height_m)
        / vertical_component
        * 1.18
    )

    diameter = 0.045
    body = Body(
        px_to_m(FIREWORK_AREA_RIGHT / 2.0),
        px_to_m(LAUNCH_Y),
        launch_speed * math.cos(angle),
        -launch_speed * math.sin(angle),
        0.18,
        math.pi * (diameter / 2.0) ** 2,
        0.47,
    )

    points: list[tuple[int, int]] = []
    step = 0.055

    for _ in range(100):
        points.append(
            (int(body.x_px), int(body.y_px))
        )
        altitude = (LAUNCH_Y - body.y_px) / PIXELS_PER_METER
        if altitude >= target_height_m or body.vy_mps >= -0.45:
            break
        body.integrate(
            step,
            wind_mps,
            density_multiplier,
        )

    preview = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA,
    )

    for index in range(1, len(points), 2):
        pygame.draw.aaline(
            preview,
            (116, 220, 255, 125),
            points[index - 1],
            points[index],
        )

    if points:
        end = points[-1]
        pygame.draw.circle(
            preview,
            (255, 211, 95, 185),
            end,
            6,
            1,
        )
        pygame.draw.aaline(
            preview,
            (255, 211, 95, 140),
            (end[0] - 9, end[1]),
            (end[0] + 9, end[1]),
        )
        pygame.draw.aaline(
            preview,
            (255, 211, 95, 140),
            (end[0], end[1] - 9),
            (end[0], end[1] + 9),
        )

    screen.blit(preview, (0, 0))


# ============================================================
# ARAYÜZ
# ============================================================

def draw_header(
    surface: pygame.Surface,
    font: pygame.font.Font,
) -> None:
    rect = pygame.Rect(24, 20, 610, 66)
    pygame.draw.rect(surface, PANEL, rect, border_radius=14)
    pygame.draw.rect(
        surface,
        PANEL_BORDER,
        rect,
        2,
        border_radius=14,
    )
    surface.blit(
        font.render(
            "Rüzgâr Etkili Havai Fişek Simülasyonu",
            True,
            WHITE,
        ),
        (45, 38),
    )


def draw_mode_buttons(
    surface: pygame.Surface,
    font: pygame.font.Font,
    mode: str,
    mouse: tuple[int, int],
) -> None:
    labels = {
        "day": "Gündüz",
        "sunset": "Gün Batımı",
        "night": "Gece",
    }

    for key, rect in MODE_BUTTONS.items():
        color = (
            ACTIVE
            if key == mode
            else HOVER
            if rect.collidepoint(mouse)
            else PASSIVE
        )
        pygame.draw.rect(surface, color, rect, border_radius=11)
        pygame.draw.rect(
            surface,
            PANEL_BORDER,
            rect,
            2,
            border_radius=11,
        )
        text = font.render(labels[key], True, WHITE)
        surface.blit(text, text.get_rect(center=rect.center))


def draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    text: str,
    font: pygame.font.Font,
    mouse: tuple[int, int],
    *,
    active: bool = False,
    danger: bool = False,
) -> None:
    color = (
        ACTIVE
        if active
        else HOVER
        if rect.collidepoint(mouse)
        else DANGER
        if danger
        else PASSIVE
    )
    pygame.draw.rect(surface, color, rect, border_radius=9)
    pygame.draw.rect(
        surface,
        PANEL_BORDER,
        rect,
        1,
        border_radius=9,
    )
    label = font.render(text, True, WHITE)
    surface.blit(label, label.get_rect(center=rect.center))


def draw_slider(
    surface: pygame.Surface,
    slider: Slider,
    font: pygame.font.Font,
    mouse: tuple[int, int],
    display_value: str | None = None,
) -> None:
    value_text = (
        display_value
        if display_value is not None
        else f"{slider.value:g}{slider.suffix}"
    )
    label = font.render(
        f"{slider.label}: {value_text}",
        True,
        (220, 228, 244),
    )
    surface.blit(label, (slider.rect.left, slider.rect.top - 27))

    pygame.draw.rect(
        surface,
        (45, 54, 77),
        slider.rect,
        border_radius=4,
    )
    fill = pygame.Rect(
        slider.rect.left,
        slider.rect.top,
        max(0, slider.handle_x() - slider.rect.left),
        slider.rect.height,
    )
    if fill.width > 0:
        pygame.draw.rect(
            surface,
            (68, 166, 231),
            fill,
            border_radius=4,
        )

    hover_rect = slider.rect.inflate(20, 28)
    hover = hover_rect.collidepoint(mouse)
    pygame.draw.circle(
        surface,
        (245, 214, 143) if hover else (203, 216, 239),
        (slider.handle_x(), slider.rect.centery),
        8 if hover else 7,
    )


def draw_cycle_value_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    value: str,
    font: pygame.font.Font,
    mouse: tuple[int, int],
) -> None:
    draw_button(
        surface,
        rect,
        f"{label}: {value}",
        font,
        mouse,
    )


def draw_right_panel(
    surface: pygame.Surface,
    tab: str,
    fonts: dict[str, pygame.font.Font],
    mouse: tuple[int, int],
    selected_pattern: str,
    selected_palette: str,
    selected_formation: str,
    trajectory_enabled: bool,
    air_level: str,
    weather_name: str,
    cycle_enabled: bool,
    cycle_speed_key: str,
    cycle_label: str,
    simulation_speed_key: str,
    live_info: dict[str, object],
    active_shells: int,
    active_stars: int,
    total_launches: int,
    total_bursts: int,
) -> None:
    panel_layer = pygame.Surface(
        RIGHT_PANEL.size,
        pygame.SRCALPHA,
    )
    pygame.draw.rect(
        panel_layer,
        (7, 11, 25, 237),
        (0, 0, *RIGHT_PANEL.size),
        border_radius=14,
    )
    pygame.draw.rect(
        panel_layer,
        (*PANEL_BORDER, 230),
        (0, 0, *RIGHT_PANEL.size),
        1,
        border_radius=14,
    )
    surface.blit(panel_layer, RIGHT_PANEL.topleft)

    tab_labels = {
        "launch": "Fırlatma",
        "environment": "Ortam",
        "info": "Bilgi",
    }
    for key, rect in TAB_BUTTONS.items():
        draw_button(
            surface,
            rect,
            tab_labels[key],
            fonts["small"],
            mouse,
            active=key == tab,
        )

    if tab == "launch":
        draw_slider(
            surface,
            SLIDERS["height"],
            fonts["small"],
            mouse,
        )
        draw_slider(
            surface,
            SLIDERS["angle"],
            fonts["small"],
            mouse,
        )
        draw_slider(
            surface,
            SLIDERS["power"],
            fonts["small"],
            mouse,
            f"%{SLIDERS['power'].value * 100:.0f}",
        )

        pattern_rect = pygame.Rect(938, 344, 302, 36)
        palette_rect = pygame.Rect(938, 389, 302, 36)
        formation_rect = pygame.Rect(938, 434, 302, 36)

        draw_cycle_value_button(
            surface,
            pattern_rect,
            "Tür",
            selected_pattern,
            fonts["small"],
            mouse,
        )
        draw_cycle_value_button(
            surface,
            palette_rect,
            "Renk",
            selected_palette,
            fonts["small"],
            mouse,
        )
        draw_cycle_value_button(
            surface,
            formation_rect,
            "Düzen",
            selected_formation,
            fonts["small"],
            mouse,
        )
        draw_button(
            surface,
            TRAJECTORY_BUTTON,
            (
                "Yörünge Önizlemesi: Açık"
                if trajectory_enabled
                else "Yörünge Önizlemesi: Kapalı"
            ),
            fonts["small"],
            mouse,
            active=trajectory_enabled,
        )

    elif tab == "environment":
        wind_value = SLIDERS["wind"].value
        direction = (
            "sağa"
            if wind_value > 0
            else "sola"
            if wind_value < 0
            else "durgun"
        )
        draw_slider(
            surface,
            SLIDERS["wind"],
            fonts["small"],
            mouse,
            f"{abs(wind_value):.1f} m/sn {direction}",
        )

        air_rect = pygame.Rect(938, 244, 302, 36)
        weather_rect = pygame.Rect(938, 294, 302, 36)

        draw_cycle_value_button(
            surface,
            air_rect,
            "Hava direnci",
            air_level,
            fonts["small"],
            mouse,
        )
        draw_cycle_value_button(
            surface,
            weather_rect,
            "Hava durumu",
            weather_name,
            fonts["small"],
            mouse,
        )
        draw_slider(
            surface,
            SLIDERS["precipitation"],
            fonts["small"],
            mouse,
            f"%{SLIDERS['precipitation'].value * 100:.0f}",
        )

        draw_button(
            surface,
            TIME_CYCLE_BUTTON,
            (
                "Zaman Döngüsü: Açık"
                if cycle_enabled
                else "Zaman Döngüsü: Kapalı"
            ),
            fonts["small"],
            mouse,
            active=cycle_enabled,
        )

        speed_labels = {
            "slow": "Yavaş",
            "normal": "Normal",
            "fast": "Hızlı",
        }
        for key, rect in CYCLE_SPEED_BUTTONS.items():
            draw_button(
                surface,
                rect,
                speed_labels[key],
                fonts["small"],
                mouse,
                active=key == cycle_speed_key,
            )

        phase_text = fonts["small"].render(
            f"Sahne: {cycle_label}",
            True,
            (255, 208, 123),
        )
        surface.blit(phase_text, (938, 494))

        simulation_speed_title = fonts["small"].render(
            "Genel simülasyon hızı",
            True,
            (155, 170, 200),
        )
        surface.blit(simulation_speed_title, (938, 516))

        for key, rect in SIMULATION_SPEED_BUTTONS.items():
            draw_button(
                surface,
                rect,
                SIMULATION_SPEED_LABELS[key],
                fonts["small"],
                mouse,
                active=key == simulation_speed_key,
            )

    else:
        lines = [
            ("Son tür", str(live_info.get("pattern", "—"))),
            ("Son palet", str(live_info.get("palette", "—"))),
            ("Son yükseklik", f"{float(live_info.get('height', 0.0)):.0f} m"),
            ("Son açı", f"{float(live_info.get('angle', 0.0)):.0f}°"),
            ("Son güç", f"%{float(live_info.get('power', 0.0)) * 100:.0f}"),
            ("Düzen", str(live_info.get("formation", "—"))),
            ("Aktif roket", str(active_shells)),
            ("Aktif yıldız", str(active_stars)),
            ("Toplam fırlatma", str(total_launches)),
            ("Toplam patlama", str(total_bursts)),
            (
                "Simülasyon hızı",
                SIMULATION_SPEED_LABELS[simulation_speed_key],
            ),
        ]

        for index, (label, value) in enumerate(lines):
            y = 170 + index * 34
            surface.blit(
                fonts["small"].render(
                    label,
                    True,
                    (155, 170, 200),
                ),
                (942, y),
            )
            value_surface = fonts["small_bold"].render(
                value,
                True,
                (236, 242, 255),
            )
            surface.blit(
                value_surface,
                (1234 - value_surface.get_width(), y),
            )


def draw_bottom_bar(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    mouse: tuple[int, int],
    paused: bool,
    auto_show: bool,
    selected_formation: str,
    weather_name: str,
) -> None:
    """İnce alt araç çubuğunu ve temel durum bilgisini çizer."""
    bar = pygame.Surface(BOTTOM_BAR.size, pygame.SRCALPHA)
    pygame.draw.rect(
        bar,
        (6, 10, 23, 238),
        (0, 0, *BOTTOM_BAR.size),
        border_radius=14,
    )
    pygame.draw.rect(
        bar,
        (*PANEL_BORDER, 225),
        (0, 0, *BOTTOM_BAR.size),
        1,
        border_radius=14,
    )
    surface.blit(bar, BOTTOM_BAR.topleft)

    draw_button(
        surface,
        BOTTOM_BUTTONS["launch"],
        "Fırlat",
        fonts["button"],
        mouse,
        active=True,
    )
    draw_button(
        surface,
        BOTTOM_BUTTONS["show"],
        "Gösteriyi Durdur" if auto_show else "Otomatik Gösteri",
        fonts["small_bold"],
        mouse,
        active=auto_show,
    )
    draw_button(
        surface,
        BOTTOM_BUTTONS["pause"],
        "Devam" if paused else "Duraklat",
        fonts["button"],
        mouse,
    )
    draw_button(
        surface,
        BOTTOM_BUTTONS["reset"],
        "Sıfırla",
        fonts["button"],
        mouse,
        danger=True,
    )

    status = fonts["small"].render(
        f"Düzen: {selected_formation}   |   Hava: {weather_name}",
        True,
        (190, 202, 226),
    )
    surface.blit(status, (552, 662))

    draw_button(
        surface,
        FORMULA_BUTTON,
        "Formüller (I)",
        fonts["small"],
        mouse,
    )

def draw_formula_overlay(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    density_multiplier: float,
    angle_deg: float,
    height_m: float,
    power: float,
) -> None:
    rect = pygame.Rect(248, 132, 626, 345)
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        layer,
        (8, 12, 25, 244),
        (0, 0, *rect.size),
        border_radius=14,
    )
    pygame.draw.rect(
        layer,
        (*PANEL_BORDER, 230),
        (0, 0, *rect.size),
        2,
        border_radius=14,
    )
    surface.blit(layer, rect.topleft)

    surface.blit(
        fonts["button"].render(
            "Kullanılan Fizik Modeli",
            True,
            (255, 220, 132),
        ),
        (274, 155),
    )

    effective_density = AIR_DENSITY * density_multiplier
    lines = [
        "Yatay hız: vₓ = v₀ · cos(θ)",
        "Dikey hız: vᵧ = −v₀ · sin(θ)",
        "Yükseklik: H ≈ vᵧ² / (2g)",
        "Bağıl hız: v_rel = v_parçacık − v_rüzgâr",
        "Sürükleme: F_d = 1/2 · ρ · C_d · A · |v_rel|²",
        "Newton: a = (F_g + F_d) / m",
        "Hız: v(t+Δt) = v(t) + a·Δt",
        "Konum: p(t+Δt) = p(t) + v(t+Δt)·Δt",
        "Patlama enerjisi: E_k = 1/2 · m · (P·v_ref)²",
        f"θ = {angle_deg:.0f}°, H = {height_m:.0f} m, P = {power:.2f}",
        f"ρ_etkin = {effective_density:.3f} kg/m³, g = {GRAVITY_MPS2:.2f} m/sn²",
        "Sayısal yöntem: yarı örtük Euler",
    ]

    for index, line in enumerate(lines):
        surface.blit(
            fonts["small"].render(
                line,
                True,
                (213, 222, 241),
            ),
            (274, 198 + index * 24),
        )


def scene_visibility(mode: str) -> float:
    if mode == "day":
        return 0.50
    if mode == "sunset":
        return 0.80
    if mode == "dawn":
        return 0.66
    return 1.0



def draw_decorative_fireworks(
    surface: pygame.Surface,
    time_s: float,
) -> None:
    """Karşılama ekranı için hafif ve döngüsel dekoratif patlamalar çizer."""
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    bursts = (
        (230, 225, 72, (255, 92, 130), 0.0),
        (1010, 255, 88, (85, 190, 255), 1.9),
        (770, 170, 58, (255, 214, 96), 3.5),
    )

    for cx, cy, max_radius, color, phase in bursts:
        local = (time_s * 0.34 + phase) % 4.4
        if local > 2.35:
            continue

        progress = clamp(local / 2.35, 0.0, 1.0)
        radius = max_radius * (1.0 - math.exp(-4.2 * progress))
        fade = (1.0 - progress) ** 0.72
        particle_count = 42

        for index in range(particle_count):
            angle = math.tau * index / particle_count + phase * 0.12
            irregularity = 0.88 + 0.14 * math.sin(index * 2.13 + phase)
            px = cx + math.cos(angle) * radius * irregularity
            py = cy + math.sin(angle) * radius * irregularity + progress * progress * 24
            alpha = int(180 * fade)

            if alpha <= 4:
                continue

            draw_radial_glow(glow, px, py, color, 4.0, alpha)
            pygame.draw.circle(layer, (*color, alpha), (int(px), int(py)), 1)

    surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    surface.blit(layer, (0, 0))


def draw_welcome_modal(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    mouse: tuple[int, int],
    modal: str,
) -> None:
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 155))
    surface.blit(shade, (0, 0))

    panel = pygame.Surface(WELCOME_MODAL_RECT.size, pygame.SRCALPHA)
    pygame.draw.rect(
        panel,
        (8, 13, 29, 247),
        (0, 0, *WELCOME_MODAL_RECT.size),
        border_radius=18,
    )
    pygame.draw.rect(
        panel,
        (*PANEL_BORDER, 235),
        (0, 0, *WELCOME_MODAL_RECT.size),
        2,
        border_radius=18,
    )
    surface.blit(panel, WELCOME_MODAL_RECT.topleft)

    title = "Hızlı Kullanım" if modal == "help" else "Fizik Modeli"
    surface.blit(
        fonts["button"].render(title, True, (255, 220, 132)),
        (WELCOME_MODAL_RECT.left + 28, WELCOME_MODAL_RECT.top + 24),
    )

    if modal == "help":
        lines = (
            "SPACE  Seçili gösteri düzenini fırlatır.",
            "G      Otomatik gösteriyi açar veya kapatır.",
            "P      Simülasyonu duraklatır veya devam ettirir.",
            "R      Aktif roketleri ve parçacıkları sıfırlar.",
            "TAB    Ayar panelini açar veya gizler.",
            "1/2/3  Gündüz, gün batımı ve gece sahnesini seçer.",
            "4/5/6  Simülasyonu 0.5x, 1x ve 2x hızda çalıştırır.",
            "I      Kullanılan fizik formüllerini gösterir.",
        )
    else:
        lines = (
            "vₓ = v₀ · cos(θ)    ve    vᵧ = −v₀ · sin(θ)",
            "F_d = 1/2 · ρ · C_d · A · |v_rel|²",
            "a = (F_g + F_d) / m",
            "v(t+Δt) = v(t) + a·Δt",
            "p(t+Δt) = p(t) + v(t+Δt)·Δt",
            "E_k = 1/2 · m · (P·v_ref)²",
            "Yer çekimi: 9.81 m/sn²",
            "Sayısal yöntem: yarı örtük Euler integrasyonu",
        )

    for index, line in enumerate(lines):
        surface.blit(
            fonts["small"].render(line, True, (217, 226, 244)),
            (WELCOME_MODAL_RECT.left + 30, WELCOME_MODAL_RECT.top + 78 + index * 34),
        )

    draw_button(
        surface,
        WELCOME_MODAL_CLOSE,
        "Kapat",
        fonts["small_bold"],
        mouse,
        active=True,
    )


def draw_welcome_screen(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    stars: list[dict[str, float]],
    time_s: float,
    mouse: tuple[int, int],
    modal: str | None,
) -> None:
    """Uygulamanın sade ve animasyonlu karşılama ekranını çizer."""
    render_scene(surface, "night", stars, time_s)
    draw_decorative_fireworks(surface, time_s)

    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((2, 5, 16, 68))
    surface.blit(shade, (0, 0))

    card_rect = pygame.Rect(315, 86, 650, 515)
    card = pygame.Surface(card_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        card,
        (7, 11, 26, 224),
        (0, 0, *card_rect.size),
        border_radius=22,
    )
    pygame.draw.rect(
        card,
        (*PANEL_BORDER, 225),
        (0, 0, *card_rect.size),
        2,
        border_radius=22,
    )
    surface.blit(card, card_rect.topleft)

    title_font = pygame.font.SysFont("arial", 35, bold=True)
    subtitle_font = pygame.font.SysFont("arial", 17)

    title = title_font.render(
        "Rüzgâr Etkili Havai Fişek Simülasyonu",
        True,
        WHITE,
    )
    surface.blit(title, title.get_rect(center=(WIDTH // 2, 150)))

    subtitle_lines = (
        "Rüzgâr, hava direnci, yağış ve parçacık hareketlerine bağlı",
        "etkileşimli fizik ve grafik programlama uygulaması",
    )
    for index, line in enumerate(subtitle_lines):
        subtitle = subtitle_font.render(line, True, (177, 193, 221))
        surface.blit(
            subtitle,
            subtitle.get_rect(center=(WIDTH // 2, 207 + index * 24)),
        )

    labels = {
        "start": "Simülasyonu Başlat",
        "help": "Hızlı Kullanım",
        "physics": "Fizik Modeli",
        "exit": "Programdan Çık",
    }

    for key, rect in WELCOME_BUTTONS.items():
        draw_button(
            surface,
            rect,
            labels[key],
            fonts["button"] if key == "start" else fonts["small_bold"],
            mouse,
            active=key == "start",
            danger=key == "exit",
        )

    footer = fonts["small"].render(
        "Grafik Programlama Dersi Dönem Sonu Projesi  •  Fatma Koyuncu",
        True,
        (135, 151, 182),
    )
    surface.blit(footer, footer.get_rect(center=(WIDTH // 2, 579)))

    if modal is not None:
        draw_welcome_modal(surface, fonts, mouse, modal)


def draw_navigation_controls(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    mouse: tuple[int, int],
    panel_open: bool,
) -> None:
    """Ana menü ve ayar paneli açma/kapatma düğmelerini çizer."""
    draw_button(
        surface,
        HOME_BUTTON,
        "Ana Menü",
        fonts["small_bold"],
        mouse,
    )

    toggle_rect = PANEL_CLOSE_BUTTON if panel_open else PANEL_OPEN_BUTTON
    toggle_text = "▶" if panel_open else "◀"
    draw_button(
        surface,
        toggle_rect,
        toggle_text,
        fonts["button"],
        mouse,
        active=panel_open,
    )

    if not panel_open:
        label = fonts["small"].render("Ayarlar", True, (198, 210, 235))
        surface.blit(label, (1162, 112))


def draw_home_confirmation(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    mouse: tuple[int, int],
) -> None:
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    surface.blit(shade, (0, 0))

    panel = pygame.Surface(HOME_CONFIRM_RECT.size, pygame.SRCALPHA)
    pygame.draw.rect(
        panel,
        (8, 12, 26, 248),
        (0, 0, *HOME_CONFIRM_RECT.size),
        border_radius=16,
    )
    pygame.draw.rect(
        panel,
        (*PANEL_BORDER, 235),
        (0, 0, *HOME_CONFIRM_RECT.size),
        2,
        border_radius=16,
    )
    surface.blit(panel, HOME_CONFIRM_RECT.topleft)

    title = fonts["button"].render(
        "Ana menüye dönülsün mü?",
        True,
        (255, 220, 132),
    )
    surface.blit(title, title.get_rect(center=(WIDTH // 2, 292)))

    message = fonts["small"].render(
        "Mevcut simülasyon ve sayaçlar sıfırlanacaktır.",
        True,
        (214, 224, 243),
    )
    surface.blit(message, message.get_rect(center=(WIDTH // 2, 342)))

    draw_button(
        surface,
        HOME_CONFIRM_CANCEL,
        "İptal",
        fonts["small_bold"],
        mouse,
    )
    draw_button(
        surface,
        HOME_CONFIRM_ACCEPT,
        "Ana Menüye Dön",
        fonts["small_bold"],
        mouse,
        danger=True,
    )


def cycle_elapsed_for_mode(
    mode: str,
    duration: float,
) -> float:
    safe_mode = mode if mode in CYCLE_PHASES else "night"
    phase_index = CYCLE_PHASES.index(safe_mode)
    return phase_index * duration / len(CYCLE_PHASES)


# ============================================================
# ANA PROGRAM
# ============================================================

def main() -> None:
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Wind Fireworks Simulation")
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont("arial", 28, bold=True),
        "button": pygame.font.SysFont("arial", 17, bold=True),
        "small": pygame.font.SysFont("arial", 14),
        "small_bold": pygame.font.SysFont("arial", 14, bold=True),
    }

    background_stars = create_stars(165)
    scene_first = pygame.Surface((WIDTH, HEIGHT))
    scene_second = pygame.Surface((WIDTH, HEIGHT))

    mode = "night"
    visible_mode = mode
    active_tab = "launch"

    # Uygulama önce karşılama ekranında açılır. Ayar paneli simülasyona
    # girildiğinde kapalıdır; kullanıcı TAB veya kenar düğmesiyle açabilir.
    app_state = "welcome"
    welcome_modal: str | None = None
    panel_open = False
    home_confirmation = False

    paused = False
    auto_show = False
    formula_visible = False
    trajectory_enabled = True

    selected_pattern = "Rastgele"
    selected_palette = "Rastgele"
    selected_formation = "Tekli"
    air_level = "Normal"
    weather_name = "Açık"

    cycle_enabled = False
    cycle_speed_key = "normal"
    simulation_speed_key = "normal"
    cycle_elapsed = cycle_elapsed_for_mode(
        mode,
        CYCLE_SPEEDS[cycle_speed_key],
    )

    dragging_slider: str | None = None
    time_s = 0.0
    show_timer = 0.0
    weather_spawn_accumulator = 0.0

    shells: list[Shell] = []
    shell_sparks: list[ShellSpark] = []
    smoke_particles: list[Smoke] = []
    firework_stars: list[FireworkStar] = []
    flashes: list[Flash] = []
    pending_launches: list[LaunchRequest] = []
    weather_particles: list[WeatherParticle] = []

    total_launches = 0
    total_bursts = 0
    live_info: dict[str, object] = {
        "pattern": "—",
        "palette": "—",
        "height": 0.0,
        "angle": 0.0,
        "power": 0.0,
        "formation": "—",
    }

    running = True

    while running:
        frame_dt = min(clock.tick(FPS) / 1000.0, 0.04)
        mouse = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            # Karşılama ekranı kendi basit olay akışına sahiptir.
            if app_state == "welcome":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if welcome_modal is not None:
                            welcome_modal = None
                        else:
                            running = False
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if welcome_modal is None:
                            app_state = "simulation"
                            panel_open = False

                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                ):
                    if welcome_modal is not None:
                        if WELCOME_MODAL_CLOSE.collidepoint(event.pos):
                            welcome_modal = None
                    elif WELCOME_BUTTONS["start"].collidepoint(event.pos):
                        app_state = "simulation"
                        panel_open = False
                    elif WELCOME_BUTTONS["help"].collidepoint(event.pos):
                        welcome_modal = "help"
                    elif WELCOME_BUTTONS["physics"].collidepoint(event.pos):
                        welcome_modal = "physics"
                    elif WELCOME_BUTTONS["exit"].collidepoint(event.pos):
                        running = False
                continue

            # Ana menüye dönüş onayı açıkken simülasyon kontrolleri çalışmaz.
            if home_confirmation:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    home_confirmation = False
                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                ):
                    if HOME_CONFIRM_CANCEL.collidepoint(event.pos):
                        home_confirmation = False
                    elif HOME_CONFIRM_ACCEPT.collidepoint(event.pos):
                        shells.clear()
                        shell_sparks.clear()
                        smoke_particles.clear()
                        firework_stars.clear()
                        flashes.clear()
                        pending_launches.clear()
                        weather_particles.clear()
                        total_launches = 0
                        total_bursts = 0
                        live_info.update(
                            {
                                "pattern": "—",
                                "palette": "—",
                                "height": 0.0,
                                "angle": 0.0,
                                "power": 0.0,
                                "formation": "—",
                            }
                        )
                        paused = False
                        auto_show = False
                        formula_visible = False
                        home_confirmation = False
                        panel_open = False
                        welcome_modal = None
                        app_state = "welcome"
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_1:
                    mode = "day"
                    visible_mode = mode
                    cycle_enabled = False
                elif event.key == pygame.K_2:
                    mode = "sunset"
                    visible_mode = mode
                    cycle_enabled = False
                elif event.key == pygame.K_3:
                    mode = "night"
                    visible_mode = mode
                    cycle_enabled = False
                elif event.key == pygame.K_SPACE:
                    pending_launches.extend(
                        create_launch_requests(
                            selected_formation,
                            SLIDERS["angle"].value,
                            SLIDERS["height"].value,
                            SLIDERS["power"].value,
                            selected_pattern,
                            selected_palette,
                        )
                    )
                    live_info["formation"] = selected_formation
                elif event.key == pygame.K_g:
                    auto_show = not auto_show
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_r:
                    shells.clear()
                    shell_sparks.clear()
                    smoke_particles.clear()
                    firework_stars.clear()
                    flashes.clear()
                    pending_launches.clear()
                elif event.key == pygame.K_i:
                    formula_visible = not formula_visible
                elif event.key == pygame.K_t:
                    trajectory_enabled = not trajectory_enabled
                elif event.key == pygame.K_c:
                    cycle_enabled = not cycle_enabled
                    if cycle_enabled:
                        cycle_elapsed = cycle_elapsed_for_mode(
                            visible_mode,
                            CYCLE_SPEEDS[cycle_speed_key],
                        )
                    else:
                        mode = visible_mode
                elif event.key == pygame.K_4:
                    simulation_speed_key = "half"
                elif event.key == pygame.K_5:
                    simulation_speed_key = "normal"
                elif event.key == pygame.K_6:
                    simulation_speed_key = "double"
                elif event.key == pygame.K_TAB:
                    panel_open = not panel_open
                    dragging_slider = None

            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button in (1, 3)
            ):
                direction = 1 if event.button == 1 else -1
                clicked = False

                if event.button == 1 and HOME_BUTTON.collidepoint(event.pos):
                    home_confirmation = True
                    continue

                panel_toggle_rect = (
                    PANEL_CLOSE_BUTTON if panel_open else PANEL_OPEN_BUTTON
                )
                if event.button == 1 and panel_toggle_rect.collidepoint(event.pos):
                    panel_open = not panel_open
                    dragging_slider = None
                    continue

                for key, rect in MODE_BUTTONS.items():
                    if rect.collidepoint(event.pos):
                        mode = key
                        visible_mode = key
                        cycle_enabled = False
                        clicked = True
                        break

                if clicked:
                    continue

                if panel_open:
                    for key, rect in TAB_BUTTONS.items():
                        if rect.collidepoint(event.pos):
                            active_tab = key
                            clicked = True
                            break

                if clicked:
                    continue

                if BOTTOM_BUTTONS["launch"].collidepoint(event.pos):
                    pending_launches.extend(
                        create_launch_requests(
                            selected_formation,
                            SLIDERS["angle"].value,
                            SLIDERS["height"].value,
                            SLIDERS["power"].value,
                            selected_pattern,
                            selected_palette,
                        )
                    )
                    live_info["formation"] = selected_formation
                    continue

                if BOTTOM_BUTTONS["show"].collidepoint(event.pos):
                    auto_show = not auto_show
                    continue

                if BOTTOM_BUTTONS["pause"].collidepoint(event.pos):
                    paused = not paused
                    continue

                if BOTTOM_BUTTONS["reset"].collidepoint(event.pos):
                    shells.clear()
                    shell_sparks.clear()
                    smoke_particles.clear()
                    firework_stars.clear()
                    flashes.clear()
                    pending_launches.clear()
                    continue

                if FORMULA_BUTTON.collidepoint(event.pos):
                    formula_visible = not formula_visible
                    continue

                if panel_open and active_tab == "launch":
                    for slider_name in ("height", "angle", "power"):
                        slider = SLIDERS[slider_name]
                        if slider.rect.inflate(22, 30).collidepoint(event.pos):
                            dragging_slider = slider_name
                            slider.set_from_x(event.pos[0])
                            clicked = True
                            break

                    if clicked:
                        continue

                    pattern_rect = pygame.Rect(938, 344, 302, 36)
                    palette_rect = pygame.Rect(938, 389, 302, 36)
                    formation_rect = pygame.Rect(938, 434, 302, 36)

                    if pattern_rect.collidepoint(event.pos):
                        selected_pattern = cycle_option(
                            PATTERN_OPTIONS,
                            selected_pattern,
                            direction,
                        )
                    elif palette_rect.collidepoint(event.pos):
                        selected_palette = cycle_option(
                            PALETTE_OPTIONS,
                            selected_palette,
                            direction,
                        )
                    elif formation_rect.collidepoint(event.pos):
                        selected_formation = cycle_option(
                            FORMATION_OPTIONS,
                            selected_formation,
                            direction,
                        )
                    elif TRAJECTORY_BUTTON.collidepoint(event.pos):
                        trajectory_enabled = not trajectory_enabled

                elif panel_open and active_tab == "environment":
                    for slider_name in ("wind", "precipitation"):
                        slider = SLIDERS[slider_name]
                        if slider.rect.inflate(22, 30).collidepoint(event.pos):
                            dragging_slider = slider_name
                            slider.set_from_x(event.pos[0])
                            clicked = True
                            break

                    if clicked:
                        continue

                    air_rect = pygame.Rect(938, 244, 302, 36)
                    weather_rect = pygame.Rect(938, 294, 302, 36)

                    if air_rect.collidepoint(event.pos):
                        air_level = cycle_option(
                            AIR_RESISTANCE_OPTIONS,
                            air_level,
                            direction,
                        )
                    elif weather_rect.collidepoint(event.pos):
                        weather_name = cycle_option(
                            WEATHER_OPTIONS,
                            weather_name,
                            direction,
                        )
                    elif TIME_CYCLE_BUTTON.collidepoint(event.pos):
                        cycle_enabled = not cycle_enabled
                        if cycle_enabled:
                            cycle_elapsed = cycle_elapsed_for_mode(
                                visible_mode,
                                CYCLE_SPEEDS[cycle_speed_key],
                            )
                        else:
                            mode = visible_mode
                    else:
                        cycle_speed_changed = False

                        for key, rect in CYCLE_SPEED_BUTTONS.items():
                            if rect.collidepoint(event.pos):
                                old_duration = CYCLE_SPEEDS[cycle_speed_key]
                                progress = (
                                    cycle_elapsed % old_duration
                                ) / old_duration
                                cycle_speed_key = key
                                cycle_elapsed = (
                                    progress * CYCLE_SPEEDS[cycle_speed_key]
                                )
                                cycle_speed_changed = True
                                break

                        if not cycle_speed_changed:
                            for key, rect in SIMULATION_SPEED_BUTTONS.items():
                                if rect.collidepoint(event.pos):
                                    simulation_speed_key = key
                                    break

            elif (
                event.type == pygame.MOUSEMOTION
                and panel_open
                and dragging_slider
            ):
                SLIDERS[dragging_slider].set_from_x(event.pos[0])

            elif (
                event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
            ):
                dragging_slider = None

        if app_state == "welcome":
            time_s += frame_dt
            draw_welcome_screen(
                screen,
                fonts,
                background_stars,
                time_s,
                mouse,
                welcome_modal,
            )
            pygame.display.flip()
            continue

        dt = (
            frame_dt
            * SIMULATION_SPEEDS[simulation_speed_key]
        )

        density_multiplier = effective_density_multiplier(
            air_level,
            weather_name,
            SLIDERS["precipitation"].value,
        )
        weather_visibility = weather_visibility_multiplier(
            weather_name,
            SLIDERS["precipitation"].value,
        )
        burn_loss = precipitation_burn_loss(
            weather_name,
            SLIDERS["precipitation"].value,
        )

        if not paused:
            time_s += dt

            if cycle_enabled:
                cycle_elapsed += dt

            if auto_show:
                show_timer -= dt
                if show_timer <= 0.0:
                    pending_launches.extend(
                        create_launch_requests(
                            selected_formation,
                            SLIDERS["angle"].value,
                            SLIDERS["height"].value,
                            SLIDERS["power"].value,
                            selected_pattern,
                            selected_palette,
                        )
                    )
                    live_info["formation"] = selected_formation
                    show_timer = {
                        "Tekli": 1.15,
                        "İkili": 1.45,
                        "Yelpaze": 2.15,
                        "Dalga": 2.35,
                        "Final": 4.20,
                    }[selected_formation]

            for request in pending_launches:
                request.delay -= dt

            ready_requests = [
                request
                for request in pending_launches
                if request.delay <= 0.0
            ]
            pending_launches = [
                request
                for request in pending_launches
                if request.delay > 0.0
            ]

            for request in ready_requests:
                launched, info = spawn_shell_from_request(
                    request,
                    shells,
                )
                if launched:
                    total_launches += 1
                    live_info.update(info)

            exploded_shells: list[Shell] = []
            for shell in shells:
                if shell.update(
                    dt,
                    SLIDERS["wind"].value,
                    density_multiplier,
                    burn_loss,
                    shell_sparks,
                    smoke_particles,
                ):
                    exploded_shells.append(shell)

            for shell in exploded_shells:
                new_stars, flash = shell.burst()
                available = max(0, MAX_STARS - len(firework_stars))
                firework_stars.extend(new_stars[:available])
                flashes.append(flash)
                total_bursts += 1
                live_info.update(
                    {
                        "pattern": shell.pattern,
                        "palette": shell.palette_name,
                        "height": shell.altitude_m,
                        "angle": shell.angle_deg,
                        "power": shell.power,
                    }
                )

            shells = [shell for shell in shells if shell.alive]

            for spark in shell_sparks:
                spark.update(
                    dt,
                    SLIDERS["wind"].value,
                    burn_loss,
                )
            shell_sparks = [
                spark
                for spark in shell_sparks
                if spark.alive
            ]

            for smoke_particle in smoke_particles:
                smoke_particle.update(
                    dt,
                    SLIDERS["wind"].value,
                    weather_name,
                    SLIDERS["precipitation"].value,
                )
            smoke_particles = [
                particle
                for particle in smoke_particles
                if particle.alive
            ]

            for star in firework_stars:
                star.update(
                    dt,
                    SLIDERS["wind"].value,
                    density_multiplier,
                    burn_loss,
                )
            firework_stars = [
                star
                for star in firework_stars
                if star.alive
            ]

            for flash in flashes:
                flash.update(dt)
            flashes = [flash for flash in flashes if flash.alive]

            weather_spawn_accumulator = update_weather_particles(
                weather_particles,
                weather_name,
                SLIDERS["precipitation"].value,
                dt,
                SLIDERS["wind"].value,
                weather_spawn_accumulator,
            )

        if cycle_enabled:
            visible_mode, scene_visibility_value = draw_cycle_scene(
                screen,
                scene_first,
                scene_second,
                background_stars,
                time_s,
                cycle_elapsed,
                CYCLE_SPEEDS[cycle_speed_key],
            )
        else:
            render_scene(
                screen,
                mode,
                background_stars,
                time_s,
            )
            visible_mode = mode
            scene_visibility_value = scene_visibility(mode)

        if trajectory_enabled and (not panel_open or active_tab == "launch"):
            draw_trajectory_preview(
                screen,
                SLIDERS["angle"].value,
                SLIDERS["height"].value,
                SLIDERS["wind"].value,
                density_multiplier,
            )

        visibility = scene_visibility_value * weather_visibility
        effects = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        for smoke_particle in smoke_particles:
            smoke_particle.draw(effects, visibility)
        for spark in shell_sparks:
            spark.draw(effects, glow, visibility)
        for shell in shells:
            shell.draw(effects, glow, visibility)
        for star in firework_stars:
            star.draw(effects, glow, visibility)
        for flash in flashes:
            flash.draw(effects, glow, visibility)

        screen.blit(
            glow,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_ADD,
        )
        screen.blit(effects, (0, 0))

        draw_weather(
            screen,
            weather_particles,
            weather_name,
            SLIDERS["precipitation"].value,
        )

        draw_header(screen, fonts["title"])
        draw_mode_buttons(
            screen,
            fonts["button"],
            visible_mode if visible_mode != "dawn" else "",
            mouse,
        )
        if panel_open:
            draw_right_panel(
                screen,
                active_tab,
                fonts,
                mouse,
                selected_pattern,
                selected_palette,
                selected_formation,
                trajectory_enabled,
                air_level,
                weather_name,
                cycle_enabled,
                cycle_speed_key,
                CYCLE_PHASE_LABELS[visible_mode],
                simulation_speed_key,
                live_info,
                len(shells),
                len(firework_stars),
                total_launches,
                total_bursts,
            )

        draw_navigation_controls(
            screen,
            fonts,
            mouse,
            panel_open,
        )

        draw_bottom_bar(
            screen,
            fonts,
            mouse,
            paused,
            auto_show,
            selected_formation,
            weather_name,
        )

        if formula_visible:
            draw_formula_overlay(
                screen,
                fonts,
                density_multiplier,
                SLIDERS["angle"].value,
                SLIDERS["height"].value,
                SLIDERS["power"].value,
            )

        if paused:
            pause_rect = pygame.Rect(278, 108, 360, 52)
            pygame.draw.rect(
                screen,
                (9, 13, 29),
                pause_rect,
                border_radius=12,
            )
            pygame.draw.rect(
                screen,
                (255, 202, 91),
                pause_rect,
                2,
                border_radius=12,
            )
            pause_text = fonts["button"].render(
                "SİMÜLASYON DURAKLATILDI",
                True,
                (255, 230, 155),
            )
            screen.blit(
                pause_text,
                pause_text.get_rect(center=pause_rect.center),
            )

        if home_confirmation:
            draw_home_confirmation(
                screen,
                fonts,
                mouse,
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except pygame.error:
        pygame.quit()
        print(
            "Program başlatılamadı: grafik penceresi oluşturulamadı.\n"
            "Ekran sürücüsünü kontrol edip programı yeniden çalıştırın."
        )
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        pygame.quit()
        print("Program kullanıcı tarafından durduruldu.")
        raise SystemExit(0) from None
