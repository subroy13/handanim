from typing import Any, List, Union
from enum import Enum
import json
import numpy as np


class OpsType(Enum):
    SET_PEN = "set_pen"
    MOVE_TO = "move_to"
    LINE_TO = "line_to"
    CURVE_TO = "curve_to"
    QUAD_CURVE_TO = "quad_curve_to"
    CLOSE_PATH = "close_path"


class Ops:
    """
    Describes a drawing operation to be performed
    """

    def __init__(self, type: OpsType, data: Any, partial: float = 1.0):
        self.type = type
        self.data = data  # the data to use to perform draw operation
        self.partial = partial  # how much of the ops needs to be performed

    def __repr__(self):
        if isinstance(self.data, list) or isinstance(self.data, np.ndarray):
            rounded_data = [[np.round(x, 2) for x in point] for point in self.data]
        else:
            rounded_data = self.data
        return f"Ops({self.type}, {json.dumps(rounded_data)}, {self.partial})"


class OpsSet:

    def __init__(self, initial_set: List[Union[dict, Ops]] = []):
        if len(initial_set) == 0 or isinstance(initial_set[0], Ops):
            self.opsset = initial_set
        else:
            self.opsset = [Ops(**d) for d in initial_set]

    def __repr__(self):
        return "OpsSet:" + "\n\t".join([str(ops) for ops in self.opsset])

    def add(self, ops: Union[Ops, dict]):
        if isinstance(ops, dict):
            ops = Ops(**ops)
        self.opsset.append(ops)

    def extend(self, other_opsset: Any):
        if isinstance(other_opsset, OpsSet):
            for op in other_opsset.opsset:
                self.opsset.append(op)
        else:
            raise TypeError("other value is not an opsset")

    def translate(self, offset_x: float, offset_y: float):
        """
        Translates every operation of the opsset by the (offset_x, offset_y) amount
        """
        new_ops = []
        for ops in self.opsset:
            if isinstance(ops.data, list):
                # ops.data is list means, everything is a point
                new_data = [(x + offset_x, y + offset_y) for x, y in ops.data]
                new_ops.append(Ops(ops.type, new_data, ops.partial))
            else:
                new_ops.append(ops)  # keep same ops
        self.opsset = new_ops
