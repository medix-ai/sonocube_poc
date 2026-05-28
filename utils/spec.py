"""
설정 및 경로 관리 모듈
PyInstaller 환경에서도 안전하게 리소스에 접근할 수 있도록 경로 처리
"""
import sys
from pathlib import Path
from typing import Union


def resource_path(relative_path: Union[str, Path]) -> Path:
    """PyInstaller 패키징 환경과 개발 환경 모두에서 리소스 경로 반환.

    반드시 상대 경로(str 또는 Path)를 전달해야 함.
    절대경로를 넘기면 _MEIPASS가 무시되므로 허용하지 않음.
    """
    p = Path(relative_path)
    if p.is_absolute():
        return p  # 이미 절대경로면 그대로 반환 (개발 환경 호환)
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / p
    return Path(__file__).parent.parent / p


# 프로젝트 루트 경로
if hasattr(sys, '_MEIPASS'):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).parent.parent

# 주요 디렉토리 경로 (상대 경로 문자열로 관리 → resource_path 호환)
MODEL_DIR      = resource_path("model")
ASSETS_DIR     = resource_path("gui/assets")
TEMPLATES_DIR  = resource_path("report/templates")
DATA_DIR       = PROJECT_ROOT / "data"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

# 모델 파일 경로 (나중에 실제 모델 파일로 교체)
LV_SEG_MODEL_PATH = MODEL_DIR / "lv_seg.pt"
TUMOR_SEG_MODEL_PATH = MODEL_DIR / "tumor_seg.pt"

# 설정값
DEFAULT_FRAME_SIZE = (224, 224)  # 전처리 기본 프레임 크기
DEFAULT_FPS = 30  # 기본 FPS (실제 영상에서 추출하거나 설정값 사용)

