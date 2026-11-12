import json
import os
import warnings
from importlib.resources import files
from pathlib import Path

_USER_CONFIG_PATH = Path.home() / ".handanim" / "config.json"

BACKSTAY_PERSONAL_USE_WARNING = (
    "Font 'backstay' (BackstaySingleLine) is only allowed for personal use. "
    "For commercial use, please use 'feasibly' or another commercial-friendly font."
)

_BUILTIN_FONTS: dict[str, dict[str, str]] = {
    "feasibly": {"type": "ttf", "file": "FeasiblySingleLine-z8D90.ttf"},
    "backstay": {"type": "ttf", "file": "BackstaySingleLine-rgOw8.ttf", "license": "personal_use_only"},
    "handanimtype1": {"type": "custom", "file": "handanimtype1.json"},
    "noto_sans_math": {"type": "custom", "file": "noto_sans_math_skeleton.json"},
    "hershey_mathlow": {"type": "hershey", "name": "mathlow"},
    "hershey_rowmans": {"type": "hershey", "name": "rowmans"},
    "hershey_cursive": {"type": "hershey", "name": "cursive"},
}


def _load_user_fonts() -> dict[str, dict[str, str]]:
    """Read ~/.handanim/config.json and return its fonts section, or {} if absent."""
    if _USER_CONFIG_PATH.exists():
        try:
            fonts_data = json.loads(_USER_CONFIG_PATH.read_text()).get("fonts", {})
            if isinstance(fonts_data, dict):
                return fonts_data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


# User config wins on name collision so user-registered fonts can override built-ins.
FONTS: dict[str, dict[str, str]] = {**_BUILTIN_FONTS, **_load_user_fonts()}


def list_fonts() -> list[str]:
    """List all available font names (built-in and user-registered)."""
    return list(FONTS.keys())


def get_font_info(font_name: str) -> dict[str, str] | None:
    """Return the metadata dict for font_name, or None if not found."""
    if font_name == "backstay":
        warnings.warn(BACKSTAY_PERSONAL_USE_WARNING, UserWarning, stacklevel=2)
    return FONTS.get(font_name)


def register_font(
    name: str,
    file_path: str | Path,
    font_type: str = "ttf",
    persist: bool = False,
) -> str:
    """Register a TTF or custom JSON font for use in `Text` and `Math`.

    By default (`persist=False`), registers the font in memory for the current
    Python process without modifying `~/.handanim/config.json`.

    Args:
        name: Identifier to use as `font_name` (e.g. `"kalam"`).
        file_path: Path to the `.ttf` or `.json` font file.
        font_type: Either `"ttf"` (default) or `"custom"`.
        persist: If True, also saves the registration in `~/.handanim/config.json`.

    Returns:
        The resolved absolute path to the registered font file.
    """
    if font_type not in ("ttf", "custom"):
        raise ValueError(f"font_type must be 'ttf' or 'custom', got {font_type!r}")
    resolved = Path(file_path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Font file not found: {resolved}")

    entry = {"type": font_type, "file": str(resolved)}
    FONTS[name] = entry

    if persist:
        _USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        config: dict = {}
        if _USER_CONFIG_PATH.exists():
            try:
                loaded = json.loads(_USER_CONFIG_PATH.read_text())
                if isinstance(loaded, dict):
                    config = loaded
            except (json.JSONDecodeError, OSError):
                config = {}
        fonts_sec = config.setdefault("fonts", {})
        if isinstance(fonts_sec, dict):
            fonts_sec[name] = entry
        _USER_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")

    return str(resolved)


def get_font_path(font_name: str) -> str:
    """Return the filesystem path to a TTF or custom JSON font.

    User-registered fonts may supply an absolute path in their 'file' field;
    built-in fonts are resolved via importlib.resources from handanim.fonts.
    """
    if font_name == "backstay":
        warnings.warn(BACKSTAY_PERSONAL_USE_WARNING, UserWarning, stacklevel=2)
    info = FONTS.get(font_name)
    if not info or info.get("type") == "hershey":
        raise ValueError(f"Font {font_name} does not have a physical path")

    file_val = info["file"]
    if os.path.isabs(file_val):
        return file_val

    resource = files("handanim.fonts").joinpath(info["type"], file_val)
    return str(resource)
