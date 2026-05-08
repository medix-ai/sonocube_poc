"""Frame-wise EF curve 위젯 v1.2 — hover, mean line, outlier marker, image export"""
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

_BG    = "#0d1117"
_AX_BG = "#161b22"
_SPINE = "#30363d"
_TEXT  = "#e6edf3"
_SEC   = "#8b949e"


class EFCurveWidget(QWidget):
    """프레임별 EF 예측 곡선 위젯 (메인 스레드 전용)"""

    frame_hovered = pyqtSignal(int, float)  # (frame_idx, ef_value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._framewise_ef: List[float] = []
        self._ed_idx = 0
        self._es_idx = 0
        self._ef_median = 0.0
        self._ef_mean = 0.0
        self._ef_std = 0.0
        self._hover_line = None
        self._hover_label_artist = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 2)
        layout.setSpacing(2)

        self.fig = Figure(figsize=(10, 2.4), facecolor=_BG)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.ax = self.fig.add_subplot(111, facecolor=_AX_BG)
        self._draw_placeholder()
        self.fig.tight_layout(pad=0.6)

        # 하단 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(4, 0, 4, 0)
        self.hover_label = QLabel("")
        self.hover_label.setStyleSheet(f"color: {_SEC}; font-size: 11px;")
        btn_row.addWidget(self.hover_label)
        btn_row.addStretch()

        self.btn_export = QPushButton("Export Curve")
        self.btn_export.setFixedHeight(24)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_image)
        btn_row.addWidget(self.btn_export)
        layout.addLayout(btn_row)

        self.canvas.mpl_connect("motion_notify_event", self._on_hover)
        self.canvas.mpl_connect("axes_leave_event", self._on_leave)

    # ── 스타일 ────────────────────────────────────────────────────────────────

    def _style_ax(self):
        self.ax.tick_params(colors=_TEXT, labelsize=7)
        self.ax.xaxis.label.set_color(_TEXT)
        self.ax.yaxis.label.set_color(_TEXT)
        self.ax.title.set_color(_TEXT)
        for sp in self.ax.spines.values():
            sp.set_color(_SPINE)

    # ── placeholder ───────────────────────────────────────────────────────────

    def _draw_placeholder(self):
        self.ax.clear()
        self.ax.set_facecolor(_AX_BG)
        self.ax.text(0.5, 0.5,
                     "Run analysis to see frame-wise EF prediction curve",
                     transform=self.ax.transAxes, ha="center", va="center",
                     color="#484f58", fontsize=9)
        self._style_ax()
        self.canvas.draw()

    # ── 데이터 업데이트 ───────────────────────────────────────────────────────

    def update_curve(
        self,
        framewise_ef: List[float],
        ed_idx: int,
        es_idx: int,
        ef_median: float,
        ef_std: float,
        ef_mean: Optional[float] = None,
    ):
        self._framewise_ef = framewise_ef
        self._ed_idx = ed_idx
        self._es_idx = es_idx
        self._ef_median = ef_median
        self._ef_mean = ef_mean if ef_mean is not None else ef_median
        self._ef_std = ef_std
        self._redraw()
        self.btn_export.setEnabled(True)

    def update_ed_es(self, ed_idx: int, es_idx: int):
        """ED/ES override 후 마커만 갱신"""
        self._ed_idx = ed_idx
        self._es_idx = es_idx
        if self._framewise_ef:
            self._redraw()

    # ── 내부 그리기 ───────────────────────────────────────────────────────────

    def _redraw(self):
        self.ax.clear()
        self.ax.set_facecolor(_AX_BG)
        efs = self._framewise_ef
        xs = list(range(len(efs)))

        # 메인 곡선
        self.ax.plot(xs, efs, color="#58a6ff", linewidth=1.3, label="Frame EF", zorder=3)

        # Confidence band (median ± std)
        lo = self._ef_median - self._ef_std
        hi = self._ef_median + self._ef_std
        self.ax.fill_between(xs, lo, hi, alpha=0.12, color="#58a6ff", zorder=1)

        # Median 기준선
        self.ax.axhline(y=self._ef_median, color="#58a6ff", linestyle="--",
                        alpha=0.5, linewidth=1, label=f"Median {self._ef_median:.1f}%", zorder=2)

        # Mean 기준선
        if abs(self._ef_mean - self._ef_median) > 0.05:
            self.ax.axhline(y=self._ef_mean, color="#d29922", linestyle=":",
                            alpha=0.6, linewidth=1, label=f"Mean {self._ef_mean:.1f}%", zorder=2)

        # 정상 기준선 55%
        self.ax.axhline(y=55, color="#ff7b72", linestyle=":", alpha=0.5, linewidth=1,
                        label="Normal (55%)", zorder=2)

        # Outlier 마커 (median ± 2*std 밖)
        lo2, hi2 = self._ef_median - 2 * self._ef_std, self._ef_median + 2 * self._ef_std
        outliers = [(i, v) for i, v in enumerate(efs) if v < lo2 or v > hi2]
        if outliers:
            ox, oy = zip(*outliers)
            self.ax.scatter(list(ox), list(oy), color="#f85149", s=18, zorder=4,
                            label="Outlier", marker="x", linewidths=1.5)

        # ED / ES 마커
        if 0 <= self._ed_idx < len(efs):
            self.ax.plot(self._ed_idx, efs[self._ed_idx], "^",
                         color="#3fb950", markersize=8, zorder=5,
                         label=f"ED f{self._ed_idx}")
        if 0 <= self._es_idx < len(efs):
            self.ax.plot(self._es_idx, efs[self._es_idx], "v",
                         color="#f85149", markersize=8, zorder=5,
                         label=f"ES f{self._es_idx}")

        self.ax.set_xlabel("Frame Index", fontsize=8)
        self.ax.set_ylabel("EF (%)", fontsize=8)
        self.ax.set_title("Frame-wise EF Prediction  (ED=▲  ES=▼  ×=outlier)", fontsize=9)
        self.ax.legend(
            facecolor=_AX_BG, edgecolor=_SPINE, labelcolor=_TEXT,
            fontsize=7, loc="upper right", ncol=5,
        )
        self._style_ax()
        self.fig.tight_layout(pad=0.6)
        self.canvas.draw()

    # ── Hover 처리 ────────────────────────────────────────────────────────────

    def _on_hover(self, event):
        if event.inaxes != self.ax or not self._framewise_ef:
            return
        x = int(round(event.xdata)) if event.xdata is not None else -1
        if 0 <= x < len(self._framewise_ef):
            ef_val = self._framewise_ef[x]
            self.hover_label.setText(f"Frame {x}  →  EF {ef_val:.1f}%")
            self.frame_hovered.emit(x, ef_val)

    def _on_leave(self, event):
        self.hover_label.setText("")

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save EF Curve Image", "ef_curve.png",
            "PNG Image (*.png);;All Files (*)"
        )
        if path:
            try:
                self.fig.savefig(path, dpi=150, bbox_inches="tight",
                                 facecolor=self.fig.get_facecolor())
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Export Error", str(e))
