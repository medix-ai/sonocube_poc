"""Analysis 패널 — 프레임 뷰어, EF curve, ED/ES override, side-by-side"""
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QSlider, QSplitter, QVBoxLayout, QWidget, QFileDialog,
)

from gui.ef_curve_widget import EFCurveWidget


class FrameView(QLabel):
    """단일 프레임 표시 QLabel (aspect-ratio 유지)"""

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self._placeholder = placeholder
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; border-radius:4px;")
        self._show_placeholder()

    def _show_placeholder(self):
        self.setText(self._placeholder or "No frame")
        self.setStyleSheet(
            "background-color: #0d1117; border: 1px solid #30363d; border-radius:4px;"
            "color: #484f58; font-size: 11px;"
        )

    def set_frame(self, frame: np.ndarray, label: str = ""):
        if frame is None:
            self._show_placeholder()
            return
        h, w = frame.shape[:2]
        if frame.ndim == 2:
            q_img = QImage(frame.data, w, h, w, QImage.Format_Grayscale8)
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.shape[2] == 3 else frame
            q_img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(pix)
        self.setStyleSheet(
            "background-color: #0d1117; border: 1px solid #30363d; border-radius:4px;"
        )
        if label:
            # 라벨 오버레이는 윈도우 타이틀로 표시
            self.setToolTip(label)


