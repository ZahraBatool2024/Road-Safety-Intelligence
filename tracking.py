"""Track bookkeeping and robust velocity estimation (pure numpy, no CV deps)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import numpy as np


@dataclass
class Detection:
    track_id: int
    cls: int
    box: Tuple[float, float, float, float]  # x1, y1, x2, y2


@dataclass
class Track:
    track_id: int
    cls: int
    history: int = 12
    trail_length: int = 30
    size: float = 0.0
    last_frame: int = -1
    box: Tuple[float, float, float, float] = (0, 0, 0, 0)
    t: Deque[float] = field(init=False)
    x: Deque[float] = field(init=False)
    y: Deque[float] = field(init=False)
    trail: Deque[Tuple[int, int]] = field(init=False)

    def __post_init__(self) -> None:
        self.t = deque(maxlen=self.history)
        self.x = deque(maxlen=self.history)
        self.y = deque(maxlen=self.history)
        self.trail = deque(maxlen=self.trail_length)

    def update(self, frame_idx: int, t: float, box: Tuple[float, float, float, float], cls: int) -> None:
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) / 2.0, y2  # bottom-centre ~ ground contact point
        self.t.append(t)
        self.x.append(cx)
        self.y.append(cy)
        self.trail.append((int(cx), int(cy)))
        self.size = float(np.sqrt(max(x2 - x1, 1.0) * max(y2 - y1, 1.0)))
        self.box = box
        self.cls = cls
        self.last_frame = frame_idx

    @property
    def pos(self) -> np.ndarray:
        return np.array([self.x[-1], self.y[-1]], dtype=float)

    def velocity(self, min_points: int = 5) -> Optional[np.ndarray]:
        """Least-squares velocity (px/s) over the recent window; robust to detector jitter."""
        if len(self.t) < min_points:
            return None
        t = np.asarray(self.t, dtype=float)
        if t[-1] - t[0] <= 1e-9:
            return None
        vx = np.polyfit(t, np.asarray(self.x, dtype=float), 1)[0]
        vy = np.polyfit(t, np.asarray(self.y, dtype=float), 1)[0]
        return np.array([vx, vy], dtype=float)


class TrackBook:
    """Keeps the live set of tracks and prunes stale ones."""

    def __init__(self, history: int, trail_length: int, stale_frames: int) -> None:
        self.history = history
        self.trail_length = trail_length
        self.stale_frames = stale_frames
        self.tracks: Dict[int, Track] = {}
        self.seen_ids: set = set()

    def update(self, frame_idx: int, t: float, detections: Iterable[Detection]) -> List[Track]:
        active: List[Track] = []
        for d in detections:
            tr = self.tracks.get(d.track_id)
            if tr is None:
                tr = Track(d.track_id, d.cls, self.history, self.trail_length)
                self.tracks[d.track_id] = tr
                self.seen_ids.add(d.track_id)
            tr.update(frame_idx, t, d.box, d.cls)
            active.append(tr)
        stale = [k for k, v in self.tracks.items() if frame_idx - v.last_frame > self.stale_frames]
        for k in stale:
            del self.tracks[k]
        return active
