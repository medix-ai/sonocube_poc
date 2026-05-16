"""
SonoCube — Clinical Workstation QSS Theme
GE Vivid / Philips EPIQ 계열 의료 영상 소프트웨어 스타일
: warm dark gray, functional color only, minimal decoration
"""

# ── 팔레트 (Clinical Dark Gray) ───────────────────────────────────────────────
BG_BASE    = "#1a1a1a"   # 배경 (warm dark gray, not cool navy)
BG_PANEL   = "#252525"   # 패널 / 사이드바
BG_CARD    = "#2e2e2e"   # 카드 / 컨테이너
BG_INPUT   = "#363636"   # 입력 필드
BG_HOVER   = "#3a3a3a"   # hover 상태

BORDER     = "#404040"   # 표준 테두리
BORDER_LT  = "#505050"   # 밝은 테두리

# Accent — clinical cyan (GE Vivid 스타일)
ACCENT     = "#00b4cc"
ACCENT_HOV = "#00cce6"
ACCENT_DIM = "#007a8c"

# Text
TEXT_PRI   = "#f0f0f0"   # 주요 텍스트 (따뜻한 흰색)
TEXT_SEC   = "#909090"   # 레이블 / 보조
TEXT_DIS   = "#505050"   # 비활성

# EF 참고 색상 (임상 기준선 표시용, 진단 목적 아님)
EF_NORMAL  = "#52c27a"   # ≥55% — 참고 범위 내
EF_MID     = "#e8a217"   # 40-54% — 참고 범위 이하
EF_LOW     = "#e05252"   # <40% — 참고 범위 크게 이하

# Stability
HIGH_CLR   = "#52c27a"
MED_CLR    = "#e8a217"
LOW_CLR    = "#e05252"


def load_style_sheet(theme_name: str = "dark_theme") -> str:
    return _CLINICAL_QSS


def ef_color(ef: float) -> str:
    """EF 수치에 대한 참고 색상 (연구 참고값, 진단 기준 아님)"""
    if ef >= 55:
        return EF_NORMAL
    elif ef >= 40:
        return EF_MID
    return EF_LOW


_CLINICAL_QSS = f"""
/* ── 전체 기반 ──────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRI};
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

/* ── 탭 위젯 ────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {BORDER};
    background-color: {BG_BASE};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_SEC};
    padding: 9px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-size: 12px;
    font-weight: 500;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    color: {TEXT_PRI};
    border-bottom: 2px solid {ACCENT};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_PRI};
    background-color: {BG_PANEL};
}}

/* ── 그룹박스 ───────────────────────────────────────────────────── */
QGroupBox {{
    background-color: transparent;
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 16px;
    padding: 10px 8px 8px 8px;
    color: {TEXT_SEC};
    font-size: 11px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    top: 2px;
    color: {TEXT_SEC};
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 0 4px;
    background-color: {BG_BASE};
}}

/* ── 버튼 ───────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER_LT};
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
    min-height: 26px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {ACCENT_DIM};
    border-color: {ACCENT};
    color: white;
}}
QPushButton:disabled {{
    background-color: {BG_CARD};
    color: {TEXT_DIS};
    border-color: {BORDER};
}}
QPushButton[class="primary"] {{
    background-color: {ACCENT};
    color: #0a0a0a;
    border-color: {ACCENT};
    font-weight: 700;
}}
QPushButton[class="primary"]:hover {{
    background-color: {ACCENT_HOV};
    border-color: {ACCENT_HOV};
}}
QPushButton[class="primary"]:disabled {{
    background-color: {ACCENT_DIM};
    color: #1a3a42;
    border-color: {ACCENT_DIM};
    opacity: 0.5;
}}
QPushButton[class="danger"] {{
    background-color: transparent;
    color: {LOW_CLR};
    border-color: {LOW_CLR};
}}
QPushButton[class="danger"]:hover {{
    background-color: {LOW_CLR};
    color: white;
}}

/* ── 입력 필드 ──────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
    outline: none;
}}
QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    min-height: 22px;
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM};
}}

/* ── 슬라이더 ───────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 3px;
    background-color: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background-color: {ACCENT};
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QSlider::sub-page:horizontal {{
    background-color: {ACCENT_DIM};
    border-radius: 2px;
}}

/* ── 테이블 ─────────────────────────────────────────────────────── */
QTableWidget, QTableView {{
    background-color: {BG_BASE};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    gridline-color: {BORDER};
    selection-background-color: {ACCENT_DIM};
    selection-color: {TEXT_PRI};
    font-size: 12px;
    alternate-background-color: {BG_PANEL};
}}
QTableWidget::item {{
    padding: 6px 10px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {ACCENT_DIM};
}}
QHeaderView::section {{
    background-color: {BG_PANEL};
    color: {TEXT_SEC};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}}

/* ── 리스트 ─────────────────────────────────────────────────────── */
QListWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    font-size: 12px;
    outline: none;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-bottom: 1px solid {BORDER};
}}
QListWidget::item:last {{
    border-bottom: none;
}}
QListWidget::item:selected {{
    background-color: {ACCENT_DIM};
    color: {TEXT_PRI};
    border-left: 2px solid {ACCENT};
}}
QListWidget::item:hover {{
    background-color: {BG_PANEL};
}}

/* ── 스크롤바 ───────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {BG_BASE};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER_LT};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_SEC};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background-color: {BG_BASE};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER_LT};
    border-radius: 3px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── 메뉴바 ─────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {BG_PANEL};
    color: {TEXT_PRI};
    border-bottom: 1px solid {BORDER};
    padding: 1px;
    font-size: 13px;
}}
QMenuBar::item {{
    padding: 5px 10px;
    border-radius: 3px;
}}
QMenuBar::item:selected {{
    background-color: {BG_HOVER};
}}
QMenu {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER_LT};
    border-radius: 4px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    background-color: {ACCENT_DIM};
    color: {TEXT_PRI};
}}
QMenu::separator {{
    height: 1px;
    background-color: {BORDER};
    margin: 4px 8px;
}}

/* ── 툴바 ───────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
    spacing: 4px;
    padding: 4px 10px;
}}
QToolBar::separator {{
    background-color: {BORDER};
    width: 1px;
    margin: 4px 6px;
}}

/* ── 상태바 ─────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {BG_PANEL};
    color: {TEXT_SEC};
    border-top: 1px solid {BORDER};
    font-size: 11px;
    padding: 2px 10px;
}}

/* ── 진행바 ─────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    text-align: center;
    color: {TEXT_SEC};
    font-size: 11px;
    min-height: 14px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 2px;
}}

/* ── QSplitter ──────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── CheckBox ───────────────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT_PRI};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {BORDER_LT};
    border-radius: 3px;
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ── 스크롤 영역 ────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* ── 도크 (필요 시) ─────────────────────────────────────────────── */
QDockWidget {{
    color: {TEXT_PRI};
}}
QDockWidget::title {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
    padding: 5px 10px;
    font-size: 10px;
    font-weight: 600;
    color: {TEXT_SEC};
    text-transform: uppercase;
    letter-spacing: 0.6px;
}}
"""