class AnalysisPanel(QWidget):
    """Analysis 탭"""

    # 신호 — ED/ES override 시 main window가 result 업데이트하도록
    ed_override = pyqtSignal(int)
    es_override = pyqtSignal(int)
    snapshot_saved = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frames: List[np.ndarray] = []
        self._framewise_ef: List[float] = []
        self._ed_idx = 0
        self._es_idx = 0
        self._brightness = 0
        self._contrast = 1.0
        self._build_ui()

    # ── UI 구성 ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QSplitter(Qt.Vertical)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── 상단: 뷰어 영역 ──
        viewer_widget = QWidget()
        viewer_layout = QHBoxLayout(viewer_widget)
        viewer_layout.setContentsMargins(8, 8, 8, 4)
        viewer_layout.setSpacing(8)

        # 메인 뷰어 + 컨트롤
        left = QVBoxLayout()
        left.setSpacing(6)

        self.main_view = FrameView("No analysis loaded")
        self.main_view.setMinimumHeight(280)
        left.addWidget(self.main_view)

        # 프레임 슬라이더
        slider_row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self._on_slider)
        slider_row.addWidget(self.slider)

        self.lbl_frame_idx = QLabel("Frame --/--")
        self.lbl_frame_idx.setFixedWidth(90)
        self.lbl_frame_idx.setStyleSheet("color: #8b949e; font-size: 11px;")
        slider_row.addWidget(self.lbl_frame_idx)
        left.addLayout(slider_row)

        # 프레임 EF 표시
        ef_row = QHBoxLayout()
        self.lbl_frame_ef = QLabel("EF at frame: --")
        self.lbl_frame_ef.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: 600;")
        ef_row.addWidget(self.lbl_frame_ef)
        ef_row.addStretch()

        # 밝기 / 대비 슬라이더
        ef_row.addWidget(QLabel("Brightness:"))
        self.brt_slider = QSlider(Qt.Horizontal)
        self.brt_slider.setRange(-80, 80)
        self.brt_slider.setValue(0)
        self.brt_slider.setFixedWidth(90)
        self.brt_slider.valueChanged.connect(self._update_display)
        ef_row.addWidget(self.brt_slider)

        ef_row.addWidget(QLabel("Contrast:"))
        self.cst_slider = QSlider(Qt.Horizontal)
        self.cst_slider.setRange(50, 200)
        self.cst_slider.setValue(100)
        self.cst_slider.setFixedWidth(90)
        self.cst_slider.valueChanged.connect(self._update_display)
        ef_row.addWidget(self.cst_slider)
        left.addLayout(ef_row)

        viewer_layout.addLayout(left, 4)

        # 오른쪽: 컨트롤 패널
        right_panel = QWidget()
        right_panel.setFixedWidth(220)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # ED/ES 이동 버튼
        jump_group = QGroupBox("Jump to Frame")
        jump_layout = QVBoxLayout(jump_group)
        jump_layout.setSpacing(6)

        self.btn_goto_ed = QPushButton("Go to ED Candidate")
        self.btn_goto_ed.setEnabled(False)
        self.btn_goto_ed.clicked.connect(lambda: self._goto_frame(self._ed_idx))
        jump_layout.addWidget(self.btn_goto_ed)

        self.btn_goto_es = QPushButton("Go to ES Candidate")
        self.btn_goto_es.setEnabled(False)
        self.btn_goto_es.clicked.connect(lambda: self._goto_frame(self._es_idx))
        jump_layout.addWidget(self.btn_goto_es)

        self.lbl_ed_info = QLabel("ED: --")
        self.lbl_ed_info.setStyleSheet("color: #3fb950; font-size: 11px;")
        self.lbl_es_info = QLabel("ES: --")
        self.lbl_es_info.setStyleSheet("color: #f85149; font-size: 11px;")
        jump_layout.addWidget(self.lbl_ed_info)
        jump_layout.addWidget(self.lbl_es_info)
        right_layout.addWidget(jump_group)

        # Manual override 버튼
        override_group = QGroupBox("Manual ED/ES Override")
        override_layout = QVBoxLayout(override_group)
        override_layout.setSpacing(6)

        hint = QLabel("Navigate to a frame, then set it as ED or ES.")
        hint.setStyleSheet("color: #8b949e; font-size: 10px;")
        hint.setWordWrap(True)
        override_layout.addWidget(hint)

        self.btn_set_ed = QPushButton("Set Current as ED")
        self.btn_set_ed.setEnabled(False)
        self.btn_set_ed.clicked.connect(self._set_current_as_ed)
        override_layout.addWidget(self.btn_set_ed)

        self.btn_set_es = QPushButton("Set Current as ES")
        self.btn_set_es.setEnabled(False)
        self.btn_set_es.clicked.connect(self._set_current_as_es)
        override_layout.addWidget(self.btn_set_es)

        self.lbl_override_status = QLabel("")
        self.lbl_override_status.setStyleSheet(
            "color: #d29922; font-size: 10px; font-weight: 600;"
        )
        self.lbl_override_status.setWordWrap(True)
        override_layout.addWidget(self.lbl_override_status)
        right_layout.addWidget(override_group)

        # Snapshot
        snap_group = QGroupBox("Snapshot")
        snap_layout = QVBoxLayout(snap_group)
        self.btn_snapshot = QPushButton("Save Current Frame")
        self.btn_snapshot.setEnabled(False)
        self.btn_snapshot.clicked.connect(self._save_snapshot)
        snap_layout.addWidget(self.btn_snapshot)
        right_layout.addWidget(snap_group)

        right_layout.addStretch()
        viewer_layout.addWidget(right_panel, 0)
        outer.addWidget(viewer_widget)

        # ── 중단: Side-by-side ED/ES ──
        sbs_widget = QWidget()
        sbs_layout = QHBoxLayout(sbs_widget)
        sbs_layout.setContentsMargins(8, 0, 8, 4)
        sbs_layout.setSpacing(8)

        ed_col = QVBoxLayout()
        ed_lbl = QLabel("ED Candidate Frame")
        ed_lbl.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: 600;")
        ed_col.addWidget(ed_lbl)
        self.ed_view = FrameView("ED")
        self.ed_view.setMinimumHeight(140)
        ed_col.addWidget(self.ed_view)

        es_col = QVBoxLayout()
        es_lbl = QLabel("ES Candidate Frame")
        es_lbl.setStyleSheet("color: #f85149; font-size: 11px; font-weight: 600;")
        es_col.addWidget(es_lbl)
        self.es_view = FrameView("ES")
        self.es_view.setMinimumHeight(140)
        es_col.addWidget(self.es_view)

        sbs_layout.addLayout(ed_col)
        sbs_layout.addLayout(es_col)
        outer.addWidget(sbs_widget)

        # ── 하단: EF Curve ──
        self.ef_curve = EFCurveWidget()
        self.ef_curve.frame_hovered.connect(self._on_curve_hover)
        outer.addWidget(self.ef_curve)

        outer.setStretchFactor(0, 5)
        outer.setStretchFactor(1, 2)
        outer.setStretchFactor(2, 2)

        # 전체를 스크롤 가능하게
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(outer)

    # ── 데이터 로드 ────────────────────────────────────────────────────────────

    def load_result(self, result: Dict[str, Any]):
        self._frames = result.get("frames", [])
        self._framewise_ef = result.get("framewise_ef", [])
        self._ed_idx = result.get("ed_frame_index_final",
                                  result.get("ed_frame_idx", 0))
        self._es_idx = result.get("es_frame_index_final",
                                  result.get("es_frame_idx", 0))

        if not self._frames:
            return

        self.slider.setMaximum(len(self._frames) - 1)
        self.slider.setValue(0)
        self._update_display()
        self._update_ed_es_views()

        # EF curve
        self.ef_curve.update_curve(
            framewise_ef=self._framewise_ef,
            ed_idx=self._ed_idx,
            es_idx=self._es_idx,
            ef_median=result.get("ef", 0.0),
            ef_std=result.get("ef_std", 0.0),
            ef_mean=result.get("ef_mean"),
        )

        for btn in (self.btn_goto_ed, self.btn_goto_es,
                    self.btn_set_ed, self.btn_set_es, self.btn_snapshot):
            btn.setEnabled(True)

        self._update_ed_es_labels()

    # ── 슬라이더 / 표시 ───────────────────────────────────────────────────────

    def _on_slider(self, value: int):
        self._update_display(value)

    def _update_display(self, frame_idx: int = None):
        if not self._frames:
            return
        idx = self.slider.value() if frame_idx is None else frame_idx

        frame = self._frames[idx].copy()
        # Brightness + Contrast
        brt = self.brt_slider.value()
        cst = self.cst_slider.value() / 100.0
        frame = np.clip(frame.astype(np.float32) * cst + brt, 0, 255).astype(np.uint8)

        suffix = ""
        if idx == self._ed_idx:
            suffix = " [ED]"
        elif idx == self._es_idx:
            suffix = " [ES]"
        self.main_view.set_frame(frame, f"Frame {idx}{suffix}")

        total = len(self._frames)
        self.lbl_frame_idx.setText(f"Frame {idx + 1}/{total}{suffix}")

        if self._framewise_ef and idx < len(self._framewise_ef):
            self.lbl_frame_ef.setText(f"EF at frame {idx}: {self._framewise_ef[idx]:.1f}%")
        else:
            self.lbl_frame_ef.setText("EF at frame: --")

    def _goto_frame(self, idx: int):
        if 0 <= idx < len(self._frames):
            self.slider.setValue(idx)

    # ── ED/ES 업데이트 ────────────────────────────────────────────────────────

    def _update_ed_es_views(self):
        if not self._frames:
            return
        if self._ed_idx < len(self._frames):
            self.ed_view.set_frame(self._frames[self._ed_idx], "ED")
        if self._es_idx < len(self._frames):
            self.es_view.set_frame(self._frames[self._es_idx], "ES")

    def _update_ed_es_labels(self):
        ef_ed = self._framewise_ef[self._ed_idx] if self._framewise_ef else 0
        ef_es = self._framewise_ef[self._es_idx] if self._framewise_ef else 0
        self.lbl_ed_info.setText(f"ED: Frame #{self._ed_idx}  (EF {ef_ed:.1f}%)")
        self.lbl_es_info.setText(f"ES: Frame #{self._es_idx}  (EF {ef_es:.1f}%)")
        self.btn_goto_ed.setText(f"Go to ED (#{self._ed_idx})")
        self.btn_goto_es.setText(f"Go to ES (#{self._es_idx})")

    # ── Manual override ───────────────────────────────────────────────────────

    def _set_current_as_ed(self):
        idx = self.slider.value()
        self._ed_idx = idx
        self._update_ed_es_views()
        self._update_ed_es_labels()
        self.ef_curve.update_ed_es(self._ed_idx, self._es_idx)
        self.lbl_override_status.setText(f"Manual override: ED = Frame #{idx}")
        self.ed_override.emit(idx)

    def _set_current_as_es(self):
        idx = self.slider.value()
        self._es_idx = idx
        self._update_ed_es_views()
        self._update_ed_es_labels()
        self.ef_curve.update_ed_es(self._ed_idx, self._es_idx)
        self.lbl_override_status.setText(
            (self.lbl_override_status.text().split("\n")[0] + "\n" if "ED" in self.lbl_override_status.text() else "")
            + f"Manual override: ES = Frame #{idx}"
        )
        self.es_override.emit(idx)

    # ── Hover 연동 ────────────────────────────────────────────────────────────

    def _on_curve_hover(self, frame_idx: int, ef_val: float):
        pass  # 필요 시 슬라이더를 연동할 수 있음

    # ── Snapshot ─────────────────────────────────────────────────────────────

    def _save_snapshot(self):
        idx = self.slider.value()
        if not self._frames or idx >= len(self._frames):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Snapshot", f"frame_{idx:04d}.png", "PNG Image (*.png)"
        )
        if path:
            try:
                frame = self._frames[idx]
                if frame.ndim == 3:
                    cv2.imwrite(path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                else:
                    cv2.imwrite(path, frame)
                self.snapshot_saved.emit(path)
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", str(e))
