import numpy as np

from evaluate import match
from nearmiss.config import Config, CAR, PERSON
from nearmiss.risk import NearMissEngine, closest_approach, time_to_collision
from nearmiss.tracking import Detection, TrackBook

V = np.array


def test_head_on_ttc():
    t = time_to_collision(V([0., 0.]), V([100., 0.]), V([300., 0.]), V([0., 0.]), radius=50)
    assert abs(t - 2.5) < 1e-6


def test_diverging_returns_none():
    assert time_to_collision(V([0., 0.]), V([-100., 0.]), V([300., 0.]), V([0., 0.]), 50) is None


def test_paths_that_miss_return_none():
    assert time_to_collision(V([0., 0.]), V([100., 0.]), V([300., 200.]), V([0., 0.]), 50) is None


def test_already_in_contact():
    assert time_to_collision(V([0., 0.]), V([1., 0.]), V([10., 0.]), V([0., 0.]), 50) == 0.0


def test_closest_approach():
    t, d = closest_approach(V([0., 0.]), V([100., 0.]), V([300., 30.]), V([0., 0.]))
    assert abs(t - 3.0) < 1e-6 and abs(d - 30.0) < 1e-6


def _run(car_speed):
    fps, cfg = 30.0, Config()
    book = TrackBook(cfg.history, cfg.trail_length, 60)
    engine = NearMissEngine(cfg, fps, {CAR: "car", PERSON: "person"})
    events = []
    for f in range(20):
        t = f / fps
        cx = 100 + car_speed * t
        dets = [Detection(1, CAR, (cx - 60, 340, cx + 60, 400)),          # 120 px wide car
                Detection(2, PERSON, (480, 340, 520, 400))]               # stationary pedestrian
        tracks = book.update(f, t, dets)
        events += engine.assess(tracks, f, t).new_events
    return events


def test_approaching_car_triggers_single_event():
    events = _run(car_speed=300.0)
    assert len(events) == 1                      # cooldown prevents duplicates
    assert events[0].ttc_s <= Config().ttc_threshold_s


def test_receding_or_static_car_no_event():
    assert _run(car_speed=0.0) == []
    assert _run(car_speed=-300.0) == []


def test_matching_metrics():
    m = match([1.0, 5.0, 9.0], [1.2, 5.5, 20.0], tol=1.0)
    assert (m["tp"], m["fp"], m["fn"]) == (2, 1, 1)
