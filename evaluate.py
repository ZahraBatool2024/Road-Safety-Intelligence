"""Evaluate detected near-miss events against a manually labelled CSV.

labels.csv needs one column: time_s   (timestamp of each true near-miss you labelled)
Usage:  python evaluate.py --events outputs/events.csv --truth labels.csv --tol 1.0
"""
import argparse

import pandas as pd


def match(pred, truth, tol):
    """Greedy one-to-one matching of timestamps within +/- tol seconds."""
    pred, truth = sorted(pred), sorted(truth)
    used, tp = set(), 0
    for p in pred:
        best, best_d = None, tol + 1e-9
        for i, t in enumerate(truth):
            if i not in used and abs(p - t) <= best_d:
                best, best_d = i, abs(p - t)
        if best is not None:
            used.add(best)
            tp += 1
    fp, fn = len(pred) - tp, len(truth) - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return dict(tp=tp, fp=fp, fn=fn, precision=round(precision, 3), recall=round(recall, 3), f1=round(f1, 3))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--tol", type=float, default=1.0, help="matching tolerance in seconds")
    a = ap.parse_args()
    pred = pd.read_csv(a.events)["time_s"].tolist()
    truth = pd.read_csv(a.truth)["time_s"].tolist()
    for k, v in match(pred, truth, a.tol).items():
        print(f"{k:>10}: {v}")


if __name__ == "__main__":
    main()
