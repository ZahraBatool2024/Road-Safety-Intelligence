"""CLI entry point:  python run.py traffic.mp4 --out outputs"""
import argparse
import logging

from nearmiss import Config, analyze_video


def main() -> None:
    p = argparse.ArgumentParser(description="Near-miss traffic safety analyzer (pretrained YOLO + ByteTrack)")
    p.add_argument("video")
    p.add_argument("--out", default="outputs")
    p.add_argument("--model", default="yolo11m.pt", help="yolo11n.pt (fast) ... yolo11x.pt (accurate)")
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--imgsz", type=int, default=960)
    p.add_argument("--ttc", type=float, default=1.5, help="TTC threshold in seconds")
    p.add_argument("--persist", type=int, default=3, help="min consecutive flagged frames")
    p.add_argument("--ppm", type=float, default=None, help="pixels per meter (optional calibration)")
    p.add_argument("--vehicle-pairs", action="store_true", help="also analyse vehicle-vehicle conflicts")
    p.add_argument("--max-frames", type=int, default=None)
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    cfg = Config(model=args.model, conf=args.conf, imgsz=args.imgsz, ttc_threshold_s=args.ttc,
                 min_persist_frames=args.persist, pixels_per_meter=args.ppm,
                 include_vehicle_pairs=args.vehicle_pairs)

    def bar(i, n):
        print(f"\rframe {i}/{n}", end="", flush=True)

    res = analyze_video(args.video, cfg, args.out, progress=bar, max_frames=args.max_frames)
    print()
    for k, v in res.summary.items():
        print(f"{k:>20}: {v}")
    print(f"\nArtefacts written to {args.out}/")


if __name__ == "__main__":
    main()
