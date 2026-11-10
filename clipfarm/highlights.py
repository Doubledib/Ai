"""Find clip-worthy windows.

Signal 1 (always on): audio excitement - shouting, laughter, explosions and chat-reading
spikes show up as loudness well above the stream's own baseline.
Signal 2 (optional): transcript, used by ai.py to rerank and title candidates.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

import numpy as np

SR = 16000


@dataclass
class Window:
    start: float
    end: float
    score: float
    text: str = ""


def audio_envelope(path: str, hop: float = 0.5) -> np.ndarray:
    """RMS loudness (dB) per `hop` seconds."""
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        check=True, capture_output=True).stdout
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    n = int(SR * hop)
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-10)
    return 20 * np.log10(rms)


def find_windows(path: str, top_n: int = 5, min_len: float = 15.0, max_len: float = 45.0,
                 lead_in: float = 6.0, hop: float = 0.5, min_z: float = 1.0) -> list[Window]:
    """Pick up to top_n non-overlapping windows around the loudest sustained moments."""
    env = audio_envelope(path, hop)
    if len(env) < 4:
        return []
    med = np.median(env)
    mad = np.median(np.abs(env - med)) * 1.4826 + 1e-6
    z = (env - med) / mad                      # robust z-score vs. this stream's baseline
    k = max(1, int(3.0 / hop))                 # 3 s smoothing: reward sustained hype, not clicks
    smooth = np.convolve(z, np.ones(k) / k, mode="same")
    duration = len(env) * hop

    windows: list[Window] = []
    taken = np.zeros(len(env), dtype=bool)
    for idx in np.argsort(smooth)[::-1]:
        if len(windows) >= top_n or smooth[idx] < min_z:
            break
        if taken[idx]:
            continue
        # grow outward while still above half the peak's excitement
        lo = hi = idx
        thresh = max(min_z / 2, smooth[idx] / 2)
        while lo > 0 and smooth[lo - 1] > thresh:
            lo -= 1
        while hi < len(env) - 1 and smooth[hi + 1] > thresh:
            hi += 1
        start = max(0.0, lo * hop - lead_in)   # include the setup before the payoff
        end = min(duration, (hi + 1) * hop + 2.0)
        if end - start < min_len:
            end = min(duration, start + min_len)
            start = max(0.0, end - min_len)
        if end - start > max_len:
            end = start + max_len
        a, b = int(start / hop), int(end / hop)
        if taken[a:b].any():
            continue
        taken[a:b] = True
        windows.append(Window(round(start, 2), round(end, 2), round(float(smooth[idx]), 2)))
    return sorted(windows, key=lambda w: -w.score)


def transcribe(path: str, model: str = "small") -> list[tuple[float, float, str]]:
    """Word-level transcript via faster-whisper. Returns [] if the model isn't available."""
    try:
        from faster_whisper import WhisperModel
        segs, _ = WhisperModel(model, compute_type="int8").transcribe(str(path), word_timestamps=True)
        return [(w.start, w.end, w.word.strip()) for s in segs for w in (s.words or [])]
    except Exception as e:  # no model cache / no network: captions are optional
        print(f"[transcribe] skipped: {type(e).__name__}: {e}")
        return []


def attach_text(windows: list[Window], words: list[tuple[float, float, str]]) -> None:
    for w in windows:
        w.text = " ".join(t for s, e, t in words if s >= w.start and e <= w.end)
