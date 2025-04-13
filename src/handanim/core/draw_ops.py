from typing import Any, List, Union
from enum import Enum

class OpsType(Enum):
    SET_PEN = "set_pen"
    MOVE_TO = "move_to"
    LINE_TO = "line_to"
    CURVE_TO = "curve_to"

class Ops:
    """
        Describes a drawing operation to be performed
    """
    def __init__(self, type: OpsType, data: Any):
        self.type = type
        self.data = data    # the data to use to perform draw operation


class OpsSet:

    def __init__(self, initial_set: List[Union[dict, Ops]] = []):
        if len(initial_set) == 0 or isinstance(initial_set[0], Ops):
            self.opsset = initial_set
        else:
            self.opsset = [Ops(**d) for d in initial_set]

    def add(self, ops: Union[Ops, dict]):
        if isinstance(ops, dict):
            ops = Ops(**ops)
        self.opsset.append(ops)
