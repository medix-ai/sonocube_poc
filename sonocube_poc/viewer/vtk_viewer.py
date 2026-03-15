"""
3D VTK 뷰어 모듈
PyVista를 사용한 3D 메시 시각화
"""
import numpy as np
from typing import Optional
try:
    import pyvista as pv
    from pyvistaqt import QtInteractor
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False
    QtInteractor = None

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt
import open3d as o3d


class VTKViewer(QWidget):
    """3D 메시 뷰어 위젯"""
    
    def __init__(self):
        super().__init__()
        self.mesh: Optional[o3d.geometry.TriangleMesh] = None
        self.plotter: Optional[QtInteractor] = None
        
        if not PYVISTA_AVAILABLE:
            self.label_info = QLabel("PyVista not available. Install with: pip install pyvista pyvistaqt")
            layout = QVBoxLayout(self)
            layout.addWidget(self.label_info)
        else:
            self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # PyVista plotter
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor)
        
        # 초기 플레이스홀더 메시지 표시
        self.plotter.background_color = '#1e1e1e'
        # PyVista는 corner annotation만 지원하므로 QLabel 사용
        self.plotter.show()
        
        # 제어 버튼
        button_layout = QVBoxLayout()
        
        self.btn_reset_view = QPushButton("Reset View")
        self.btn_reset_view.clicked.connect(self.reset_view)
        button_layout.addWidget(self.btn_reset_view)
        
        self.btn_screenshot = QPushButton("Save 3D Screenshot")
        self.btn_screenshot.clicked.connect(self.save_screenshot)
        button_layout.addWidget(self.btn_screenshot)
        
        layout.addLayout(button_layout)
        
        # 정보 라벨 (플레이스홀더 메시지 포함)
        self.label_info = QLabel("3D Reconstruction\n(Coming Soon)\n\n2D→3D model is under development")
        self.label_info.setAlignment(Qt.AlignCenter)
        self.label_info.setStyleSheet("""
            QLabel {
                color: #4ec9b0;
                font-size: 18px;
                font-weight: bold;
                padding: 20px;
                background-color: #1e1e1e;
                border: 2px dashed #4ec9b0;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.label_info)
    
    def set_mesh(self, mesh: Optional[o3d.geometry.TriangleMesh]):
        """메시 설정 및 표시"""
        self.mesh = mesh
        
        if not PYVISTA_AVAILABLE:
            return
        
        if mesh is None:
            if self.plotter:
                self.plotter.clear()
                self.plotter.background_color = '#1e1e1e'
                self.plotter.show()
            if hasattr(self, 'label_info'):
                self.label_info.setText("3D Reconstruction\n(Coming Soon)\n\n2D→3D model is under development")
                self.label_info.setAlignment(Qt.AlignCenter)
                self.label_info.setStyleSheet("""
                    QLabel {
                        color: #4ec9b0;
                        font-size: 18px;
                        font-weight: bold;
                        padding: 20px;
                        background-color: #1e1e1e;
                        border: 2px dashed #4ec9b0;
                        border-radius: 8px;
                    }
                """)
            return
        
        # Open3D 메시를 PyVista로 변환
        vertices = np.asarray(mesh.vertices)
        faces = np.asarray(mesh.triangles)
        
        # PyVista 메시 생성
        # faces 배열을 PyVista 형식으로 변환 (각 face 앞에 vertex 개수 추가)
        faces_pv = np.column_stack([np.full(len(faces), 3), faces]).flatten()
        pv_mesh = pv.PolyData(vertices, faces_pv)
        
        # 기존 메시 제거 후 새 메시 추가
        self.plotter.clear()
        # 어두운 배경 설정
        self.plotter.background_color = '#1e1e1e'
        self.plotter.add_mesh(pv_mesh, color='#4ec9b0', opacity=0.8, show_edges=True, edge_color='#0078d4')
        self.plotter.add_axes(line_width=3, labels_off=False)
        # 축 색상 설정
        self.plotter.show()
        
        # 정보 업데이트
        num_vertices = len(vertices)
        num_faces = len(faces)
        self.label_info.setText(f"Vertices: {num_vertices}, Faces: {num_faces}")
        self.label_info.setAlignment(Qt.AlignLeft)
        self.label_info.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 12px;
                padding: 8px;
                background-color: transparent;
                border: none;
            }
        """)
    
    def reset_view(self):
        """뷰 리셋"""
        if self.plotter:
            self.plotter.reset_camera()
            self.plotter.show()
    
    def save_screenshot(self):
        """3D 뷰 스크린샷 저장"""
        if self.plotter and self.mesh:
            from utils.spec import SCREENSHOTS_DIR
            SCREENSHOTS_DIR.mkdir(exist_ok=True)
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = SCREENSHOTS_DIR / f"3d_view_{timestamp}.png"
            
            self.plotter.screenshot(str(screenshot_path))
            self.label_info.setText(f"Screenshot saved: {screenshot_path.name}")

