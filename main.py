import math
import random
import sys

import pygame


# ============================================================
# GENEL AYARLAR
# ============================================================

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

CITY_BASE_Y = WINDOW_HEIGHT - 35

WHITE = (245, 245, 255)

PANEL_COLOR = (13, 18, 34)
PANEL_BORDER = (59, 75, 112)

ACTIVE_BUTTON = (39, 121, 205)
PASSIVE_BUTTON = (27, 34, 55)
BUTTON_HOVER = (48, 62, 93)


# ============================================================
# ŞEHİR VERİLERİ
# ============================================================

BUILDINGS = [
    (0, 620, 90, 65),
    (90, 580, 110, 105),
    (200, 605, 80, 80),
    (280, 540, 115, 145),
    (395, 585, 95, 100),
    (490, 560, 130, 125),
    (620, 610, 90, 75),
    (710, 530, 105, 155),
    (815, 575, 125, 110),
    (940, 615, 85, 70),
    (1025, 550, 120, 135),
    (1145, 590, 135, 95),
]


MODE_BUTTONS = {
    "day": pygame.Rect(748, 28, 145, 50),
    "sunset": pygame.Rect(903, 28, 170, 50),
    "night": pygame.Rect(1083, 28, 145, 50),
}


# Kuş verileri:
# başlangıç x, başlangıç y, ölçek, hız, faz, yön, dönüş açısı

DAY_BIRDS = [
    (345, 185, 0.55, 17, 0.0, 1, -4),
    (410, 158, 0.72, 15, 1.3, 1, 2),
    (480, 195, 0.48, 19, 2.5, 1, -2),
    (760, 245, 0.40, 13, 3.4, 1, 3),
]

SUNSET_BIRDS = [
    (290, 235, 0.48, 13, 0.4, 1, -3),
    (350, 205, 0.67, 12, 1.7, 1, 1),
    (420, 238, 0.44, 15, 2.9, 1, -2),
    (690, 285, 0.36, 10, 4.1, 1, 2),
]


# ============================================================
# RENK VE GÖKYÜZÜ YARDIMCILARI
# ============================================================

def interpolate_color(
    start_color: tuple[int, int, int],
    end_color: tuple[int, int, int],
    ratio: float,
) -> tuple[int, int, int]:
    """İki renk arasında geçiş rengi hesaplar."""

    ratio = max(0.0, min(1.0, ratio))

    return tuple(
        int(start + (end - start) * ratio)
        for start, end in zip(start_color, end_color)
    )


def draw_multi_stop_gradient(
    surface: pygame.Surface,
    color_stops: list[tuple[float, tuple[int, int, int]]],
) -> None:
    """Birden fazla renk durağıyla dikey gökyüzü geçişi çizer."""

    for y in range(WINDOW_HEIGHT):
        position = y / (WINDOW_HEIGHT - 1)

        for index in range(len(color_stops) - 1):
            start_position, start_color = color_stops[index]
            end_position, end_color = color_stops[index + 1]

            if start_position <= position <= end_position:
                distance = end_position - start_position

                if distance == 0:
                    local_ratio = 0.0
                else:
                    local_ratio = (
                        position - start_position
                    ) / distance

                color = interpolate_color(
                    start_color,
                    end_color,
                    local_ratio,
                )

                pygame.draw.line(
                    surface,
                    color,
                    (0, y),
                    (WINDOW_WIDTH, y),
                )

                break


def draw_radial_glow(
    surface: pygame.Surface,
    center: tuple[int, int],
    color: tuple[int, int, int],
    radius: int,
    maximum_alpha: int = 75,
) -> None:
    """Güneş veya ay çevresine yumuşak ışık ekler."""

    glow_surface = pygame.Surface(
        (radius * 2, radius * 2),
        pygame.SRCALPHA,
    )

    layer_count = 24

    for layer in range(layer_count, 0, -1):
        layer_ratio = layer / layer_count
        layer_radius = int(radius * layer_ratio)

        alpha = int(
            maximum_alpha
            * (1.0 - layer_ratio) ** 1.5
        )

        pygame.draw.circle(
            glow_surface,
            (*color, alpha),
            (radius, radius),
            layer_radius,
        )

    surface.blit(
        glow_surface,
        (
            center[0] - radius,
            center[1] - radius,
        ),
    )


