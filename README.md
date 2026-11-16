# Road Safety Intelligence

_Near-miss traffic analytics from ordinary video, powered by a pretrained YOLO11 model._

Turns raw traffic video into **safety analytics** using only a **pretrained YOLO11** model (no training):
detect road users -> track them -> estimate motion -> compute **time-to-collision (TTC)** -> flag near-misses,
build a hotspot heatmap and a risk timeline.

## Why this is more than "detect and draw boxes"
| Layer | What it adds |
|---|---|
| YOLO11 (COCO) | person, bicycle, motorcycle, car, bus, truck detection |
| ByteTrack | persistent IDs across frames |
| Kinematics | least-squares velocity per track (robust to jitter) |
| Risk model | pairwise TTC with size-adaptive contact radius |
| Filtering | persistence + cooldown to suppress ID-switch false alarms |
| Analytics | events table with severity levels, events/min, % time at risk, heatmap, risk timeline, auto-written key finding |
| Evaluation | precision / recall / F1 against hand-labelled events |

## Quick start
```bash
pip install -r requirements.txt
python run.py traffic.mp4 --out outputs          # CLI
streamlit run app.py                              # Road Safety Intelligence web app (top navigation)
pytest -q                                         # unit tests
```
Useful flags: `--model yolo11n.pt` (fast) / `yolo11x.pt` (accurate), `--ttc 2.0`, `--persist 4`,
`--ppm 20` (pixels per metre if known), `--vehicle-pairs`, `--max-frames 900`.

Outputs in `outputs/`: `annotated.mp4`, `events.csv`, `heatmap.png`, `risk_timeline.csv`, `summary.json`.

## Method
1. Ultralytics `model.track` (YOLO11 + ByteTrack) filtered to six COCO road-user classes.
2. Position = bottom-centre of the box (ground contact). Velocity = linear fit over the last 12 frames.
3. For each vulnerable-user/vehicle pair within a search radius, solve
   `|dp + dv*t| = r` for the earliest `t >= 0` (constant-velocity discs). `r = 0.4 * (size_a + size_b)`.
4. Flag when `TTC <= 1.5 s` for 3 consecutive frames; 2 s cooldown per pair.
5. Severity = `1 - TTC / threshold`. Event locations feed a Gaussian-blurred heatmap.

## Evaluation (do this, it is what makes results credible)
1. Watch `annotated.mp4` and write the timestamps of true near-misses to `labels.csv` (column `time_s`).
2. `python evaluate.py --events outputs/events.csv --truth labels.csv --tol 1.0`
3. Report precision / recall / F1 here:

| Clip | True events | Detected | Precision | Recall | F1 |
|---|---|---|---|---|---|
| _fill in_ | | | | | |

## Limitations (honest)
- No camera calibration: distances are in pixels unless `--ppm` is set; perspective distorts speeds.
- Constant-velocity assumption ignores braking/steering; TTC is a surrogate measure, not a crash predictor.
- ID switches and occlusion can create false events (mitigated by the persistence filter).
- COCO detector misses small/distant objects and has no helmet/lane/signal awareness.

## Future work
- Ground-plane homography for real-world metres and km/h.
- Post-encroachment time (PET) and deceleration-based conflict measures.
- Fine-tune on helmet/e-scooter classes; trajectory prediction with learned motion models.
- Multi-camera fusion and a live RTSP mode.

## Layout
```
nearmiss/  config.py  tracking.py  risk.py  viz.py  pipeline.py  report.py
ui/        theme.py (brand + light-theme CSS)   views.py (Overview, Analyze, Insights)
assets/    logo_full.png  logo_header.png  logo_icon.png  icon.png
app.py  run.py  evaluate.py  tests/test_risk.py  requirements.txt  .streamlit/config.toml
```
