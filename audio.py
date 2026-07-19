"""Embedded or custom disk-backed alarm audio."""
from __future__ import annotations

import io
import math
import os
import struct
import threading
import wave
from pathlib import Path
from typing import Optional

try:
    import simpleaudio as sa
except ImportError:
    sa = None  # Audio becomes a silent no-op; the visual flash still fires.

SAMPLE_RATE = 22050
_BEEP_HZ = (988, 1319)
_BEEP_MS = 220
_GAP_MS = 90
_FADE_S = 0.01

def _tone(freq: float, duration_ms: int, sample_rate: int = SAMPLE_RATE) -> bytes:
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    fade_samples = int(sample_rate * _FADE_S)
    data = []
    for i in range(n_samples):
        val = math.sin(2.0 * math.pi * freq * i / sample_rate)
        if i < fade_samples:
            val *= (i / fade_samples)
        elif i > n_samples - fade_samples:
            val *= ((n_samples - i) / fade_samples)
        data.append(int(val * 32767))
    return struct.pack(f"<{len(data)}h", *data)

def _silence(duration_ms: int, sample_rate: int = SAMPLE_RATE) -> bytes:
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    return b"\x00" * (n_samples * 2)

def _build_alarm_pcm() -> bytes:
    b1 = _tone(_BEEP_HZ[0], _BEEP_MS)
    b2 = _tone(_BEEP_HZ[1], _BEEP_MS)
    g = _silence(_GAP_MS)
    
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SAMPLE_RATE)
    
    # 3-beep pattern followed by a long pause
    for _ in range(3):
        w.writeframes(b1 + g + b2 + g)
    w.writeframes(_silence(800))
    
    w.close()
    return buf.getvalue()

ALARM_WAV_BYTES = _build_alarm_pcm()

class AlarmPlayer:
    """Manages audio playback loop until stopped."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._play_obj = None
        # Target a custom audio path inside your project repository
        self.custom_audio_path = Path("/home/artem/Projects/ScramAlarm/alarm.wav")

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
        # Check if user has uploaded a custom audio file, otherwise use fallback siren
        if self.custom_audio_path.exists():
            try:
                wave_read = wave.open(str(self.custom_audio_path), "rb")
            except Exception:
                # If the custom file is corrupted, fall back safely to built-in bytes
                wave_read = wave.open(io.BytesIO(ALARM_WAV_BYTES), "rb")
        else:
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
        if self._thread:
            self._thread.join(timeout=1.0)
