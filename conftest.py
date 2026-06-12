"""Make the public SDK importable for local pytest runs.

The examples depend on the public SDK surface only. When ``verifiable_labs_envs``
is not installed (or an incomplete build shadows it), fall back to a sibling
``vlabs-sdk`` checkout and export it on ``PYTHONPATH`` so the example
subprocesses and the ``vlabs-prm-eval`` CLI resolve the same package. In CI,
where the SDK is pip-installed and no sibling checkout exists, this is a no-op.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_SDK_ROOT = Path(__file__).resolve().parent.parent / "vlabs-sdk"
_SDK_PATHS = [
    p
    for p in (_SDK_ROOT / "src", _SDK_ROOT / "tools" / "vlabs-prm-eval" / "src")
    if p.is_dir()
]

if _SDK_PATHS:
    for _p in reversed(_SDK_PATHS):
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
    _entries = [str(p) for p in _SDK_PATHS]
    _existing = os.environ.get("PYTHONPATH", "")
    if _existing:
        _entries.append(_existing)
    os.environ["PYTHONPATH"] = os.pathsep.join(_entries)
