"""
Greedy nearest-neighbour stroke ordering.

Given an unordered set of branches (each a list of (row, col) pixel coords),
returns them in an order that minimises total pen-lift travel distance.
Each branch may be reversed if that reduces the distance from the current
pen position to its nearer endpoint.
"""

from __future__ import annotations

import math


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def order_strokes(
    branches: list[list[tuple[int, int]]],
) -> list[list[tuple[int, int]]]:
    """
    Reorder and optionally reverse branches for a pen-up-minimal drawing order.

    Single-pixel branches (dots) are appended at the end.

    Returns a new list (branches themselves are not copied).
    """
    if not branches:
        return []

    dots   = [b for b in branches if len(b) == 1]
    strokes = [b for b in branches if len(b) > 1]

    if not strokes:
        return dots

    ordered: list[list[tuple[int, int]]] = []
    remaining = list(strokes)

    # Start from the branch whose start point is nearest to (0, 0) — top-left
    # of the bitmap, which tends to be the natural writing start position.
    pen = (0, 0)
    first_idx = min(
        range(len(remaining)),
        key=lambda i: min(_dist(pen, remaining[i][0]), _dist(pen, remaining[i][-1])),
    )
    branch = remaining.pop(first_idx)
    if _dist(pen, branch[-1]) < _dist(pen, branch[0]):
        branch = branch[::-1]
    ordered.append(branch)
    pen = branch[-1]

    while remaining:
        # Find the branch (and its orientation) that minimises pen-lift
        best_i, best_dist, best_reversed = 0, float("inf"), False
        for i, b in enumerate(remaining):
            d_fwd = _dist(pen, b[0])
            d_rev = _dist(pen, b[-1])
            d = min(d_fwd, d_rev)
            if d < best_dist:
                best_dist = d
                best_i = i
                best_reversed = d_rev < d_fwd

        branch = remaining.pop(best_i)
        if best_reversed:
            branch = branch[::-1]
        ordered.append(branch)
        pen = branch[-1]

    return ordered + dots
