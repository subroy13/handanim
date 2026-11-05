"""Dynamic asset discovery and environment inspection for AI prompts and agents."""

from pathlib import Path
from typing import Any

import handanim.stylings.color as color_module
from handanim.stylings.fonts import get_font_info, get_font_path, list_fonts


def get_available_assets() -> dict[str, Any]:
    """Scan and return available fonts, colors, and asset files."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    assets_dir = repo_root / "assets"
    examples_assets_dir = repo_root / "examples" / "assets"

    ttf_fonts = []
    custom_json_fonts = []
    hershey_fonts = []
    # Use the renderer's registry so reported names work as font_name values.
    # This also includes registered user fonts and resolves assets/fonts correctly.
    for name in list_fonts():
        info = get_font_info(name)
        if info["type"] == "hershey":
            hershey_fonts.append(name)
        elif Path(get_font_path(name)).is_file():
            if info["type"] == "ttf":
                ttf_fonts.append(name)
            elif info["type"] == "custom":
                custom_json_fonts.append(name)

    # Extract color names
    colors = [
        name
        for name in dir(color_module)
        if name.isupper() and not name.startswith("_") and isinstance(getattr(color_module, name), (tuple, list))
    ]

    # Discover image / SVG assets
    media_assets = []
    for search_dir in (assets_dir, examples_assets_dir):
        if search_dir.exists():
            for p in search_dir.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".svg", ".png", ".jpg", ".jpeg"):
                    media_assets.append(str(p.relative_to(repo_root)))

    return {
        "fonts": {
            "ttf": sorted(ttf_fonts),
            "custom_json": sorted(custom_json_fonts),
            "hershey": sorted(hershey_fonts),
        },
        "colors": sorted(colors),
        "media_assets": sorted(media_assets),
    }


def format_assets_markdown() -> str:
    """Format available assets as clean Markdown for prompt injection."""
    catalog = get_available_assets()
    lines = [
        "### Available System Assets",
        "",
        "**Fonts:**",
        f"- TTF Fonts: {', '.join(catalog['fonts']['ttf']) if catalog['fonts']['ttf'] else 'None'}",
        f"- Custom Stroke Fonts: {', '.join(catalog['fonts']['custom_json']) if catalog['fonts']['custom_json'] else 'None'}",
        f"- Hershey Stroke Fonts: {', '.join(catalog['fonts']['hershey'])}",
        "",
        "**Standard Colors (from `handanim.stylings.color`):**",
        f"{', '.join(catalog['colors'])}",
    ]
    if catalog["media_assets"]:
        lines.extend(
            [
                "",
                "**Bundled SVG/Image Assets:**",
                *(f"- `{a}`" for a in catalog["media_assets"]),
            ]
        )
    return "\n".join(lines)
