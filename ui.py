"""Simulation panels, controls, overlays, and trajectory rendering."""

import math

import pygame

from common import clamp, px_to_m
from config import *
from environment import render_scene
from graphics import draw_radial_glow
from physics import Body
from ui_models import SLIDERS, Slider

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
        "start": "Tam Simülasyon",
        "compact": "Kompakt Mod",
        "help": "Hızlı Kullanım",
        "physics": "Fizik Modeli",
        "exit": "Programdan Çık",
    }

    for key, rect in WELCOME_BUTTONS.items():
        draw_button(
            surface,
            rect,
            labels[key],
            fonts["button"] if key in ("start", "compact") else fonts["small_bold"],
            mouse,
            active=key in ("start", "compact"),
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


def draw_compact_controls(
    surface: pygame.Surface,
    font: pygame.font.Font,
    mouse: tuple[int, int],
    paused: bool,
    auto_show: bool,
    menu_open: bool,
) -> None:
    """Fare hareketinde beliren kompakt kontrol ve ikincil menüyü çizer."""
    layer = pygame.Surface(
        (COMPACT_WIDTH, COMPACT_HEIGHT),
        pygame.SRCALPHA,
    )
    icon_labels = {
        "pause": "▶" if paused else "Ⅱ",
        "menu": "⋯",
        "close": "×",
    }

    for key, rect in COMPACT_HOVER_BUTTONS.items():
        hovered = rect.collidepoint(mouse)
        fill_alpha = 178 if hovered else 118
        pygame.draw.rect(
            layer,
            (8, 13, 28, fill_alpha),
            rect,
            border_radius=6,
        )
        pygame.draw.rect(
            layer,
            (*PANEL_BORDER, 155 if hovered else 90),
            rect,
            1,
            border_radius=6,
        )
        label = font.render(icon_labels[key], True, (224, 231, 245))
        layer.blit(label, label.get_rect(center=rect.center))

    if menu_open:
        menu_labels = {
            "customize": "Gökyüzünü Özelleştir",
            "full": "Tam Simülasyon",
            "home": "Ana Menü",
            "show": (
                "Otomatik Gösteriyi Kapat"
                if auto_show
                else "Otomatik Gösteriyi Aç"
            ),
        }
        for key, rect in COMPACT_MENU_BUTTONS.items():
            hovered = rect.collidepoint(mouse)
            pygame.draw.rect(
                layer,
                (8, 13, 28, 205 if hovered else 178),
                rect,
                border_radius=5,
            )
            pygame.draw.rect(
                layer,
                (*PANEL_BORDER, 145 if hovered else 95),
                rect,
                1,
                border_radius=5,
            )
            label = font.render(menu_labels[key], True, (215, 224, 242))
            layer.blit(label, label.get_rect(center=rect.center))

    surface.blit(layer, (0, 0))


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
