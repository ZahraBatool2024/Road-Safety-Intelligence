"""Self-contained HTML safety report (shareable, prints cleanly to PDF)."""
from __future__ import annotations

import base64
import html
from datetime import datetime
from pathlib import Path

from .pipeline import AnalysisResult

_CSS = """
body{font-family:Inter,Segoe UI,Arial,sans-serif;color:#0F172A;max-width:960px;margin:2rem auto;padding:0 1.2rem}
h1{margin-bottom:.2rem} .sub{color:#64748B;margin-top:0}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:1.2rem 0}
.k{border:1px solid #E2E8F0;border-radius:12px;padding:12px}.k b{display:block;font-size:1.6rem}
.k span{color:#64748B;font-size:.75rem;text-transform:uppercase;letter-spacing:.08em}
table{border-collapse:collapse;width:100%;font-size:.85rem}th,td{border-bottom:1px solid #E2E8F0;padding:6px 8px;text-align:left}
th{background:#F1F5F9} img{max-width:100%;border-radius:12px} h2{margin-top:2rem}
.note{background:#FEF3C7;border-radius:10px;padding:10px 14px;font-size:.88rem}
"""


def build_report_html(result: AnalysisResult, video_name: str = "", config: dict | None = None,
                      brand: str = "Road Safety Intelligence") -> str:
    s = result.summary
    heat = Path(result.paths["heatmap"]).read_bytes() if "heatmap" in result.paths else b""
    heat_b64 = base64.b64encode(heat).decode()
    kpis = [("Near-miss events", s["near_miss_events"]), ("Events / min", s["events_per_minute"]),
            ("Min TTC (s)", s["min_ttc_s"] if s["min_ttc_s"] is not None else "-"),
            ("Time at risk", f"{s['pct_time_at_risk']}%")]
    kpi_html = "".join(f'<div class="k"><b>{html.escape(str(v))}</b><span>{k}</span></div>' for k, v in kpis)
    conflicts = "".join(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>" for k, v in s["conflict_types"].items())
    events = result.events_df.to_html(index=False, border=0) if result.events else "<p>No events detected.</p>"
    cfg_rows = "".join(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
                       for k, v in (config or {}).items())
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{brand} Safety Report</title>
<style>{_CSS}</style></head><body>
<h1>{brand} Safety Report</h1>
<p class="sub">{html.escape(video_name)} &middot; generated {datetime.now():%Y-%m-%d %H:%M} &middot;
{s['duration_s']} s analysed &middot; distances in {s['units']}</p>
<div class="grid">{kpi_html}</div>
<h2>Hotspot heatmap</h2><img src="data:image/png;base64,{heat_b64}" alt="heatmap">
<h2>Conflict types</h2><table><tr><th>Road-user pair</th><th>Events</th></tr>{conflicts}</table>
<h2>Event log</h2>{events}
<h2>Method</h2>
<p>YOLO11 (COCO) detection, ByteTrack identities, least-squares velocity per track, pairwise time-to-collision
under a constant-velocity disc model, persistence and cooldown filtering.</p>
<h2>Configuration</h2><table>{cfg_rows}</table>
<h2>Limitations</h2>
<p class="note">Uncalibrated 2-D camera (perspective distortion), constant-velocity assumption, possible ID switches,
pretrained COCO detector limits. TTC is a surrogate safety measure, not a crash predictor.</p>
</body></html>"""
