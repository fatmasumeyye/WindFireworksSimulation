"""Top-level Pygame application coordination."""

from __future__ import annotations

import pygame

from config import *
from customization import (
    CUSTOMIZE_SIZE,
    RETURN_RECT,
    TAB_RECTS,
    card_rects,
    draw_customization_screen,
)
from environment import (
    create_stars,
    draw_cycle_scene,
    present_compact_scene,
    render_scene,
    scene_visibility,
)
from fireworks import Shell
from formations import (
    LaunchRequest,
    create_launch_requests,
    cycle_option,
    spawn_shell_from_request,
)
from particles import FireworkStar, Flash, ShellSpark, Smoke
from save_manager import SaveState, load_save, save_state
from ui import *
from ui_models import SLIDERS
from weather import WeatherParticle, draw_weather, effective_density_multiplier, precipitation_burn_loss, update_weather_particles, weather_visibility_multiplier


def clamp_compact_position(
    position: tuple[int, int] | None,
) -> tuple[int, int] | None:
    """Keep a restored compact window fully visible on the primary desktop."""
    if position is None:
        return None
    desktop_sizes = pygame.display.get_desktop_sizes()
    if not desktop_sizes:
        return None
    desktop_width, desktop_height = desktop_sizes[0]
    return (
        max(0, min(position[0], desktop_width - COMPACT_WIDTH)),
        max(0, min(position[1], desktop_height - COMPACT_HEIGHT)),
    )


def create_compact_window(
    position: tuple[int, int] | None = None,
) -> tuple[pygame.Surface, pygame.Window]:
    """Create the frameless companion window and restore its session position."""
    surface = pygame.display.set_mode(
        (COMPACT_WIDTH, COMPACT_HEIGHT),
        pygame.NOFRAME,
    )
    window = pygame.Window.from_display_module()
    window.always_on_top = True
    pygame.display.set_caption("Wind Fireworks Simulation")
    safe_position = clamp_compact_position(position)
    if safe_position is not None:
        window.position = safe_position
    return surface, window


