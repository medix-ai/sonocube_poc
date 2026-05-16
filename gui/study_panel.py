"""
Study Panel — SonoCube 메인 작업 공간
3-column 레이아웃: 좌(파일·컨트롤) | 중(뷰어·EF curve) | 우(EF 결과·Quality)

의료 workstation 스타일: 단일 화면에서 업로드→분석→결과 확인 완결
"""
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPixmap
from PyQt5.QtWidgets import (
    QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSlider, QSplitter, QVBoxLayout, QWidget, QComboBox, QLineEdit,
    QStackedWidget,
)

from gui.ef_curve_widget import EFCurveWidget
from gui.styles import ef_color, HIGH_CLR, MED_CLR, LOW_CLR, EF_NORMAL, EF_MID, EF_LOW
from utils.constants import APP_NAME, APP_VERSION, DISCLAIMER, CONFIDENCE_COLORS

_SUPPORTED_EXT = {".mp4", ".avi", ".mov", ".mkv", ".dcm", ".dicom"}


# ── 작은 유틸 위젯 ─────────────────────────────────────────────────────────────

class Divider(QFrame):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine if orientation == Qt.Horizontal else QFrame.VLine)
        self.setStyleSheet("color: #404040;")
        self.setFixedHeight(1) if orientation == Qt.Horizontal else self.setFixedWidth(1)


class EFDisplay(QWidget):
    """EF 수치 강조 표시 위젯 — 결과 패널 상단의 핵심 요소"""

    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(16, 16, 16, 12)
        lo.setSpacing(4)

        lbl_title = QLabel("Estimated EF")
        lbl_title.setStyleSheet(
            "color: #909090; font-size: 10px; font-weight: 600;"
            "text-transform: uppercase; letter-spacing: 0.8px;"
        )
        lo.addWidget(lbl_title)

        self._val = QLabel("--")
        self._val.setStyleSheet(
            "color: #f0f0f0; font-size: 52px; font-weight: 700; line-height: 1;"
        )
        lo.addWidget(self._val)

        self._unit = QLabel("% (median)")
        self._unit.setStyleSheet("color: #909090; font-size: 11px;")
        lo.addWidget(self._unit)

        lo.addSpacing(8)

        row = QHBoxLayout()
        self._mean_lbl = QLabel("Mean --")
        self._std_lbl  = QLabel("Std --")
        self._rng_lbl  = QLabel("Range --")
        for l in (self._mean_lbl, self._std_lbl, self._rng_lbl):
            l.setStyleSheet("color: #707070; font-size: 11px;")
            row.addWidget(l)
        row.addStretch()
        lo.addLayout(row)

        note = QLabel("For research reference only — not for diagnostic use")
        note.setStyleSheet("color: #505050; font-size: 9px; font-style: italic;")
        lo.addWidget(note)

    def update(self, ef: Optional[float], ef_mean=None, ef_std=None, ef_min=None, ef_max=None):
        if ef is None:
            self._val.setText("--")
            self._val.setStyleSheet("color: #f0f0f0; font-size: 52px; font-weight: 700;")
            self._mean_lbl.setText("Mean --")
            self._std_lbl.setText("Std --")
            self._rng_lbl.setText("Range --")
            return
        color = ef_color(ef)
        self._val.setText(f"{ef:.1f}")
        self._val.setStyleSheet(f"color: {color}; font-size: 52px; font-weight: 700;")
        self._mean_lbl.setText(f"Mean {ef_mean:.1f}%" if ef_mean is not None else "Mean --")
        self._std_lbl.setText(f"Std ±{ef_std:.1f}%" if ef_std is not None else "Std --")
        if ef_min is not None and ef_max is not None:
            self._rng_lbl.setText(f"Range {ef_min:.1f}–{ef_max:.1f}%")
        else:
            self._rng_lbl.setText("Range --")


