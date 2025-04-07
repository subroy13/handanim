import numpy as np
from ..transformed_context import TransformedContext

class HachureFillPatterns:
    DIAGONAL = "diagonal"
    ANTI_DIAGONAL = "anti_diagonal"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    CHECKER = "checker"
    CHECKER_DIAGONAL = "checker_diagonal"

def apply_hachure_fill_patterns(
    ctx: TransformedContext,
    bound_box: tuple[float, float, float, float],  # (x, y, width, height) to specify the bounding box
    fill_type: HachureFillPatterns,  # the type of fill pattern to apply
    fill_spacing: float = 10,  # spacing between lines
    fill_color: tuple[float, float, float] = (0, 0, 0),  # color of the fill pattern
    pastel: bool = False,  # whether to use pastel colors
    stroke_width: float = 1,  # width of the lines
):
    # pastel fill effect
    r, g, b = fill_color
    ctx.set_source_rgba(r, g, b, 0.3 if pastel else 1.0)
    ctx.set_line_width(1 if not pastel else 2)  # thicker lines for pastel
    
    # extract the bounding box parameters
    x, y, width, height = bound_box

    # now draw the filling pattern
    if fill_type == HachureFillPatterns.HORIZONTAL:
        for ysub in np.arange(y, y + height, fill_spacing):
            ctx.move_to(x, ysub)
            ctx.line_to(x + width, ysub)
            ctx.stroke()
    elif fill_type == HachureFillPatterns.VERTICAL:
        for xsub in np.arange(x, x + width, fill_spacing):
            ctx.move_to(xsub, y)
            ctx.line_to(xsub, y + height)
            ctx.stroke()
    elif fill_type == HachureFillPatterns.CHECKER:
        # both horizontal and vertical lines
        for ysub in np.arange(y, y + height, fill_spacing):
            ctx.move_to(x, ysub)
            ctx.line_to(x + width, ysub)
            ctx.stroke()
        for xsub in np.arange(x, x + width, fill_spacing):
            ctx.move_to(xsub, y)
            ctx.line_to(xsub, y + height)
            ctx.stroke()
    elif fill_type == HachureFillPatterns.DIAGONAL:
        # diagonal hatch lines
        angle = np.radians(45)
        tan_a = np.tan(angle)
        for ysub in np.arange(y, y + height + width * tan_a, fill_spacing):
            ctx.move_to(x, ysub)
            ctx.line_to(x + width, ysub - width / tan_a)
            ctx.stroke()
    elif fill_type == HachureFillPatterns.ANTI_DIAGONAL:
        # anti-diagonal hatch lines
        angle = np.radians(45)
        tan_a = np.tan(angle)
        for ysub in np.arange(y - width * tan_a, y + height, fill_spacing):
            ctx.move_to(x, ysub)
            ctx.line_to(x + width, ysub + width * tan_a)
            ctx.stroke()
    elif fill_type == HachureFillPatterns.CHECKER_DIAGONAL:
        # both diagonal and anti-diagonal lines
        angle = np.radians(45)
        tan_a = np.tan(angle)
        for ysub in np.arange(y, y + height + width * tan_a, fill_spacing):
            ctx.move_to(x, ysub)
            ctx.line_to(x + width, ysub - width / tan_a)
            ctx.stroke()
        for ysub in np.arange(y - width * tan_a, y + height, fill_spacing):
            ctx.move_to(x, ysub)
            ctx.line_to(x + width, ysub + width * tan_a)
            ctx.stroke()
    else:
        raise ValueError(f"Unknown fill type: {fill_type}")
    