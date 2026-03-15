"""
설정 및 경로 관리 모듈
PyInstaller 환경에서도 안전하게 리소스에 접근할 수 있도록 경로 처리
"""
import sys
from pathlib import Path
from typing import Union


def resource_path(relative_path: Union[str, Path]) -> Path:
    """
    PyInstaller로 패키징된 환경에서도 리소스 파일에 안전하게 접근
    
    Args:
        relative_path: 리소스 파일의 상대 경로
        
    Returns:
        실제 리소스 파일의 절대 경로
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller로 패키징된 경우
        base_path = Path(sys._MEIPASS)
    else:
        # 개발 환경
        base_path = Path(__file__).parent.parent
    
    return base_path / relative_path


# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

# 주요 디렉토리 경로
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "model"
ASSETS_DIR = PROJECT_ROOT / "gui" / "assets"
TEMPLATES_DIR = PROJECT_ROOT / "report" / "templates"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

# 모델 파일 경로 (나중에 실제 모델 파일로 교체)
LV_SEG_MODEL_PATH = MODEL_DIR / "lv_seg.pt"
TUMOR_SEG_MODEL_PATH = MODEL_DIR / "tumor_seg.pt"

# 설정값
DEFAULT_FRAME_SIZE = (224, 224)  # 전처리 기본 프레임 크기
DEFAULT_FPS = 30  # 기본 FPS (실제 영상에서 추출하거나 설정값 사용)