def main() -> None:
    pygame.init()

    screen = pygame.display.set_mode((FULL_WIDTH, FULL_HEIGHT))
    pygame.display.set_caption("Wind Fireworks Simulation")
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont("arial", 28, bold=True),
        "button": pygame.font.SysFont("arial", 17, bold=True),
        "small": pygame.font.SysFont("arial", 14),
        "small_bold": pygame.font.SysFont("arial", 14, bold=True),
        "custom_title": pygame.font.SysFont("arial", 30, bold=True),
    }

    background_stars = create_stars(165)
    scene_first = pygame.Surface((WIDTH, HEIGHT))
    scene_second = pygame.Surface((WIDTH, HEIGHT))
    compact_scene = pygame.Surface((WIDTH, HEIGHT))

    saved_state, save_loaded = load_save()

    mode = saved_state.environment
    visible_mode = mode
    active_tab = "launch"

    # Uygulama önce karşılama ekranında açılır. Ayar paneli simülasyona
    # girildiğinde kapalıdır; kullanıcı TAB veya kenar düğmesiyle açabilir.
    app_state = "welcome"
    view_mode = "full"
    compact_controls_visible = False
    compact_menu_open = False
    compact_last_motion_ms = 0
    compact_window: pygame.Window | None = None
    compact_saved_position = saved_state.compact_position
    compact_dragging = False
    compact_drag_offset = (0, 0)
    customize_tab = "environments"
    welcome_modal: str | None = None
    panel_open = False
    home_confirmation = False

    paused = False
    auto_show = saved_state.auto_show if save_loaded else False
    formula_visible = False
    trajectory_enabled = True

    selected_pattern = saved_state.pattern
    selected_palette = saved_state.palette
    selected_formation = saved_state.formation
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

    def persist_preferences() -> None:
        nonlocal compact_saved_position, save_loaded
        if view_mode == "compact" and compact_window is not None:
            compact_saved_position = tuple(compact_window.position)
        saved = save_state(
            SaveState(
                environment=mode if mode in MODE_BUTTONS else "night",
                pattern=selected_pattern,
                palette=selected_palette,
                formation=selected_formation,
                auto_show=auto_show,
                compact_position=compact_saved_position,
            )
        )
        if saved:
            save_loaded = True

    running = True

    while running:
        frame_dt = min(clock.tick(FPS) / 1000.0, 0.04)
        mouse = pygame.mouse.get_pos()

        if view_mode == "compact":
            mouse_inside = pygame.mouse.get_focused()
            if not mouse_inside:
                compact_menu_open = False
            compact_controls_visible = mouse_inside and (
                compact_menu_open
                or pygame.time.get_ticks() - compact_last_motion_ms
                <= COMPACT_CONTROLS_TIMEOUT_MS
            )
        else:
            compact_controls_visible = False
            compact_menu_open = False
            compact_dragging = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if view_mode == "compact" and event.type == pygame.MOUSEMOTION:
                compact_last_motion_ms = pygame.time.get_ticks()
                compact_controls_visible = True
                if compact_dragging and compact_window is not None:
                    window_x, window_y = compact_window.position
                    global_mouse_x = window_x + event.pos[0]
                    global_mouse_y = window_y + event.pos[1]
                    compact_window.position = (
                        global_mouse_x - compact_drag_offset[0],
                        global_mouse_y - compact_drag_offset[1],
                    )

            if (
                view_mode == "compact"
                and event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
            ):
                drag_finished = compact_dragging
                compact_dragging = False
                if drag_finished:
                    persist_preferences()

            if view_mode == "customize":
                return_to_compact = (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE
                ) or (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and RETURN_RECT.collidepoint(event.pos)
                )
                if return_to_compact:
                    screen, compact_window = create_compact_window(
                        compact_saved_position
                    )
                    view_mode = "compact"
                    compact_last_motion_ms = pygame.time.get_ticks()
                    continue

                if (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                ):
                    for tab_key, tab_rect in TAB_RECTS.items():
                        if tab_rect.collidepoint(event.pos):
                            customize_tab = tab_key
                            break
                    else:
                        for value, card_rect in card_rects(
                            customize_tab
                        ).items():
                            if not card_rect.collidepoint(event.pos):
                                continue
                            if customize_tab == "environments":
                                mode = value
                                visible_mode = value
                                cycle_enabled = False
                            elif customize_tab == "patterns":
                                selected_pattern = value
                            elif customize_tab == "palettes":
                                selected_palette = value
                            else:
                                selected_formation = value
                            persist_preferences()
                            break
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
                            view_mode = "full"
                            screen = pygame.display.set_mode(
                                (FULL_WIDTH, FULL_HEIGHT)
                            )
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
                        view_mode = "full"
                        screen = pygame.display.set_mode(
                            (FULL_WIDTH, FULL_HEIGHT)
                        )
                        app_state = "simulation"
                        panel_open = False
                    elif WELCOME_BUTTONS["compact"].collidepoint(event.pos):
                        view_mode = "compact"
                        screen, compact_window = create_compact_window(
                            compact_saved_position
                        )
                        app_state = "simulation"
                        panel_open = False
                        if not save_loaded:
                            auto_show = True
                        compact_menu_open = False
                        compact_last_motion_ms = pygame.time.get_ticks()
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
                        persist_preferences()
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_1:
                    mode = "day"
                    visible_mode = mode
                    cycle_enabled = False
                    persist_preferences()
                elif event.key == pygame.K_2:
                    mode = "sunset"
                    visible_mode = mode
                    cycle_enabled = False
                    persist_preferences()
                elif event.key == pygame.K_3:
                    mode = "night"
                    visible_mode = mode
                    cycle_enabled = False
                    persist_preferences()
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
                    persist_preferences()
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
                    if view_mode == "full":
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
                    if view_mode == "full":
                        panel_open = not panel_open
                        dragging_slider = None

            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button in (1, 3)
            ):
                direction = 1 if event.button == 1 else -1
                clicked = False

                if view_mode == "compact":
                    if event.button != 1:
                        continue
                    if (
                        compact_controls_visible
                        and COMPACT_HOVER_BUTTONS["pause"].collidepoint(event.pos)
                    ):
                        paused = not paused
                    elif (
                        compact_controls_visible
                        and COMPACT_HOVER_BUTTONS["menu"].collidepoint(event.pos)
                    ):
                        compact_menu_open = not compact_menu_open
                    elif (
                        compact_controls_visible
                        and COMPACT_HOVER_BUTTONS["close"].collidepoint(event.pos)
                    ):
                        running = False
                    elif (
                        compact_menu_open
                        and COMPACT_MENU_BUTTONS["customize"].collidepoint(
                            event.pos
                        )
                    ):
                        compact_dragging = False
                        if compact_window is not None:
                            compact_saved_position = tuple(
                                compact_window.position
                            )
                            persist_preferences()
                            compact_window.always_on_top = False
                        compact_window = None
                        screen = pygame.display.set_mode(CUSTOMIZE_SIZE)
                        pygame.display.set_caption(
                            "Gökyüzünü Özelleştir"
                        )
                        view_mode = "customize"
                        compact_menu_open = False
                    elif (
                        compact_menu_open
                        and COMPACT_MENU_BUTTONS["full"].collidepoint(event.pos)
                    ):
                        view_mode = "full"
                        compact_dragging = False
                        if compact_window is not None:
                            compact_saved_position = tuple(
                                compact_window.position
                            )
                            persist_preferences()
                            compact_window.always_on_top = False
                        compact_window = None
                        screen = pygame.display.set_mode(
                            (FULL_WIDTH, FULL_HEIGHT)
                        )
                        panel_open = False
                        compact_menu_open = False
                    elif (
                        compact_menu_open
                        and COMPACT_MENU_BUTTONS["home"].collidepoint(event.pos)
                    ):
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
                        panel_open = False
                        welcome_modal = None
                        app_state = "welcome"
                        view_mode = "full"
                        compact_dragging = False
                        if compact_window is not None:
                            compact_saved_position = tuple(
                                compact_window.position
                            )
                            persist_preferences()
                            compact_window.always_on_top = False
                        compact_window = None
                        screen = pygame.display.set_mode(
                            (FULL_WIDTH, FULL_HEIGHT)
                        )
                        compact_menu_open = False
                    elif (
                        compact_menu_open
                        and COMPACT_MENU_BUTTONS["show"].collidepoint(event.pos)
                    ):
                        auto_show = not auto_show
                        persist_preferences()
                        compact_menu_open = False
                    else:
                        over_primary_control = any(
                            rect.collidepoint(event.pos)
                            for rect in COMPACT_HOVER_BUTTONS.values()
                        )
                        over_menu_option = compact_menu_open and any(
                            rect.collidepoint(event.pos)
                            for rect in COMPACT_MENU_BUTTONS.values()
                        )
                        if not over_primary_control and not over_menu_option:
                            compact_menu_open = False
                            compact_dragging = True
                            compact_drag_offset = event.pos
                    continue

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
                        persist_preferences()
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
                    persist_preferences()
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
                        persist_preferences()
                    elif palette_rect.collidepoint(event.pos):
                        selected_palette = cycle_option(
                            PALETTE_OPTIONS,
                            selected_palette,
                            direction,
                        )
                        persist_preferences()
                    elif formation_rect.collidepoint(event.pos):
                        selected_formation = cycle_option(
                            FORMATION_OPTIONS,
                            selected_formation,
                            direction,
                        )
                        persist_preferences()
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

        if view_mode == "customize":
            draw_customization_screen(
                screen,
                fonts,
                mouse,
                customize_tab,
                mode,
                selected_pattern,
                selected_palette,
                selected_formation,
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

        render_target = compact_scene if view_mode == "compact" else screen

        if cycle_enabled:
            visible_mode, scene_visibility_value = draw_cycle_scene(
                render_target,
                scene_first,
                scene_second,
                background_stars,
                time_s,
                cycle_elapsed,
                CYCLE_SPEEDS[cycle_speed_key],
            )
        else:
            render_scene(
                render_target,
                mode,
                background_stars,
                time_s,
            )
            visible_mode = mode
            scene_visibility_value = scene_visibility(mode)

        if (
            view_mode == "full"
            and trajectory_enabled
            and (not panel_open or active_tab == "launch")
        ):
            draw_trajectory_preview(
                render_target,
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

        render_target.blit(
            glow,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_ADD,
        )
        render_target.blit(effects, (0, 0))

        draw_weather(
            render_target,
            weather_particles,
            weather_name,
            SLIDERS["precipitation"].value,
        )

        if view_mode == "compact":
            present_compact_scene(screen, render_target)
            if compact_controls_visible:
                draw_compact_controls(
                    screen,
                    fonts["small_bold"],
                    mouse,
                    paused,
                    auto_show,
                    compact_menu_open,
                )
        else:
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

    persist_preferences()
    pygame.quit()
