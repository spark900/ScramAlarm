"""Dismissal-code generation and keyboard-interrupt suppression.

While an alarm is ringing, the only sanctioned way out is typing the exact
scrambled code shown on screen. This module owns both halves of that
guarantee: generating the code cryptographically (not with the predictable
``random`` module) and shielding the process from Ctrl+C / Ctrl+Z / Ctrl+\\
for the duration of the ring.
"""
from __future__ import annotations

import secrets
import signal
import string
from types import FrameType
from typing import Dict, Optional

_ALPHABET = string.ascii_letters + string.digits
BASE_CODE_LENGTH = 20
SNOOZE_PENALTY = 5


def generate_dismissal_code(length: int = BASE_CODE_LENGTH) -> str:
    """Return a cryptographically random alphanumeric string.

    ``length`` is clamped to at least :data:`BASE_CODE_LENGTH` so callers
    can never accidentally weaken the dismissal challenge.
    """
    length = max(length, BASE_CODE_LENGTH)
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def code_length_after_snoozes(snooze_count: int, base_length: int = BASE_CODE_LENGTH) -> int:
    """Each snooze makes the *next* dismissal code 5 characters longer."""
    return base_length + SNOOZE_PENALTY * max(snooze_count, 0)


class InterruptShield:
    """Context manager that swallows SIGINT/SIGTSTP/SIGQUIT while active.

    Must be entered/exited from the main thread (Python signal handlers can
    only be installed there); it fails silently if used elsewhere so it
    never crashes a background worker.
    """

    _SUPPRESSED = (signal.SIGINT, signal.SIGTSTP, signal.SIGQUIT)

    def __init__(self) -> None:
        self._previous: Dict[int, object] = {}

    @staticmethod
    def _ignore(signum: int, frame: Optional[FrameType]) -> None:  # noqa: ARG004
        return None

    def __enter__(self) -> "InterruptShield":
        for sig in self._SUPPRESSED:
            try:
                self._previous[sig] = signal.signal(sig, self._ignore)
            except (ValueError, OSError):
                # Not the main thread, or signal unsupported on this platform.
                pass
        return self

    def __exit__(self, *exc_info: object) -> None:
        for sig, handler in self._previous.items():
            try:
                signal.signal(sig, handler)  # type: ignore[arg-type]
            except (ValueError, OSError):
                pass
        self._previous.clear()
