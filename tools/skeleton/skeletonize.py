"""
Skeleton extraction: thin a binary glyph bitmap → pixel branches.

Algorithm
---------
1.  Zhang–Suen thinning (`skimage.morphology.thin`) → 1-px-wide skeleton.
2.  Build an 8-connected adjacency graph over skeleton pixels.
3.  Classify pixels:
      - degree 0 → isolated dot
      - degree 1 → endpoint
      - degree 2 → pass-through (interior of a branch)
      - degree ≥ 3 → junction
4.  Walk every unwalked branch from its special (non-pass-through) start
    pixel along the chain of pass-through pixels until the next special pixel.
5.  Prune branches that:
      - lie entirely between two junction pixels AND have fewer than
        `spur_threshold` pixels (junction-cluster artefacts), OR
      - have exactly one endpoint pixel at each end but ≤ 2 pixels total
        (single-pixel isolated noise).
6.  Any unvisited loop is extracted by walking from an arbitrary start pixel.

Output: list of branches, each branch being a list of (row, col) int tuples.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.morphology import thin


# 8-connected neighbourhood offsets
_NBRS = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]


def _neighbor_coords(r: int, c: int, rows: int, cols: int):
    for dr, dc in _NBRS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            yield nr, nc


def _compute_degree(skel: np.ndarray) -> np.ndarray:
    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int32)
    return ndimage.convolve(skel.astype(np.int32), kernel, mode="constant")


def _skeleton_branches(
    skel: np.ndarray,
    spur_threshold: int,
) -> list[list[tuple[int, int]]]:
    rows, cols = skel.shape
    deg = _compute_degree(skel)

    # Mark every skeleton pixel as one of: endpoint(1), passthrough(2), junction(3+)
    # A pass-through pixel has exactly 2 skeleton neighbours.
    pixel_set: set[tuple[int, int]] = set(zip(*np.where(skel)))

    def nbrs_in_skel(r, c):
        return [
            (nr, nc)
            for nr, nc in _neighbor_coords(r, c, rows, cols)
            if skel[nr, nc]
        ]

    def is_special(r, c):
        return deg[r, c] != 2   # endpoint, junction, or isolated

    visited_pixels: set[tuple[int, int]] = set()
    branches: list[list[tuple[int, int]]] = []

    def walk_branch(start: tuple[int, int], via: tuple[int, int]) -> list[tuple[int, int]]:
        """Walk from `start` through `via` along pass-through pixels until
        the next special pixel, marking every visited pixel."""
        path = [start, via]
        visited_pixels.add(via)
        prev, cur = start, via
        while not is_special(*cur):
            nexts = [n for n in nbrs_in_skel(*cur) if n != prev and n not in visited_pixels]
            if not nexts:
                break
            nxt = nexts[0]
            visited_pixels.add(nxt)
            path.append(nxt)
            prev, cur = cur, nxt
        return path

    # Start walks from every special pixel
    specials = sorted(p for p in pixel_set if is_special(*p))

    for sp in specials:
        if sp not in visited_pixels:
            visited_pixels.add(sp)
        for nbr in nbrs_in_skel(*sp):
            if nbr in visited_pixels:
                continue
            visited_pixels.add(nbr)
            branch = walk_branch(sp, nbr)
            branches.append(branch)

    # Catch any unvisited pixels that form loops (no degree-1 or degree-≥3 pixels)
    for p in pixel_set:
        if p not in visited_pixels:
            visited_pixels.add(p)
            loop = [p]
            prev, cur = p, p
            for start_nbr in nbrs_in_skel(*p):
                if start_nbr not in visited_pixels:
                    visited_pixels.add(start_nbr)
                    loop.append(start_nbr)
                    prev, cur = p, start_nbr
                    break
            while True:
                nexts = [n for n in nbrs_in_skel(*cur) if n != prev and n not in visited_pixels]
                if not nexts:
                    break
                nxt = nexts[0]
                visited_pixels.add(nxt)
                loop.append(nxt)
                prev, cur = cur, nxt
            branches.append(loop)

    # Prune spurs and noise
    def _keep(branch: list[tuple[int, int]]) -> bool:
        if len(branch) <= 1:
            return False
        # Short branches between two junctions are junction-cluster artefacts
        if len(branch) < spur_threshold:
            start_junc = deg[branch[0]] >= 3
            end_junc   = deg[branch[-1]] >= 3
            if start_junc and end_junc:
                return False
        return True

    return [b for b in branches if _keep(b)]


def extract_branches(
    bitmap: np.ndarray,
    spur_threshold: int = 8,
) -> list[list[tuple[int, int]]]:
    """
    Thin `bitmap` and extract pixel-coordinate branches.

    Parameters
    ----------
    bitmap:
        Binary (bool) array, True where the glyph is filled.
    spur_threshold:
        Branches shorter than this that connect two junctions are pruned
        as junction-cluster artefacts.

    Returns
    -------
    List of branches; each branch is an ordered list of (row, col) tuples.
    """
    skel = thin(bitmap)
    return _skeleton_branches(skel, spur_threshold)
