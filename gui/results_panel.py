"""Results 패널 — 요약 카드 4개, 상세 통계, quality warning"""
from typing import Any, Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget,
)

from utils.constants import APP_VERSION, CONFIDENCE_COLORS, CONFIDENCE_NOTE, CONFIDENCE_LOW_WARNING


class _SummaryCard(QWidget):
    def __init__(self, title: str, value: str = "--", unit: str = "",
                 color: str = "#58a6ff", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        self.setStyleSheet(
            "background-color: #1c2128; border: 1px solid #30363d; border-radius: 8px;"
        )
        lo = QVBoxLayout(self)
        lo.setContentsMargins(16, 14, 16, 14)
        lo.setSpacing(2)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(
            "color: #8b949e; font-size: 10px; font-weight: 600;"
            "letter-spacing: 0.5px; border: none;"
        )
        lo.addWidget(title_lbl)

        val_row = QHBoxLayout()
        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color: {color}; font-size: 30px; font-weight: 700; border: none;"
        )
        val_row.addWidget(self._val)
        if unit:
            u = QLabel(unit)
            u.setStyleSheet("color: #8b949e; font-size: 13px; border: none;")
            u.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
            val_row.addWidget(u)
        val_row.addStretch()
        lo.addLayout(val_row)

    def update(self, value: str, color: str = None):
        self._val.setText(value)
        if color:
            self._val.setStyleSheet(
                f"color: {color}; font-size: 30px; font-weight: 700; border: none;"
            )


