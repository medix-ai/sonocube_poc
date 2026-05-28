"""
PDF 리포트 생성 모듈 — SonoCube v1.3
ReportLab + matplotlib(Agg, 스레드 안전) — 라이트 임상 테마
"""
import io
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import cv2
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from utils.constants import (
    APP_NAME, APP_VERSION, DISCLAIMER, UNSUPPORTED_METRICS,
    CONFIDENCE_NOTE, CONFIDENCE_LOW_WARNING,
)


# ── 임상 라이트 팔레트 ─────────────────────────────────────────────────────────
_WHITE   = colors.white
_BG_LIGHT= colors.HexColor("#f8f9fa")
_HDR_BG  = colors.HexColor("#e9ecef")
_BORDER  = colors.HexColor("#dee2e6")
_TEXT    = colors.HexColor("#212529")
_TEXT_SEC= colors.HexColor("#6c757d")
_ACCENT  = colors.HexColor("#0d6efd")
_GREEN   = colors.HexColor("#198754")
_AMBER   = colors.HexColor("#fd7e14")
_RED     = colors.HexColor("#dc3545")
_WARN_BG = colors.HexColor("#fff3cd")
_ERR_BG  = colors.HexColor("#f8d7da")
_INFO_BG = colors.HexColor("#e7f3ff")


# ── 공개 API ──────────────────────────────────────────────────────────────────

def build_pdf(report_path: Path, analysis_result: Dict[str, Any]):
    """분석 결과를 PDF 리포트로 저장한다."""
    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = _build_styles()
    story  = _build_story(analysis_result, styles)
    doc.build(story)
    _cleanup_temp_images()


# ── 스토리 ────────────────────────────────────────────────────────────────────

