"""
메인 GUI 윈도우
PyQt5 기반 데스크탑 애플리케이션 UI - 의료 영상 워크스테이션 스타일
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QProgressBar, QSplitter, QListWidget, QListWidgetItem,
    QMessageBox, QGroupBox, QGridLayout, QToolBar, QMenuBar, QMenu,
    QDockWidget, QTextEdit, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSlot, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap

from gui.worker import AnalysisWorker
from gui.styles import load_style_sheet
from viewer.slice_view import SliceViewer
from viewer.vtk_viewer import VTKViewer


class MainWindow(QMainWindow):
    """메인 윈도우 클래스 - 의료 영상 워크스테이션 스타일"""
    
    def __init__(self):
        super().__init__()
        self.current_result: Optional[Dict[str, Any]] = None
        self.worker: Optional[AnalysisWorker] = None
        self.video_path: Optional[Path] = None
        
        self.init_ui()
        self.apply_style()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("SonoCube PoC - Cardiac Echo Analysis")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 메뉴바 생성
        self._create_menu_bar()
        
        # 툴바 생성
        self._create_toolbar()
        
        # 중앙 위젯 (뷰어 영역)
        self._create_central_widget()
        
        # 좌측 도크 (파일 목록, 환자 정보)
        self._create_left_dock()
        
        # 우측 도크 (분석 결과, 메트릭)
        self._create_right_dock()
        
        # 상태바
        self.statusBar().showMessage("Ready - Select a video file to begin analysis")
    
    def apply_style(self):
        """스타일시트 적용"""
        style_sheet = load_style_sheet("dark_theme")
        self.setStyleSheet(style_sheet)
    
    def _create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # File 메뉴
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open Video...", self.select_file, "Ctrl+O")
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close, "Ctrl+Q")
        
        # View 메뉴
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Reset Layout", self.reset_layout)
        
        # Analysis 메뉴
        analysis_menu = menubar.addMenu("Analysis")
        analysis_menu.addAction("Start Analysis", self.start_analysis, "Ctrl+R")
        analysis_menu.addAction("Stop Analysis", self.stop_analysis, "Ctrl+S")
        
        # Tools 메뉴
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Save Screenshot", self.save_screenshot, "Ctrl+Shift+S")
        tools_menu.addAction("Open Report", self.open_report, "Ctrl+P")
        
        # Help 메뉴
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.show_about)
    
    def _create_toolbar(self):
        """툴바 생성"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 로고/제목 영역
        title_label = QLabel("SonoCube PoC")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setProperty("class", "title")
        toolbar.addWidget(title_label)
        
        toolbar.addSeparator()
        
        # 파일 열기 버튼
        self.btn_open = QPushButton("Open File")
        self.btn_open.setProperty("class", "primary")
        self.btn_open.clicked.connect(self.select_file)
        toolbar.addWidget(self.btn_open)
        
        # 분석 시작 버튼
        self.btn_analyze = QPushButton("Start Analysis")
        self.btn_analyze.setProperty("class", "primary")
        self.btn_analyze.clicked.connect(self.start_analysis)
        self.btn_analyze.setEnabled(False)
        toolbar.addWidget(self.btn_analyze)
        
        toolbar.addSeparator()
        
        # 리포트 버튼
        self.btn_report = QPushButton("Generate Report")
        self.btn_report.clicked.connect(self.open_report)
        self.btn_report.setEnabled(False)
        toolbar.addWidget(self.btn_report)
        
        # 스크린샷 버튼
        self.btn_screenshot = QPushButton("Screenshot")
        self.btn_screenshot.clicked.connect(self.save_screenshot)
        self.btn_screenshot.setEnabled(False)
        toolbar.addWidget(self.btn_screenshot)
        
        toolbar.addSeparator()
        
        # 진행 상황 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        toolbar.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setProperty("class", "status")
        toolbar.addWidget(self.progress_label)
    
    def _create_central_widget(self):
        """중앙 위젯 생성 (뷰어 영역)"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 뷰어 스플리터 (2D | 3D)
        splitter = QSplitter(Qt.Horizontal)
        
        # 2D 슬라이스 뷰어
        self.slice_viewer = SliceViewer()
        splitter.addWidget(self.slice_viewer)
        
        # 3D 뷰어
        self.vtk_viewer = VTKViewer()
        splitter.addWidget(self.vtk_viewer)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([800, 800])
        
        layout.addWidget(splitter)
    
    def _create_left_dock(self):
        """좌측 도크 위젯 생성"""
        dock = QDockWidget("Patient & Files", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)
        dock_layout.setContentsMargins(8, 8, 8, 8)
        
        # 환자 정보 그룹
        patient_group = QGroupBox("Patient Information")
        patient_layout = QVBoxLayout()
        
        self.label_patient_name = QLabel("No patient selected")
        self.label_patient_name.setProperty("class", "title")
        patient_layout.addWidget(self.label_patient_name)
        
        self.label_case_number = QLabel("Case: --")
        self.label_case_number.setProperty("class", "status")
        patient_layout.addWidget(self.label_case_number)
        
        self.label_file_info = QLabel("File: --")
        self.label_file_info.setProperty("class", "status")
        patient_layout.addWidget(self.label_file_info)
        
        patient_group.setLayout(patient_layout)
        dock_layout.addWidget(patient_group)
        
        # 파일 목록 그룹
        files_group = QGroupBox("Recent Files")
        files_layout = QVBoxLayout()
        
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.on_file_selected)
        files_layout.addWidget(self.file_list)
        
        files_group.setLayout(files_layout)
        dock_layout.addWidget(files_group)
        
        dock_layout.addStretch()
        
        dock.setWidget(dock_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
    
    def _create_right_dock(self):
        """우측 도크 위젯 생성 (분석 결과)"""
        dock = QDockWidget("Analysis Results", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)
        dock_layout.setContentsMargins(8, 8, 8, 8)
        
        # 메트릭 그룹
        metrics_group = QGroupBox("Cardiac Metrics")
        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(8)
        
        # EF
        ef_label = QLabel("Ejection Fraction:")
        ef_label.setProperty("class", "metric-label")
        self.label_ef = QLabel("--")
        self.label_ef.setProperty("class", "metric")
        metrics_layout.addWidget(ef_label, 0, 0)
        metrics_layout.addWidget(self.label_ef, 0, 1)
        
        # EDV
        edv_label = QLabel("EDV:")
        edv_label.setProperty("class", "metric-label")
        self.label_edv = QLabel("-- ml")
        self.label_edv.setProperty("class", "metric")
        metrics_layout.addWidget(edv_label, 1, 0)
        metrics_layout.addWidget(self.label_edv, 1, 1)
        
        # ESV
        esv_label = QLabel("ESV:")
        esv_label.setProperty("class", "metric-label")
        self.label_esv = QLabel("-- ml")
        self.label_esv.setProperty("class", "metric")
        metrics_layout.addWidget(esv_label, 2, 0)
        metrics_layout.addWidget(self.label_esv, 2, 1)
        
        # Tumor Volume
        tumor_label = QLabel("Tumor Volume:")
        tumor_label.setProperty("class", "metric-label")
        self.label_tumor = QLabel("Not detected")
        self.label_tumor.setProperty("class", "metric")
        metrics_layout.addWidget(tumor_label, 3, 0)
        metrics_layout.addWidget(self.label_tumor, 3, 1)
        
        metrics_group.setLayout(metrics_layout)
        dock_layout.addWidget(metrics_group)
        
        # 분석 정보 그룹
        info_group = QGroupBox("Analysis Information")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        dock_layout.addWidget(info_group)
        
        # 리포트 그룹
        report_group = QGroupBox("Report")
        report_layout = QVBoxLayout()
        
        self.btn_open_report_dock = QPushButton("Open PDF Report")
        self.btn_open_report_dock.setProperty("class", "primary")
        self.btn_open_report_dock.clicked.connect(self.open_report)
        self.btn_open_report_dock.setEnabled(False)
        report_layout.addWidget(self.btn_open_report_dock)
        
        report_group.setLayout(report_layout)
        dock_layout.addWidget(report_group)
        
        dock_layout.addStretch()
        
        dock.setWidget(dock_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
    
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
            self._update_file_info()
            self.btn_analyze.setEnabled(True)
            self.statusBar().showMessage(f"File selected: {self.video_path.name}")
    
    def _update_file_info(self):
        """파일 정보 업데이트"""
        if self.video_path:
            self.label_file_info.setText(f"File: {self.video_path.name}")
            
            # 케이스 번호 생성 (파일명 기반)
            case_num = self.video_path.stem[:8].upper()
            if len(case_num) < 8:
                case_num = case_num.ljust(8, '0')
            self.label_case_number.setText(f"Case: {case_num}")
            
            # 파일 목록에 추가
            item = QListWidgetItem(self.video_path.name)
            item.setData(Qt.UserRole, str(self.video_path))
            self.file_list.insertItem(0, item)
    
    def on_file_selected(self, item: QListWidgetItem):
        """파일 목록에서 파일 선택"""
        file_path = item.data(Qt.UserRole)
        if file_path:
            self.video_path = Path(file_path)
            self._update_file_info()
            self.btn_analyze.setEnabled(True)
    
    def start_analysis(self):
        """분석 시작"""
        if not self.video_path or not self.video_path.exists():
            QMessageBox.warning(self, "Warning", "Please select a valid video file first.")
            return
        
        # UI 상태 변경
        self.btn_analyze.setEnabled(False)
        self.btn_open.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Starting analysis...")
        
        # 워커 스레드 시작
        self.worker = AnalysisWorker(self.video_path)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.analysis_finished.connect(self.on_analysis_finished)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def stop_analysis(self):
        """분석 중지"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self.progress_bar.setVisible(False)
            self.progress_label.setText("Analysis cancelled")
            self.btn_analyze.setEnabled(True)
            self.btn_open.setEnabled(True)
    
    @pyqtSlot(str)
    def on_progress_updated(self, message: str):
        """진행 상황 업데이트"""
        self.progress_label.setText(message)
        self.statusBar().showMessage(message)
    
    @pyqtSlot(dict)
    def on_analysis_finished(self, result: Dict[str, Any]):
        """분석 완료 처리"""
        self.current_result = result
        
        # 진행 상황 UI 숨기기
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Analysis complete!")
        
        # 버튼 활성화
        self.btn_analyze.setEnabled(True)
        self.btn_open.setEnabled(True)
        self.btn_screenshot.setEnabled(True)
        self.btn_report.setEnabled(True)
        self.btn_open_report_dock.setEnabled(True)
        
        # 결과 표시
        self._display_results(result)
        
        # 뷰어 업데이트
        self._update_viewers(result)
        
        self.statusBar().showMessage("Analysis complete!")
    
    @pyqtSlot(str)
    def on_error(self, error_message: str):
        """에러 처리"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"Error: {error_message}")
        self.btn_analyze.setEnabled(True)
        self.btn_open.setEnabled(True)
        
        QMessageBox.critical(self, "Error", f"Analysis failed:\n{error_message}")
        self.statusBar().showMessage("Error occurred")
    
    def _display_results(self, result: Dict[str, Any]):
        """결과 메트릭 표시"""
        ef = result.get("ef", 0.0)
        volume_info = result.get("volume_info", {})
        edv = volume_info.get("edv", 0.0)
        esv = volume_info.get("esv", 0.0)
        tumor_volume = volume_info.get("tumor_volume")
        metadata = result.get("metadata", {})
        
        # 메트릭 업데이트
        self.label_ef.setText(f"{ef:.1f}%")
        self.label_edv.setText(f"{edv:.1f} ml")
        self.label_esv.setText(f"{esv:.1f} ml")
        
        if tumor_volume is not None:
            self.label_tumor.setText(f"{tumor_volume:.1f} ml")
        else:
            self.label_tumor.setText("Not detected")
        
        # 분석 정보 텍스트
        info_text = f"""
Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
File: {metadata.get('file_path', 'N/A')}
Frames: {metadata.get('num_frames', 'N/A')}
Frame Size: {metadata.get('frame_size', 'N/A')}
FPS: {result.get('fps', 0):.1f}
        """
        self.info_text.setText(info_text.strip())
    
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = SCREENSHOTS_DIR / f"screenshot_{timestamp}.png"
        
        pixmap = self.grab()
        pixmap.save(str(screenshot_path))
        
        QMessageBox.information(self, "Success", f"Screenshot saved to:\n{screenshot_path}")
    
    def open_report(self):
        """PDF 리포트 열기"""
        if not self.current_result:
            QMessageBox.warning(self, "Warning", "No analysis result available.")
            return
        
        report_path = self.current_result.get("report_path")
        if not report_path or not Path(report_path).exists():
            QMessageBox.warning(self, "Warning", "Report file not found. Please run analysis first.")
            return
        
        import platform
        import subprocess
        
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(report_path)])
        elif platform.system() == "Windows":
            subprocess.run(["start", str(report_path)], shell=True)
        else:  # Linux
            subprocess.run(["xdg-open", str(report_path)])
    
    def reset_layout(self):
        """레이아웃 리셋"""
        # 도크 위젯 위치 리셋 (간단한 구현)
        QMessageBox.information(self, "Info", "Layout reset (feature to be implemented)")
    
    def show_about(self):
        """About 다이얼로그"""
        QMessageBox.about(
            self,
            "About SonoCube PoC",
            "SonoCube PoC - Cardiac Echo Analysis\n\n"
            "Research tool for 2D echocardiography analysis\n"
            "Version 1.0.0\n\n"
            "Not for diagnostic use."
        )