def draw_horizon_haze(
    surface: pygame.Surface,
    y: int,
    color: tuple[int, int, int],
    height: int,
    maximum_alpha: int,
) -> None:
    """Ufuk bölgesine yumuşak atmosfer sisi ekler."""

    haze_surface = pygame.Surface(
        (WINDOW_WIDTH, height),
        pygame.SRCALPHA,
    )

    for line_y in range(height):
        distance_from_center = abs(
            line_y - height / 2
        )

        center_ratio = 1.0 - (
            distance_from_center / (height / 2)
        )

        alpha = int(
            maximum_alpha
            * max(0.0, center_ratio)
        )

        pygame.draw.line(
            haze_surface,
            (*color, alpha),
            (0, line_y),
            (WINDOW_WIDTH, line_y),
        )

    surface.blit(
        haze_surface,
        (0, y),
    )


# ============================================================
# YILDIZLAR
# ============================================================

def create_stars(
    count: int,
) -> list[dict[str, float]]:
    """Yıldızların konum ve parlama bilgilerini oluşturur."""

    random.seed(42)

    stars: list[dict[str, float]] = []

    for _ in range(count):
        stars.append(
            {
                "x": random.randint(15, WINDOW_WIDTH - 15),
                "y": random.randint(92, 510),
                "radius": random.choice([1, 1, 1, 2]),
                "phase": random.uniform(0, math.tau),
                "speed": random.uniform(0.8, 2.4),
                "glow": random.random() > 0.88,
            }
        )

    return stars


def draw_stars(
    surface: pygame.Surface,
    stars: list[dict[str, float]],
    elapsed_time: float,
) -> None:
    """Yıldızları yumuşak parlama animasyonuyla çizer."""

    for star in stars:
        pulse = math.sin(
            elapsed_time * star["speed"]
            + star["phase"]
        )

        normalized_pulse = (pulse + 1.0) / 2.0

        brightness = int(
            145 + 110 * normalized_pulse
        )

        x = int(star["x"])
        y = int(star["y"])
        radius = int(star["radius"])

        if star["glow"]:
            glow_radius = radius + int(
                2 + normalized_pulse * 3
            )

            glow_surface = pygame.Surface(
                (
                    glow_radius * 4,
                    glow_radius * 4,
                ),
                pygame.SRCALPHA,
            )

            center = glow_radius * 2

            pygame.draw.circle(
                glow_surface,
                (
                    175,
                    195,
                    255,
                    int(25 + 55 * normalized_pulse),
                ),
                (center, center),
                glow_radius * 2,
            )

            surface.blit(
                glow_surface,
                (
                    x - center,
                    y - center,
                ),
            )

        pygame.draw.circle(
            surface,
            (
                brightness,
                brightness,
                min(255, brightness + 12),
            ),
            (x, y),
            radius,
        )

        # Büyük yıldızlarda küçük ışık çizgileri
        if radius == 2 and normalized_pulse > 0.78:
            line_alpha = int(
                80 + 100 * normalized_pulse
            )

            star_light = pygame.Surface(
                (16, 16),
                pygame.SRCALPHA,
            )

            pygame.draw.line(
                star_light,
                (220, 230, 255, line_alpha),
                (8, 1),
                (8, 15),
                1,
            )

            pygame.draw.line(
                star_light,
                (220, 230, 255, line_alpha),
                (1, 8),
                (15, 8),
                1,
            )

            surface.blit(
                star_light,
                (x - 8, y - 8),
            )


# ============================================================
# BULUTLAR
# ============================================================

