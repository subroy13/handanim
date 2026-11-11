##############
# This code is used to generate a grid of symbols, useful to generate custom font styles
#############

import sys
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
from PIL import Image, ImageDraw, ImageFont

CURRENT_PATH = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_PATH.parent.parent
if str(CURRENT_PATH) not in sys.path:
    sys.path.insert(0, str(CURRENT_PATH))

from symbols import SYMBOL_LABELS  # noqa: E402

# Prefer the local NotoSansMath-Regular.ttf in assets/fonts/ttf/; download only if missing
LOCAL_TTF_PATH = REPO_ROOT / "assets" / "fonts" / "ttf" / "NotoSansMath-Regular.ttf"
FALLBACK_OTF_URL = (
    "https://github.com/googlefonts/noto-fonts/blob/main/unhinted/otf/NotoSansMath/NotoSansMath-Regular.otf?raw=true"
)
FALLBACK_OTF_PATH = CURRENT_PATH / "NotoSansMath-Regular.otf"


def get_grid_label_font_path() -> str:
    if LOCAL_TTF_PATH.is_file():
        return str(LOCAL_TTF_PATH)
    if not FALLBACK_OTF_PATH.is_file():
        urlretrieve(FALLBACK_OTF_URL, str(FALLBACK_OTF_PATH))
    return str(FALLBACK_OTF_PATH)


# SETTINGS
cell_size = 100  # width/height of each box (in px)
cols = 15  # number of boxes per row
font_size = 24  # make text larger
rows = int(np.ceil(len(SYMBOL_LABELS) / cols))  # number of rows needed

# IMAGE SIZE
padding = 10  # padding around grid
header_height = 40  # space for header text above each row
img_width = padding * 2 + cols * cell_size
img_height = padding * 2 + rows * (header_height + cell_size)

if __name__ == "__main__":
    # CREATE BLANK IMAGE (white)
    img = Image.new("RGB", (img_width, img_height), color="white")
    draw = ImageDraw.Draw(img)

    # LOAD font
    font_path = get_grid_label_font_path()
    font = ImageFont.truetype(font_path, font_size)

    # DRAW GRID + LABELS
    for row in range(rows):
        y_top = padding + row * (header_height + cell_size)

        # Draw header text for this row
        label_idx = row * cols
        label_texts = SYMBOL_LABELS[label_idx : label_idx + cols]
        for col, label in enumerate(label_texts):
            x_left = padding + col * cell_size
            bbox = draw.textbbox((0, 0), label, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = x_left + (cell_size - text_w) // 2
            text_y = y_top
            draw.text((text_x, text_y), label, fill="black", font=font)

        # Draw boxes
        box_y_top = y_top + header_height
        for col in range(cols):
            x_left = padding + col * cell_size
            box = [(x_left, box_y_top), (x_left + cell_size, box_y_top + cell_size)]
            draw.rectangle(box, outline="black", width=2)

    # SAVE IMAGE
    output_file = CURRENT_PATH / "glyph_grid_sheet.png"
    img.save(output_file)
    print(f"Saved worksheet grid as {output_file}")
