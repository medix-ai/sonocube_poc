"""Import 패널 — drag-and-drop 파일 업로드, 파일 정보, 분석 시작"""
import os
from pathlib import Path
from typing import Callable, Optional

import cv2
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

_SUPPORTED_EXT = {".mp4", ".avi", ".mov", ".mkv", ".dcm", ".dicom"}
_DISCLAIMER = (
    "Research use only — NOT FOR DIAGNOSTIC USE.\n"
    "This software estimates EF from video input and is intended for research purposes only."
)


class DropArea(QWidget):
    """파일 Drag-and-Drop 영역"""

    file_dropped = pyqtSignal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.setStyleSheet(
            "background-color: #1c2128;"
            "border: 2px dashed #30363d;"
            "border-radius: 10px;"
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self._icon = QLabel("⬆")
        self._icon.setStyleSheet("font-size: 36px; color: #58a6ff; border: none;")
        self._icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._icon)

        self._text = QLabel("Drag & drop an echo video file here")
        self._text.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: 600; border: none;")
        self._text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._text)

        self._sub = QLabel("Supported: MP4 · AVI · MOV · MKV · DICOM")
        self._sub.setStyleSheet("color: #8b949e; font-size: 11px; border: none;")
        self._sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._sub)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "background-color: #1c2940;"
                "border: 2px dashed #1f6feb;"
                "border-radius: 10px;"
            )

    def dragLeaveEvent(self, event):
        self._reset_style()

    def dropEvent(self, event):
        self._reset_style()
        urls = event.mimeData().urls()
        if urls:
            p = Path(urls[0].toLocalFile())
            if p.suffix.lower() in _SUPPORTED_EXT:
                self.file_dropped.emit(p)
            else:
                self._sub.setText(f"Unsupported format: {p.suffix} — use MP4/AVI/MOV/MKV/DICOM")

    def _reset_style(self):
        self.setStyleSheet(
            "background-color: #1c2128;"
            "border: 2px dashed #30363d;"
            "border-radius: 10px;"
        )


class ImportPanel(QWidget):
    """Import 탭 위젯"""

    analysis_requested = pyqtSignal(Path, str, str)  # (video_path, case_id, view_type)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_path: Optional[Path] = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 24, 40, 24)
        outer.setSpacing(16)

        # 제목
        title = QLabel("Import Echo Video")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: 700;")
        outer.addWidget(title)

        # Disclaimer
        disc = QLabel(_DISCLAIMER)
        disc.setStyleSheet(
            "color: #d29922; font-size: 11px; font-weight: 600;"
            "background-color: #1c1800; border: 1px solid #3d2e00;"
            "border-radius: 4px; padding: 8px;"
        )
        disc.setWordWrap(True)
        outer.addWidget(disc)

        # Drop 영역
        self.drop_area = DropArea()
        self.drop_area.file_dropped.connect(self._on_file_selected)
        outer.addWidget(self.drop_area)

        # OR 구분선 + 파일 선택 버튼
        or_row = QHBoxLayout()
        for _ in range(2):
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #30363d;")
            or_row.addWidget(line, 1)
        or_lbl = QLabel("or")
        or_lbl.setStyleSheet("color: #8b949e; font-size: 12px; padding: 0 10px;")
        or_row.addWidget(or_lbl)
        outer.addLayout(or_row)

        btn_browse = QPushButton("Browse File…")
        btn_browse.setFixedHeight(36)
        btn_browse.clicked.connect(self._browse_file)
        outer.addWidget(btn_browse, alignment=Qt.AlignHCenter)

        # 파일 정보
        self.info_group = QGroupBox("File Information")
        info_form = QFormLayout()
        info_form.setLabelAlignment(Qt.AlignRight)
        info_form.setSpacing(8)

        self.lbl_filename  = QLabel("--")
        self.lbl_size      = QLabel("--")
        self.lbl_format    = QLabel("--")
        self.lbl_frames    = QLabel("--")
        self.lbl_res       = QLabel("--")
        self.lbl_error     = QLabel("")
        self.lbl_error.setStyleSheet("color: #f85149; font-size: 11px;")
        self.lbl_error.setWordWrap(True)

        for k, v in [
            ("File name:", self.lbl_filename),
            ("File size:", self.lbl_size),
            ("Format:", self.lbl_format),
            ("Frame count:", self.lbl_frames),
            ("Resolution:", self.lbl_res),
        ]:
            lbl = QLabel(k)
            lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
            v.setStyleSheet("color: #e6edf3; font-size: 12px;")
            info_form.addRow(lbl, v)
        info_form.addRow(QLabel(""), self.lbl_error)
        self.info_group.setLayout(info_form)
        outer.addWidget(self.info_group)

        # 케이스 설정
        cfg_group = QGroupBox("Analysis Configuration")
        cfg_form = QFormLayout()
        cfg_form.setLabelAlignment(Qt.AlignRight)
        cfg_form.setSpacing(8)

        self.case_id_edit = QLineEdit()
        self.case_id_edit.setPlaceholderText("Auto-generated if empty")
        self.case_id_edit.setFixedWidth(200)

        self.view_combo = QComboBox()
        self.view_combo.addItems(["A4C", "A2C", "PLAX", "Unknown"])
        self.view_combo.setCurrentText("A4C")
        self.view_combo.setFixedWidth(120)

        for k, v in [
            ("Case ID:", self.case_id_edit),
            ("View type:", self.view_combo),
        ]:
            lbl = QLabel(k)
            lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
            cfg_form.addRow(lbl, v)
        cfg_group.setLayout(cfg_form)
        outer.addWidget(cfg_group)

        # 분석 시작 버튼
        self.btn_start = QPushButton("Start Analysis")
        self.btn_start.setProperty("class", "primary")
        self.btn_start.setFixedHeight(40)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start)
        outer.addWidget(self.btn_start)

        outer.addStretch()

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
        self.lbl_error.setText("")
        self.lbl_filename.setText(path.name)
        size_mb = path.stat().st_size / (1024 * 1024)
        self.lbl_size.setText(f"{size_mb:.2f} MB")
        self.lbl_format.setText(path.suffix.upper().lstrip("."))

        # Case ID 자동 채우기
        if not self.case_id_edit.text().strip():
            self.case_id_edit.setText(path.stem[:8].upper().ljust(8, "0"))

        # 프레임 정보 추출 (OpenCV)
        try:
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                raise RuntimeError("Cannot open file.")
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            self.lbl_frames.setText(str(total) if total > 0 else "Unknown")
            self.lbl_res.setText(f"{w} × {h}" if w > 0 else "Unknown")
            self.btn_start.setEnabled(True)
        except Exception as e:
            self.lbl_frames.setText("--")
            self.lbl_res.setText("--")
            self.lbl_error.setText(f"Warning: {e}")
            self.btn_start.setEnabled(True)

    def _on_start(self):
        if not self._video_path:
            return
        case_id = self.case_id_edit.text().strip() or \
                  self._video_path.stem[:8].upper().ljust(8, "0")
        view_type = self.view_combo.currentText()
        self.analysis_requested.emit(self._video_path, case_id, view_type)

    def set_enabled_start(self, enabled: bool):
        self.btn_start.setEnabled(enabled)