def draw_soft_cloud(
    surface: pygame.Surface,
    x: float,
    y: float,
    scale: float,
    top_color: tuple[int, int, int, int],
    shadow_color: tuple[int, int, int, int],
) -> None:
    """Yarı saydam ve alt kısmı gölgeli bulut çizer."""

    cloud_width = int(220 * scale)
    cloud_height = int(105 * scale)

    cloud_surface = pygame.Surface(
        (cloud_width, cloud_height),
        pygame.SRCALPHA,
    )

    pygame.draw.ellipse(
        cloud_surface,
        shadow_color,
        (
            int(25 * scale),
            int(56 * scale),
            int(168 * scale),
            int(32 * scale),
        ),
    )

    pygame.draw.circle(
        cloud_surface,
        top_color,
        (int(53 * scale), int(57 * scale)),
        int(31 * scale),
    )

    pygame.draw.circle(
        cloud_surface,
        top_color,
        (int(91 * scale), int(39 * scale)),
        int(41 * scale),
    )

    pygame.draw.circle(
        cloud_surface,
        top_color,
        (int(136 * scale), int(46 * scale)),
        int(36 * scale),
    )

    pygame.draw.circle(
        cloud_surface,
        top_color,
        (int(171 * scale), int(60 * scale)),
        int(27 * scale),
    )

    pygame.draw.ellipse(
        cloud_surface,
        top_color,
        (
            int(33 * scale),
            int(52 * scale),
            int(158 * scale),
            int(39 * scale),
        ),
    )

    highlight_color = (
        min(255, top_color[0] + 8),
        min(255, top_color[1] + 8),
        min(255, top_color[2] + 8),
        top_color[3],
    )

    pygame.draw.arc(
        cloud_surface,
        highlight_color,
        (
            int(59 * scale),
            int(12 * scale),
            int(69 * scale),
            int(55 * scale),
        ),
        math.radians(195),
        math.radians(330),
        max(1, int(2 * scale)),
    )

    surface.blit(
        cloud_surface,
        (int(x), int(y)),
    )


# ============================================================
# PROFESYONEL KUŞ SİLÜETLERİ
# ============================================================

def draw_single_bird(
    surface: pygame.Surface,
    x: float,
    y: float,
    scale: float,
    color: tuple[int, int, int],
    flap_value: float,
    direction: int = 1,
    angle: float = 0,
) -> None:
    """
    Gövdeli, başlı, kuyruklu ve hareketli kanatlara
    sahip kuş silüeti çizer.
    """

    quality_multiplier = 3
    base_width = 92
    base_height = 54

    bird_surface = pygame.Surface(
        (
            base_width * quality_multiplier,
            base_height * quality_multiplier,
        ),
        pygame.SRCALPHA,
    )

    def scaled_point(
        point: tuple[float, float],
    ) -> tuple[int, int]:
        return (
            int(point[0] * quality_multiplier),
            int(point[1] * quality_multiplier),
        )

    def scaled_rect(
        rect: tuple[float, float, float, float],
    ) -> pygame.Rect:
        return pygame.Rect(
            int(rect[0] * quality_multiplier),
            int(rect[1] * quality_multiplier),
            int(rect[2] * quality_multiplier),
            int(rect[3] * quality_multiplier),
        )

    body_color = (*color, 255)

    darker_color = (
        max(0, color[0] - 18),
        max(0, color[1] - 18),
        max(0, color[2] - 18),
        235,
    )

    wing_tip_y = 8 - flap_value * 7

    # Arkadaki kanat
    rear_wing_points = [
        scaled_point((39, 25)),
        scaled_point((26, 33 + flap_value * 4)),
        scaled_point((18, 42 + flap_value * 3)),
        scaled_point((35, 35)),
        scaled_point((51, 27)),
    ]

    pygame.draw.polygon(
        bird_surface,
        darker_color,
        rear_wing_points,
    )

    # Öndeki kanat
    front_wing_points = [
        scaled_point((37, 24)),
        scaled_point((25, wing_tip_y)),
        scaled_point((38, 13 + flap_value * 2)),
        scaled_point((55, 23)),
        scaled_point((49, 28)),
    ]

    pygame.draw.polygon(
        bird_surface,
        body_color,
        front_wing_points,
    )

    # Kuyruk
    tail_points = [
        scaled_point((27, 25)),
        scaled_point((12, 18)),
        scaled_point((19, 26)),
        scaled_point((11, 34)),
        scaled_point((30, 29)),
    ]

    pygame.draw.polygon(
        bird_surface,
        body_color,
        tail_points,
    )

    # Gövde
    pygame.draw.ellipse(
        bird_surface,
        body_color,
        scaled_rect((25, 21, 40, 13)),
    )

    # Alt gölge
    pygame.draw.ellipse(
        bird_surface,
        darker_color,
        scaled_rect((29, 28, 31, 5)),
    )

    # Baş
    pygame.draw.circle(
        bird_surface,
        body_color,
        scaled_point((65, 24)),
        int(6 * quality_multiplier),
    )

    # Gaga
    beak_color = (
        min(255, color[0] + 24),
        min(255, color[1] + 20),
        min(255, color[2] + 15),
        255,
    )

    beak_points = [
        scaled_point((69, 22)),
        scaled_point((79, 25)),
        scaled_point((69, 27)),
    ]

    pygame.draw.polygon(
        bird_surface,
        beak_color,
        beak_points,
    )

    # Göz
    pygame.draw.circle(
        bird_surface,
        (5, 7, 10, 235),
        scaled_point((67, 22)),
        quality_multiplier,
    )

    target_width = max(
        1,
        int(base_width * scale),
    )

    target_height = max(
        1,
        int(base_height * scale),
    )

    bird_surface = pygame.transform.smoothscale(
        bird_surface,
        (
            target_width,
            target_height,
        ),
    )

    if direction < 0:
        bird_surface = pygame.transform.flip(
            bird_surface,
            True,
            False,
        )

    if angle != 0:
        bird_surface = pygame.transform.rotate(
            bird_surface,
            angle,
        )

    bird_rect = bird_surface.get_rect(
        center=(int(x), int(y))
    )

    surface.blit(
        bird_surface,
        bird_rect,
    )


