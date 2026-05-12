"""
Stroke sequence preprocessing for Sketch-RNN training.

Pipeline:
  raw JSON (collect.py output)
  → normalize (translate to origin, scale to unit box)
  → convert to delta format  (Δx, Δy, pen_state)
  → augment  (random scale, rotation, elastic noise)
  → split train / val / test
  → save as .npz for training

Pen state encoding (3-class):
  0 — pen down  (drawing, move to next point)
  1 — pen up    (lift pen, move without drawing)
  2 — end       (end-of-sequence sentinel)

Usage:
  python preprocess.py --input strokes.json --output dataset.npz
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_raw(json_path: str | Path) -> list[dict]:
    """Load the raw JSON produced by collect.py."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Conversion: absolute coords → delta format
# ---------------------------------------------------------------------------

def strokes_to_deltas(strokes: list[list[list[float]]]) -> np.ndarray:
    """
    Convert absolute stroke lists to delta format.

    Returns an (N, 3) array where each row is [Δx, Δy, pen_state].
    The last row always has pen_state == 2 (end-of-sequence).
    """
    points: list[tuple[float, float, int]] = []
    for stroke in strokes:
        for i, (x, y) in enumerate(stroke):
            pen = 0 if i < len(stroke) - 1 else 1  # last point of stroke → pen-up
            points.append((x, y, pen))
    if not points:
        return np.zeros((1, 3), dtype=np.float32)

    # Replace last pen-up with end-of-sequence
    points[-1] = (points[-1][0], points[-1][1], 2)

    coords = np.array([(x, y) for x, y, _ in points], dtype=np.float32)
    pens = np.array([p for _, _, p in points], dtype=np.float32)

    deltas = np.diff(coords, axis=0, prepend=coords[:1])
    return np.column_stack([deltas, pens])


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize(seq: np.ndarray) -> np.ndarray:
    """Translate so first point is at origin; scale so std of Δx,Δy is 1."""
    seq = seq.copy()
    std = seq[:, :2].std() + 1e-8
    seq[:, :2] /= std
    return seq


# ---------------------------------------------------------------------------
# Augmentation
# ---------------------------------------------------------------------------

def augment(seq: np.ndarray, scale_range=(0.9, 1.1), angle_range=(-10, 10)) -> np.ndarray:
    """Random scale and rotation applied to the Δx, Δy columns."""
    seq = seq.copy()
    scale = random.uniform(*scale_range)
    angle = np.deg2rad(random.uniform(*angle_range))
    rot = np.array([[np.cos(angle), -np.sin(angle)],
                    [np.sin(angle),  np.cos(angle)]], dtype=np.float32)
    seq[:, :2] = (seq[:, :2] * scale) @ rot.T
    return seq


# ---------------------------------------------------------------------------
# Dataset building
# ---------------------------------------------------------------------------

def build_dataset(
    raw: list[dict],
    val_frac: float = 0.1,
    test_frac: float = 0.1,
    augment_copies: int = 5,
) -> dict[str, list[np.ndarray]]:
    """
    Convert raw records to train/val/test splits of delta-format sequences.

    Returns a dict with keys "train", "val", "test", each containing a list
    of (N, 3) numpy arrays.
    """
    sequences: list[np.ndarray] = []
    for record in raw:
        seq = strokes_to_deltas(record["strokes"])
        seq = normalize(seq)
        sequences.append(seq)
        for _ in range(augment_copies):
            sequences.append(augment(seq))

    random.shuffle(sequences)
    n = len(sequences)
    n_val = max(1, int(n * val_frac))
    n_test = max(1, int(n * test_frac))

    return {
        "train": sequences[n_val + n_test:],
        "val": sequences[:n_val],
        "test": sequences[n_val: n_val + n_test],
    }


def save_dataset(splits: dict[str, list[np.ndarray]], output_path: str | Path):
    """Save the dataset splits to a .npz file (object array of variable-length sequences)."""
    np.savez(
        output_path,
        train=np.array(splits["train"], dtype=object),
        val=np.array(splits["val"], dtype=object),
        test=np.array(splits["test"], dtype=object),
    )
    total = sum(len(v) for v in splits.values())
    print(f"Saved {total} sequences → {output_path}")
    for split, seqs in splits.items():
        print(f"  {split}: {len(seqs)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess stroke sequences for training.")
    parser.add_argument("--input", required=True, help="Path to strokes.json from collect.py")
    parser.add_argument("--output", default="dataset.npz", help="Output .npz path")
    parser.add_argument("--val-frac", type=float, default=0.1)
    parser.add_argument("--test-frac", type=float, default=0.1)
    parser.add_argument("--augment-copies", type=int, default=5)
    args = parser.parse_args()

    raw = load_raw(args.input)
    print(f"Loaded {len(raw)} raw glyph records.")
    splits = build_dataset(raw, args.val_frac, args.test_frac, args.augment_copies)
    save_dataset(splits, args.output)
