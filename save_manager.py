"""Versioned loading, validation, and atomic saving of user preferences."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import FORMATION_OPTIONS, MODE_BUTTONS, PALETTE_OPTIONS, PATTERN_OPTIONS


SAVE_VERSION = 1
APP_DIRECTORY_NAME = "WindFireworksSimulation"
SAVE_FILE_NAME = "save.json"


@dataclass(frozen=True)
class SaveState:
    environment: str = "night"
    pattern: str = "Rastgele"
    palette: str = "Rastgele"
    formation: str = "Tekli"
    auto_show: bool = True
    compact_position: tuple[int, int] | None = None


def get_save_path() -> Path:
    """Return an OS-appropriate per-user data path without creating it."""
    app_data = os.environ.get("APPDATA")
    if app_data:
        base_directory = Path(app_data)
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        base_directory = (
            Path(xdg_config)
            if xdg_config
            else Path.home() / ".config"
        )
    return base_directory / APP_DIRECTORY_NAME / SAVE_FILE_NAME


def _valid_choice(value: Any, options: tuple[str, ...], default: str) -> str:
    return value if isinstance(value, str) and value in options else default


def _sanitize_position(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, dict):
        return None
    x = value.get("compact_x")
    y = value.get("compact_y")
    if (
        not isinstance(x, int)
        or isinstance(x, bool)
        or not isinstance(y, int)
        or isinstance(y, bool)
    ):
        return None
    return x, y


def sanitize_save(data: Any) -> SaveState:
    """Validate a decoded save document and replace bad fields with defaults."""
    defaults = SaveState()
    if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
        return defaults

    preferences = data.get("preferences")
    if not isinstance(preferences, dict):
        preferences = {}

    auto_show = preferences.get("auto_show")
    if not isinstance(auto_show, bool):
        auto_show = defaults.auto_show

    return SaveState(
        environment=_valid_choice(
            preferences.get("environment"),
            tuple(MODE_BUTTONS),
            defaults.environment,
        ),
        pattern=_valid_choice(
            preferences.get("pattern"),
            PATTERN_OPTIONS,
            defaults.pattern,
        ),
        palette=_valid_choice(
            preferences.get("palette"),
            PALETTE_OPTIONS,
            defaults.palette,
        ),
        formation=_valid_choice(
            preferences.get("formation"),
            FORMATION_OPTIONS,
            defaults.formation,
        ),
        auto_show=auto_show,
        compact_position=_sanitize_position(data.get("window")),
    )


def load_save(path: Path | None = None) -> tuple[SaveState, bool]:
    """Load a save; return defaults and False when no usable document exists."""
    save_path = path or get_save_path()
    try:
        with save_path.open("r", encoding="utf-8") as save_file:
            data = json.load(save_file)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return SaveState(), False

    if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
        return SaveState(), False
    return sanitize_save(data), True


def save_state(state: SaveState, path: Path | None = None) -> bool:
    """Atomically replace the save document after a complete temporary write."""
    save_path = path or get_save_path()
    document = {
        "version": SAVE_VERSION,
        "preferences": {
            "environment": state.environment,
            "pattern": state.pattern,
            "palette": state.palette,
            "formation": state.formation,
            "auto_show": state.auto_show,
        },
        "window": {
            "compact_x": (
                state.compact_position[0]
                if state.compact_position is not None
                else None
            ),
            "compact_y": (
                state.compact_position[1]
                if state.compact_position is not None
                else None
            ),
        },
    }

    temporary_path: Path | None = None
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=save_path.parent,
            prefix=f".{save_path.stem}-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(document, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, save_path)
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        return False
    return True