def draw_birds(
    surface: pygame.Surface,
    birds: list[
        tuple[
            float,
            float,
            float,
            float,
            float,
            int,
            float,
        ]
    ],
    color: tuple[int, int, int],
    elapsed_time: float,
) -> None:
    """Hareket eden ve kanat çırpan kuş sürüsünü çizer."""

    travel_width = WINDOW_WIDTH + 300

    for (
        starting_x,
        starting_y,
        scale,
        speed,
        phase,
        direction,
        angle,
    ) in birds:

        raw_x = (
            starting_x
            + elapsed_time * speed * direction
        )

        bird_x = (
            (raw_x + 150) % travel_width
        ) - 150

        bird_y = (
            starting_y
            + math.sin(
                elapsed_time * 0.75 + phase
            ) * 3.5
        )

        flap_value = math.sin(
            elapsed_time * 4.2 + phase
        )

        draw_single_bird(
            surface=surface,
            x=bird_x,
            y=bird_y,
            scale=scale,
            color=color,
            flap_value=flap_value,
            direction=direction,
            angle=angle,
        )


# ============================================================
# DAĞ KATMANLARI
# ============================================================

def draw_mountain_layers(
    surface: pygame.Surface,
    scene_mode: str,
) -> None:
    """Uzaklık hissi veren üç dağ katmanı çizer."""

    if scene_mode == "day":
        far_color = (112, 153, 178)
        middle_color = (76, 117, 139)
        near_color = (45, 76, 91)

    elif scene_mode == "sunset":
        far_color = (117, 68, 126)
        middle_color = (74, 48, 91)
        near_color = (43, 34, 62)

    else:
        far_color = (28, 35, 67)
        middle_color = (19, 26, 49)
        near_color = (11, 17, 31)

    far_mountains = [
        (0, 565),
        (80, 520),
        (160, 550),
        (260, 472),
        (360, 545),
        (465, 490),
        (560, 552),
        (670, 478),
        (780, 552),
        (900, 486),
        (1010, 548),
        (1130, 472),
        (1280, 550),
        (1280, WINDOW_HEIGHT),
        (0, WINDOW_HEIGHT),
    ]

    middle_mountains = [
        (0, 600),
        (125, 535),
        (245, 595),
        (375, 515),
        (510, 600),
        (645, 525),
        (785, 595),
        (930, 515),
        (1070, 600),
        (1190, 530),
        (1280, 585),
        (1280, WINDOW_HEIGHT),
        (0, WINDOW_HEIGHT),
    ]

    near_mountains = [
        (0, 630),
        (150, 570),
        (310, 630),
        (475, 555),
        (650, 635),
        (825, 565),
        (1000, 630),
        (1165, 550),
        (1280, 610),
        (1280, WINDOW_HEIGHT),
        (0, WINDOW_HEIGHT),
    ]

    pygame.draw.polygon(
        surface,
        far_color,
        far_mountains,
    )

    pygame.draw.polygon(
        surface,
        middle_color,
        middle_mountains,
    )

    pygame.draw.polygon(
        surface,
        near_color,
        near_mountains,
    )


