"""Backward-compatibility module: handanim_ai is now 'aianim'."""

import sys
import warnings

import aianim

warnings.warn(
    "'handanim_ai' has been renamed to 'aianim'. Please import from 'aianim' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all attributes from aianim
for _attr in dir(aianim):
    if not _attr.startswith("_"):
        globals()[_attr] = getattr(aianim, _attr)

sys.modules["handanim_ai"] = aianim
