"""Page views for the Road Safety Intelligence web app."""
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from nearmiss import Config, analyze_video
from nearmiss.pipeline import load_model
from nearmiss.report import build_report_html
from .theme import APP_NAME, TAGLINE

PAGES: dict = {}          # filled by app.py so views can link to each other

PROFILES = {              # one control instead of three technical ones
    "Fast":     dict(model="yolo11n.pt", imgsz=640),
    "Balanced": dict(model="yolo11m.pt", imgsz=960),
    "Accurate": dict(model="yolo11l.pt", imgsz=1280),
}
SENSITIVITY = {"Conservative": 1.0, "Standard": 1.5, "Sensitive": 2.2}   # TTC threshold in seconds


@st.cache_resource(show_spinner="Loading detection model...")
def get_model(name: str):
    return load_model(name)


def _link(key: str, label: str, icon: str | None = None) -> None:
    if key in PAGES:
        st.page_link(PAGES[key], label=label, icon=icon)


def _kpi(label: str, value, alert: bool = False) -> str:
    return f'<div class="kpi {"alert" if alert else ""}"><div class="l">{label}</div><div class="v">{value}</div></div>'


def _region(x: float, y: float, w: float, h: float) -> str:
    col = "left" if x < w / 3 else "right" if x > 2 * w / 3 else "centre"
    row = "upper" if y < h / 3 else "lower" if y > 2 * h / 3 else "middle"
    return "the centre of the frame" if (row, col) == ("middle", "centre") else f"the {row} {col} of the frame"


def _finding(result) -> str:
    """One-paragraph, plain-English takeaway generated from the analysis."""
    s, df = result.summary, result.events_df
    if df.empty:
        return "No near-miss events were detected at this sensitivity, so no road-user pair came close to a conflict in this clip."
    top, n_top = next(iter(s["conflict_types"].items()))
    worst = df.loc[df.ttc_s.idxmin()]
    mm, ss = int(worst.time_s // 60), int(worst.time_s % 60)
    parts = [f"{s['near_miss_events']} near-miss events in {s['duration_s']} s ({s['events_per_minute']} per minute).",
             f"Most involved {top} ({n_top} of {len(df)}).",
             f"The closest call had a TTC of {worst.ttc_s:.1f} s at {mm}:{ss:02d}."]
    high = int((df.level == "High").sum())
    if high:
        parts.append(f"{high} {'was' if high == 1 else 'were'} high severity.")
    if s["hotspot_xy"]:
        w, h = s["video_size"]
        parts.append(f"Conflicts cluster in {_region(*s['hotspot_xy'], w, h)}.")
    return " ".join(parts)


# --------------------------------------------------------------------------- Overview
def overview() -> None:
    st.markdown(f"""
<div class="hero"><div class="eyebrow">{TAGLINE}</div>
<h1>Find the near-misses <span>before they become collisions.</span></h1>
<p>Turn ordinary traffic video into quantified safety insight: who nearly collided, when, where,
and how close it was. Built on a pretrained vision model, with no new training data needed.</p></div>""",
                unsafe_allow_html=True)
    _link("analyze", "Start an analysis", ":material/play_arrow:")

    st.markdown("### What you get")
    cards = [("🎯", "Time-to-collision", "Every pedestrian, cyclist or motorcyclist paired with a vehicle is scored continuously."),
             ("🗺️", "Hotspot heatmap", "See which part of the junction produces the most conflicts."),
             ("📈", "Risk timeline", "Spot the exact moments when exposure peaked."),
             ("📄", "Shareable report", "One-click HTML report with metrics, heatmap and full event log.")]
    for col, (ic, t, d) in zip(st.columns(4), cards):
        col.markdown(f'<div class="kcard"><div class="ic">{ic}</div><h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)

    st.markdown("### How it works")
    steps = [("Detect", "YOLO11 finds people, bicycles, motorcycles, cars, buses and trucks."),
             ("Track", "ByteTrack keeps a persistent identity for each road user."),
             ("Predict", "Velocity is fitted per track; time-to-collision is solved for every risky pair."),
             ("Filter", "Persistence and cooldown rules remove ID-switch false alarms."),
             ("Report", "Events, heatmap, timeline and exportable report.")]
    st.markdown("".join(f'<div class="step"><div class="n">{i}</div><div><b>{t}</b><span>{d}</span></div></div>'
                        for i, (t, d) in enumerate(steps, 1)), unsafe_allow_html=True)

    hist = st.session_state.get("history", [])
    if hist:
        st.markdown("### Recent analyses")
        st.dataframe(pd.DataFrame(hist), hide_index=True, width="stretch")

    st.markdown('<div class="footnote">Pretrained YOLO11 detection &middot; ByteTrack tracking &middot; time-to-collision analytics</div>',
                unsafe_allow_html=True)


# --------------------------------------------------------------------------- Analyze
def analyze() -> None:
    st.markdown("## Analyze footage")
    st.caption("Use a fixed-camera clip (CCTV, junction or dashcam), 1 to 3 minutes works best.")
    left, right = st.columns([3, 2], gap="large")

    with left:
        file = st.file_uploader("Traffic video", type=["mp4", "mov", "avi", "mkv"], label_visibility="collapsed")
        if file:
            st.video(file)

    with right:
        profile = st.radio("Speed vs accuracy", list(PROFILES), index=1, horizontal=True,
                           help="Fast = YOLO11n, Balanced = YOLO11m, Accurate = YOLO11l")
        sens = st.select_slider("Detection sensitivity", list(SENSITIVITY), value="Standard",
                                help="Higher sensitivity flags conflicts that are further from collision.")
        run = st.button("Run analysis", type="primary", disabled=file is None, width="stretch")

    if not run or file is None:
        return

    tmp = Path(tempfile.mkdtemp())
    src = tmp / file.name
    src.write_bytes(file.getbuffer())
    p = PROFILES[profile]
    cfg = Config(model=p["model"], imgsz=p["imgsz"], ttc_threshold_s=SENSITIVITY[sens])

    bar = st.progress(0.0, text="Starting...")
    try:
        result = analyze_video(src, cfg, tmp / "out", model=get_model(cfg.model),
                               progress=lambda i, n: bar.progress(min(i / max(n, 1), 1.0), text=f"Analysing frame {i} of {n}"))
    except Exception as exc:
        bar.empty()
        st.error(f"Analysis failed: {exc}")
        return
    bar.empty()

    st.session_state["result"] = result
    st.session_state["meta"] = {"video": file.name, "config": cfg.to_dict()}
    st.session_state.setdefault("history", []).insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"), "video": file.name, "profile": profile,
        "events": result.summary["near_miss_events"], "events/min": result.summary["events_per_minute"]})
    st.success(f"Done: {result.summary['near_miss_events']} near-miss events found.")
    _link("insights", "Open insights", ":material/insights:")


