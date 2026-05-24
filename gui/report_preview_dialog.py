"""Report Preview Dialog — 분석 결과 요약 모달 (PDF 열기 전 확인)"""
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPolygon
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget, QFrame,
)

from gui.styles import (
    BG_BASE, BG_CARD, BG_PANEL, BORDER, TEXT_PRI, TEXT_SEC,
    EF_NORMAL, EF_MID, EF_LOW, HIGH_CLR, MED_CLR, LOW_CLR,
    ACCENT, ef_color,
)
from utils.constants import CONFIDENCE_COLORS


class _EFBar(QWidget):
    """EF 값을 0-100% 임상 참고 범위 위에 표시하는 수평 바"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._ef: Optional[float] = None
        self._ef_min: Optional[float] = None
        self._ef_max: Optional[float] = None

    def set_value(self, ef: float, ef_min: float = None, ef_max: float = None):
        self._ef = ef
        self._ef_min = ef_min
        self._ef_max = ef_max
        self.update()

    def paintEvent(self, _):
        if self._ef is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        BAR_Y, BAR_H = 14, 10

        def xp(pct):
            return int(w * max(0.0, min(pct, 100.0)) / 100.0)

        # 배경 구역
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(EF_LOW));    p.drawRect(0,       BAR_Y, xp(40),          BAR_H)
        p.setBrush(QColor(EF_MID));    p.drawRect(xp(40),  BAR_Y, xp(55)-xp(40),   BAR_H)
        p.setBrush(QColor(EF_NORMAL)); p.drawRect(xp(55),  BAR_Y, w - xp(55),       BAR_H)

        # min-max 범위 표시
        if self._ef_min is not None and self._ef_max is not None:
            x1, x2 = xp(self._ef_min), xp(self._ef_max)
            p.setBrush(QColor(255, 255, 255, 55))
            p.drawRect(x1, BAR_Y - 2, max(x2 - x1, 2), BAR_H + 4)

        # 현재 EF 삼각 마커
        mx = xp(self._ef)
        p.setBrush(QColor("white"))
        tri = QPolygon([QPoint(mx - 5, BAR_Y - 1),
                        QPoint(mx + 5, BAR_Y - 1),
                        QPoint(mx, BAR_Y + BAR_H + 3)])
        p.drawPolygon(tri)

        # 구역 레이블
        p.setPen(QColor(255, 255, 255, 200))
        font = p.font(); font.setPointSize(7); p.setFont(font)
        p.drawText(2, BAR_Y, xp(40) - 4, BAR_H, Qt.AlignCenter | Qt.AlignVCenter, "<40%")
        p.drawText(xp(40) + 2, BAR_Y, xp(55) - xp(40) - 4, BAR_H, Qt.AlignCenter | Qt.AlignVCenter, "40-54%")
        p.drawText(xp(55) + 2, BAR_Y, w - xp(55) - 4, BAR_H, Qt.AlignCenter | Qt.AlignVCenter, "≥55%")


class ReportPreviewDialog(QDialog):
    """분석 결과 요약 모달 — PDF 열기 전 핵심 수치 확인"""

    def __init__(self, result: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._result = result
        self.setWindowTitle("Analysis Summary")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog   {{ background-color: {BG_BASE}; color: {TEXT_PRI}; }}
            QLabel    {{ color: {TEXT_PRI}; }}
            QFrame    {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 4px; }}
        """)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # 헤더
        lbl_title = QLabel("Analysis Summary")
        lbl_title.setStyleSheet(f"color:{TEXT_PRI}; font-size:15px; font-weight:700; border:none;")
        root.addWidget(lbl_title)

        ef        = self._result.get("ef")
        ef_mean   = self._result.get("ef_mean")
        ef_std    = self._result.get("ef_std")
        ef_min    = self._result.get("ef_min")
        ef_max    = self._result.get("ef_max")
        conf      = self._result.get("confidence_level", "Unknown")
        frames    = self._result.get("metadata", {}).get("num_frames", 0)
        latency   = self._result.get("inference_latency_s")
        quality   = self._result.get("quality_metrics", {})
        q_level   = quality.get("quality_level", "good")
        q_warns   = quality.get("warnings", [])

        # ── EF 히어로 카드 ──
        ef_card = QFrame()
        ef_lo = QVBoxLayout(ef_card)
        ef_lo.setContentsMargins(16, 14, 16, 14)
        ef_lo.setSpacing(6)

        lbl_ef_title = QLabel("Estimated EF (median)")
        lbl_ef_title.setStyleSheet(f"color:{TEXT_SEC}; font-size:10px; font-weight:600; text-transform:uppercase; border:none;")
        ef_lo.addWidget(lbl_ef_title)

        ef_row = QHBoxLayout()
        ef_str = f"{ef:.1f}" if ef is not None else "--"
        color  = ef_color(ef) if ef is not None else TEXT_SEC
        lbl_ef_val = QLabel(ef_str)
        lbl_ef_val.setStyleSheet(f"color:{color}; font-size:48px; font-weight:700; border:none;")
        lbl_ef_unit = QLabel("  %")
        lbl_ef_unit.setStyleSheet(f"color:{TEXT_SEC}; font-size:18px; border:none;")
        lbl_ef_unit.setAlignment(Qt.AlignBottom)
        ef_row.addWidget(lbl_ef_val)
        ef_row.addWidget(lbl_ef_unit)
        ef_row.addStretch()
        ef_lo.addLayout(ef_row)

        # EF 범위 바
        self.ef_bar = _EFBar()
        if ef is not None:
            self.ef_bar.set_value(ef, ef_min, ef_max)
        ef_lo.addWidget(self.ef_bar)

        # 참고 범위 레이블
        lbl_ref = QLabel("Reference: <40% Reduced  ·  40–54% Mildly Reduced  ·  ≥55% Normal")
        lbl_ref.setStyleSheet(f"color:{TEXT_SEC}; font-size:9px; border:none;")
        ef_lo.addWidget(lbl_ref)

        root.addWidget(ef_card)

        # ── 통계 행 ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        for label, value in [
            ("Mean",      f"{ef_mean:.1f}%" if ef_mean is not None else "--"),
            ("Std (σ)",   f"±{ef_std:.1f}%" if ef_std is not None else "--"),
            ("Range",     f"{ef_min:.1f}–{ef_max:.1f}%" if ef_min is not None else "--"),
            ("Frames",    str(frames) if frames else "--"),
            ("Latency",   f"{latency:.2f}s" if latency else "--"),
        ]:
            stat = self._stat_chip(label, value)
            stats_row.addWidget(stat)
        root.addLayout(stats_row)

        # ── Stability + Quality ──
        sq_row = QHBoxLayout()
        sq_row.setSpacing(10)

        stab_card = QFrame()
        stab_lo = QVBoxLayout(stab_card)
        stab_lo.setContentsMargins(12, 10, 12, 10)
        stab_lo.setSpacing(4)
        lbl_stab_t = QLabel("Prediction Stability")
        lbl_stab_t.setStyleSheet(f"color:{TEXT_SEC}; font-size:9px; font-weight:600; border:none;")
        stab_lo.addWidget(lbl_stab_t)
        c = CONFIDENCE_COLORS.get(conf, TEXT_SEC)
        lbl_stab_v = QLabel(conf)
        lbl_stab_v.setStyleSheet(f"color:{c}; font-size:13px; font-weight:700; border:none;")
        stab_lo.addWidget(lbl_stab_v)
        if ef_std is not None:
            lbl_stab_s = QLabel(f"EF std ±{ef_std:.2f}%  ·  {frames} frames")
            lbl_stab_s.setStyleSheet(f"color:{TEXT_SEC}; font-size:9px; border:none;")
            stab_lo.addWidget(lbl_stab_s)
        sq_row.addWidget(stab_card, 1)

        qual_card = QFrame()
        qual_lo = QVBoxLayout(qual_card)
        qual_lo.setContentsMargins(12, 10, 12, 10)
        qual_lo.setSpacing(4)
        lbl_q_t = QLabel("Image Quality")
        lbl_q_t.setStyleSheet(f"color:{TEXT_SEC}; font-size:9px; font-weight:600; border:none;")
        qual_lo.addWidget(lbl_q_t)
        q_color = {"good": HIGH_CLR, "moderate": MED_CLR, "poor": LOW_CLR}.get(q_level, TEXT_SEC)
        q_icon  = {"good": "● Good", "moderate": "▲ Moderate", "poor": "✕ Poor"}.get(q_level, q_level.title())
        lbl_q_v = QLabel(q_icon)
        lbl_q_v.setStyleSheet(f"color:{q_color}; font-size:13px; font-weight:700; border:none;")
        qual_lo.addWidget(lbl_q_v)
        if q_warns:
            lbl_q_w = QLabel(f"{len(q_warns)} warning(s)")
            lbl_q_w.setStyleSheet(f"color:{TEXT_SEC}; font-size:9px; border:none;")
            qual_lo.addWidget(lbl_q_w)
        sq_row.addWidget(qual_card, 1)
        root.addLayout(sq_row)

        # ── 경고 목록 (있는 경우만) ──
        if q_warns:
            for w in q_warns[:3]:
                short = w[:90] + ("…" if len(w) > 90 else "")
                lbl_w = QLabel(f"• {short}")
                lbl_w.setWordWrap(True)
                lbl_w.setStyleSheet(f"color:#909090; font-size:9px;")
                root.addWidget(lbl_w)

        # ── 버튼 행 ──
        root.addSpacing(4)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{BORDER}; border:none; max-height:1px;")
        root.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setFixedHeight(32)
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)

        self.btn_pdf = QPushButton("Open PDF Report")
        self.btn_pdf.setProperty("class", "primary")
        self.btn_pdf.setFixedHeight(32)
        report_path = self._result.get("report_path")
        self.btn_pdf.setEnabled(bool(report_path and Path(str(report_path)).exists()))
        self.btn_pdf.clicked.connect(self._open_pdf)
        btn_row.addWidget(self.btn_pdf)

        root.addLayout(btn_row)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _stat_chip(self, label: str, value: str) -> QFrame:
        chip = QFrame()
        chip.setStyleSheet(f"QFrame {{ background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:4px; }}")
        lo = QVBoxLayout(chip)
        lo.setContentsMargins(10, 8, 10, 8)
        lo.setSpacing(2)
        l1 = QLabel(label)
        l1.setStyleSheet(f"color:{TEXT_SEC}; font-size:9px; border:none;")
        l2 = QLabel(value)
        l2.setStyleSheet(f"color:{TEXT_PRI}; font-size:12px; font-weight:600; border:none;")
        lo.addWidget(l1)
        lo.addWidget(l2)
        return chip

    def _open_pdf(self):
        import platform, subprocess
        path = self._result.get("report_path")
        if path and Path(str(path)).exists():
            sys_ = platform.system()
            if sys_ == "Darwin":   subprocess.run(["open", str(path)])
            elif sys_ == "Windows": subprocess.run(["start", str(path)], shell=True)
            else:                   subprocess.run(["xdg-open", str(path)])
        self.accept()