class ResultsPanel(QWidget):
    """Results 탭"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(16)

        # 제목
        title = QLabel("Analysis Results")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: 700;")
        outer.addWidget(title)

        # ── 요약 카드 4개 ──
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.card_ef    = _SummaryCard("Estimated EF", "--", "%")
        self.card_conf  = _SummaryCard("Prediction Stability", "--", "", "#8b949e")
        self.card_ed    = _SummaryCard("ED Candidate", "--", "frame", "#3fb950")
        self.card_es    = _SummaryCard("ES Candidate", "--", "frame", "#f85149")
        for c in (self.card_ef, self.card_conf, self.card_ed, self.card_es):
            cards_row.addWidget(c)
        outer.addLayout(cards_row)

        # ── Confidence 경고 ──
        self.warn_box = QLabel("")
        self.warn_box.setWordWrap(True)
        self.warn_box.setVisible(False)
        self.warn_box.setStyleSheet(
            "color: #f85149; font-size: 11px; font-weight: 600;"
            "background-color: #2a0d0d; border: 1px solid #4a1515;"
            "border-radius: 4px; padding: 8px;"
        )
        outer.addWidget(self.warn_box)

        # ── 통계 상세 ──
        stats_group = QGroupBox("EF Statistics")
        stats_form = QFormLayout(stats_group)
        stats_form.setLabelAlignment(Qt.AlignRight)
        stats_form.setSpacing(10)

        self._stat_labels: Dict[str, QLabel] = {}
        rows = [
            ("ef_median",    "EF Median"),
            ("ef_mean",      "EF Mean"),
            ("ef_std",       "EF Std (σ)"),
            ("ef_min",       "EF Min"),
            ("ef_max",       "EF Max"),
            ("conf_range",   "Confidence Range"),
            ("conf_level",   "Prediction Stability"),
            ("ed_frame",     "ED Candidate Frame"),
            ("es_frame",     "ES Candidate Frame"),
            ("override",     "Manual Override"),
            ("frames",       "Frames Analyzed"),
            ("latency",      "Inference Latency"),
        ]
        for key, label in rows:
            lbl = QLabel(label + ":")
            lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
            val = QLabel("--")
            val.setStyleSheet("color: #e6edf3; font-size: 12px; font-weight: 500;")
            stats_form.addRow(lbl, val)
            self._stat_labels[key] = val
        outer.addWidget(stats_group)

        # ── 모델 / 앱 정보 ──
        meta_group = QGroupBox("Model & Application")
        meta_form = QFormLayout(meta_group)
        meta_form.setLabelAlignment(Qt.AlignRight)
        meta_form.setSpacing(8)
        self._meta_labels: Dict[str, QLabel] = {}
        for key, label in [
            ("model_name",    "Model Name"),
            ("model_variant", "Model Variant"),
            ("model_version", "Model Version"),
            ("model_path",    "Model Path"),
            ("app_version",   "App Version"),
            ("timestamp",     "Analysis Timestamp"),
        ]:
            lbl = QLabel(label + ":")
            lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
            val = QLabel("--")
            val.setStyleSheet("color: #e6edf3; font-size: 12px;")
            val.setWordWrap(True)
            meta_form.addRow(lbl, val)
            self._meta_labels[key] = val
        outer.addWidget(meta_group)

        # ── Quality Warnings ──
        self.qw_group = QGroupBox("Quality Warnings")
        qw_layout = QVBoxLayout(self.qw_group)
        self.qw_content = QLabel("No warnings.")
        self.qw_content.setWordWrap(True)
        self.qw_content.setStyleSheet("color: #8b949e; font-size: 12px;")
        qw_layout.addWidget(self.qw_content)
        outer.addWidget(self.qw_group)

        # ── Stability 설명 ──
        note_lbl = QLabel(CONFIDENCE_NOTE)
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-style: italic;"
            "background-color: #1c2128; border: 1px solid #30363d;"
            "border-radius: 4px; padding: 8px;"
        )
        outer.addWidget(note_lbl)

        # ── 미지원 지표 ──
        unsup_group = QGroupBox("Unsupported Metrics (v1.2)")
        unsup_layout = QVBoxLayout(unsup_group)
        from utils.constants import UNSUPPORTED_METRICS
        for key, desc in UNSUPPORTED_METRICS.items():
            row = QHBoxLayout()
            k_lbl = QLabel(key.replace("_", " ").title() + ":")
            k_lbl.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 600;")
            k_lbl.setFixedWidth(160)
            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("color: #484f58; font-size: 11px;")
            d_lbl.setWordWrap(True)
            row.addWidget(k_lbl)
            row.addWidget(d_lbl)
            unsup_layout.addLayout(row)
        outer.addWidget(unsup_group)

        outer.addStretch()
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    # ── 데이터 업데이트 ───────────────────────────────────────────────────────

    def update_result(self, result: Dict[str, Any]):
        ef = result.get("ef")
        ef_mean = result.get("ef_mean")
        ef_std = result.get("ef_std")
        ef_min = result.get("ef_min")
        ef_max = result.get("ef_max")
        conf = result.get("confidence_level", "Unknown")
        ed = result.get("ed_frame_index_final", result.get("ed_frame_idx", 0))
        es = result.get("es_frame_index_final", result.get("es_frame_idx", 0))
        override = result.get("manual_override", False)
        model_info = result.get("model_info", {})
        meta = result.get("metadata", {})
        latency = result.get("inference_latency_s")
        quality = result.get("quality_metrics", {})
        from datetime import datetime

        # 요약 카드
        ef_str = f"{ef:.1f}" if ef is not None else "--"
        self.card_ef.update(ef_str)
        conf_color = CONFIDENCE_COLORS.get(conf, "#8b949e")
        self.card_conf.update(conf, conf_color)
        self.card_ed.update(str(ed))
        self.card_es.update(str(es))

        # Low confidence 경고
        if conf == "Low":
            self.warn_box.setText(f"⚠  {CONFIDENCE_LOW_WARNING}")
            self.warn_box.setVisible(True)
        else:
            self.warn_box.setVisible(False)

        # 통계
        s = self._stat_labels
        s["ef_median"].setText(f"{ef:.1f}%" if ef is not None else "--")
        s["ef_mean"].setText(f"{ef_mean:.1f}%" if ef_mean is not None else "--")
        s["ef_std"].setText(f"± {ef_std:.1f}%" if ef_std is not None else "--")
        s["ef_min"].setText(f"{ef_min:.1f}%" if ef_min is not None else "--")
        s["ef_max"].setText(f"{ef_max:.1f}%" if ef_max is not None else "--")
        if ef is not None and ef_std is not None:
            s["conf_range"].setText(f"{ef:.1f}% ± {ef_std:.1f}%")
        else:
            s["conf_range"].setText("--")
        s["conf_level"].setText(conf)
        s["conf_level"].setStyleSheet(f"color: {conf_color}; font-size: 12px; font-weight: 600;")
        s["ed_frame"].setText(f"#{ed}")
        s["es_frame"].setText(f"#{es}")
        s["override"].setText("Yes (manual)" if override else "No (AI)")
        s["frames"].setText(str(meta.get("num_frames", "--")))
        s["latency"].setText(f"{latency:.2f} s" if latency else "--")

        # 모델 / 앱
        m = self._meta_labels
        m["model_name"].setText(model_info.get("name", "--"))
        m["model_variant"].setText(model_info.get("variant", "--"))
        m["model_version"].setText(model_info.get("version", "--"))
        m["model_path"].setText(model_info.get("path", "--"))
        m["app_version"].setText(APP_VERSION)
        m["timestamp"].setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Quality warnings
        warnings = quality.get("warnings", [])
        if warnings:
            text = "\n".join(f"• {w}" for w in warnings)
            self.qw_content.setText(text)
            self.qw_content.setStyleSheet("color: #d29922; font-size: 12px;")
        else:
            self.qw_content.setText("No warnings.")
            self.qw_content.setStyleSheet("color: #3fb950; font-size: 12px;")