# ============================================================
# GÜNDÜZ SAHNESİ
# ============================================================

def draw_day_scene(
    surface: pygame.Surface,
    elapsed_time: float,
) -> None:
    """Gündüz gökyüzünü ve hareketli ortamı çizer."""

    draw_multi_stop_gradient(
        surface,
        [
            (0.00, (24, 91, 182)),
            (0.28, (45, 135, 215)),
            (0.58, (105, 187, 234)),
            (0.82, (181, 223, 244)),
            (1.00, (228, 241, 245)),
        ],
    )

    sun_position = (1065, 142)

    draw_radial_glow(
        surface,
        sun_position,
        (255, 226, 139),
        150,
        75,
    )

    pygame.draw.circle(
        surface,
        (255, 230, 132),
        sun_position,
        48,
    )

    pygame.draw.circle(
        surface,
        (255, 247, 199),
        (1050, 126),
        14,
    )

    cloud_data = [
        (-180 + elapsed_time * 13, 135, 0.92),
        (290 + elapsed_time * 8, 225, 0.65),
        (720 + elapsed_time * 6, 105, 0.72),
    ]

    for raw_x, y, scale in cloud_data:
        wrap_width = WINDOW_WIDTH + 300
        cloud_x = (raw_x % wrap_width) - 220

        draw_soft_cloud(
            surface,
            cloud_x,
            y,
            scale,
            (247, 251, 255, 225),
            (124, 170, 199, 105),
        )

    draw_birds(
        surface=surface,
        birds=DAY_BIRDS,
        color=(31, 43, 52),
        elapsed_time=elapsed_time,
    )

    draw_horizon_haze(
        surface,
        450,
        (211, 232, 239),
        150,
        75,
    )

    draw_mountain_layers(
        surface,
        "day",
    )


# ============================================================
# GÜN BATIMI SAHNESİ
# ============================================================

def draw_sunset_scene(
    surface: pygame.Surface,
    elapsed_time: float,
) -> None:
    """Mor, pembe ve turuncu gün batımı sahnesini çizer."""

    draw_multi_stop_gradient(
        surface,
        [
            (0.00, (28, 20, 72)),
            (0.18, (57, 31, 105)),
            (0.38, (120, 52, 135)),
            (0.57, (202, 76, 128)),
            (0.76, (247, 123, 89)),
            (0.90, (255, 177, 101)),
            (1.00, (255, 216, 148)),
        ],
    )

    sun_position = (1045, 447)

    draw_radial_glow(
        surface,
        sun_position,
        (255, 121, 74),
        220,
        80,
    )

    draw_radial_glow(
        surface,
        sun_position,
        (255, 221, 145),
        120,
        95,
    )

    pygame.draw.circle(
        surface,
        (255, 219, 133),
        sun_position,
        55,
    )

    pygame.draw.circle(
        surface,
        (255, 239, 187),
        (1031, 433),
        14,
    )

    draw_horizon_haze(
        surface,
        370,
        (255, 184, 131),
        190,
        90,
    )

    cloud_data = [
        (-170 + elapsed_time * 8, 125, 0.95),
        (340 + elapsed_time * 5, 235, 0.70),
        (760 + elapsed_time * 4, 105, 0.78),
    ]

    for raw_x, y, scale in cloud_data:
        wrap_width = WINDOW_WIDTH + 320
        cloud_x = (raw_x % wrap_width) - 230

        draw_soft_cloud(
            surface,
            cloud_x,
            y,
            scale,
            (174, 90, 147, 170),
            (65, 39, 96, 130),
        )

    streak_surface = pygame.Surface(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.SRCALPHA,
    )

    pygame.draw.ellipse(
        streak_surface,
        (255, 164, 142, 95),
        (65, 315, 360, 26),
    )

    pygame.draw.ellipse(
        streak_surface,
        (251, 135, 142, 75),
        (555, 345, 445, 30),
    )

    pygame.draw.ellipse(
        streak_surface,
        (255, 197, 146, 60),
        (780, 290, 290, 19),
    )

    surface.blit(
        streak_surface,
        (0, 0),
    )

    draw_birds(
        surface=surface,
        birds=SUNSET_BIRDS,
        color=(45, 28, 51),
        elapsed_time=elapsed_time,
    )

    draw_mountain_layers(
        surface,
        "sunset",
    )


