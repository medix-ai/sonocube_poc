"""
스타일시트 로드 유틸리티
"""
from pathlib import Path
from utils.spec import resource_path


def load_style_sheet(theme_name: str = "dark_theme") -> str:
    """
    스타일시트 파일 로드
    
    Args:
        theme_name: 테마 이름 (파일명에서 .qss 제외)
        
    Returns:
        스타일시트 문자열
    """
    style_path = resource_path(f"gui/assets/{theme_name}.qss")
    
    if not style_path.exists():
        # 기본 스타일시트 반환
        return get_default_style()
    
    try:
        with open(style_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not load style sheet: {e}")
        return get_default_style()


def get_default_style() -> str:
    """기본 스타일시트 반환"""
    return """
    QMainWindow {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    QPushButton {
        background-color: #3d3d3d;
        color: #e0e0e0;
        border: 1px solid #4d4d4d;
        border-radius: 4px;
        padding: 6px 12px;
    }
    QPushButton:hover {
        background-color: #4d4d4d;
    }
    QLabel {
        color: #e0e0e0;
    }
    QGroupBox {
        background-color: #252526;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        color: #e0e0e0;
    }
    """

