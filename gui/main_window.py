"""
메인 GUI 윈도우
PyQt5 기반 데스크탑 애플리케이션 UI
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QProgressBar, QSplitter,
    QMessageBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSlot

from gui.worker import AnalysisWorker
from viewer.slice_view import SliceViewer
from viewer.vtk_viewer import VTKViewer


class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""
    
    def __init__(self):
        super().__init__()
        self.current_result: Optional[Dict[str, Any]] = None
        self.worker: Optional[AnalysisWorker] = None
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("SonoCube PoC - Cardiac Echo Analysis")
        self.setGeometry(100, 100, 1400, 900)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 상단: 파일 선택 및 제어 버튼
        control_group = self._create_control_panel()
        main_layout.addWidget(control_group)
        
        # 중앙: 스플리터 (2D 뷰어 | 3D 뷰어)
        splitter = QSplitter(Qt.Horizontal)
        
        # 2D 슬라이스 뷰어
        self.slice_viewer = SliceViewer()
        splitter.addWidget(self.slice_viewer)
        
        # 3D 뷰어
        self.vtk_viewer = VTKViewer()
        splitter.addWidget(self.vtk_viewer)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)
        
        # 하단: 결과 표시 및 진행 상황
        result_group = self._create_result_panel()
        main_layout.addWidget(result_group)
        
        # 상태바
        self.statusBar().showMessage("Ready")
    
    def _create_control_panel(self) -> QGroupBox:
        """제어 패널 생성"""
        group = QGroupBox("Control")
        layout = QHBoxLayout()
        
        # 파일 선택 버튼
        self.btn_select_file = QPushButton("Select Video File")
        self.btn_select_file.clicked.connect(self.select_file)
        layout.addWidget(self.btn_select_file)
        
        # 분석 시작 버튼
        self.btn_analyze = QPushButton("Start Analysis")
        self.btn_analyze.clicked.connect(self.start_analysis)
        self.btn_analyze.setEnabled(False)
        layout.addWidget(self.btn_analyze)
        
        # 스크린샷 저장 버튼
        self.btn_screenshot = QPushButton("Save Screenshot")
        self.btn_screenshot.clicked.connect(self.save_screenshot)
        self.btn_screenshot.setEnabled(False)
        layout.addWidget(self.btn_screenshot)
        
        # 선택된 파일 표시
        self.label_file = QLabel("No file selected")
        layout.addWidget(self.label_file)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_result_panel(self) -> QGroupBox:
        """결과 패널 생성"""
        group = QGroupBox("Results")
        layout = QVBoxLayout()
        
        # 진행 상황 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 무한 진행
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 진행 상황 텍스트
        self.progress_text = QLabel("")
        layout.addWidget(self.progress_text)
        
        # 결과 메트릭 표시
        metrics_layout = QGridLayout()
        
        self.label_ef = QLabel("EF: --")
        self.label_edv = QLabel("EDV: -- ml")
        self.label_esv = QLabel("ESV: -- ml")
        self.label_tumor = QLabel("Tumor Volume: --")
        
        metrics_layout.addWidget(QLabel("Ejection Fraction:"), 0, 0)
        metrics_layout.addWidget(self.label_ef, 0, 1)
        metrics_layout.addWidget(QLabel("EDV:"), 1, 0)
        metrics_layout.addWidget(self.label_edv, 1, 1)
        metrics_layout.addWidget(QLabel("ESV:"), 2, 0)
        metrics_layout.addWidget(self.label_esv, 2, 1)
        metrics_layout.addWidget(QLabel("Tumor Volume:"), 3, 0)
        metrics_layout.addWidget(self.label_tumor, 3, 1)
        
        layout.addLayout(metrics_layout)
        
        # 리포트 열기 버튼
        self.btn_open_report = QPushButton("Open PDF Report")
        self.btn_open_report.clicked.connect(self.open_report)
        self.btn_open_report.setEnabled(False)
        layout.addWidget(self.btn_open_report)
        
        group.setLayout(layout)
        return group
    
    def select_file(self):
        """파일 선택 다이얼로그"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Echo Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv);;DICOM Files (*.dcm *.dicom);;All Files (*)"
        )
        
        if file_path:
            self.video_path = Path(file_path)
            self.label_file.setText(f"Selected: {self.video_path.name}")
            self.btn_analyze.setEnabled(True)
            self.statusBar().showMessage(f"File selected: {self.video_path.name}")
    
    def start_analysis(self):
        """분석 시작"""
        if not hasattr(self, 'video_path'):
            QMessageBox.warning(self, "Warning", "Please select a video file first.")
            return
        
        # UI 상태 변경
        self.btn_analyze.setEnabled(False)
        self.btn_select_file.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_text.setText("Starting analysis...")
        
        # 워커 스레드 시작
        self.worker = AnalysisWorker(self.video_path)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.analysis_finished.connect(self.on_analysis_finished)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    @pyqtSlot(str)
    def on_progress_updated(self, message: str):
        """진행 상황 업데이트"""
        self.progress_text.setText(message)
        self.statusBar().showMessage(message)
    
    @pyqtSlot(dict)
    def on_analysis_finished(self, result: Dict[str, Any]):
        """분석 완료 처리"""
        self.current_result = result
        
        # 진행 상황 UI 숨기기
        self.progress_bar.setVisible(False)
        self.progress_text.setText("Analysis complete!")
        
        # 버튼 활성화
        self.btn_analyze.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        self.btn_screenshot.setEnabled(True)
        self.btn_open_report.setEnabled(True)
        
        # 결과 표시
        self._display_results(result)
        
        # 뷰어 업데이트
        self._update_viewers(result)
        
        self.statusBar().showMessage("Analysis complete!")
    
    @pyqtSlot(str)
    def on_error(self, error_message: str):
        """에러 처리"""
        self.progress_bar.setVisible(False)
        self.progress_text.setText(f"Error: {error_message}")
        self.btn_analyze.setEnabled(True)
        self.btn_select_file.setEnabled(True)
        
        QMessageBox.critical(self, "Error", f"Analysis failed:\n{error_message}")
        self.statusBar().showMessage("Error occurred")
    
    def _display_results(self, result: Dict[str, Any]):
        """결과 메트릭 표시"""
        ef = result.get("ef", 0.0)
        volume_info = result.get("volume_info", {})
        edv = volume_info.get("edv", 0.0)
        esv = volume_info.get("esv", 0.0)
        tumor_volume = volume_info.get("tumor_volume")
        
        self.label_ef.setText(f"{ef:.1f}%")
        self.label_edv.setText(f"{edv:.1f} ml")
        self.label_esv.setText(f"{esv:.1f} ml")
        
        if tumor_volume is not None:
            self.label_tumor.setText(f"{tumor_volume:.1f} ml")
        else:
            self.label_tumor.setText("Not detected")
    
    def _update_viewers(self, result: Dict[str, Any]):
        """2D/3D 뷰어 업데이트"""
        # 2D 슬라이스 뷰어 업데이트
        frames = result.get("frames", [])
        lv_masks = result.get("lv_masks", {})
        ed_idx = result.get("ed_frame_idx", 0)
        es_idx = result.get("es_frame_idx", 0)
        
        if frames and lv_masks:
            self.slice_viewer.set_data(
                frames=frames,
                masks=lv_masks.get("all", []),
                ed_idx=ed_idx,
                es_idx=es_idx
            )
        
        # 3D 뷰어 업데이트
        volume_3d = result.get("volume_3d")
        if volume_3d:
            self.vtk_viewer.set_mesh(volume_3d.get("mesh"))
    
    def save_screenshot(self):
        """스크린샷 저장"""
        if not self.current_result:
            QMessageBox.warning(self, "Warning", "No analysis result to save.")
            return
        
        from utils.spec import SCREENSHOTS_DIR
        SCREENSHOTS_DIR.mkdir(exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = SCREENSHOTS_DIR / f"screenshot_{timestamp}.png"
        
        # 현재 윈도우 캡처 (간단한 구현)
        pixmap = self.grab()
        pixmap.save(str(screenshot_path))
        
        QMessageBox.information(self, "Success", f"Screenshot saved to:\n{screenshot_path}")
    
    def open_report(self):
        """PDF 리포트 열기"""
        if not self.current_result:
            return
        
        report_path = self.current_result.get("report_path")
        if not report_path or not Path(report_path).exists():
            QMessageBox.warning(self, "Warning", "Report file not found.")
            return
        
        import platform
        import subprocess
        
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(report_path)])
        elif platform.system() == "Windows":
            subprocess.run(["start", str(report_path)], shell=True)
        else:  # Linux
            subprocess.run(["xdg-open", str(report_path)])