class StabilityIndicator(QWidget):
    """Prediction Stability 표시 — 도트 + 텍스트"""

    _DOTS = 5
    _FILLS = {"High": 5, "Medium": 3, "Low": 1, "Unknown": 0}
    _COLORS = CONFIDENCE_COLORS

    def __init__(self, parent=None):
        super().__init__(parent)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(6)

        dots_row = QHBoxLayout()
        dots_row.setSpacing(4)
        self._dots = []
        for _ in range(self._DOTS):
            d = QLabel("●")
            d.setStyleSheet("font-size: 10px; color: #404040;")
            dots_row.addWidget(d)
            self._dots.append(d)
        lo.addLayout(dots_row)

        self._lbl = QLabel("Stability: --")
        self._lbl.setStyleSheet("color: #909090; font-size: 12px; font-weight: 600;")
        lo.addWidget(self._lbl)
        lo.addStretch()

    def update(self, level: str):
        fill = self._FILLS.get(level, 0)
        color = self._COLORS.get(level, "#505050")
        for i, d in enumerate(self._dots):
            d.setStyleSheet(
                f"font-size: 10px; color: {color if i < fill else '#404040'};"
            )
        self._lbl.setText(f"Stability: {level}")
        self._lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")


class FrameLabel(QLabel):
    """단순 QLabel 기반 프레임 표시 — matplotlib 없이 빠르게 렌더링"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "background-color: #111111; border: 1px solid #404040; border-radius: 2px;"
        )
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setText("No image loaded")
        self.setStyleSheet(
            "background-color: #111111; color: #505050;"
            "border: 1px solid #404040; border-radius: 2px; font-size: 12px;"
        )

    def show_frame(self, frame: np.ndarray, label: str = ""):
        if frame is None:
            return
        h, w = frame.shape[:2]
        if frame.ndim == 2:
            q_img = QImage(frame.data, w, h, w, QImage.Format_Grayscale8)
        elif frame.shape[2] == 4:
            rgb = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
            q_img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.shape[2] == 3 else frame
            q_img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(pix)
        if label:
            self.setToolTip(label)


# ── 메인 Study 패널 ─────────────────────────────────────────────────────────────

class StudyPanel(QWidget):
    """
    메인 분석 작업 공간

    Left  (220px): 파일 선택, 케이스 정보, View type, 분석 시작
    Center (flex) : 프레임 뷰어 + EF curve
    Right (270px) : EF 결과, Stability, ED/ES, Quality warnings, 내보내기
    """

    analysis_requested = pyqtSignal(Path, str, str)   # (video_path, case_id, view_type)
    ed_override        = pyqtSignal(int)
    es_override        = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_path: Optional[Path] = None
        self._frames: List[np.ndarray] = []
        self._framewise_ef: List[float] = []
        self._ed_idx = 0
        self._es_idx = 0
        self._result: Optional[Dict[str, Any]] = None
        self._build_ui()

    # ── UI 구성 ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setChildrenCollapsible(False)

        self.splitter.addWidget(self._build_left())
        self.splitter.addWidget(self._build_center())
        self.splitter.addWidget(self._build_right())

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([230, 700, 280])

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.splitter)

    # ── 좌측 패널: 파일 + 컨트롤 ────────────────────────────────────────────────

    def _build_left(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(230)
        w.setStyleSheet("background-color: #252525; border-right: 1px solid #404040;")
        lo = QVBoxLayout(w)
        lo.setContentsMargins(12, 14, 12, 12)
        lo.setSpacing(10)

        # 파일 drop / browse
        file_grp = QGroupBox("Study")
        file_lo = QVBoxLayout(file_grp)
        file_lo.setSpacing(6)

        # Drop zone
        self.drop_area = _DropZone()
        self.drop_area.file_dropped.connect(self._on_file_selected)
        file_lo.addWidget(self.drop_area)

        btn_browse = QPushButton("Browse File…")
        btn_browse.setFixedHeight(28)
        btn_browse.clicked.connect(self._browse_file)
        file_lo.addWidget(btn_browse)

        self.lbl_filename = QLabel("No file selected")
        self.lbl_filename.setStyleSheet("color: #909090; font-size: 11px;")
        self.lbl_filename.setWordWrap(True)
        file_lo.addWidget(self.lbl_filename)

        self.lbl_file_meta = QLabel("")
        self.lbl_file_meta.setStyleSheet("color: #606060; font-size: 10px;")
        file_lo.addWidget(self.lbl_file_meta)
        lo.addWidget(file_grp)

        # Case 설정
        case_grp = QGroupBox("Case")
        case_lo = QVBoxLayout(case_grp)
        case_lo.setSpacing(6)

        self.case_id_edit = QLineEdit()
        self.case_id_edit.setPlaceholderText("Case ID (auto)")
        self.case_id_edit.setFixedHeight(28)
        case_lo.addWidget(self.case_id_edit)

        vt_row = QHBoxLayout()
        vt_lbl = QLabel("View:")
        vt_lbl.setStyleSheet("color: #909090; font-size: 11px;")
        vt_lbl.setFixedWidth(32)
        self.view_combo = QComboBox()
        self.view_combo.addItems(["A4C", "A2C", "PLAX", "Unknown"])
        self.view_combo.setFixedHeight(28)
        vt_row.addWidget(vt_lbl)
        vt_row.addWidget(self.view_combo)
        case_lo.addLayout(vt_row)
        lo.addWidget(case_grp)

        # 분석 버튼 + 진행 상태
        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setProperty("class", "primary")
        self.btn_analyze.setFixedHeight(36)
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._on_start)
        lo.addWidget(self.btn_analyze)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet("color: #909090; font-size: 10px;")
        self.lbl_progress.setWordWrap(True)
        self.lbl_progress.setAlignment(Qt.AlignCenter)
        lo.addWidget(self.lbl_progress)

        lo.addWidget(Divider())

        # 분석 후 내보내기 버튼
        export_grp = QGroupBox("Export")
        export_lo = QVBoxLayout(export_grp)
        export_lo.setSpacing(5)

        self.btn_open_pdf  = self._export_btn("Open PDF Report")
        self.btn_open_json = self._export_btn("Open JSON")
        self.btn_regen_pdf = self._export_btn("Regenerate PDF")
        for b in (self.btn_open_pdf, self.btn_open_json, self.btn_regen_pdf):
            b.setFixedHeight(26)
            b.setEnabled(False)
            export_lo.addWidget(b)

        self.btn_open_pdf.clicked.connect(self._open_pdf)
        self.btn_open_json.clicked.connect(self._open_json)
        self.btn_regen_pdf.clicked.connect(self._regen_pdf)
        lo.addWidget(export_grp)

        lo.addStretch()

        # Disclaimer
        disc = QLabel("Research use only\nNot for diagnostic use")
        disc.setStyleSheet("color: #604000; font-size: 9px; font-weight: 600; text-align: center;")
        disc.setAlignment(Qt.AlignCenter)
        lo.addWidget(disc)

        return w

    def _export_btn(self, text: str) -> QPushButton:
        b = QPushButton(text)
        b.setStyleSheet(
            "QPushButton { font-size: 11px; padding: 4px 8px; }"
        )
        return b

    # ── 중앙 패널: 뷰어 + EF Curve ─────────────────────────────────────────────

    def _build_center(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background-color: #1a1a1a;")
        lo = QVBoxLayout(w)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        # QStackedWidget: placeholder / loading / active
        self.center_stack = QStackedWidget()

        # Page 0: placeholder
        placeholder = QLabel("Open an echo video to begin")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #505050; font-size: 13px;")
        self.center_stack.addWidget(placeholder)

        # Page 1: loading
        loading_w = QWidget()
        loading_lo = QVBoxLayout(loading_w)
        loading_lo.setAlignment(Qt.AlignCenter)
        self.lbl_loading = QLabel("Analyzing…")
        self.lbl_loading.setAlignment(Qt.AlignCenter)
        self.lbl_loading.setStyleSheet("color: #909090; font-size: 13px;")
        self.loading_bar = _LoadingBar()
        loading_lo.addWidget(self.lbl_loading)
        loading_lo.addWidget(self.loading_bar)
        self.center_stack.addWidget(loading_w)

        # Page 2: active viewer
        active_w = QWidget()
        active_lo = QVBoxLayout(active_w)
        active_lo.setContentsMargins(0, 0, 0, 0)
        active_lo.setSpacing(0)

        # Frame viewer
        self.frame_view = FrameLabel()
        active_lo.addWidget(self.frame_view, 5)

        # 슬라이더 + frame info
        ctrl_bar = QWidget()
        ctrl_bar.setStyleSheet("background-color: #202020; border-top: 1px solid #404040;")
        ctrl_lo = QVBoxLayout(ctrl_bar)
        ctrl_lo.setContentsMargins(10, 6, 10, 6)
        ctrl_lo.setSpacing(4)

        slider_row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self._on_slider)
        slider_row.addWidget(self.slider)
        self.lbl_frame = QLabel("--/--")
        self.lbl_frame.setStyleSheet("color: #909090; font-size: 11px; min-width: 60px;")
        self.lbl_frame.setAlignment(Qt.AlignRight)
        slider_row.addWidget(self.lbl_frame)
        ctrl_lo.addLayout(slider_row)

        info_row = QHBoxLayout()
        self.lbl_frame_ef = QLabel("EF at frame: --")
        self.lbl_frame_ef.setStyleSheet("color: #00b4cc; font-size: 11px; font-weight: 600;")
        info_row.addWidget(self.lbl_frame_ef)
        info_row.addStretch()

        # Brightness / Contrast
        for lbl_text, attr, rng, val in [
            ("Brightness:", "brt_slider", (-80, 80), 0),
            ("Contrast:",   "cst_slider", (50, 200), 100),
        ]:
            info_row.addWidget(QLabel(lbl_text))
            s = QSlider(Qt.Horizontal)
            s.setRange(*rng)
            s.setValue(val)
            s.setFixedWidth(80)
            s.valueChanged.connect(self._refresh_frame)
            setattr(self, attr, s)
            info_row.addWidget(s)

        ctrl_lo.addLayout(info_row)
        active_lo.addWidget(ctrl_bar)

        # ED/ES jump + override buttons
        ed_es_bar = QWidget()
        ed_es_bar.setStyleSheet("background-color: #1e1e1e; border-top: 1px solid #383838;")
        ed_es_lo = QHBoxLayout(ed_es_bar)
        ed_es_lo.setContentsMargins(10, 5, 10, 5)
        ed_es_lo.setSpacing(8)

        self.btn_goto_ed = QPushButton("→ ED")
        self.btn_goto_es = QPushButton("→ ES")
        self.btn_set_ed  = QPushButton("Set ED")
        self.btn_set_es  = QPushButton("Set ES")
        self.lbl_ed_es   = QLabel("ED: --  |  ES: --")
        self.lbl_ed_es.setStyleSheet("color: #707070; font-size: 11px;")
        self.lbl_override_note = QLabel("")
        self.lbl_override_note.setStyleSheet("color: #e8a217; font-size: 10px;")

        for b in (self.btn_goto_ed, self.btn_goto_es, self.btn_set_ed, self.btn_set_es):
            b.setFixedHeight(24)
            b.setEnabled(False)
            ed_es_lo.addWidget(b)

        ed_es_lo.addWidget(self.lbl_ed_es)
        ed_es_lo.addWidget(self.lbl_override_note)
        ed_es_lo.addStretch()
        active_lo.addWidget(ed_es_bar)

        # EF Curve
        self.ef_curve = EFCurveWidget()
        self.ef_curve.setMinimumHeight(150)
        active_lo.addWidget(self.ef_curve, 2)

        self.center_stack.addWidget(active_w)
        lo.addWidget(self.center_stack)

        # 버튼 시그널 연결
        self.btn_goto_ed.clicked.connect(lambda: self._goto(self._ed_idx))
        self.btn_goto_es.clicked.connect(lambda: self._goto(self._es_idx))
        self.btn_set_ed.clicked.connect(self._set_ed)
        self.btn_set_es.clicked.connect(self._set_es)

        return w

    # ── 우측 패널: EF 결과 + Quality ───────────────────────────────────────────

    def _build_right(self) -> QWidget:
        outer = QWidget()
        outer.setFixedWidth(280)
        outer.setStyleSheet(
            "background-color: #252525; border-left: 1px solid #404040;"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        lo = QVBoxLayout(container)
        lo.setContentsMargins(12, 14, 12, 14)
        lo.setSpacing(10)

        # ── EF 수치 (핵심 표시) ──
        self.ef_display = EFDisplay()
        self.ef_display.setStyleSheet(
            "background-color: #2e2e2e; border: 1px solid #404040; border-radius: 4px;"
        )
        lo.addWidget(self.ef_display)

        # ── Stability ──
        stab_grp = QGroupBox("Prediction Stability")
        stab_lo = QVBoxLayout(stab_grp)
        self.stability_ind = StabilityIndicator()
        stab_lo.addWidget(self.stability_ind)

        self.lbl_low_warn = QLabel("")
        self.lbl_low_warn.setWordWrap(True)
        self.lbl_low_warn.setStyleSheet(
            "color: #e05252; font-size: 10px; font-weight: 600;"
        )
        self.lbl_low_warn.setVisible(False)
        stab_lo.addWidget(self.lbl_low_warn)
        lo.addWidget(stab_grp)

        # ── ED/ES ──
        ed_es_grp = QGroupBox("ED / ES Candidate Frames")
        ed_es_lo = QVBoxLayout(ed_es_grp)
        ed_es_lo.setSpacing(4)
        self.lbl_ed = QLabel("ED:  --")
        self.lbl_ed.setStyleSheet("color: #52c27a; font-size: 12px; font-weight: 600;")
        self.lbl_es = QLabel("ES:  --")
        self.lbl_es.setStyleSheet("color: #e05252; font-size: 12px; font-weight: 600;")
        self.lbl_override_badge = QLabel("")
        self.lbl_override_badge.setStyleSheet("color: #e8a217; font-size: 10px;")
        ed_es_lo.addWidget(self.lbl_ed)
        ed_es_lo.addWidget(self.lbl_es)
        ed_es_lo.addWidget(self.lbl_override_badge)
        lo.addWidget(ed_es_grp)

        lo.addWidget(Divider())

        # ── Quality Warnings ──
        qw_grp = QGroupBox("Image Quality")
        qw_lo = QVBoxLayout(qw_grp)
        self.qw_status = QLabel("●  No quality warnings")
        self.qw_status.setStyleSheet("color: #52c27a; font-size: 12px; font-weight: 600;")
        qw_lo.addWidget(self.qw_status)
        self.qw_list = QVBoxLayout()
        qw_lo.addLayout(self.qw_list)
        lo.addWidget(qw_grp)

        lo.addWidget(Divider())

        # ── Model info ──
        model_grp = QGroupBox("Model")
        model_lo = QVBoxLayout(model_grp)
        model_lo.setSpacing(3)
        self.lbl_model = QLabel("--")
        self.lbl_model.setStyleSheet("color: #707070; font-size: 11px;")
        self.lbl_model.setWordWrap(True)
        self.lbl_latency = QLabel("Latency: --")
        self.lbl_latency.setStyleSheet("color: #606060; font-size: 10px;")
        model_lo.addWidget(self.lbl_model)
        model_lo.addWidget(self.lbl_latency)
        lo.addWidget(model_grp)

        lo.addStretch()

        scroll.setWidget(container)
        root = QVBoxLayout(outer)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)
        return outer

    # ── 파일 처리 ─────────────────────────────────────────────────────────────

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Echo Video", "",
            "Video / DICOM (*.mp4 *.avi *.mov *.mkv *.dcm *.dicom);;All Files (*)"
        )
        if path:
            self._on_file_selected(Path(path))

    def _on_file_selected(self, path: Path):
        self._video_path = path
        self.lbl_filename.setText(path.name)

        # Case ID 자동
        if not self.case_id_edit.text().strip():
            self.case_id_edit.setText(path.stem[:8].upper().ljust(8, "0"))

        # 파일 메타 (OpenCV)
        try:
            cap = cv2.VideoCapture(str(path))
            if cap.isOpened():
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()
                size_mb = path.stat().st_size / (1024 * 1024)
                self.lbl_file_meta.setText(
                    f"{total} frames  {w}×{h}  {fps:.0f}fps  {size_mb:.1f}MB"
                )
            else:
                self.lbl_file_meta.setText("Could not read file metadata")
        except Exception:
            self.lbl_file_meta.setText("")

        self.btn_analyze.setEnabled(True)

    # ── 분석 요청 ─────────────────────────────────────────────────────────────

    def set_video_path(self, path: Path):
        """main_window에서 Open Video 다이얼로그로 파일을 선택했을 때 호출"""
        self._on_file_selected(path)

    def trigger_analysis(self):
        """toolbar/menu에서 분석 시작 요청"""
        self._on_start()

    def _on_start(self):
        if not self._video_path:
            return
        case_id = self.case_id_edit.text().strip() or \
                  self._video_path.stem[:8].upper().ljust(8, "0")
        view_type = self.view_combo.currentText()
        self.analysis_requested.emit(self._video_path, case_id, view_type)

    def set_analyzing(self, is_analyzing: bool, message: str = ""):
        """분석 중 UI 전환"""
        self.btn_analyze.setEnabled(not is_analyzing)
        if is_analyzing:
            self.center_stack.setCurrentIndex(1)  # loading page
            self.lbl_loading.setText(message or "Analyzing…")
            self.loading_bar.start()
            self.lbl_progress.setText(message)
        else:
            self.loading_bar.stop()
            self.lbl_progress.setText("")

    def update_progress(self, message: str):
        self.lbl_loading.setText(message)
        self.lbl_progress.setText(message)

    # ── 결과 로드 ─────────────────────────────────────────────────────────────

    def load_result(self, result: Dict[str, Any]):
        self._result = result
        self._frames = result.get("frames", [])
        self._framewise_ef = result.get("framewise_ef", [])
        self._ed_idx = result.get("ed_frame_index_final", result.get("ed_frame_idx", 0))
        self._es_idx = result.get("es_frame_index_final", result.get("es_frame_idx", 0))

        # 중앙 뷰어 활성화
        if self._frames:
            self.slider.setMaximum(len(self._frames) - 1)
            self.slider.setValue(0)
            self._refresh_frame()
            self.center_stack.setCurrentIndex(2)

            for b in (self.btn_goto_ed, self.btn_goto_es,
                      self.btn_set_ed, self.btn_set_es):
                b.setEnabled(True)

        # EF curve
        if self._framewise_ef:
            self.ef_curve.update_curve(
                framewise_ef=self._framewise_ef,
                ed_idx=self._ed_idx,
                es_idx=self._es_idx,
                ef_median=result.get("ef", 0.0),
                ef_std=result.get("ef_std", 0.0),
                ef_mean=result.get("ef_mean"),
            )

        # 우측 패널
        self._update_right_panel(result)

        # export 버튼 활성화
        self.btn_open_pdf.setEnabled(bool(result.get("report_path")))
        self.btn_open_json.setEnabled(bool(result.get("json_path")))
        self.btn_regen_pdf.setEnabled(True)

        # ED/ES 레이블
        self._update_ed_es_labels()

    def _update_right_panel(self, result: Dict[str, Any]):
        ef     = result.get("ef")
        ef_mean = result.get("ef_mean")
        ef_std = result.get("ef_std")
        ef_min = result.get("ef_min")
        ef_max = result.get("ef_max")
        conf   = result.get("confidence_level", "Unknown")
        model_info = result.get("model_info", {})
        quality = result.get("quality_metrics", {})
        latency = result.get("inference_latency_s")

        # EF display
        self.ef_display.update(ef, ef_mean, ef_std, ef_min, ef_max)

        # Stability
        self.stability_ind.update(conf)
        if conf == "Low":
            self.lbl_low_warn.setText(
                "Frame-to-frame EF variability is high.\n"
                "Manual review of ED/ES frames recommended."
            )
            self.lbl_low_warn.setVisible(True)
        else:
            self.lbl_low_warn.setVisible(False)

        # Quality warnings
        self._update_quality_warnings(quality)

        # Model
        model_str = (
            f"{model_info.get('name','?')} {model_info.get('variant','?')} "
            f"v{model_info.get('version','?')}"
        )
        self.lbl_model.setText(model_str)
        self.lbl_latency.setText(f"Latency: {latency:.2f}s" if latency else "Latency: --")

    def _update_quality_warnings(self, quality: Dict[str, Any]):
        # 기존 경고 클리어
        while self.qw_list.count():
            item = self.qw_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        warnings = quality.get("warnings", [])
        level = quality.get("quality_level", "good")

        if not warnings:
            self.qw_status.setText("●  Image quality: Good")
            self.qw_status.setStyleSheet("color: #52c27a; font-size: 12px; font-weight: 600;")
        else:
            colors_map = {"poor": "#e05252", "moderate": "#e8a217"}
            c = colors_map.get(level, "#e8a217")
            self.qw_status.setText(f"●  {len(warnings)} warning(s) found")
            self.qw_status.setStyleSheet(f"color: {c}; font-size: 12px; font-weight: 600;")
            for w in warnings:
                lbl = QLabel(f"• {w}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet("color: #909090; font-size: 10px; padding: 2px 0;")
                self.qw_list.addWidget(lbl)

    # ── 뷰어 컨트롤 ──────────────────────────────────────────────────────────

    def _on_slider(self, val: int):
        self._refresh_frame(val)

    def _refresh_frame(self, frame_idx: int = None):
        if not self._frames:
            return
        idx = self.slider.value() if frame_idx is None else frame_idx
        if idx >= len(self._frames):
            return

        frame = self._frames[idx].copy()
        brt = self.brt_slider.value()
        cst = self.cst_slider.value() / 100.0
        frame = np.clip(frame.astype(np.float32) * cst + brt, 0, 255).astype(np.uint8)

        tag = ""
        if idx == self._ed_idx:
            tag = " [ED]"
        elif idx == self._es_idx:
            tag = " [ES]"

        self.frame_view.show_frame(frame, f"Frame {idx}{tag}")
        total = len(self._frames)
        self.lbl_frame.setText(f"{idx+1}/{total}{tag}")

        if self._framewise_ef and idx < len(self._framewise_ef):
            self.lbl_frame_ef.setText(f"EF at frame {idx}: {self._framewise_ef[idx]:.1f}%")

    def _goto(self, idx: int):
        if 0 <= idx < len(self._frames):
            self.slider.setValue(idx)

    def _update_ed_es_labels(self):
        ef_ed = self._framewise_ef[self._ed_idx] if self._framewise_ef else 0
        ef_es = self._framewise_ef[self._es_idx] if self._framewise_ef else 0
        self.lbl_ed_es.setText(f"ED #{self._ed_idx}  |  ES #{self._es_idx}")
        self.lbl_ed.setText(f"ED:  Frame #{self._ed_idx}   ({ef_ed:.1f}%)")
        self.lbl_es.setText(f"ES:  Frame #{self._es_idx}   ({ef_es:.1f}%)")
        self.btn_goto_ed.setText(f"→ ED #{self._ed_idx}")
        self.btn_goto_es.setText(f"→ ES #{self._es_idx}")

    # ── Manual ED/ES override ────────────────────────────────────────────────

    def _set_ed(self):
        idx = self.slider.value()
        self._ed_idx = idx
        if self._result:
            self._result["ed_frame_index_final"] = idx
            self._result["manual_override"] = True
        self.ef_curve.update_ed_es(self._ed_idx, self._es_idx)
        self._update_ed_es_labels()
        self.lbl_override_note.setText(f"Manual: ED={self._ed_idx}")
        self.lbl_override_badge.setText(
            f"Manually overridden: ED=#{self._ed_idx}  ES=#{self._es_idx}"
        )
        self._refresh_frame()
        self.ed_override.emit(idx)

    def _set_es(self):
        idx = self.slider.value()
        self._es_idx = idx
        if self._result:
            self._result["es_frame_index_final"] = idx
            self._result["manual_override"] = True
        self.ef_curve.update_ed_es(self._ed_idx, self._es_idx)
        self._update_ed_es_labels()
        self.lbl_override_note.setText(f"Manual: ED={self._ed_idx}  ES={self._es_idx}")
        self.lbl_override_badge.setText(
            f"Manually overridden: ED=#{self._ed_idx}  ES=#{self._es_idx}"
        )
        self._refresh_frame()
        self.es_override.emit(idx)

    # ── 내보내기 ─────────────────────────────────────────────────────────────

    def _open_pdf(self):
        self._open_file(self._result.get("report_path") if self._result else None)

    def _open_json(self):
        self._open_file(self._result.get("json_path") if self._result else None)

    def _regen_pdf(self):
        if not self._result:
            return
        try:
            from datetime import datetime as dt
            from utils.spec import PROJECT_ROOT
            from report.report_builder import build_pdf
            stem = Path(str(self._result.get("metadata", {}).get("file_path", "case"))).stem
            ts = dt.now().strftime("%Y%m%d_%H%M%S")
            rp = PROJECT_ROOT / "output" / f"{stem}_{ts}.pdf"
            rp.parent.mkdir(exist_ok=True)
            build_pdf(report_path=rp, analysis_result=self._result)
            self._result["report_path"] = rp
            self.btn_open_pdf.setEnabled(True)
            QMessageBox.information(self, "PDF", f"Generated:\n{rp.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _open_file(self, path):
        if not path or not Path(str(path)).exists():
            QMessageBox.warning(self, "Warning", "File not found.")
            return
        if platform.system() == "Darwin":
            subprocess.run(["open", str(path)])
        elif platform.system() == "Windows":
            subprocess.run(["start", str(path)], shell=True)
        else:
            subprocess.run(["xdg-open", str(path)])


# ── 내부 유틸 위젯 ─────────────────────────────────────────────────────────────

class _DropZone(QLabel):
    """파일 Drag-and-Drop 영역"""
    file_dropped = pyqtSignal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(70)
        self.setText("Drop file here")
        self._default_style()

    def _default_style(self):
        self.setStyleSheet(
            "background-color: #1e1e1e; border: 1px dashed #505050;"
            "border-radius: 4px; color: #606060; font-size: 11px;"
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "background-color: #1a2a2a; border: 1px dashed #00b4cc;"
                "border-radius: 4px; color: #00b4cc; font-size: 11px;"
            )

    def dragLeaveEvent(self, event):
        self._default_style()

    def dropEvent(self, event):
        self._default_style()
        urls = event.mimeData().urls()
        if urls:
            p = Path(urls[0].toLocalFile())
            if p.suffix.lower() in _SUPPORTED_EXT:
                self.file_dropped.emit(p)
            else:
                self.setText(f"Unsupported: {p.suffix}")


class _LoadingBar(QWidget):
    """간단한 진행 애니메이션 바"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 4)
        self._pos = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self.setStyleSheet("background-color: #2e2e2e; border-radius: 2px;")

    def start(self):
        self._pos = 0
        self._timer.start(30)

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._pos = (self._pos + 4) % 210
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(0, 0, self.width(), self.height(), QColor("#2e2e2e"))
        bar_w = 60
        x = self._pos - bar_w
        p.fillRect(max(0, x), 0, min(bar_w, self.width() - max(0, x)), 4, QColor("#00b4cc"))