# ============================================================
# GECE SAHNESİ
# ============================================================

def draw_night_scene(
    surface: pygame.Surface,
    stars: list[dict[str, float]],
    elapsed_time: float,
) -> None:
    """Ay ve parlayan yıldızlarla gece sahnesini çizer."""

    draw_multi_stop_gradient(
        surface,
        [
            (0.00, (3, 6, 25)),
            (0.45, (7, 12, 43)),
            (0.78, (12, 18, 58)),
            (1.00, (20, 27, 70)),
        ],
    )

    draw_stars(
        surface,
        stars,
        elapsed_time,
    )

    moon_position = (1080, 135)

    draw_radial_glow(
        surface,
        moon_position,
        (180, 195, 255),
        115,
        45,
    )

    pygame.draw.circle(
        surface,
        (250, 244, 207),
        moon_position,
        48,
    )

    pygame.draw.circle(
        surface,
        (8, 13, 44),
        (1101, 117),
        46,
    )

    draw_horizon_haze(
        surface,
        470,
        (76, 92, 149),
        120,
        35,
    )

    draw_mountain_layers(
        surface,
        "night",
    )


# ============================================================
# ŞEHİR
# ============================================================

def draw_city(
    surface: pygame.Surface,
    scene_mode: str,
) -> None:
    """Sahne moduna uygun şehir silüeti çizer."""

    if scene_mode == "day":
        building_color = (47, 68, 86)
        building_top = (77, 101, 120)
        ground_color = (28, 40, 50)
        window_color = (92, 123, 143)
        lights_enabled = False

    elif scene_mode == "sunset":
        building_color = (28, 24, 44)
        building_top = (53, 43, 69)
        ground_color = (17, 15, 28)
        window_color = (255, 184, 82)
        lights_enabled = True

    else:
        building_color = (6, 8, 16)
        building_top = (21, 26, 42)
        ground_color = (2, 4, 10)
        window_color = (241, 190, 72)
        lights_enabled = True

    for building_index, (
        x,
        y,
        width,
        height,
    ) in enumerate(BUILDINGS):

        pygame.draw.rect(
            surface,
            building_color,
            (x, y, width, height),
        )

        pygame.draw.line(
            surface,
            building_top,
            (x, y),
            (x + width, y),
            2,
        )

        if building_index in (3, 7, 10):
            antenna_x = x + width // 2

            pygame.draw.line(
                surface,
                building_top,
                (antenna_x, y),
                (antenna_x, y - 26),
                2,
            )

            pygame.draw.circle(
                surface,
                (218, 63, 73),
                (antenna_x, y - 28),
                3,
            )

        for window_x in range(
            x + 14,
            x + width - 10,
            24,
        ):
            for window_y in range(
                y + 18,
                y + height - 10,
                28,
            ):
                window_number = (
                    window_x // 24
                    + window_y // 28
                    + building_index
                )

                if lights_enabled:
                    should_draw = window_number % 3 != 0
                else:
                    should_draw = window_number % 2 == 0

                if should_draw:
                    pygame.draw.rect(
                        surface,
                        window_color,
                        (
                            window_x,
                            window_y,
                            7,
                            11,
                        ),
                        border_radius=1,
                    )

    pygame.draw.rect(
        surface,
        ground_color,
        (
            0,
            CITY_BASE_Y,
            WINDOW_WIDTH,
            WINDOW_HEIGHT - CITY_BASE_Y,
        ),
    )


# ============================================================
# ARAYÜZ
# ============================================================

