"""Symbol vocabulary shared with the fontmaker tool."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "fontmaker"))
from symbols import SYMBOL_LABELS  # noqa: E402

__all__ = ["SYMBOL_LABELS"]