def _build_story(result: Dict[str, Any], styles) -> list:
    s = []

    # ── 헤더 ──
    s.append(Paragraph(f"{APP_NAME}", styles["app_name"]))
    s.append(Paragraph("Cardiac Echo Analysis Report", styles["report_title"]))
    s.append(Spacer(1, 0.2 * cm))
    s.append(HRFlowable(width="100%", thickness=1, color=_BORDER))
    s.append(Spacer(1, 0.3 * cm))
    s.append(Paragraph(
        f"⚠ {DISCLAIMER}  This report is auto-generated and must not be used for clinical diagnosis.",
        styles["disclaimer"]
    ))
    s.append(Spacer(1, 0.5 * cm))

    # ── 케이스 정보 ──
    s.append(Paragraph("Case Information", styles["h2"]))
    s.append(Spacer(1, 0.15 * cm))
    s.append(_case_info_table(result))
    s.append(Spacer(1, 0.5 * cm))

    # ── EF 결과 (핵심) ──
    s.append(Paragraph("EF Analysis Results", styles["h2"]))
    s.append(Spacer(1, 0.15 * cm))

    # EF 요약 카드 (큰 숫자 + 범위 바)
    ef_bar_img = _create_ef_bar_image(
        result.get("ef"), result.get("ef_min"), result.get("ef_max"),
        result.get("ef_std")
    )
    if ef_bar_img:
        s.append(Image(str(ef_bar_img), width=15 * cm, height=3.2 * cm))
        s.append(Spacer(1, 0.2 * cm))

    s.append(_ef_results_table(result))
    s.append(Spacer(1, 0.3 * cm))

    # Stability note
    conf = result.get("confidence_level", "Unknown")
    conf_color = {"High": _GREEN, "Medium": _AMBER, "Low": _RED}.get(conf, _TEXT_SEC)
    s.append(Paragraph(
        f"Prediction Stability: <b>{conf}</b>  —  {CONFIDENCE_NOTE}",
        styles["small_grey"]
    ))
    if conf == "Low":
        s.append(Spacer(1, 0.15 * cm))
        s.append(Paragraph(f"⚠ {CONFIDENCE_LOW_WARNING}", styles["warning_high"]))
    s.append(Spacer(1, 0.3 * cm))

    # Manual override
    if result.get("manual_override"):
        s.append(Paragraph(
            f"ED/ES Source: <b>Manual Override</b>  "
            f"(AI candidates: ED=#{result.get('ed_frame_index_ai','?')}  "
            f"ES=#{result.get('es_frame_index_ai','?')})",
            styles["normal"]
        ))
        s.append(Spacer(1, 0.3 * cm))

    # ── Quality Warnings ──
    quality  = result.get("quality_metrics", {})
    warnings = quality.get("warnings", [])
    if warnings:
        s.append(Paragraph("Image Quality Warnings", styles["h2"]))
        s.append(Spacer(1, 0.1 * cm))
        for w in warnings:
            s.append(_warning_block(w, styles))
            s.append(Spacer(1, 0.1 * cm))
        s.append(Spacer(1, 0.3 * cm))

    # ── Frame-wise EF Curve ──
    framewise_ef = result.get("framewise_ef", [])
    if framewise_ef:
        s.append(Paragraph("Frame-wise EF Prediction Curve", styles["h2"]))
        s.append(Spacer(1, 0.15 * cm))
        ed = result.get("ed_frame_index_final", result.get("ed_frame_idx", 0))
        es = result.get("es_frame_index_final", result.get("es_frame_idx", 0))
        curve_path = _create_ef_curve_image(
            framewise_ef, ed, es,
            result.get("ef", 0.0), result.get("ef_std", 0.0), result.get("ef_mean"),
        )
        if curve_path:
            s.append(Image(str(curve_path), width=15 * cm, height=5.5 * cm))
        s.append(Spacer(1, 0.5 * cm))

    # ── ED/ES 스냅샷 (LV 마스크 overlay 포함) ──
    frames = result.get("frames", [])
    ed_idx = result.get("ed_frame_index_final", result.get("ed_frame_idx", 0))
    es_idx = result.get("es_frame_index_final", result.get("es_frame_idx", 0))
    raw_masks = result.get("lv_masks", {})
    ed_mask = raw_masks.get("ed") if isinstance(raw_masks, dict) else None
    es_mask = raw_masks.get("es") if isinstance(raw_masks, dict) else None
    if frames:
        s.append(Paragraph("Candidate Frame Snapshots", styles["h2"]))
        s.append(Spacer(1, 0.05 * cm))
        if ed_mask is not None:
            s.append(Paragraph(
                "LV segmentation mask overlay shown in cyan.",
                styles["small_grey"]
            ))
        s.append(Spacer(1, 0.1 * cm))
        snap_data = [
            [Paragraph("ED Candidate Frame", styles["tbl_hdr"]),
             Paragraph("ES Candidate Frame", styles["tbl_hdr"])],
        ]
        ed_img = _frame_image_element(frames, ed_idx, "ED", lv_mask=ed_mask)
        es_img = _frame_image_element(frames, es_idx, "ES", lv_mask=es_mask)
        snap_data.append([ed_img or "N/A", es_img or "N/A"])
        t = Table(snap_data, colWidths=[7.5 * cm, 7.5 * cm])
        t.setStyle(TableStyle([
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, 0),  _HDR_BG),
            ("GRID",       (0, 0), (-1, -1), 0.5, _BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        s.append(t)
        s.append(Spacer(1, 0.5 * cm))

    # ── 미지원 지표 ──
    s.append(Paragraph("Unsupported Metrics (Current Version)", styles["h2"]))
    s.append(Spacer(1, 0.15 * cm))
    s.append(_unsupported_table())
    s.append(Spacer(1, 0.5 * cm))

    # ── 모델 / 메타데이터 ──
    s.append(Paragraph("Model & Analysis Metadata", styles["h2"]))
    s.append(Spacer(1, 0.15 * cm))
    s.append(_metadata_table(result))
    s.append(Spacer(1, 0.5 * cm))

    # ── 푸터 ──
    s.append(HRFlowable(width="100%", thickness=0.5, color=_BORDER))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph(
        f"{APP_NAME} v{APP_VERSION}  ·  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ·  {DISCLAIMER}",
        styles["footer"]
    ))
    return s


# ── 경고 블록 ──────────────────────────────────────────────────────────────────

def _warning_block(msg: str, styles) -> Table:
    sev, icon, bg = _warning_severity_pdf(msg)
    title, action = _split_warning(msg)

    cell_content = [Paragraph(f"{icon}  {title}", styles[f"warn_{sev}"])]
    if action:
        cell_content.append(Paragraph(f"→ {action}", styles["warn_action"]))

    bar_color = {"high": _RED, "moderate": _AMBER, "info": colors.HexColor("#0d6efd")}.get(sev, _AMBER)
    t = Table([[cell_content]], colWidths=[15 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBEFORE",    (0, 0), (0, -1),  3, bar_color),
    ]))
    return t


