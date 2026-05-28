"""
End-to-end pipeline 검증 — LVSeg → ED/ES → SonoCubeV2 → EF
echo-sample TEST 케이스 대상, ground truth EF와 비교.

실행: python tests/validate_pipeline.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from utils.ai_engine import SonoCubeV2Engine, get_lvseg_engine

SAMPLE_DIR = Path("/Users/ohseoyoung/Documents/GitHub/sonocube_research/echo-sample")
FILELIST   = SAMPLE_DIR / "FileList.csv"
TRACINGS   = SAMPLE_DIR / "VolumeTracings.csv"
VIDEOS_DIR = SAMPLE_DIR / "Videos"


def load_gt_ed_es() -> dict[str, tuple[int, int]]:
    file_frames: dict[str, set] = {}
    with open(TRACINGS, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stem  = Path(row["FileName"].strip()).stem
            frame = int(float(row["Frame"]))
            file_frames.setdefault(stem, set()).add(frame)
    return {
        stem: (sorted(frames)[0], sorted(frames)[-1])
        for stem, frames in file_frames.items()
        if len(frames) >= 2
    }


def load_frames(vpath: Path) -> list[np.ndarray]:
    cap, frames = cv2.VideoCapture(str(vpath)), []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames


def main():
    print("=" * 65)
    print("End-to-End Pipeline 검증")
    print("  LVSeg → ED/ES 검출 → SonoCubeV2 → EF")
    print("=" * 65)

    seg_engine = get_lvseg_engine()
    v2_engine  = SonoCubeV2Engine()
    gt_ed_es   = load_gt_ed_es()

    print(f"LVSegEngine : {'✓ loaded' if seg_engine.available else '✗ brightness fallback'}")
    print(f"SonoCubeV2  : {'✓ loaded' if v2_engine.model_loaded else '✗ not loaded'}")
    print()

    test_cases = []
    with open(FILELIST, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Split"] != "TEST":
                continue
            stem  = row["FileName"].strip()
            vpath = VIDEOS_DIR / f"{stem}.avi"
            if not vpath.exists():
                continue
            try:
                ef_gt = float(row["EF"])
            except ValueError:
                continue
            test_cases.append((stem, vpath, ef_gt))

    print(f"TEST 케이스: {len(test_cases)}개\n")

    results, ed_es_errors = [], []

    for i, (stem, vpath, ef_gt) in enumerate(test_cases):
        frames = load_frames(vpath)
        if not frames:
            continue

        out     = v2_engine.infer(frames)
        ef_pred = out["ef"]
        ed_pred = out["ed_frame_idx"]
        es_pred = out["es_frame_idx"]

        if stem in gt_ed_es:
            ed_gt, es_gt = gt_ed_es[stem]
            ed_es_errors.append((abs(ed_pred - ed_gt), abs(es_pred - es_gt)))

        results.append({"stem": stem, "ef_gt": ef_gt, "ef_pred": ef_pred,
                        "ed": ed_pred, "es": es_pred, "n_frames": len(frames)})

        if (i + 1) % 25 == 0 or i == 0:
            print(f"  [{i+1:3d}/{len(test_cases)}] {stem[:22]}  "
                  f"GT={ef_gt:.1f}%  pred={ef_pred:.1f}%  "
                  f"err={ef_pred-ef_gt:+.1f}%  ed={ed_pred} es={es_pred}")

    print()

    gt   = np.array([r["ef_gt"]   for r in results])
    pred = np.array([r["ef_pred"] for r in results])
    errs = pred - gt

    from scipy.stats import pearsonr
    r_val, _ = pearsonr(gt, pred)

    print("=" * 65)
    print("EF 예측 성능")
    print(f"  케이스  : {len(results)}")
    print(f"  MAE     : {np.mean(np.abs(errs)):.3f}%")
    print(f"  RMSE    : {np.sqrt(np.mean(errs**2)):.3f}%")
    print(f"  r       : {r_val:.4f}")
    print(f"  Bias    : {np.mean(errs):+.3f}%")
    print(f"  pred 범위: {pred.min():.1f} ~ {pred.max():.1f}%")
    print(f"  GT 범위 : {gt.min():.1f} ~ {gt.max():.1f}%")

    if ed_es_errors:
        ed_errs = np.array([e[0] for e in ed_es_errors])
        es_errs = np.array([e[1] for e in ed_es_errors])
        print()
        print("ED/ES 검출 오차 (vs VolumeTracings GT)")
        print(f"  ED 평균오차: {ed_errs.mean():.1f}프레임  중앙값={np.median(ed_errs):.0f}  "
              f"±5f이내={np.mean(ed_errs<=5)*100:.0f}%")
        print(f"  ES 평균오차: {es_errs.mean():.1f}프레임  중앙값={np.median(es_errs):.0f}  "
              f"±5f이내={np.mean(es_errs<=5)*100:.0f}%")

    print()
    print("오차 Top 5:")
    for r in sorted(results, key=lambda x: abs(x["ef_pred"]-x["ef_gt"]), reverse=True)[:5]:
        print(f"  {r['stem'][:24]}  GT={r['ef_gt']:.1f}%  pred={r['ef_pred']:.1f}%  "
              f"err={r['ef_pred']-r['ef_gt']:+.1f}%  frames={r['n_frames']}")
    print("=" * 65)


if __name__ == "__main__":
    main()
