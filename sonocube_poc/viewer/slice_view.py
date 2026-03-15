"""
2D 슬라이스 뷰어 모듈
프레임과 segmentation 마스크를 오버레이하여 표시
"""
import numpy as np
from typing import List, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel
from PyQt5.QtCore import Qt

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = None
    Figure = None


class SliceViewer(QWidget):
    """2D 슬라이스 뷰어 위젯"""
    
    def __init__(self):
        super().__init__()
        self.frames: List[np.ndarray] = []
        self.masks: List[np.ndarray] = []
        self.ed_idx: int = 0
        self.es_idx: int = 0
        self.current_idx: int = 0
        
        if not MATPLOTLIB_AVAILABLE:
            layout = QVBoxLayout(self)
            self.label_info = QLabel("Matplotlib not available. Install with: pip install matplotlib")
            layout.addWidget(self.label_info)
        else:
            self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Matplotlib 캔버스 (어두운 테마)
        self.figure = Figure(figsize=(8, 8), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111, facecolor='#1e1e1e')
        self.ax.tick_params(colors='#e0e0e0')
        self.ax.spines['bottom'].set_color('#4d4d4d')
        self.ax.spines['top'].set_color('#4d4d4d')
        self.ax.spines['right'].set_color('#4d4d4d')
        self.ax.spines['left'].set_color('#4d4d4d')
        layout.addWidget(self.canvas)
        
        # 슬라이더
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.on_slider_changed)
        layout.addWidget(self.slider)
        
        # 프레임 정보 라벨
        self.label_info = QLabel("No data")
        layout.addWidget(self.label_info)
    
    def set_data(
        self,
        frames: List[np.ndarray],
        masks: List[np.ndarray],
        ed_idx: int,
        es_idx: int
    ):
        """데이터 설정"""
        self.frames = frames
        self.masks = masks
        self.ed_idx = ed_idx
        self.es_idx = es_idx
        
        if len(frames) > 0:
            self.current_idx = 0
            self.slider.setMaximum(len(frames) - 1)
            self.slider.setValue(0)
            self.update_display()
    
    def on_slider_changed(self, value: int):
        """슬라이더 값 변경 시 호출"""
        self.current_idx = value
        self.update_display()
    
    def update_display(self):
        """화면 업데이트"""
        if not self.frames or self.current_idx >= len(self.frames):
            return
        
        self.ax.clear()
        
        # 프레임 표시
        frame = self.frames[self.current_idx]
        if len(frame.shape) == 3:
            self.ax.imshow(frame, cmap='gray')
        else:
            self.ax.imshow(frame, cmap='gray')
        
        # 마스크 오버레이
        if self.current_idx < len(self.masks):
            mask = self.masks[self.current_idx]
            self.ax.contour(mask, levels=[0.5], colors=['red'], linewidths=2)
        
        # ED/ES 표시
        if self.current_idx == self.ed_idx:
            self.ax.set_title(f"Frame {self.current_idx} (ED)", fontsize=14, color='#4ec9b0', pad=10)
        elif self.current_idx == self.es_idx:
            self.ax.set_title(f"Frame {self.current_idx} (ES)", fontsize=14, color='#f48771', pad=10)
        else:
            self.ax.set_title(f"Frame {self.current_idx}", fontsize=14, color='#e0e0e0', pad=10)
        
        self.ax.axis('off')
        self.figure.patch.set_facecolor('#1e1e1e')
        self.canvas.draw()
        
        # 정보 업데이트
        info = f"Frame {self.current_idx + 1}/{len(self.frames)}"
        if self.current_idx == self.ed_idx:
            info += " [ED]"
        elif self.current_idx == self.es_idx:
            info += " [ES]"
        self.label_info.setText(info)

