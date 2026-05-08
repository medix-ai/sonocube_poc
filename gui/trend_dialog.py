"""EF 트렌드 그래프 다이얼로그"""
from datetime import datetime
from typing import Any, Dict, List

from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from utils.constants import CONFIDENCE_COLORS


_BG = "#1e1e1e"
_AX_BG = "#2d2d2d"
_SPINE = "#4d4d4d"
_TEXT = "#e0e0e0"


class TrendDialog(QDialog):
    def __init__(self, history: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("EF Trend")
        self.setMinimumSize(800, 500)
        self._history = history
        self._fig = None
        self._build_ui(history)

    def _build_ui(self, history: List[Dict[str, Any]]):
        layout = QVBoxLayout(self)

        self._fig = Figure(figsize=(9, 5), facecolor=_BG)
        canvas = FigureCanvas(self._fig)
        layout.addWidget(canvas)

        ax = self._fig.add_subplot(111, facecolor=_AX_BG)
        self._populate_chart(ax, history)

        self._fig.tight_layout(pad=0.8)
        canvas.draw()

        # 하단 버튼
        btn_row = QHBoxLayout()
        btn_save = QPushButton("Save Image...")
        btn_save.clicked.connect(self._save_image)
        btn_row.addWidget(btn_save)
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _populate_chart(self, ax, history: List[Dict[str, Any]]):
        entries = []
        for entry in history:
            try:
                date = datetime.fromisoformat(entry["date"])
                ef = float(entry["ef"])
                ef_std = float(entry.get("ef_std", entry.get("ef_confidence", 0.0)))
                conf = entry.get("confidence_level", "Unknown")
                entries.append((date, ef, ef_std, conf, entry.get("case_id", "")))
            except Exception:
                pass

        if not entries:
            ax.text(0.5, 0.5, "No history available",
                    transform=ax.transAxes, ha="center", va="center", color=_TEXT)
        else:
            xs = list(range(len(entries)))
            dates, efs, stds, confs, case_ids = zip(*entries)

            # 선 그리기
            ax.plot(xs, efs, color="#00bcd4", linewidth=1.5, zorder=2)

            # 신뢰도별 마커 색상
            for i, (x, ef, conf) in enumerate(zip(xs, efs, confs)):
                color = CONFIDENCE_COLORS.get(conf, "#9e9e9e")
                ax.plot(x, ef, "o", color=color, markersize=8, zorder=3)

            # ±std 에러바
            ax.errorbar(xs, efs, yerr=stds, fmt="none",
                        ecolor="#4dd0e1", capsize=4, linewidth=1, zorder=1)

            ax.axhline(y=55, color="#ff5722", linestyle="--",
                       alpha=0.6, label="Normal threshold (55%)")
            ax.set_xticks(xs)
            ax.set_xticklabels(
                [f"{d.strftime('%m/%d %H:%M')}\n{cid}"
                 for d, cid in zip(dates, case_ids)],
                rotation=30, ha="right", color=_TEXT, fontsize=7,
            )
            ax.set_ylim(0, 100)

            # 범례: 신뢰도 색상 설명
            from matplotlib.lines import Line2D
            legend_handles = [
                Line2D([0], [0], color="#ff5722", linestyle="--", alpha=0.6,
                       label="Normal (55%)"),
                Line2D([0], [0], marker="o", color="w",
                       markerfacecolor=CONFIDENCE_COLORS["High"],
                       markersize=8, label="Stability: High"),
                Line2D([0], [0], marker="o", color="w",
                       markerfacecolor=CONFIDENCE_COLORS["Medium"],
                       markersize=8, label="Stability: Medium"),
                Line2D([0], [0], marker="o", color="w",
                       markerfacecolor=CONFIDENCE_COLORS["Low"],
                       markersize=8, label="Stability: Low"),
            ]
            ax.legend(handles=legend_handles, facecolor=_AX_BG,
                      edgecolor=_SPINE, labelcolor=_TEXT, fontsize=8)

        ax.set_ylabel("EF (%)", color=_TEXT)
        ax.set_title("Ejection Fraction Trend  (marker color = prediction stability)",
                     color=_TEXT, fontsize=10)
        ax.tick_params(colors=_TEXT)
        for spine in ax.spines.values():
            spine.set_color(_SPINE)

    def _save_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Trend Image", "ef_trend.png",
            "PNG Image (*.png);;All Files (*)"
        )
        if path:
            try:
                self._fig.savefig(path, dpi=150, bbox_inches="tight",
                                  facecolor=self._fig.get_facecolor())
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Failed to save image:\n{e}")
