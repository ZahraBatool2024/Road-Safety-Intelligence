"""Surrogate safety measures: time-to-collision (TTC) and near-miss event logic.

Model: two discs with constant velocity. TTC is the earliest time at which the
distance between their ground-contact points falls to the contact radius.
Pure numpy so it is unit-testable without any CV dependency.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, asdict
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np

from .config import Config
from .tracking import Track


def time_to_collision(p_a: np.ndarray, v_a: np.ndarray, p_b: np.ndarray, v_b: np.ndarray,
                      radius: float) -> Optional[float]:
    """Earliest t >= 0 where |(p_b - p_a) + (v_b - v_a) t| == radius, else None."""
    dp, dv = p_b - p_a, v_b - v_a
    a = float(dv @ dv)
    if a < 1e-9:
        return None                       # no relative motion
    c = float(dp @ dp) - radius ** 2
    if c <= 0:
        return 0.0                        # already in contact
    b = 2.0 * float(dp @ dv)
    if b >= 0:
        return None                       # moving apart
    disc = b * b - 4 * a * c
    if disc < 0:
        return None                       # paths never come within radius
    t = (-b - np.sqrt(disc)) / (2 * a)
    return t if t >= 0 else None


def closest_approach(p_a: np.ndarray, v_a: np.ndarray, p_b: np.ndarray, v_b: np.ndarray) -> Tuple[float, float]:
    """Return (time of closest approach >= 0, minimum distance) under constant velocity."""
    dp, dv = p_b - p_a, v_b - v_a
    a = float(dv @ dv)
    t_star = 0.0 if a < 1e-9 else max(0.0, -float(dp @ dv) / a)
    return t_star, float(np.linalg.norm(dp + dv * t_star))


@dataclass
class Event:
    frame: int
    time_s: float
    id_a: int
    id_b: int
    class_a: str
    class_b: str
    ttc_s: float
    min_dist_px: float
    severity: float          # 0..1, higher = closer call
    x: int
    y: int
    min_dist_m: Optional[float] = None

    @property
    def level(self) -> str:
        return "High" if self.severity >= 0.67 else "Medium" if self.severity >= 0.33 else "Low"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["level"] = self.level
        return d


@dataclass
class FrameAssessment:
    risk: float                        # max severity among flagged pairs this frame (0 if none)
    new_events: List[Event]


class NearMissEngine:
    def __init__(self, cfg: Config, fps: float, names: Mapping[int, str]) -> None:
        self.cfg, self.fps, self.names = cfg, fps, names
        self._vulnerable: Set[int] = set(cfg.vulnerable)
        self._streak: Dict[Tuple[int, int], int] = {}
        self._last_event: Dict[Tuple[int, int], int] = {}
        self._cooldown_frames = int(cfg.event_cooldown_s * fps)

    def _eligible(self, a: Track, b: Track) -> bool:
        va, vb = a.cls in self._vulnerable, b.cls in self._vulnerable
        if va and vb:
            return False                                   # pedestrian<->pedestrian is not a traffic conflict
        if not va and not vb:
            return self.cfg.include_vehicle_pairs
        return True                                         # vulnerable user <-> vehicle

    def assess(self, tracks: Sequence[Track], frame_idx: int, t: float) -> FrameAssessment:
        cfg = self.cfg
        flagged: Set[Tuple[int, int]] = set()
        risk, new_events = 0.0, []

        for a, b in itertools.combinations(tracks, 2):
            if not self._eligible(a, b):
                continue
            size_sum = a.size + b.size
            pa, pb = a.pos, b.pos
            if np.linalg.norm(pb - pa) > cfg.search_factor * size_sum:
                continue
            va, vb = a.velocity(cfg.min_track_points), b.velocity(cfg.min_track_points)
            if va is None or vb is None or np.linalg.norm(vb - va) < cfg.min_rel_speed_px_s:
                continue

            radius = cfg.contact_factor * size_sum
            ttc = time_to_collision(pa, va, pb, vb, radius)
            if ttc is None or ttc > cfg.ttc_threshold_s:
                continue

            key = (min(a.track_id, b.track_id), max(a.track_id, b.track_id))
            flagged.add(key)
            self._streak[key] = self._streak.get(key, 0) + 1
            severity = float(np.clip(1.0 - ttc / cfg.ttc_threshold_s, 0.0, 1.0))
            risk = max(risk, severity)

            if (self._streak[key] >= cfg.min_persist_frames
                    and frame_idx - self._last_event.get(key, -10 ** 9) > self._cooldown_frames):
                self._last_event[key] = frame_idx
                _, dmin = closest_approach(pa, va, pb, vb)
                mid = (pa + pb) / 2.0
                new_events.append(Event(
                    frame=frame_idx, time_s=round(t, 2), id_a=key[0], id_b=key[1],
                    class_a=self.names.get(a.cls, str(a.cls)), class_b=self.names.get(b.cls, str(b.cls)),
                    ttc_s=round(float(ttc), 2), min_dist_px=round(dmin, 1), severity=round(severity, 3),
                    x=int(mid[0]), y=int(mid[1]),
                    min_dist_m=round(dmin / cfg.pixels_per_meter, 2) if cfg.pixels_per_meter else None,
                ))

        for key in [k for k in self._streak if k not in flagged]:   # streak must be consecutive
            del self._streak[key]
        return FrameAssessment(risk=risk, new_events=new_events)
