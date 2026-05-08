"""
PDF 리포트 생성 모듈 — SonoCube v1.2
ReportLab + OpenCV + matplotlib(Agg, 스레드 안전)
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from utils.constants import (
    APP_NAME, APP_VERSION, DISCLAIMER, UNSUPPORTED_METRICS,
    CONFIDENCE_NOTE, CONFIDENCE_LOW_WARNING, CONFIDENCE_COLORS,
)


# ── 색상 ──────────────────────────────────────────────────────────────────────
_NAVY  = colors.HexColor("#0d1117")
_BLUE  = colors.HexColor("#1f6feb")
_CYAN  = colors.HexColor("#58a6ff")
_GREY  = colors.HexColor("#8b949e")
_WARN  = colors.HexColor("#d29922")
_HIGH  = colors.HexColor("#3fb950")
_MED   = colors.HexColor("#d29922")
_LOW   = colors.HexColor("#f85149")
_TEXT  = colors.HexColor("#1a1a2e")
_LIGHT = colors.HexColor("#f6f8fa")
_HDR   = colors.HexColor("#e8eaf6")


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
    story = _build_story(analysis_result, styles)
    doc.build(story)
    _cleanup_temp_images()


# ── 스토리 구성 ───────────────────────────────────────────────────────────────

def _build_story(result: Dict[str, Any], styles) -> list:
    story = []

    # ── 헤더 ──
    story.append(Paragraph(f"{APP_NAME} — Cardiac Echo Analysis Report", styles["title"]))
    story.append(Paragraph(f"Version {APP_VERSION}", styles["subtitle"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(DISCLAIMER, styles["disclaimer"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── 케이스 정보 ──
    story.append(Paragraph("Case Information", styles["h2"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_case_info_table(result, styles))
    story.append(Spacer(1, 0.5 * cm))

    # ── EF 결과 ──
    story.append(Paragraph("EF Analysis Results", styles["h2"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_ef_results_table(result, styles))
    story.append(Spacer(1, 0.3 * cm))

    conf = result.get("confidence_level", "Unknown")
    story.append(Paragraph(f"Prediction Stability: <b>{conf}</b>", styles["normal"]))
    story.append(Paragraph(CONFIDENCE_NOTE, styles["small_grey"]))
    if conf == "Low":
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"⚠ {CONFIDENCE_LOW_WARNING}", styles["warning"]))
    story.append(Spacer(1, 0.3 * cm))

    # ── Manual override 표시 ──
    if result.get("manual_override"):
        story.append(Paragraph(
            "ED/ES Override: <b>Manual</b>  "
            f"(AI candidates: ED=#{result.get('ed_frame_index_ai','?')}  "
            f"ES=#{result.get('es_frame_index_ai','?')})",
            styles["normal"]
        ))
        story.append(Spacer(1, 0.3 * cm))

    # ── Quality Warnings ──
    quality = result.get("quality_metrics", {})
    warnings = quality.get("warnings", [])
    if warnings:
        story.append(Paragraph("Quality Warnings", styles["h2"]))
        story.append(Spacer(1, 0.1 * cm))
        for w in warnings:
            story.append(Paragraph(f"• {w}", styles["warning"]))
        story.append(Spacer(1, 0.4 * cm))

    # ── Frame-wise EF Curve ──
    framewise_ef = result.get("framewise_ef", [])
    if framewise_ef:
        story.append(Paragraph("Frame-wise EF Prediction Curve", styles["h2"]))
        story.append(Spacer(1, 0.2 * cm))
        ed_final = result.get("ed_frame_index_final", result.get("ed_frame_idx", 0))
        es_final = result.get("es_frame_index_final", result.get("es_frame_idx", 0))
        curve_path = _create_ef_curve_image(
            framewise_ef,
            ed_final,
            es_final,
            result.get("ef", 0.0),
            result.get("ef_std", 0.0),
            result.get("ef_mean"),
        )
        if curve_path:
            story.append(Image(str(curve_path), width=15 * cm, height=5.5 * cm))
        story.append(Spacer(1, 0.5 * cm))

    # ── ED/ES Snapshots ──
    frames = result.get("frames", [])
    ed_idx = result.get("ed_frame_index_final", result.get("ed_frame_idx", 0))
    es_idx = result.get("es_frame_index_final", result.get("es_frame_idx", 0))
    if frames:
        story.append(Paragraph("Candidate Frame Snapshots", styles["h2"]))
        story.append(Spacer(1, 0.2 * cm))
        snap_data = [["ED Candidate Frame", "ES Candidate Frame"]]
        ed_img = _frame_image_element(frames, ed_idx, label="ED")
        es_img = _frame_image_element(frames, es_idx, label="ES")
        snap_data.append([ed_img or "N/A", es_img or "N/A"])
        snap_table = Table(snap_data, colWidths=[7.5 * cm, 7.5 * cm])
        snap_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, 0), _HDR),
        ]))
        story.append(snap_table)
        story.append(Spacer(1, 0.5 * cm))

    # ── 미지원 지표 ──
    story.append(Paragraph("Unsupported Metrics (Current Version)", styles["h2"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_unsupported_table(styles))
    story.append(Spacer(1, 0.5 * cm))

    # ── 모델 / 메타데이터 ──
    story.append(Paragraph("Model & Analysis Metadata", styles["h2"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_metadata_table(result, styles))
    story.append(Spacer(1, 0.5 * cm))

    # ── 푸터 ──
    story.append(Paragraph(
        DISCLAIMER + " This report is auto-generated and must not be used for clinical decisions.",
        styles["footer"],
    ))

    return story


# ── 테이블 빌더 ──────────────────────────────────────────────────────────────

def _case_info_table(result: Dict[str, Any], styles) -> Table:
    metadata = result.get("metadata", {})
    file_path = metadata.get("file_path", "N/A")
    file_name = Path(file_path).name if file_path != "N/A" else "N/A"
    stem = Path(file_path).stem if file_path != "N/A" else "UNKNOWN"
    case_id = stem[:8].upper().ljust(8, "0")
    override = result.get("manual_override", False)

    rows = [
        ["Case ID",          case_id],
        ["Input File",       file_name],
        ["Analysis Date",    datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["View Type",        result.get("view_type", "Unknown")],
        ["App Version",      APP_VERSION],
        ["ED/ES Source",     "Manual override" if override else "AI prediction"],
    ]
    return _simple_kv_table(rows)


def _ef_results_table(result: Dict[str, Any], styles) -> Table:
    ef     = result.get("ef", 0.0)
    ef_mean = result.get("ef_mean", 0.0)
    ef_std = result.get("ef_std", 0.0)
    ef_min = result.get("ef_min", 0.0)
    ef_max = result.get("ef_max", 0.0)
    conf   = result.get("confidence_level", "Unknown")
    ed_idx = result.get("ed_frame_index_final", result.get("ed_frame_idx", 0))
    es_idx = result.get("es_frame_index_final", result.get("es_frame_idx", 0))
    latency = result.get("inference_latency_s")

    rows = [
        ["Estimated EF (median)",    f"{ef:.1f}%"],
        ["EF Mean",                  f"{ef_mean:.1f}%"],
        ["EF Std (σ)",               f"{ef_std:.1f}%"],
        ["EF Min / Max",             f"{ef_min:.1f}% / {ef_max:.1f}%"],
        ["Confidence Range",         f"{ef:.1f}% ± {ef_std:.1f}%"],
        ["Prediction Stability",     conf],
        ["ED Candidate Frame",       f"#{ed_idx}"],
        ["ES Candidate Frame",       f"#{es_idx}"],
        ["Manual Override",          "Yes" if result.get("manual_override") else "No"],
        ["Inference Latency",        f"{latency:.2f} s" if latency else "N/A"],
        ["EDV",                      "Not available — " + UNSUPPORTED_METRICS["edv"]],
        ["ESV",                      "Not available — " + UNSUPPORTED_METRICS["esv"]],
    ]
    return _simple_kv_table(rows)


def _unsupported_table(styles) -> Table:
    rows = [["Metric", "Status"]]
    labels = {
        "edv": "EDV",
        "esv": "ESV",
        "wall_thickness": "Wall Thickness",
        "sphericity": "Sphericity Index",
        "la_volume": "LA Volume",
        "ra_volume": "RA Volume",
        "segmentation_overlay": "Segmentation Overlay",
        "three_d_reconstruction": "3D Reconstruction",
    }
    for key, label in labels.items():
        rows.append([label, UNSUPPORTED_METRICS[key]])
    t = Table(rows, colWidths=[5 * cm, 10.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _HDR),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("TEXTCOLOR", (1, 1), (1, -1), _GREY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
    ]))
    return t


def _metadata_table(result: Dict[str, Any], styles) -> Table:
    metadata = result.get("metadata", {})
    model_info = result.get("model_info", {})
    qm = result.get("quality_metrics", {})
    rows = [
        ["Model Name",       model_info.get("name", "unknown")],
        ["Model Variant",    model_info.get("variant", "unknown")],
        ["Model Version",    model_info.get("version", "unknown")],
        ["Model Path",       model_info.get("path", "unknown")],
        ["Total Frames",     str(metadata.get("num_frames", "N/A"))],
        ["Frame Size",       str(metadata.get("frame_size", "N/A"))],
        ["FPS",              f"{result.get('fps', 0):.1f}"],
        ["Blur Score",       f"{qm.get('blur_score', 'N/A'):.1f}" if qm.get("blur_score") else "N/A"],
        ["Brightness Mean",  f"{qm.get('brightness_mean', 'N/A'):.1f}" if qm.get("brightness_mean") else "N/A"],
    ]
    return _simple_kv_table(rows)


def _simple_kv_table(rows: list) -> Table:
    t = Table(rows, colWidths=[5.5 * cm, 10 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ── 이미지 생성 (스레드 안전) ─────────────────────────────────────────────────

_TEMP_IMAGES: list = []


def _create_ef_curve_image(
    framewise_ef: List[float],
    ed_idx: int,
    es_idx: int,
    ef_median: float,
    ef_std: float,
    ef_mean: Optional[float] = None,
) -> Optional[Path]:
    try:
        fig = Figure(figsize=(13, 3.8), facecolor="#0d1117")
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111, facecolor="#161b22")

        xs = range(len(framewise_ef))
        ax.plot(xs, framewise_ef, color="#58a6ff", linewidth=1.2, label="Frame EF")
        ax.fill_between(xs, ef_median - ef_std, ef_median + ef_std,
                        alpha=0.12, color="#58a6ff", label="±1σ band")
        ax.axhline(y=ef_median, color="#58a6ff", linestyle="--", alpha=0.5, linewidth=1,
                   label=f"Median {ef_median:.1f}%")
        if ef_mean is not None and abs(ef_mean - ef_median) > 0.05:
            ax.axhline(y=ef_mean, color="#d29922", linestyle=":", alpha=0.6, linewidth=1,
                       label=f"Mean {ef_mean:.1f}%")
        ax.axhline(y=55, color="#f85149", linestyle=":", alpha=0.5, linewidth=1,
                   label="Normal (55%)")

        # Outlier markers
        lo2 = ef_median - 2 * ef_std
        hi2 = ef_median + 2 * ef_std
        out_x = [i for i, v in enumerate(framewise_ef) if v < lo2 or v > hi2]
        out_y = [framewise_ef[i] for i in out_x]
        if out_x:
            ax.scatter(out_x, out_y, color="#f85149", s=20, zorder=4, marker="x",
                       linewidths=1.5, label="Outlier")

        if 0 <= ed_idx < len(framewise_ef):
            ax.plot(ed_idx, framewise_ef[ed_idx], "^", color="#3fb950",
                    markersize=8, zorder=5, label=f"ED f{ed_idx}")
        if 0 <= es_idx < len(framewise_ef):
            ax.plot(es_idx, framewise_ef[es_idx], "v", color="#f85149",
                    markersize=8, zorder=5, label=f"ES f{es_idx}")

        ax.set_xlabel("Frame Index", color="#e6edf3", fontsize=8)
        ax.set_ylabel("Predicted EF (%)", color="#e6edf3", fontsize=8)
        ax.set_title("Frame-wise EF Prediction  (ED=▲  ES=▼  ×=outlier)",
                     color="#e6edf3", fontsize=9)
        ax.tick_params(colors="#e6edf3")
        ax.legend(facecolor="#161b22", edgecolor="#30363d",
                  labelcolor="#e6edf3", fontsize=7, ncol=6)
        for spine in ax.spines.values():
            spine.set_color("#30363d")
        fig.tight_layout(pad=0.5)

        tmp = Path(tempfile.mktemp(suffix=".png"))
        fig.savefig(str(tmp), dpi=120, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        _TEMP_IMAGES.append(tmp)
        return tmp
    except Exception:
        return None


def _frame_image_element(
    frames: list, idx: int, label: str, size_cm: float = 6.0
) -> Optional[Image]:
    try:
        if idx >= len(frames):
            return None
        frame = frames[idx]
        if len(frame.shape) == 2:
            img_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 1:
            img_bgr = cv2.cvtColor(frame[:, :, 0], cv2.COLOR_GRAY2BGR)
        else:
            img_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
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
    base = s["Normal"]

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base, **kw)

    return {
        "title":      ps("title",      fontSize=16, textColor=_BLUE,
                          spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "subtitle":   ps("subtitle",   fontSize=10, textColor=_GREY,
                          spaceAfter=2, alignment=TA_CENTER),
        "disclaimer": ps("disclaimer", fontSize=8, textColor=_WARN,
                          alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "h2":         ps("h2",         fontSize=11, textColor=_BLUE,
                          fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=2),
        "normal":     ps("normal_c",   fontSize=9),
        "small_grey": ps("small_grey", fontSize=8, textColor=_GREY),
        "warning":    ps("warning",    fontSize=9, textColor=_LOW,
                          fontName="Helvetica-Bold"),
        "footer":     ps("footer",     fontSize=7, textColor=_GREY,
                          alignment=TA_CENTER),
    }
