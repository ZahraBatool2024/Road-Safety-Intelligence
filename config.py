"""Central configuration. Every tunable lives here so experiments are reproducible."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Tuple

# COCO class ids used by pretrained YOLO models
PERSON, BICYCLE, CAR, MOTORCYCLE, BUS, TRUCK = 0, 1, 2, 3, 5, 7


@dataclass
class Config:
    # --- detector / tracker -------------------------------------------------
    model: str = "yolo11m.pt"
    conf: float = 0.35
    imgsz: int = 960
    tracker: str = "bytetrack.yaml"
    classes: Tuple[int, ...] = (PERSON, BICYCLE, CAR, MOTORCYCLE, BUS, TRUCK)
    vulnerable: Tuple[int, ...] = (PERSON, BICYCLE, MOTORCYCLE)

    # --- kinematics ---------------------------------------------------------
    history: int = 12                 # frames used to fit velocity (least squares)
    min_track_points: int = 5         # min observations before a velocity is trusted
    stale_seconds: float = 2.0        # drop tracks unseen for this long

    # --- risk model ---------------------------------------------------------
    ttc_threshold_s: float = 1.5      # flag when time-to-collision <= this
    contact_factor: float = 0.4       # contact radius = factor * (size_a + size_b)
    search_factor: float = 4.0        # ignore pairs farther than factor * (size_a + size_b)
    min_rel_speed_px_s: float = 15.0  # ignore jitter-level relative motion
    min_persist_frames: int = 3       # consecutive flagged frames required (kills ID-switch noise)
    event_cooldown_s: float = 2.0     # min gap between events for the same pair
    include_vehicle_pairs: bool = False  # also analyse vehicle<->vehicle conflicts

    # --- optional calibration ----------------------------------------------
    pixels_per_meter: Optional[float] = None  # set to report distances in meters

    # --- output -------------------------------------------------------------
    alert_display_s: float = 1.0
    trail_length: int = 30

    def to_dict(self) -> dict:
        return asdict(self)
