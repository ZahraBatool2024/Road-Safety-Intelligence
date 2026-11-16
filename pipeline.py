"""End-to-end pipeline: video -> detect -> track -> kinematics -> risk -> artefacts."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import cv2
import numpy as np
import pandas as pd

from .config import Config
from .risk import Event, NearMissEngine
from .tracking import Detection, TrackBook
from .viz import annotate, hotspot, make_heatmap

log = logging.getLogger("nearmiss")
ProgressFn = Callable[[int, int], None]


@dataclass
class AnalysisResult:
    events: List[Event]
    risk_series: List[float]
    fps: float
    n_frames: int
    summary: Dict
    paths: Dict[str, Path] = field(default_factory=dict)

    @property
    def events_df(self) -> pd.DataFrame:
        return pd.DataFrame([e.to_dict() for e in self.events])

    @property
    def risk_df(self) -> pd.DataFrame:
        return pd.DataFrame({"time_s": np.arange(len(self.risk_series)) / self.fps, "risk": self.risk_series})


def load_model(model_name: str):
    from ultralytics import YOLO  # imported lazily so the risk logic stays importable without it
    return YOLO(model_name)


def _transcode_h264(src: Path, dst: Path) -> Path:
    """Browsers cannot play OpenCV's mp4v; re-encode to H.264 when ffmpeg is available."""
    exe = shutil.which("ffmpeg")
    if exe is None:
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return src
    try:
        subprocess.run([exe, "-y", "-i", str(src), "-vcodec", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "23", "-preset", "veryfast", "-movflags", "+faststart", str(dst)],
                       check=True, capture_output=True)
        src.unlink(missing_ok=True)
        return dst
    except Exception as exc:  # pragma: no cover
        log.warning("H.264 transcode failed (%s); keeping mp4v output", exc)
        return src


def _extract(result) -> List[Detection]:
    boxes = result.boxes
    if boxes is None or boxes.id is None:
        return []
    xyxy = boxes.xyxy.cpu().numpy()
    ids = boxes.id.int().cpu().tolist()
    cls = boxes.cls.int().cpu().tolist()
    return [Detection(i, c, tuple(map(float, b))) for i, c, b in zip(ids, cls, xyxy)]


def analyze_video(video_path: str | Path, cfg: Optional[Config] = None, out_dir: str | Path = "outputs",
                  model=None, progress: Optional[ProgressFn] = None,
                  max_frames: Optional[int] = None) -> AnalysisResult:
    cfg = cfg or Config()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = float(fps) if fps and fps > 1 else 30.0
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if max_frames:
        total = min(total, max_frames) if total else max_frames

    model = model or load_model(cfg.model)
    if getattr(model, "predictor", None) is not None:
        model.predictor = None                 # reset tracker state between videos
    names = model.names

    raw_path = out_dir / "annotated_raw.mp4"
    writer = cv2.VideoWriter(str(raw_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    book = TrackBook(cfg.history, cfg.trail_length, int(cfg.stale_seconds * fps))
    engine = NearMissEngine(cfg, fps, names)
    heat = np.zeros((height, width), np.float32)
    events: List[Event] = []
    risk_series: List[float] = []
    alerts: List[tuple] = []                   # (Event, frames_left)
    alert_frames = max(1, int(cfg.alert_display_s * fps))
    reference = None
    vulnerable = set(cfg.vulnerable)

    t0 = time.time()
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok or (max_frames and frame_idx >= max_frames):
            break
        t = frame_idx / fps

        res = model.track(frame, persist=True, classes=list(cfg.classes), conf=cfg.conf,
                          imgsz=cfg.imgsz, tracker=cfg.tracker, verbose=False)[0]
        active = book.update(frame_idx, t, _extract(res))
        assessment = engine.assess(active, frame_idx, t)

        for ev in assessment.new_events:
            events.append(ev)
            alerts.append((ev, alert_frames))
            if 0 <= ev.y < height and 0 <= ev.x < width:
                heat[ev.y, ev.x] += ev.severity
        risk_series.append(assessment.risk)

        if reference is None and total and frame_idx >= total // 2:
            reference = frame.copy()           # clean frame for the heatmap background
        elif reference is None and not total and frame_idx == 30:
            reference = frame.copy()

        annotate(frame, active, names, vulnerable, alerts, len(events), assessment.risk, t)
        writer.write(frame)
        alerts = [(e, n - 1) for e, n in alerts if n > 1]

        frame_idx += 1
        if progress and frame_idx % 5 == 0:
            progress(frame_idx, total or frame_idx)

    cap.release()
    writer.release()
    if reference is None:
        reference = np.zeros((height, width, 3), np.uint8)
    if progress:
        progress(frame_idx, frame_idx)

    elapsed = time.time() - t0
    duration = frame_idx / fps
    summary = _summarise(events, risk_series, book, heat, cfg, duration, frame_idx, elapsed, (width, height))

    result = AnalysisResult(events, risk_series, fps, frame_idx, summary)
    video_path_out = _transcode_h264(raw_path, out_dir / "annotated.mp4")
    heatmap_path = out_dir / "heatmap.png"
    cv2.imwrite(str(heatmap_path), make_heatmap(heat, reference))
    result.events_df.to_csv(out_dir / "events.csv", index=False)
    result.risk_df.to_csv(out_dir / "risk_timeline.csv", index=False)
    (out_dir / "summary.json").write_text(json.dumps({"config": cfg.to_dict(), "summary": summary}, indent=2))
    result.paths = {"video": video_path_out, "heatmap": heatmap_path, "events": out_dir / "events.csv",
                    "risk": out_dir / "risk_timeline.csv", "summary": out_dir / "summary.json"}
    log.info("Done: %d events in %.1fs (%.1f fps)", len(events), elapsed, frame_idx / max(elapsed, 1e-9))
    return result


def _summarise(events, risk_series, book, heat, cfg, duration, frames, elapsed, size) -> Dict:
    spot = hotspot(heat)
    pairs: Dict[str, int] = {}
    for e in events:
        key = " + ".join(sorted([e.class_a, e.class_b]))
        pairs[key] = pairs.get(key, 0) + 1
    ttcs = [e.ttc_s for e in events]
    risk = np.asarray(risk_series) if risk_series else np.zeros(1)
    return {
        "video_size": list(size),
        "duration_s": round(duration, 1),
        "frames": frames,
        "unique_tracks": len(book.seen_ids),
        "near_miss_events": len(events),
        "events_per_minute": round(len(events) / (duration / 60), 2) if duration > 0 else 0.0,
        "min_ttc_s": min(ttcs) if ttcs else None,
        "mean_ttc_s": round(float(np.mean(ttcs)), 2) if ttcs else None,
        "mean_risk": round(float(risk.mean()), 4),
        "pct_time_at_risk": round(float((risk > 0).mean() * 100), 1),
        "hotspot_xy": list(spot) if spot else None,
        "conflict_types": dict(sorted(pairs.items(), key=lambda kv: -kv[1])),
        "units": "meters" if cfg.pixels_per_meter else "pixels",
        "processing_fps": round(frames / max(elapsed, 1e-9), 1),
    }
