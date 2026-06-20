import json
import os
from pathlib import Path

_USER_CONFIG_PATH = Path.home() / ".handanim" / "config.json"

_BUILTIN_FONTS = {
    "feasibly": {"type": "ttf", "file": "FeasiblySingleLine-z8D90.ttf"},
    "backstay": {"type": "ttf", "file": "BackstaySingleLine-rgOw8.ttf"},
    "handanimtype1": {"type": "custom", "file": "handanimtype1.json"},
    "hershey_mathlow": {"type": "hershey", "name": "mathlow"},
    "hershey_rowmans": {"type": "hershey", "name": "rowmans"},
    "hershey_cursive": {"type": "hershey", "name": "cursive"},
}


def _load_user_fonts() -> dict:
    """Read ~/.handanim/config.json and return its fonts section, or {} if absent."""
    if _USER_CONFIG_PATH.exists():
        try:
            return json.loads(_USER_CONFIG_PATH.read_text()).get("fonts", {})
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


# User config wins on name collision so user-registered fonts can override built-ins.
FONTS: dict = {**_BUILTIN_FONTS, **_load_user_fonts()}


def list_fonts() -> list[str]:
    """List all available font names (built-in and user-registered)."""
    return list(FONTS.keys())


def get_font_info(font_name: str) -> dict | None:
    """Return the metadata dict for font_name, or None if not found."""
    return FONTS.get(font_name)


def get_font_path(font_name: str) -> str:
    """Return the filesystem path to a TTF or custom JSON font.

    User-registered fonts may supply an absolute path in their 'file' field;
    built-in fonts are resolved relative to assets/fonts/<type>/.
    """
    info = FONTS.get(font_name)
    if not info or info.get("type") == "hershey":
        raise ValueError(f"Font {font_name} does not have a physical path")

    file_val = info["file"]
    if os.path.isabs(file_val):
        return file_val

    assets_root = os.path.join(os.path.dirname(__file__), "../../../assets/fonts/", info["type"])
    return os.path.join(assets_root, file_val)
