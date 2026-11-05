"""Deterministic compiler: translates a structured ScenePlan into clean, executable Python code."""

from typing import Any

from .schema import ScenePlan


def _format_style(styles: dict[str, Any]) -> tuple[str, str, str]:
    """Format stroke_style, sketch_style, and fill_style expressions."""
    color = styles.get("color", "BLACK")
    width = styles.get("width", 2)
    roughness = styles.get("roughness", 3)
    fill_color = styles.get("fill_color")
    hachure_gap = styles.get("hachure_gap", 10)

    stroke_expr = f"StrokeStyle(color={color}, width={width})"
    sketch_expr = f"SketchStyle(roughness={roughness})"
    fill_expr = f"FillStyle(color={fill_color}, hachure_gap={hachure_gap})" if fill_color else "None"
    return stroke_expr, sketch_expr, fill_expr


def _sanitize_primitive_params(
    d_type: str, raw_params: dict[str, Any], raw_styles: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Clean and map parameters into exact constructor arguments for each primitive."""
    params = dict(raw_params)
    styles = dict(raw_styles)

    # If color was placed in params instead of styles, migrate it
    if "color" in params:
        styles["color"] = params.pop("color")
    if "fill_color" in params:
        styles["fill_color"] = params.pop("fill_color")

    if d_type == "Text":
        # Text takes (text, position, font_size)
        if "size" in params and "font_size" not in params:
            params["font_size"] = params.pop("size")
        if "position" not in params and "x" in params and "y" in params:
            params["position"] = (params.pop("x"), params.pop("y"))
        elif "position" in params and isinstance(params["position"], list):
            params["position"] = tuple(params["position"])
        params.pop("font", None)
        valid_keys = {"text", "position", "font_size", "scale_factor"}
        params = {k: v for k, v in params.items() if k in valid_keys}

    elif d_type in ("Circle", "Ellipse"):
        if "center" in params and isinstance(params["center"], list):
            params["center"] = tuple(params["center"])
        elif "center" not in params and "x" in params and "y" in params:
            params["center"] = (params.pop("x"), params.pop("y"))
        valid_keys = {"center", "radius"} if d_type == "Circle" else {"center", "width", "height"}
        params = {k: v for k, v in params.items() if k in valid_keys}

    elif d_type in ("Rectangle", "Square", "RoundedRectangle", "RoundedSquare"):
        if "top_left" not in params and "x" in params and "y" in params:
            params["top_left"] = (params.pop("x"), params.pop("y"))
        elif "top_left" in params and isinstance(params["top_left"], list):
            params["top_left"] = tuple(params["top_left"])
        valid_keys = {"top_left", "side"} if "Square" in d_type else {"top_left", "width", "height"}
        params = {k: v for k, v in params.items() if k in valid_keys}

    elif d_type in ("Line", "Arrow"):
        if "start" in params and isinstance(params["start"], list):
            params["start"] = tuple(params["start"])
        if "end" in params and isinstance(params["end"], list):
            params["end"] = tuple(params["end"])
        params = {k: v for k, v in params.items() if k in {"start", "end"}}

    elif d_type == "CurvedArrow":
        if "start" in params and isinstance(params["start"], list):
            params["start"] = tuple(params["start"])
        if "end" in params and isinstance(params["end"], list):
            params["end"] = tuple(params["end"])
        if "control_offset" in params and isinstance(params["control_offset"], list):
            params["control_offset"] = tuple(params["control_offset"])
        params = {k: v for k, v in params.items() if k in {"start", "end", "control_offset"}}

    elif d_type == "Math":
        if "expression" in params and "latex_expr" not in params:
            params["latex_expr"] = params.pop("expression")
        if "position" not in params and "x" in params and "y" in params:
            params["position"] = (params.pop("x"), params.pop("y"))
        elif "position" in params and isinstance(params["position"], list):
            params["position"] = tuple(params["position"])
        params = {k: v for k, v in params.items() if k in {"latex_expr", "position", "font_size"}}

    return params, styles


def plan_to_python(plan: ScenePlan | dict[str, Any], output_path: str = "output.mp4") -> str:
    """Compile a structured ScenePlan into canonical handanim Python code.

    Args:
        plan: A ScenePlan instance or equivalent dictionary.
        output_path: Target video file path written to scene.render().

    Returns:
        A standalone, reproducible Python script string.
    """
    if isinstance(plan, dict):
        plan = ScenePlan.from_dict(plan)

    referenced_primitives: set[str] = set()
    referenced_animations: set[str] = set()

    for scene in plan.scenes:
        for d in scene.drawables:
            referenced_primitives.add(d.type)
        for a in scene.animations:
            referenced_animations.add(a.type)

    # Standard imports
    lines = [
        '"""Generated by handanim-ai compiler."""',
        "",
        "from handanim import (",
        "    Scene,",
        "    StrokeStyle,",
        "    SketchStyle,",
        "    FillStyle,",
    ]
    for prim in sorted(referenced_primitives):
        lines.append(f"    {prim},")
    for anim in sorted(referenced_animations):
        lines.append(f"    {anim},")
    lines.extend(
        [
            ")",
            "from handanim.stylings.color import BLACK, BLUE, RED, GREEN, YELLOW, ORANGE, WHITE, GRAY",
            "",
            "# 1. Initialize Scene (World space: 0..1777 x 0..1000)",
            f"scene = Scene(width={plan.width}, height={plan.height})",
            "",
        ]
    )

    # Build objects and animations per scene
    for scene in plan.scenes:
        lines.append(f"# --- Scene {scene.id}: {scene.title} ---")
        for d in scene.drawables:
            clean_params, clean_styles = _sanitize_primitive_params(d.type, d.params, d.styles)
            stroke_expr, sketch_expr, fill_expr = _format_style(clean_styles)
            param_items = []
            for k, v in clean_params.items():
                if isinstance(v, str) and not v.startswith(("(", "[", "{")):
                    param_items.append(f'{k}="{v}"')
                else:
                    param_items.append(f"{k}={v}")

            param_items.append(f"stroke_style={stroke_expr}")
            param_items.append(f"sketch_style={sketch_expr}")
            if fill_expr != "None":
                param_items.append(f"fill_style={fill_expr}")

            params_str = ", ".join(param_items)
            lines.append(f"{d.id} = {d.type}({params_str})")

        lines.append("")
        for a in scene.animations:
            extra_params = ", ".join(f"{k}={v}" for k, v in a.params.items())
            extra_str = f", {extra_params}" if extra_params else ""
            lines.append(
                f"scene.add("
                f"event={a.type}(start_time={a.start_time}, duration={a.duration}{extra_str}), "
                f"drawable={a.drawable_id}"
                f")"
            )
        lines.append("")

    # Final render call
    duration_str = f", max_length={plan.total_duration}" if plan.total_duration > 0 else ""
    lines.extend(
        [
            "# Render animation",
            f'scene.render("{output_path}"{duration_str})',
            "",
        ]
    )

    return "\n".join(lines)
