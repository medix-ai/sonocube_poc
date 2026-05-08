"""Settings 패널 — 모델 선택, output 경로, 자동 저장, 이력 초기화"""
import json
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from utils.constants import APP_NAME, APP_VERSION

_SETTINGS_FILE_NAME = "sonocube_settings.json"


def _settings_path() -> Path:
    from utils.spec import PROJECT_ROOT
    return PROJECT_ROOT / _SETTINGS_FILE_NAME


def load_settings() -> Dict[str, Any]:
    p = _settings_path()
    if p.exists():
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return _default_settings()


def save_settings(s: Dict[str, Any]):
    with open(_settings_path(), "w") as f:
        json.dump(s, f, indent=2)


def _default_settings() -> Dict[str, Any]:
    from utils.spec import PROJECT_ROOT
    return {
        "default_model": "w_075",
        "output_dir": str(PROJECT_ROOT / "output"),
        "auto_pdf": True,
        "auto_json": True,
        "auto_csv": True,
        "comparison_mode": False,
    }


class SettingsPanel(QWidget):
    """Settings 탭"""

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = load_settings()
        self._build_ui()
        self._load_into_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 24, 40, 24)
        outer.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: 700;")
        outer.addWidget(title)

        # 모델
        model_group = QGroupBox("Model")
        model_form = QFormLayout(model_group)
        model_form.setLabelAlignment(Qt.AlignRight)
        model_form.setSpacing(10)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["w_075 (Recommended)", "w_035"])
        self.model_combo.setFixedWidth(200)
        model_form.addRow(QLabel("Default model:"), self.model_combo)

        self.chk_comparison = QCheckBox(
            "Enable model comparison mode (Research — runs both w_035 and w_075)"
        )
        model_form.addRow(QLabel(""), self.chk_comparison)
        outer.addWidget(model_group)

        # Output
        out_group = QGroupBox("Output Directory")
        out_form = QFormLayout(out_group)
        out_form.setLabelAlignment(Qt.AlignRight)
        out_form.setSpacing(10)

        path_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setFixedWidth(320)
        path_row.addWidget(self.output_edit)
        btn_browse = QPushButton("Browse…")
        btn_browse.setFixedHeight(28)
        btn_browse.clicked.connect(self._browse_output)
        path_row.addWidget(btn_browse)
        path_row.addStretch()

        btn_open = QPushButton("Open Folder")
        btn_open.setFixedHeight(28)
        btn_open.clicked.connect(self._open_output_dir)
        path_row.addWidget(btn_open)
        out_form.addRow(QLabel("Output path:"), path_row)
        outer.addWidget(out_group)

        # 자동 저장
        auto_group = QGroupBox("Auto-save on Analysis Complete")
        auto_lo = QVBoxLayout(auto_group)
        self.chk_pdf  = QCheckBox("Auto-generate PDF report")
        self.chk_json = QCheckBox("Auto-export JSON")
        self.chk_csv  = QCheckBox("Auto-export CSV")
        for c in (self.chk_pdf, self.chk_json, self.chk_csv):
            auto_lo.addWidget(c)
        outer.addWidget(auto_group)

        # 이력 / 로그
        mgmt_group = QGroupBox("Data Management")
        mgmt_lo = QVBoxLayout(mgmt_group)
        mgmt_lo.setSpacing(8)

        btn_clear_history = QPushButton("Clear All History")
        btn_clear_history.setProperty("class", "danger")
        btn_clear_history.setFixedWidth(180)
        btn_clear_history.clicked.connect(self._clear_history)
        mgmt_lo.addWidget(btn_clear_history)

        btn_open_logs = QPushButton("Open Logs Folder")
        btn_open_logs.setFixedWidth(180)
        btn_open_logs.clicked.connect(self._open_logs)
        mgmt_lo.addWidget(btn_open_logs)
        outer.addWidget(mgmt_group)

        # 저장 버튼
        save_row = QHBoxLayout()
        save_row.addStretch()
        btn_save = QPushButton("Save Settings")
        btn_save.setProperty("class", "primary")
        btn_save.setFixedHeight(36)
        btn_save.setFixedWidth(140)
        btn_save.clicked.connect(self._save)
        save_row.addWidget(btn_save)
        outer.addLayout(save_row)

        # 앱 버전
        ver_lbl = QLabel(f"{APP_NAME}  v{APP_VERSION}  ·  Research use only")
        ver_lbl.setStyleSheet("color: #484f58; font-size: 11px;")
        ver_lbl.setAlignment(Qt.AlignCenter)
        outer.addWidget(ver_lbl)

        outer.addStretch()

    def _load_into_ui(self):
        s = self._settings
        model_val = s.get("default_model", "w_075")
        idx = 0 if "075" in model_val else 1
        self.model_combo.setCurrentIndex(idx)
        self.chk_comparison.setChecked(bool(s.get("comparison_mode", False)))
        self.output_edit.setText(s.get("output_dir", ""))
        self.chk_pdf.setChecked(bool(s.get("auto_pdf", True)))
        self.chk_json.setChecked(bool(s.get("auto_json", True)))
        self.chk_csv.setChecked(bool(s.get("auto_csv", True)))

    def _save(self):
        model_text = self.model_combo.currentText()
        self._settings["default_model"] = "w_075" if "075" in model_text else "w_035"
        self._settings["comparison_mode"] = self.chk_comparison.isChecked()
        self._settings["output_dir"] = self.output_edit.text().strip()
        self._settings["auto_pdf"]  = self.chk_pdf.isChecked()
        self._settings["auto_json"] = self.chk_json.isChecked()
        self._settings["auto_csv"]  = self.chk_csv.isChecked()
        save_settings(self._settings)
        self.settings_changed.emit(self._settings)
        QMessageBox.information(self, "Saved", "Settings saved.")

    def get_settings(self) -> Dict[str, Any]:
        return dict(self._settings)

    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory",
                                             self.output_edit.text())
        if d:
            self.output_edit.setText(d)

    def _open_output_dir(self):
        d = self.output_edit.text().strip()
        if not d or not Path(d).exists():
            QMessageBox.warning(self, "Warning", "Output directory not found.")
            return
        if platform.system() == "Darwin":
            subprocess.run(["open", d])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", d])
        else:
            subprocess.run(["xdg-open", d])

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Delete ALL history entries? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            from utils.history import save_history
            save_history([])
            QMessageBox.information(self, "Done", "History cleared.")

    def _open_logs(self):
        from utils.spec import PROJECT_ROOT
        logs_dir = PROJECT_ROOT / "output" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        if platform.system() == "Darwin":
            subprocess.run(["open", str(logs_dir)])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", str(logs_dir)])
        else:
            subprocess.run(["xdg-open", str(logs_dir)])
