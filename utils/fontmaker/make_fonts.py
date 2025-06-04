#############
# This program allows you to create a database of glyphs from a single filled in grid image
#############

import os
import json
import numpy as np
from PIL import Image

# import vtracer
import cv2
import xml.etree.ElementTree as ET
from svgpathtools import svg2paths
from tqdm import tqdm
from skimage.morphology import skeletonize
from skimage import measure
import svgwrite

from symbols import SYMBOL_LABELS

# === CONSTANTS ===
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(ROOT_PATH, "sample_symbols.png")
FONT_NAME = "handanimtype1"
OUTPUT_IMAGE_DIR = os.path.join(ROOT_PATH, "tmp", "glyph_images")
OUTPUT_SVG_DIR = os.path.join(ROOT_PATH, "tmp", "glyph_svgs")
OUTPUT_DATABASE_FILE = os.path.join(ROOT_PATH, f"{FONT_NAME}.json")
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


def compute_combined_bbox(paths):
    """Compute bounding box of all paths combined."""
    min_x, min_y, max_x, max_y = (
        float("inf"),
        float("inf"),
        -float("inf"),
        -float("inf"),
    )
    for path in paths:
        xmin, xmax, ymin, ymax = path.bbox()
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

    # Create SVG from contours
    dwg = svgwrite.Drawing(size=(img.shape[1], img.shape[0]))
    for contour in contours:
        if len(contour) < 2:
            continue
        path_data = f"M{contour[0][1]},{contour[0][0]}"
        for pt in contour[1:]:
            path_data += f" L{pt[1]},{pt[0]}"
        dwg.add(dwg.path(d=path_data, stroke="black", fill="none", stroke_width=1))

    dwg.saveas(svg_path)


if __name__ == "__main__":
    # === Ensure output folders exist ===
    os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_SVG_DIR, exist_ok=True)

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
            paths, attributes = svg2paths(svg_path)
            min_x, min_y, max_x, max_y = compute_combined_bbox(paths)
            bbox_height = max_y - min_y
            if bbox_height > glyph_max_size:
                glyph_max_size = bbox_height

            path_list = extract_svg_paths(svg_path)
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
