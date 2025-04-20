from typing import List, Tuple
import numpy as np

from ..core.styles import SketchStyle, FillStyle


def rotate_points(
    points: List[Tuple[float, float]],  # the points to rotate
    center: Tuple[float, float],  # the center of rotation
    degrees: float,
) -> np.ndarray:
    points = np.array(points)  # (n, 2)
    center = np.array(center)  # (2, )
    angle = np.pi * degrees / 180
    cos, sin = np.cos(angle), np.sin(angle)
    rotation_matrix = np.array([[cos, -sin], [sin, cos]])  # (2, 2)
    return (points - center) @ rotation_matrix + center


def straight_hachure_lines(
    polygon_list: List[List[Tuple[float, float]]],  # list of polygon point collection
    gap: float,
    step_offset: float = 1,
):
    vertex_array = []
    for polygon in polygon_list:
        pp = [point for point in polygon]
        if pp[0][0] != pp[-1][0] or pp[0][1] != pp[-1][1]:
            # the polygon is not closed
            pp.append(pp[0])  # make it closed
        if len(pp) > 2:
            vertex_array.append(
                pp
            )  # if a polygon has less than 2 vertices, then it cannot be filled

    lines = []

    # create sorted edges table
    edges = []
    for vertices in vertex_array:
        for i in range(len(vertices) - 1):
            p1, p2 = vertices[i], vertices[i + 1]
            if p1[1] != p2[1]:
                edges.append(
                    {
                        "ymin": min(p1[1], p2[1]),
                        "ymax": max(p1[1], p2[1]),
                        "x": p1[0] if p1[1] < p2[1] else p2[0],
                        "islope": (p2[0] - p1[0]) / (p2[1] - p1[1]),
                    }
                )
    if len(edges) == 0:
        return np.array(lines)

    # sort the edges
    edges.sort(
        key=lambda e: (e["ymin"], e["x"], e["ymax"])
    )  # sort by ymin, then x, then ymax

    # start the scanning
    active_edges = []
    y = edges[0]["ymin"]  # start from the lowest y value and keep going down
    iteration = 0
    while len(active_edges) > 0 or len(edges) > 0:
        if len(edges) > 0:
            ix = -1
            for i in range(len(edges)):
                if edges[i]["ymin"] > y:
                    break
                ix = i  # first the first index where there is an increment in y
            removed = edges[: (ix + 1)]
            edges = edges[(ix + 1) :]  # remove the edges that are already processed
            active_edges.extend([{"s": y, "edge": edge} for edge in removed])

        active_edges = [
            ae for ae in active_edges if ae["edge"]["ymax"] > y
        ]  # remove the edges that are points (of y-length 0)
        active_edges.sort(key=lambda ae: ae["edge"]["x"])  # sort by x

        # fill between the edges
        if (step_offset != 1) or (iteration % gap == 0):
            if len(active_edges) > 1:
                for i in range(0, len(active_edges), 2):
                    nexti = i + 1
                    if nexti >= len(active_edges):
                        break
                    ce = active_edges[i]["edge"]
                    ne = active_edges[nexti]["edge"]
                    lines.append(
                        [[np.round(ce["x"]), y], [np.round(ne["x"]), y]]
                    )  # add the hachure line

        y += step_offset
        active_edges_new = []
        for ae in active_edges:
            ae["edge"]["x"] += step_offset * ae["edge"]["islope"]
            active_edges_new.append(ae)
        iteration += 1
    return np.array(lines)


def hachure_lines(
    polygon_list: List[List[Tuple[float, float]]],  # list of polygon point collection
    gap: float,
    angle: float,
    offset: float = 1,
):
    rotation_center = np.array([0, 0])
    if angle != 0:
        rotated_polygons = [
            rotate_points(polygon, rotation_center, angle) for polygon in polygon_list
        ]  # do initial rotation of the polygon
    else:
        rotated_polygons = polygon_list

    # get the straight hachure lines for this rotated polygons
    rotated_lines = straight_hachure_lines(rotated_polygons, gap, offset)
    if angle != 0:
        # rotate the lines back
        lines = [rotate_points(line, rotation_center, -angle) for line in rotated_lines]
    else:
        lines = rotated_lines
    return lines


def polygon_hachure_lines(
    polygon_list: List[List[Tuple[float, float]]],  # list of polygon point collection
    fill_style=FillStyle(),
    sketch_style=SketchStyle(),
):
    angle = fill_style.hachure_angle + 90
    gap = np.round(max(fill_style.hachure_gap, 0.1))
    skipoffset = 1
    if sketch_style.roughness >= 1:
        # get a random number
        r = np.random.uniform()
        if r > 0.7:
            skipoffset = gap

    return hachure_lines(polygon_list, gap, angle, skipoffset)
