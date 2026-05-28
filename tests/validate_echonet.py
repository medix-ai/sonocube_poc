"""
EchoNet-Dynamic 벤치마크 검증 스크립트

EchoNet-Dynamic 공개 데이터셋(Stanford)으로 SonoCube 모델 정확도를 측정합니다.
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- R² (Pearson 상관계수 제곱)
- Bland-Altman 분석 (한계 일치도)
- Correlation plot (EF predicted vs reference)

사용법:
    python tests/validate_echonet.py \
        --data_dir /path/to/EchoNet-Dynamic/Videos \
        --filelist /path/to/EchoNet-Dynamic/FileList.csv \
        --split TEST \
        --max_cases 200 \
        --out_dir output/validation

EchoNet-Dynamic 다운로드: https://echonet.github.io/dynamic/
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# 프로젝트 루트를 sys.path에 추가 (스크립트 직접 실행 시)
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.ai_engine import analyze_clip


# ── 임상 참고 범위 색상 ────────────────────────────────────────────────────────
CLR_NORMAL  = "#52c27a"
CLR_MID     = "#e8a217"
CLR_LOW     = "#e05252"
CLR_ACCENT  = "#00b4cc"
CLR_GRAY    = "#888888"


def load_filelist(filelist_path: Path, split: str = "TEST") -> list[dict]:
    """EchoNet-Dynamic FileList.csv 로드 → {filename, ef, split} 목록 반환."""
    rows = []
    with open(filelist_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if split and row.get("Split", "").upper() != split.upper():
                continue
            ef_val = row.get("EF") or row.get("ef")
            fname  = row.get("FileName") or row.get("filename") or ""
            if ef_val and fname:
                rows.append({
                    "filename": fname if fname.endswith(".avi") else fname + ".avi",
                    "ef_ref":   float(ef_val),
                    "split":    row.get("Split", split),
                })
    return rows


def run_inference(video_path: Path) -> float | None:
    """단일 영상 추론 → EF 중앙값 반환. 실패 시 None."""
    try:
        result = analyze_clip(video_path)
        ef = result.get("ef") or result.get("estimated_ef_median")
        return float(ef) if ef is not None else None
    except Exception as e:
        print(f"  [WARN] {video_path.name}: {e}")
        return None


# ── 통계 계산 ─────────────────────────────────────────────────────────────────

def compute_metrics(ref: np.ndarray, pred: np.ndarray) -> dict:
    """MAE, RMSE, R², Pearson r, Bias, LoA 계산."""
    diff  = pred - ref
    mae   = float(np.mean(np.abs(diff)))
    rmse  = float(np.sqrt(np.mean(diff ** 2)))
    r, p  = stats.pearsonr(ref, pred)
    r2    = float(r ** 2)
    bias  = float(np.mean(diff))
    sd    = float(np.std(diff, ddof=1))
    loa_upper = bias + 1.96 * sd
    loa_lower = bias - 1.96 * sd
    return {
        "n":          len(ref),
        "mae":        mae,
        "rmse":       rmse,
        "pearson_r":  float(r),
        "r2":         r2,
        "p_value":    float(p),
        "bias":       bias,
        "std_diff":   sd,
        "loa_upper":  loa_upper,
        "loa_lower":  loa_lower,
    }


# ── 시각화 ────────────────────────────────────────────────────────────────────

def _ef_color(ef: float) -> str:
    if ef >= 55:   return CLR_NORMAL
    if ef >= 40:   return CLR_MID
    return CLR_LOW


def plot_correlation(ref: np.ndarray, pred: np.ndarray, metrics: dict, out_path: Path):
    """Predicted vs Reference EF scatter + 회귀선."""
    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8f9fa")

    colors = [_ef_color(e) for e in ref]
    ax.scatter(ref, pred, c=colors, alpha=0.55, s=18, linewidths=0, zorder=3)

    lo, hi = min(ref.min(), pred.min()) - 2, max(ref.max(), pred.max()) + 2
    ax.plot([lo, hi], [lo, hi], "--", color="#999", lw=1.2, label="Identity (y=x)", zorder=2)

    m, b, *_ = stats.linregress(ref, pred)
    xs = np.linspace(lo, hi, 200)
    ax.plot(xs, m * xs + b, "-", color=CLR_ACCENT, lw=1.8,
            label=f"Regression (r={metrics['pearson_r']:.3f})", zorder=4)

    ax.set_xlabel("Reference EF (%)", fontsize=12)
    ax.set_ylabel("SonoCube EF (%)", fontsize=12)
    ax.set_title(
        f"EF Correlation  |  n={metrics['n']}  MAE={metrics['mae']:.2f}%  RMSE={metrics['rmse']:.2f}%",
        fontsize=11, pad=10
    )
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.legend(fontsize=9)

    patches = [
        mpatches.Patch(color=CLR_NORMAL, label="Normal (≥55%)"),
        mpatches.Patch(color=CLR_MID,    label="Mildly Reduced (40–54%)"),
        mpatches.Patch(color=CLR_LOW,    label="Reduced (<40%)"),
    ]
    ax.legend(handles=patches, fontsize=8, loc="upper left")

    stats_txt = (f"R²={metrics['r2']:.3f}\n"
                 f"MAE={metrics['mae']:.2f}%\n"
                 f"RMSE={metrics['rmse']:.2f}%")
    ax.text(0.97, 0.05, stats_txt, transform=ax.transAxes,
            fontsize=9, ha="right", va="bottom",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85))

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path.name}")


def plot_bland_altman(ref: np.ndarray, pred: np.ndarray, metrics: dict, out_path: Path):
    """Bland-Altman plot (차이 vs 평균)."""
    mean_val = (ref + pred) / 2
    diff     = pred - ref

    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8f9fa")

    colors = [_ef_color(e) for e in ref]
    ax.scatter(mean_val, diff, c=colors, alpha=0.55, s=18, linewidths=0, zorder=3)

    bias = metrics["bias"]
    loa_u = metrics["loa_upper"]
    loa_l = metrics["loa_lower"]

    ax.axhline(bias,  color="#333",    lw=1.5, linestyle="-",  label=f"Bias = {bias:+.2f}%")
    ax.axhline(loa_u, color=CLR_LOW,   lw=1.2, linestyle="--", label=f"+1.96σ = {loa_u:+.2f}%")
    ax.axhline(loa_l, color=CLR_LOW,   lw=1.2, linestyle="--", label=f"−1.96σ = {loa_l:+.2f}%")
    ax.axhline(0,     color="#aaa",    lw=0.8, linestyle=":")

    # LoA 음영
    xlim = (mean_val.min() - 2, mean_val.max() + 2)
    ax.fill_between(xlim, loa_l, loa_u, alpha=0.07, color=CLR_ACCENT)

    ax.set_xlabel("Mean of Reference & SonoCube EF (%)", fontsize=11)
    ax.set_ylabel("SonoCube − Reference EF (%)", fontsize=11)
    ax.set_title(
        f"Bland-Altman Analysis  |  n={metrics['n']}  Bias={bias:+.2f}%  LoA=[{loa_l:.2f}, {loa_u:.2f}]",
        fontsize=11, pad=10
    )
    ax.set_xlim(*xlim)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.legend(fontsize=9, loc="upper right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path.name}")


def plot_error_distribution(ref: np.ndarray, pred: np.ndarray, out_path: Path):
    """오차 히스토그램 + KDE."""
    diff = pred - ref

    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8f9fa")

    ax.hist(diff, bins=30, color=CLR_ACCENT, alpha=0.65, edgecolor="white", linewidth=0.4, density=True)

    from scipy.stats import gaussian_kde
    kde_x = np.linspace(diff.min() - 2, diff.max() + 2, 300)
    kde   = gaussian_kde(diff)
    ax.plot(kde_x, kde(kde_x), color="#333", lw=1.8, label="KDE")
    ax.axvline(0, color=CLR_NORMAL, lw=1.5, linestyle="--", label="Zero error")
    ax.axvline(np.mean(diff), color=CLR_LOW, lw=1.5, linestyle="-",
               label=f"Mean error = {np.mean(diff):+.2f}%")

    ax.set_xlabel("Prediction Error (%)", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.set_title("EF Prediction Error Distribution", fontsize=11, pad=10)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, linewidth=0.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path.name}")


# ── 리포트 저장 ───────────────────────────────────────────────────────────────

def save_report(metrics: dict, cases: list[dict], out_dir: Path):
    """JSON + TXT 요약 저장."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    report = {
        "generated_at": ts,
        "model":        "SonoCube w_075 (model_fp32.onnx)",
        "dataset":      "EchoNet-Dynamic",
        "metrics":      metrics,
        "per_case":     cases,
    }
    json_path = out_dir / f"validation_{ts}.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"  saved: {json_path.name}")

    txt_path = out_dir / f"validation_{ts}.txt"
    lines = [
        "=" * 56,
        "  SonoCube — EchoNet-Dynamic Validation Report",
        "=" * 56,
        f"  Generated : {ts}",
        f"  Dataset   : EchoNet-Dynamic (split: TEST)",
        f"  Model     : w_075 / model_fp32.onnx",
        "-" * 56,
        f"  N cases   : {metrics['n']}",
        f"  MAE       : {metrics['mae']:.2f} %",
        f"  RMSE      : {metrics['rmse']:.2f} %",
        f"  Pearson r : {metrics['pearson_r']:.4f}",
        f"  R²        : {metrics['r2']:.4f}",
        f"  p-value   : {metrics['p_value']:.2e}",
        "-" * 56,
        "  Bland-Altman",
        f"  Bias      : {metrics['bias']:+.2f} %",
        f"  SD (diff) : {metrics['std_diff']:.2f} %",
        f"  LoA upper : {metrics['loa_upper']:+.2f} %",
        f"  LoA lower : {metrics['loa_lower']:+.2f} %",
        "=" * 56,
    ]
    txt_path.write_text("\n".join(lines))
    print(f"  saved: {txt_path.name}")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SonoCube — EchoNet-Dynamic Validation")
    parser.add_argument("--data_dir",  required=True, help="EchoNet-Dynamic Videos 디렉토리")
    parser.add_argument("--filelist",  required=True, help="FileList.csv 경로")
    parser.add_argument("--split",     default="TEST", help="데이터 분할 (TEST/VAL/TRAIN)")
    parser.add_argument("--max_cases", type=int, default=0, help="최대 케이스 수 (0=전체)")
    parser.add_argument("--out_dir",   default="output/validation", help="결과 저장 디렉토리")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir  = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*56}")
    print(f"  SonoCube Validation — EchoNet-Dynamic ({args.split})")
    print(f"{'='*56}")

    # FileList 로드
    rows = load_filelist(Path(args.filelist), args.split)
    if args.max_cases > 0:
        rows = rows[:args.max_cases]
    print(f"  케이스 수: {len(rows)}")

    # 추론 실행
    ref_list, pred_list, case_records = [], [], []
    t_start = time.time()

    for i, row in enumerate(rows, 1):
        video_path = data_dir / row["filename"]
        if not video_path.exists():
            print(f"  [{i:4d}/{len(rows)}] SKIP (파일 없음): {row['filename']}")
            continue

        ef_pred = run_inference(video_path)
        if ef_pred is None:
            print(f"  [{i:4d}/{len(rows)}] FAIL: {row['filename']}")
            continue

        ef_ref = row["ef_ref"]
        error  = ef_pred - ef_ref
        ref_list.append(ef_ref)
        pred_list.append(ef_pred)
        case_records.append({
            "filename": row["filename"],
            "ef_ref":   ef_ref,
            "ef_pred":  ef_pred,
            "error":    error,
        })
        print(f"  [{i:4d}/{len(rows)}] {row['filename'][:28]:28s}"
              f"  ref={ef_ref:5.1f}%  pred={ef_pred:5.1f}%  err={error:+5.1f}%")

    elapsed = time.time() - t_start
    if len(ref_list) < 2:
        print("\n[ERROR] 유효한 케이스가 2개 미만입니다. data_dir / filelist 경로를 확인하세요.")
        sys.exit(1)

    ref  = np.array(ref_list)
    pred = np.array(pred_list)

    # 통계
    metrics = compute_metrics(ref, pred)
    print(f"\n{'─'*56}")
    print(f"  유효 케이스  : {metrics['n']} / {len(rows)}")
    print(f"  MAE          : {metrics['mae']:.2f} %")
    print(f"  RMSE         : {metrics['rmse']:.2f} %")
    print(f"  Pearson r    : {metrics['pearson_r']:.4f}")
    print(f"  R²           : {metrics['r2']:.4f}")
    print(f"  Bias         : {metrics['bias']:+.2f} %")
    print(f"  LoA          : [{metrics['loa_lower']:+.2f}, {metrics['loa_upper']:+.2f}]")
    print(f"  총 소요 시간 : {elapsed:.1f}s  ({elapsed/metrics['n']:.2f}s/case)")
    print(f"{'─'*56}\n")

    # 시각화
    print("  그래프 생성 중...")
    plot_correlation(ref, pred, metrics, out_dir / "correlation.png")
    plot_bland_altman(ref, pred, metrics, out_dir / "bland_altman.png")
    plot_error_distribution(ref, pred, out_dir / "error_distribution.png")

    # 리포트 저장
    save_report(metrics, case_records, out_dir)

    print(f"\n  완료. 결과: {out_dir}/")


if __name__ == "__main__":
    main()
