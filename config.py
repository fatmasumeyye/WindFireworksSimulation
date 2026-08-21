"""Simulation constants and fixed UI geometry."""

import pygame

FULL_WIDTH = 1280
FULL_HEIGHT = 720
COMPACT_WIDTH = 432
COMPACT_HEIGHT = 243
COMPACT_CONTROLS_TIMEOUT_MS = 1600

# Mevcut fizik ve çizim sistemi tam boyutlu mantıksal tuvali kullanır.
WIDTH = FULL_WIDTH
HEIGHT = FULL_HEIGHT
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


FIREWORK_AREA_RIGHT = 900
RIGHT_PANEL = pygame.Rect(918, 96, 346, 480)

# Alt araç çubuğu daha ince tutulur; böylece şehir ve gösteri alanı kapanmaz.
BOTTOM_BAR = pygame.Rect(16, 638, 888, 66)

# Karşılama ekranı ve gezinme düğmeleri.
WELCOME_BUTTONS = {
    "start": pygame.Rect(470, 332, 165, 50),
    "compact": pygame.Rect(645, 332, 165, 50),
    "help": pygame.Rect(470, 394, 340, 46),
    "physics": pygame.Rect(470, 450, 340, 46),
    "exit": pygame.Rect(470, 506, 340, 46),
}

COMPACT_VIEW_RECT = pygame.Rect(80, 96, 1024, 576)

COMPACT_HOVER_BUTTONS = {
    "pause": pygame.Rect(COMPACT_WIDTH - 84, 8, 22, 22),
    "menu": pygame.Rect(COMPACT_WIDTH - 56, 8, 22, 22),
    "close": pygame.Rect(COMPACT_WIDTH - 28, 8, 22, 22),
}

COMPACT_MENU_BUTTONS = {
    "customize": pygame.Rect(COMPACT_WIDTH - 194, 38, 186, 24),
    "full": pygame.Rect(COMPACT_WIDTH - 194, 66, 186, 24),
    "home": pygame.Rect(COMPACT_WIDTH - 194, 94, 186, 24),
    "show": pygame.Rect(COMPACT_WIDTH - 194, 122, 186, 24),
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


