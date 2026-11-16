"""Drawing helpers: frame annotation, HUD and heatmap rendering (OpenCV)."""
from __future__ import annotations

from typing import Mapping, Sequence, Set, Tuple

import cv2
import numpy as np

from .risk import Event
from .tracking import Track

VULN_COLOR = (0, 165, 255)     # orange (BGR)
VEH_COLOR = (80, 200, 80)      # green
ALERT_COLOR = (0, 0, 255)      # red


def _risk_color(risk: float) -> Tuple[int, int, int]:
    """Green -> yellow -> red as risk rises."""
    r = float(np.clip(risk, 0, 1))
    return (0, int(255 * (1 - max(0.0, r - 0.5) * 2)), int(255 * min(1.0, r * 2)))


def annotate(frame: np.ndarray, tracks: Sequence[Track], names: Mapping[int, str], vulnerable: Set[int],
             alerts: Sequence[Tuple[Event, int]], n_events: int, risk: float, t: float) -> np.ndarray:
    for tr in tracks:
        color = VULN_COLOR if tr.cls in vulnerable else VEH_COLOR
        x1, y1, x2, y2 = map(int, tr.box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{names.get(tr.cls, tr.cls)} #{tr.track_id}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        pts = np.array(tr.trail, dtype=np.int32).reshape(-1, 1, 2)
        if len(pts) > 1:
            cv2.polylines(frame, [pts], False, color, 1, cv2.LINE_AA)

    for ev, frames_left in alerts:
        radius = 25 + int(10 * np.sin(frames_left))
        cv2.circle(frame, (ev.x, ev.y), radius, ALERT_COLOR, 3, cv2.LINE_AA)
        cv2.putText(frame, f"NEAR MISS  TTC {ev.ttc_s:.1f}s", (ev.x - 70, ev.y - radius - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, ALERT_COLOR, 2, cv2.LINE_AA)

    # HUD
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (270, 84), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
    cv2.putText(frame, f"t = {t:6.1f}s   events: {n_events}", (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, "risk", (20, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.rectangle(frame, (65, 54), (255, 70), (80, 80, 80), 1)
    cv2.rectangle(frame, (66, 55), (66 + int(188 * risk), 69), _risk_color(risk), -1)
    return frame


def make_heatmap(heat: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Blend a normalised, blurred event-density map onto a reference frame."""
    h, w = heat.shape
    sigma = max(h, w) / 40.0
    hm = cv2.GaussianBlur(heat, (0, 0), sigma)
    if hm.max() <= 0:
        return reference.copy()
    norm = hm / hm.max()
    color = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_JET)
    alpha = (np.clip(norm * 1.5, 0, 1) * 0.65)[..., None]
    return (reference * (1 - alpha) + color * alpha).astype(np.uint8)


def hotspot(heat: np.ndarray) -> Tuple[int, int] | None:
    h, w = heat.shape
    hm = cv2.GaussianBlur(heat, (0, 0), max(h, w) / 40.0)
    if hm.max() <= 0:
        return None
    y, x = np.unravel_index(np.argmax(hm), hm.shape)
    return int(x), int(y)
