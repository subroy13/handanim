#############
# This program allows you to create a database of glyphs from a single filled in grid image
#############

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage import measure
from skimage.morphology import skeletonize
from svgelements import Path as SvgPath
from tqdm import tqdm

ROOT_PATH = Path(__file__).resolve().parent
REPO_ROOT = ROOT_PATH.parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from symbols import SYMBOL_LABELS  # noqa: E402

# === CONSTANTS ===
IMAGE_PATH = str(ROOT_PATH / "sample_symbols.png")
FONT_NAME = "handanimtype1"
OUTPUT_IMAGE_DIR = str(ROOT_PATH / "tmp" / "glyph_images")
OUTPUT_SVG_DIR = str(ROOT_PATH / "tmp" / "glyph_svgs")
OUTPUT_DATABASE_FILE = str(REPO_ROOT / "src" / "handanim" / "fonts" / "custom" / f"{FONT_NAME}.json")
N_ITEMS_IN_ROW = 15  # the number of glyphs in a row in the grid
INNER_PADDING = 10  # 10 pixels are removed as inner padding within each grid
MIN_CELL_SIZE = 50  # the usual size is


def detect_grid_cells(
    image_path,
    min_cell_size=MIN_CELL_SIZE,
    n_items_in_row=N_ITEMS_IN_ROW,
    inner_padding=INNER_PADDING,
):
    """
    This function takes in the filled in image, and uses some standard configuration
    """
    # load in grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, thresh = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    # morph closing
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # filter contours by size
    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > min_cell_size and h > min_cell_size:
            boxes.append((x, y, w, h))

    # sort boxes
    boxes = sorted(boxes, key=lambda b: (b[1] // min_cell_size, b[0]))
    crops = []
    original_img = Image.open(image_path).convert("RGB")
    for box in boxes:
        x, y, w, h = box
        cell_width = w / 15
        for i in range(n_items_in_row):
            crop = original_img.crop(
                (
                    x + i * cell_width + inner_padding,
                    y + inner_padding,
                    x + (i + 1) * cell_width - inner_padding,
                    y + h - inner_padding,
                )
            )
            crops.append(crop)
    return crops


def extract_svg_paths(svg_file):
    tree = ET.parse(svg_file)
    root = tree.getroot()

    # Sometimes vtracer does not explicitly include namespaces — handle both cases
    paths = []
    for elem in root.iter():
        if elem.tag.endswith("path"):
            d_attr = elem.attrib.get("d")
            if d_attr:
                paths.append(d_attr)
    return paths


def compute_combined_bbox(path_strings: list[str]):
    """Compute bounding box of all SVG path strings combined."""
    min_x, min_y, max_x, max_y = (
        float("inf"),
        float("inf"),
        -float("inf"),
        -float("inf"),
    )
    for d_str in path_strings:
        bbox = SvgPath(d_str).bbox()
        if bbox is None:
            continue
        xmin, ymin, xmax, ymax = bbox
        min_x = min(min_x, xmin)
        max_x = max(max_x, xmax)
        min_y = min(min_y, ymin)
        max_y = max(max_y, ymax)
    return min_x, min_y, max_x, max_y


def convert_png_to_svg(img_path: str, svg_path: str):
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

    # Convert to binary (invert so handwriting is white on black)
    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)

    # Normalize binary image to 0-1 for skeletonization
    binary_norm = binary // 255

    # Perform skeletonization
    skeleton = skeletonize(binary_norm)

    # Find contours from skeleton
    contours = measure.find_contours(skeleton, level=0.5)

    # Write SVG from contours
    svg_elem = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        width=str(img.shape[1]),
        height=str(img.shape[0]),
    )
    for contour in contours:
        if len(contour) < 2:
            continue
        path_data = f"M{contour[0][1]},{contour[0][0]}"
        for pt in contour[1:]:
            path_data += f" L{pt[1]},{pt[0]}"
        ET.SubElement(
            svg_elem,
            "path",
            d=path_data,
            stroke="black",
            fill="none",
            **{"stroke-width": "1"},
        )

    tree = ET.ElementTree(svg_elem)
    tree.write(svg_path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    # === Ensure output folders exist ===
    os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_SVG_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_DATABASE_FILE), exist_ok=True)

    crops = detect_grid_cells(IMAGE_PATH)
    glyph_database = {}
    glyph_max_size = float("-inf")

    # Save cropped image
    for i in tqdm(range(len(SYMBOL_LABELS))):
        cropped_img = crops[i]
        label = SYMBOL_LABELS[i]

        safe_label = f"u{ord(label):04X}"  # fallback unicode
        png_filename = f"{safe_label}.png"
        svg_filename = f"{safe_label}.svg"

        png_path = os.path.join(OUTPUT_IMAGE_DIR, png_filename)
        svg_path = os.path.join(OUTPUT_SVG_DIR, svg_filename)

        cropped_img.save(png_path)  # save the png image

        # Run tracing
        convert_png_to_svg(png_path, svg_path)
        try:
            path_list = extract_svg_paths(svg_path)
            min_x, min_y, max_x, max_y = compute_combined_bbox(path_list)
            bbox_height = max_y - min_y
            if bbox_height > glyph_max_size:
                glyph_max_size = bbox_height

            unicode_code = ord(label)
            glyph_database[str(unicode_code)] = path_list  # use string keys in JSON
        except Exception as e:
            print(f"⚠️ Failed to extract paths for {label}: {e}")

    # === Save glyph database ===
    glyph_details = {
        "metadata": {"font_name": FONT_NAME, "font_size": glyph_max_size},
        "glyphs": glyph_database,
    }
    with open(OUTPUT_DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(glyph_details, f, ensure_ascii=False)
    print(f"Saved custom font JSON to {OUTPUT_DATABASE_FILE}")
