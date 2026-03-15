"""
백그라운드 작업 처리 모듈
QThread를 사용하여 분석 작업을 별도 스레드에서 실행
"""
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import Dict, Any, Optional

from utils.ai_engine import analyze_clip
from recon.tsdf import create_3d_volume
from report.report_builder import build_pdf


class AnalysisWorker(QThread):
    """
    영상 분석 작업을 백그라운드에서 수행하는 워커 스레드
    """
    # 시그널 정의
    progress_updated = pyqtSignal(str)  # 진행 상황 메시지
    progress_percent = pyqtSignal(int)  # 진행률 (0-100)
    analysis_finished = pyqtSignal(dict)  # 분석 완료 (결과 딕셔너리)
    error_occurred = pyqtSignal(str)  # 에러 발생
    
    def __init__(self, video_path: Path, output_dir: Optional[Path] = None):
        """
        Args:
            video_path: 분석할 영상 파일 경로
            output_dir: 결과 저장 디렉토리 (None이면 기본 경로 사용)
        """
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self._is_cancelled = False
    
    def run(self):
        """워커 스레드 실행"""
        try:
            # 1. 영상 로드 및 AI 분석
            self.progress_percent.emit(10)
            self.progress_updated.emit("Loading video file...")
            analysis_result = analyze_clip(self.video_path)
            
            if self._is_cancelled:
                return
            
            self.progress_percent.emit(50)
            self.progress_updated.emit("Running AI analysis...")
            
            if self._is_cancelled:
                return
            
            # 2. 3D 볼륨 생성 (옵션 - 연구개발 중, 나중에 탑재 예정)
            # 현재는 플레이스홀더로 처리
            self.progress_percent.emit(70)
            self.progress_updated.emit("3D reconstruction (coming soon)...")
            # TODO: 2D→3D 모델이 완성되면 여기에 탑재
            analysis_result["volume_3d"] = None
            
            if self._is_cancelled:
                return
            
            # 3. PDF 리포트 생성
            self.progress_percent.emit(80)
            self.progress_updated.emit("Generating PDF report...")
            try:
                report_path = self._get_report_path()
                build_pdf(
                    report_path=report_path,
                    analysis_result=analysis_result
                )
                analysis_result["report_path"] = report_path
                self.progress_updated.emit(f"Report saved: {report_path.name}")
            except Exception as e:
                self.progress_updated.emit(f"PDF generation failed: {str(e)}")
                analysis_result["report_path"] = None
            
            # 4. 완료
            self.progress_percent.emit(100)
            self.progress_updated.emit("Analysis complete!")
            self.analysis_finished.emit(analysis_result)
            
        except Exception as e:
            self.progress_percent.emit(0)
            self.error_occurred.emit(str(e))
    
    def cancel(self):
        """작업 취소"""
        self._is_cancelled = True
    
    def _get_report_path(self) -> Path:
        """리포트 저장 경로 결정"""
        if self.output_dir:
            output_dir = Path(self.output_dir)
        else:
            from utils.spec import PROJECT_ROOT
            output_dir = PROJECT_ROOT / "output"
            output_dir.mkdir(exist_ok=True)
        
        # 파일명: 원본 파일명_날짜시간.pdf
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = self.video_path.stem
        report_name = f"{stem}_{timestamp}.pdf"
        
        return output_dir / report_name

