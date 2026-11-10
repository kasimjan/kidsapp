"""Subtitle layout and timing: word wrapping, spoken-word windows, SRT export."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def wrap_words(text: str, max_chars: int = 44) -> list[list[str]]:
    """Greedy word wrap; returns lines, each a list of words."""
    lines: list[list[str]] = [[]]
    size = 0
    for word in text.split():
        extra = len(word) + (1 if lines[-1] else 0)
        if lines[-1] and size + extra > max_chars:
            lines.append([])
            size = 0
            extra = len(word)
        lines[-1].append(word)
        size += extra
    return lines


def word_windows(words: list[str], seconds: float, lead: float = 0.05) -> list[tuple[float, float]]:
    """When each word is spoken, assuming speech time proportional to length.

    Punctuation adds a pause weight so a comma or full stop 'takes' time.
    """
    if not words:
        return []
    weights = []
    for w in words:
        core = w.strip(".,!?;:")
        pause = 6 if w[-1] in ".!?" else 3 if w[-1] in ",;:" else 0
        weights.append(len(core) + 2 + pause)
    total = float(sum(weights))
    span = max(0.1, seconds - lead)
    out, t = [], lead
    for wt in weights:
        d = span * wt / total
        out.append((t, t + d))
        t += d
    return out


def active_word(windows: list[tuple[float, float]], t: float) -> int:
    """Index of the word being spoken at time t (-1 before, len-1 after the last)."""
    idx = -1
    for i, (start, _) in enumerate(windows):
        if t >= start:
            idx = i
    return idx


def build_cues(narrations: list[str], step_starts: list[float],
               audio_seconds: list[float]) -> list[Cue]:
    return [Cue(s, s + a + 0.15, n) for n, s, a in zip(narrations, step_starts, audio_seconds)]


def _stamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(cues: list[Cue]) -> str:
    blocks = []
    for i, c in enumerate(cues, 1):
        lines = [" ".join(line) for line in wrap_words(c.text, 42)]
        blocks.append(f"{i}\n{_stamp(c.start)} --> {_stamp(c.end)}\n" + "\n".join(lines))
    return "\n\n".join(blocks) + "\n"