# --------------------------------------------------------------------------- Insights
def insights() -> None:
    result = st.session_state.get("result")
    meta = st.session_state.get("meta", {})
    st.markdown("## Safety insights")
    if result is None:
        st.markdown('<div class="empty"><h3>No analysis yet</h3>Run an analysis to see insights here.</div>',
                    unsafe_allow_html=True)
        _link("analyze", "Go to Analyze", ":material/play_arrow:")
        return

    s = result.summary
    st.caption(f"{meta.get('video', '')}  ·  {s['duration_s']} s  ·  {s['unique_tracks']} tracked road users  ·  distances in {s['units']}")
    kp = [("Near-miss events", s["near_miss_events"], s["near_miss_events"] > 0),
          ("Events / minute", s["events_per_minute"], False),
          ("Closest call (TTC s)", s["min_ttc_s"] if s["min_ttc_s"] is not None else "-", False),
          ("Time at risk", f"{s['pct_time_at_risk']}%", False)]
    for col, (l, v, a) in zip(st.columns(4), kp):
        col.markdown(_kpi(l, v, a), unsafe_allow_html=True)
    st.write("")
    st.markdown(f'<div class="finding"><b>Key finding</b>{_finding(result)}</div>', unsafe_allow_html=True)

    t_events, t_heat, t_risk, t_export = st.tabs(["Event explorer", "Hotspot heatmap", "Risk timeline", "Export"])

    with t_events:
        df = result.events_df
        c1, c2 = st.columns([3, 2], gap="large")
        start = 0
        with c1:
            if df.empty:
                st.success("No near-miss events at this sensitivity. Try 'Sensitive' on the Analyze page.")
            else:
                st.caption("Select a row to jump the video to that moment.")
                cols = [c for c in ["time_s", "class_a", "class_b", "ttc_s", "severity", "level", "min_dist_px",
                                    "min_dist_m", "frame", "id_a", "id_b", "x", "y"] if c in df.columns]
                df = df[cols]
                sel = st.dataframe(
                    df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                    column_config={"severity": st.column_config.ProgressColumn("severity", min_value=0.0, max_value=1.0, format="%.2f"),
                                   "time_s": st.column_config.NumberColumn("time (s)"),
                                   "ttc_s": st.column_config.NumberColumn("TTC (s)")})
                rows = sel.selection.rows if sel and sel.selection else []
                if rows:
                    start = int(max(0, df.iloc[rows[0]]["time_s"] - 2))
        with c2:
            st.video(Path(result.paths["video"]).read_bytes(), start_time=start)
        if not df.empty:
            pairs = (df.class_a + " + " + df.class_b).value_counts()
            st.markdown("**Conflict types**")
            st.bar_chart(pairs)

    with t_heat:
        st.image(str(result.paths["heatmap"]), width="stretch")
        if s["hotspot_xy"]:
            st.caption(f"Primary hotspot near pixel {tuple(s['hotspot_xy'])}.")

    with t_risk:
        st.line_chart(result.risk_df.set_index("time_s")["risk"])
        st.caption("Risk = 1 - TTC / threshold for the most critical road-user pair in each frame.")

    with t_export:
        report = build_report_html(result, meta.get("video", ""), meta.get("config"), APP_NAME)
        e1, e2, e3 = st.columns(3)
        e1.download_button("Report (HTML)", report, "road_safety_report.html", "text/html", width="stretch")
        e2.download_button("Events (CSV)", result.events_df.to_csv(index=False), "events.csv", "text/csv", width="stretch")
        e3.download_button("Annotated video", Path(result.paths["video"]).read_bytes(), "annotated.mp4", width="stretch")
        st.caption("Tip: open the HTML report and use Print -> Save as PDF.")