def _warning_severity_pdf(msg: str):
    m = msg.lower()
    if any(k in m for k in ["very short", "high failed", "high frame-to-frame"]):
        return "high", "▲", _ERR_BG
    if any(k in m for k in ["short clip", "low brightness", "low image contrast",
                              "high frame blur", "moderate ef", "some frames"]):
        return "moderate", "!", _WARN_BG
    return "info", "ℹ", _INFO_BG


def _split_warning(msg: str):
    for sep in [" — ", ". Adjust ", ". Check ", ". Re-acquire ", ". Results "]:
        if sep in msg:
            parts = msg.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    sentences = [s.strip() for s in msg.split(".") if s.strip()]
    if len(sentences) > 1:
        return sentences[0] + ".", " ".join(sentences[1:])
    return msg, ""


# ── 테이블 빌더 ───────────────────────────────────────────────────────────────

def _case_info_table(result: Dict[str, Any]) -> Table:
    metadata  = result.get("metadata", {})
    file_path = metadata.get("file_path", "N/A")
    file_name = Path(file_path).name if file_path != "N/A" else "N/A"
    stem      = Path(file_path).stem if file_path != "N/A" else "UNKNOWN"
    case_id   = result.get("case_id", stem[:8].upper().ljust(8, "0"))
    override  = result.get("manual_override", False)

    rows = [
        ["Case ID",       case_id],
        ["Input File",    file_name],
        ["Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["View Type",     result.get("view_type", "Unknown")],
        ["App Version",   APP_VERSION],
        ["ED/ES Source",  "Manual override" if override else "AI prediction"],
    ]
    return _kv_table(rows)


def _ef_results_table(result: Dict[str, Any]) -> Table:
    ef      = result.get("ef", 0.0)
    ef_mean = result.get("ef_mean", 0.0)
    ef_std  = result.get("ef_std", 0.0)
    ef_min  = result.get("ef_min", 0.0)
    ef_max  = result.get("ef_max", 0.0)
    conf    = result.get("confidence_level", "Unknown")
    ed_idx  = result.get("ed_frame_index_final", result.get("ed_frame_idx", 0))
    es_idx  = result.get("es_frame_index_final", result.get("es_frame_idx", 0))
    latency = result.get("inference_latency_s")
    simpson = result.get("simpson_ef")
    vol     = result.get("volume_info", {})
    edv_rel = vol.get("edv_rel")
    esv_rel = vol.get("esv_rel")

    rows = [
        ["Estimated EF (AI)",      f"{ef:.1f}%"],
        ["EF Mean",                f"{ef_mean:.1f}%"],
        ["EF Std (σ)",             f"±{ef_std:.2f}%"],
        ["EF Min / Max",           f"{ef_min:.1f}% / {ef_max:.1f}%"],
        ["Prediction Stability",   conf],
        ["ED Candidate Frame",     f"#{ed_idx}"],
        ["ES Candidate Frame",     f"#{es_idx}"],
        ["Manual Override",        "Yes" if result.get("manual_override") else "No"],
        ["Inference Latency",      f"{latency:.2f} s" if latency else "N/A"],
        ["Simpson EF (ref)",       f"{simpson:.1f}%" if simpson is not None else "N/A"],
        ["EDV (rel. units)",       f"{edv_rel:.0f}" if edv_rel is not None else "N/A (no calib.)"],
        ["ESV (rel. units)",       f"{esv_rel:.0f}" if esv_rel is not None else "N/A (no calib.)"],
    ]
    return _kv_table(rows)


def _unsupported_table() -> Table:
    labels = {
        "wall_thickness": "Wall Thickness",
        "sphericity": "Sphericity Index",
        "la_volume": "LA Volume", "ra_volume": "RA Volume",
        "segmentation_overlay": "Segmentation Overlay (multi-frame)",
        "three_d_reconstruction": "3D Reconstruction",
    }
    rows = [["Metric", "Status"]]
    for key, label in labels.items():
        rows.append([label, UNSUPPORTED_METRICS[key]])
    t = Table(rows, colWidths=[4.5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _HDR_BG),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, _BORDER),
        ("TEXTCOLOR",     (1, 1), (1, -1),  _TEXT_SEC),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_WHITE, _BG_LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _metadata_table(result: Dict[str, Any]) -> Table:
    meta       = result.get("metadata", {})
    model_info = result.get("model_info", {})
    qm         = result.get("quality_metrics", {})
    model_label = model_info.get("label") or (
        f"{model_info.get('name', 'unknown')} {model_info.get('variant', '')} "
        f"v{model_info.get('version', '?')}"
    )
    rows = [
        ["Model",           model_label],
        ["Val MAE",         model_info.get("val_mae", "N/A")],
        ["Limitation",      model_info.get("limitation", "N/A")],
        ["Total Frames",    str(meta.get("num_frames", "N/A"))],
        ["FPS",             f"{result.get('fps', 0):.1f}"],
        ["Blur Score",      f"{qm.get('blur_score', 0):.1f}" if qm.get("blur_score") else "N/A"],
        ["Brightness Mean", f"{qm.get('brightness_mean', 0):.1f}" if qm.get("brightness_mean") else "N/A"],
        ["Quality Level",   qm.get("quality_level", "N/A").title()],
    ]
    return _kv_table(rows)


def _kv_table(rows: list) -> Table:
    t = Table(rows, colWidths=[5 * cm, 10.5 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 0), (0, -1), _TEXT),
        ("TEXTCOLOR",     (1, 0), (1, -1), _TEXT),
        ("GRID",          (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [_WHITE, _BG_LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return t


# ── 이미지 생성 (스레드 안전 — Agg only) ─────────────────────────────────────

_TEMP_IMAGES: list = []


def _create_ef_bar_image(
    ef: Optional[float], ef_min: Optional[float], ef_max: Optional[float],
    ef_std: Optional[float],
) -> Optional[Path]:
    """EF 범위 바 + 히어로 수치 이미지 생성"""
    try:
        fig = Figure(figsize=(13, 1.8), facecolor="white")
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111, facecolor="white")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 1)
        ax.axis("off")

        if ef is None:
            return None

        # 구역 배경
        ax.barh(0.4, 40,  height=0.35, left=0,  color="#dc3545", alpha=0.75)
        ax.barh(0.4, 15,  height=0.35, left=40, color="#fd7e14", alpha=0.75)
        ax.barh(0.4, 45,  height=0.35, left=55, color="#198754", alpha=0.75)

        # min-max 범위 하이라이트
        if ef_min is not None and ef_max is not None:
            ax.barh(0.4, ef_max - ef_min, height=0.45, left=ef_min,
                    color="white", alpha=0.3)

        # 현재 EF 마커
        ax.axvline(x=ef, color="white", linewidth=2.5, ymin=0.1, ymax=0.9)
        ax.plot(ef, 0.4, "v", color="white", markersize=10, zorder=5)

        # 구역 레이블
        ax.text(20,  0.40, "<40%\nReduced",        ha="center", va="center", fontsize=8,  color="white", fontweight="bold")
        ax.text(47.5,0.40, "40-54%\nMildly",       ha="center", va="center", fontsize=7.5,color="white", fontweight="bold")
        ax.text(77.5,0.40, "≥55%\nNormal",         ha="center", va="center", fontsize=8,  color="white", fontweight="bold")

        # EF 수치 (큰 텍스트)
        color = "#dc3545" if ef < 40 else "#fd7e14" if ef < 55 else "#198754"
        ax.text(ef, 0.92, f"{ef:.1f}%", ha="center", va="top",
                fontsize=16, color=color, fontweight="bold")
        ax.text(ef, 0.08, f"±{ef_std:.1f}%" if ef_std else "",
                ha="center", va="bottom", fontsize=8, color="#6c757d")

        # 눈금 (20% 간격)
        for x in range(0, 101, 20):
            ax.axvline(x=x, color="#dee2e6", linewidth=0.5, ymin=0, ymax=0.25)
            ax.text(x, 0.05, f"{x}%", ha="center", va="bottom", fontsize=7, color="#adb5bd")

        fig.tight_layout(pad=0.3)
        tmp = Path(tempfile.mktemp(suffix=".png"))
        fig.savefig(str(tmp), dpi=130, bbox_inches="tight", facecolor="white")
        _TEMP_IMAGES.append(tmp)
        return tmp
    except Exception:
        return None


def _create_ef_curve_image(
    framewise_ef: List[float], ed_idx: int, es_idx: int,
    ef_median: float, ef_std: float, ef_mean: Optional[float] = None,
) -> Optional[Path]:
    try:
        fig = Figure(figsize=(13, 3.8), facecolor="white")
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111, facecolor="#f8f9fa")

        xs = range(len(framewise_ef))
        ax.plot(xs, framewise_ef, color="#0d6efd", linewidth=1.3, label="Frame EF")
        ax.fill_between(xs, ef_median - ef_std, ef_median + ef_std,
                        alpha=0.15, color="#0d6efd", label="±1σ band")
        ax.axhline(y=ef_median, color="#0d6efd", linestyle="--", alpha=0.6, linewidth=1,
                   label=f"Median {ef_median:.1f}%")
        if ef_mean is not None and abs(ef_mean - ef_median) > 0.05:
            ax.axhline(y=ef_mean, color="#fd7e14", linestyle=":", alpha=0.7, linewidth=1,
                       label=f"Mean {ef_mean:.1f}%")
        ax.axhline(y=55, color="#dc3545", linestyle=":", alpha=0.5, linewidth=1,
                   label="Reference 55%")

        lo2, hi2 = ef_median - 2*ef_std, ef_median + 2*ef_std
        out_x = [i for i, v in enumerate(framewise_ef) if v < lo2 or v > hi2]
        out_y = [framewise_ef[i] for i in out_x]
        if out_x:
            ax.scatter(out_x, out_y, color="#dc3545", s=20, zorder=4,
                       marker="x", linewidths=1.5, label="Outlier")

        if 0 <= ed_idx < len(framewise_ef):
            ax.plot(ed_idx, framewise_ef[ed_idx], "^", color="#198754",
                    markersize=8, zorder=5, label=f"ED #{ed_idx}")
        if 0 <= es_idx < len(framewise_ef):
            ax.plot(es_idx, framewise_ef[es_idx], "v", color="#dc3545",
                    markersize=8, zorder=5, label=f"ES #{es_idx}")

        ax.set_xlabel("Frame Index", fontsize=8, color="#495057")
        ax.set_ylabel("Predicted EF (%)", fontsize=8, color="#495057")
        ax.set_title("Frame-wise EF Prediction  (ED=▲  ES=▼  ×=outlier)",
                     fontsize=9, color="#212529")
        ax.tick_params(colors="#495057", labelsize=7)
        ax.legend(facecolor="white", edgecolor="#dee2e6",
                  labelcolor="#212529", fontsize=7, ncol=6, loc="upper right")
        for spine in ax.spines.values():
            spine.set_color("#dee2e6")

        fig.tight_layout(pad=0.5)
        tmp = Path(tempfile.mktemp(suffix=".png"))
        fig.savefig(str(tmp), dpi=120, bbox_inches="tight", facecolor="white")
        _TEMP_IMAGES.append(tmp)
        return tmp
    except Exception:
        return None


def _frame_image_element(
    frames: list, idx: int, label: str,
    lv_mask: Optional[np.ndarray] = None, size_cm: float = 6.0
) -> Optional[Image]:
    try:
        if idx >= len(frames):
            return None
        frame = frames[idx]
        if frame.dtype != np.uint8:
            frame = np.clip(frame * 255, 0, 255).astype(np.uint8)
        if len(frame.shape) == 2:
            img_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 1:
            img_bgr = cv2.cvtColor(frame[:, :, 0], cv2.COLOR_GRAY2BGR)
        else:
            img_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # LV 마스크 overlay — 시안(BGR: 204,229,0) 반투명 채우기 + 경계선
        if lv_mask is not None:
            h, w = img_bgr.shape[:2]
            m = cv2.resize(lv_mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
            binary = (m > 0.5).astype(np.uint8)
            overlay = img_bgr.copy()
            mask_px = binary == 1
            overlay[mask_px] = (
                overlay[mask_px] * 0.55 + np.array([204, 229, 0]) * 0.45
            ).astype(np.uint8)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, (204, 229, 0), 1)
            img_bgr = overlay

        cv2.putText(img_bgr, label, (6, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        tmp = Path(tempfile.mktemp(suffix=".png"))
        cv2.imwrite(str(tmp), img_bgr)
        _TEMP_IMAGES.append(tmp)
        return Image(str(tmp), width=size_cm * cm, height=size_cm * cm)
    except Exception:
        return None


def _cleanup_temp_images():
    for p in _TEMP_IMAGES:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
    _TEMP_IMAGES.clear()


# ── 스타일 ────────────────────────────────────────────────────────────────────

def _build_styles():
    s = getSampleStyleSheet()
    b = s["Normal"]

    def ps(name, **kw):
        return ParagraphStyle(name, parent=b, **kw)

    return {
        "app_name":    ps("app_name",    fontSize=10, textColor=_TEXT_SEC,
                           alignment=TA_CENTER),
        "report_title":ps("report_title",fontSize=18, textColor=_TEXT,
                           alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4),
        "disclaimer":  ps("disclaimer",  fontSize=8, textColor=_AMBER,
                           alignment=TA_CENTER, fontName="Helvetica-Bold",
                           backColor=_WARN_BG, borderPadding=4),
        "h2":          ps("h2",          fontSize=11, textColor=_ACCENT,
                           fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=2),
        "normal":      ps("normal_c",    fontSize=9, textColor=_TEXT),
        "small_grey":  ps("small_grey",  fontSize=8, textColor=_TEXT_SEC),
        "warning_high":ps("warning_high",fontSize=9, textColor=_RED,
                           fontName="Helvetica-Bold"),
        "warn_high":   ps("warn_high",   fontSize=9, textColor=_RED,
                           fontName="Helvetica-Bold"),
        "warn_moderate":ps("warn_moderate",fontSize=9, textColor=colors.HexColor("#b45309"),
                            fontName="Helvetica-Bold"),
        "warn_info":   ps("warn_info",   fontSize=9, textColor=_ACCENT,
                           fontName="Helvetica-Bold"),
        "warn_action": ps("warn_action", fontSize=8, textColor=_TEXT_SEC),
        "tbl_hdr":     ps("tbl_hdr",     fontSize=10, fontName="Helvetica-Bold",
                           textColor=_TEXT, alignment=TA_CENTER),
        "footer":      ps("footer",      fontSize=7, textColor=_TEXT_SEC,
                           alignment=TA_CENTER),
    }