def draw_header(
    surface: pygame.Surface,
    title_font: pygame.font.Font,
) -> None:
    """Başlık panelini çizer."""

    header_rect = pygame.Rect(
        24,
        20,
        610,
        66,
    )

    pygame.draw.rect(
        surface,
        PANEL_COLOR,
        header_rect,
        border_radius=14,
    )

    pygame.draw.rect(
        surface,
        PANEL_BORDER,
        header_rect,
        2,
        border_radius=14,
    )

    title = title_font.render(
        "Rüzgâr Etkili Havai Fişek Simülasyonu",
        True,
        WHITE,
    )

    surface.blit(
        title,
        (45, 38),
    )


def draw_mode_buttons(
    surface: pygame.Surface,
    font: pygame.font.Font,
    active_mode: str,
    mouse_position: tuple[int, int],
) -> None:
    """Sahne seçim butonlarını çizer."""

    labels = {
        "day": "Gündüz",
        "sunset": "Gün Batımı",
        "night": "Gece",
    }

    for mode, rect in MODE_BUTTONS.items():
        if active_mode == mode:
            button_color = ACTIVE_BUTTON

        elif rect.collidepoint(mouse_position):
            button_color = BUTTON_HOVER

        else:
            button_color = PASSIVE_BUTTON

        pygame.draw.rect(
            surface,
            button_color,
            rect,
            border_radius=11,
        )

        pygame.draw.rect(
            surface,
            PANEL_BORDER,
            rect,
            2,
            border_radius=11,
        )

        text = font.render(
            labels[mode],
            True,
            WHITE,
        )

        text_rect = text.get_rect(
            center=rect.center
        )

        surface.blit(
            text,
            text_rect,
        )


def draw_bottom_info(
    surface: pygame.Surface,
    font: pygame.font.Font,
    scene_mode: str,
) -> None:
    """Alt bilgilendirme panelini çizer."""

    mode_names = {
        "day": "Gündüz",
        "sunset": "Gün Batımı",
        "night": "Gece",
    }

    panel_rect = pygame.Rect(
        18,
        WINDOW_HEIGHT - 33,
        790,
        26,
    )

    pygame.draw.rect(
        surface,
        (4, 7, 16),
        panel_rect,
        border_radius=7,
    )

    pygame.draw.rect(
        surface,
        (39, 49, 76),
        panel_rect,
        1,
        border_radius=7,
    )

    info_text = font.render(
        (
            f"Sahne: {mode_names[scene_mode]}   |   "
            "1: Gündüz   2: Gün Batımı   "
            "3: Gece   |   ESC: Çıkış"
        ),
        True,
        (196, 207, 232),
    )

    surface.blit(
        info_text,
        (30, WINDOW_HEIGHT - 28),
    )


# ============================================================
# ANA PROGRAM
# ============================================================

def main() -> None:
    pygame.init()

    screen = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT)
    )

    pygame.display.set_caption(
        "Wind Fireworks Simulation"
    )

    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont(
        "arial",
        28,
        bold=True,
    )

    button_font = pygame.font.SysFont(
        "arial",
        18,
        bold=True,
    )

    info_font = pygame.font.SysFont(
        "arial",
        16,
    )

    stars = create_stars(165)

    scene_mode = "night"
    elapsed_time = 0.0
    running = True

    while running:
        delta_time = clock.tick(FPS) / 1000.0
        elapsed_time += delta_time

        mouse_position = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_1:
                    scene_mode = "day"

                elif event.key == pygame.K_2:
                    scene_mode = "sunset"

                elif event.key == pygame.K_3:
                    scene_mode = "night"

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for mode, rect in MODE_BUTTONS.items():
                        if rect.collidepoint(event.pos):
                            scene_mode = mode
                            break

        if scene_mode == "day":
            draw_day_scene(
                screen,
                elapsed_time,
            )

        elif scene_mode == "sunset":
            draw_sunset_scene(
                screen,
                elapsed_time,
            )

        else:
            draw_night_scene(
                screen,
                stars,
                elapsed_time,
            )

        draw_city(
            screen,
            scene_mode,
        )

        draw_header(
            screen,
            title_font,
        )

        draw_mode_buttons(
            screen,
            button_font,
            scene_mode,
            mouse_position,
        )

        draw_bottom_info(
            screen,
            info_font,
            scene_mode,
        )

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()