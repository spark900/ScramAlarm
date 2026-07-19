"""Embedded alarm audio.

Design note: a real alarm .wav Base64-encoded into source is typically
tens of kilobytes of opaque text sitting in the middle of a Python file --
easy to corrupt with a stray edit and impossible to review. Instead, this
module *synthesizes* the alarm tone deterministically from a short waveform
description at import time and caches it as an in-memory WAV byte string
(``ALARM_WAV_BYTES``). The effect is identical to shipping an embedded
audio blob -- zero filesystem paths, zero external assets, works the same
on every machine -- but the "embedded asset" is auditable code instead of a
Base64 wall. If you'd rather ship a literal recorded sound, replace the
body of ``_build_alarm_pcm`` with your own PCM decoding and leave
everything else (looping, threading, stop semantics) untouched.
"""
from __future__ import annotations

import io
import math
import struct
import threading
import wave
from typing import Optional

try:
    import simpleaudio as sa
except ImportError:  # pragma: no cover - exercised on systems without ALSA dev libs
    sa = None  # Audio becomes a silent no-op; the visual flash still fires.

SAMPLE_RATE = 22050
_BEEP_HZ = (988, 1319)  # B5 / E6 two-tone siren -- bright and hard to sleep through
_BEEP_MS = 220
_GAP_MS = 90
_FADE_S = 0.01


def _tone(freq: float, duration_ms: int, sample_rate: int = SAMPLE_RATE) -> bytes:
    n_samples = int(sample_rate * duration_ms / 1000)
    fade_samples = max(1, int(sample_rate * _FADE_S))
    buf = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        envelope = min(1.0, i / fade_samples, (n_samples - i) / fade_samples)
        sample = math.sin(2 * math.pi * freq * t) * envelope
        value = int(sample * 32767 * 0.6)
        buf += struct.pack("<h", value)
    return bytes(buf)


def _silence(duration_ms: int, sample_rate: int = SAMPLE_RATE) -> bytes:
    n_samples = int(sample_rate * duration_ms / 1000)
    return b"\x00\x00" * n_samples


def _build_alarm_pcm() -> bytes:
    pattern = bytearray()
    for freq in _BEEP_HZ:
        pattern += _tone(freq, _BEEP_MS)
        pattern += _silence(_GAP_MS)
    return bytes(pattern)


def _pcm_to_wav_bytes(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return out.getvalue()


# Built once at import time. This constant *is* the embedded alarm asset --
# nothing is ever read from disk to produce it.
_ALARM_PCM = _build_alarm_pcm()
ALARM_WAV_BYTES = _pcm_to_wav_bytes(_ALARM_PCM)


class AlarmPlayer:
    """Loops the embedded alarm tone on a background thread until stopped."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._play_obj = None

    @property
    def audio_available(self) -> bool:
        return sa is not None

    def start(self) -> None:
        if sa is None or (self._thread and self._thread.is_alive()):
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        wave_read = wave.open(io.BytesIO(ALARM_WAV_BYTES), "rb")
        n_channels = wave_read.getnchannels()
        sample_width = wave_read.getsampwidth()
        frame_rate = wave_read.getframerate()
        frames = wave_read.readframes(wave_read.getnframes())
        wave_read.close()
        while not self._stop_event.is_set():
            self._play_obj = sa.play_buffer(frames, n_channels, sample_width, frame_rate)
            while self._play_obj.is_playing():
                if self._stop_event.is_set():
                    self._play_obj.stop()
                    break
                self._stop_event.wait(0.05)

    def stop(self) -> None:
        self._stop_event.set()
        if self._play_obj is not None:
            try:
                self._play_obj.stop()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
