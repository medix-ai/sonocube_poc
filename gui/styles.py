"""SonoCube v1.2 — 전문가형 dark navy QSS 테마 (인라인, 파일 I/O 없음)"""


# ── 팔레트 ────────────────────────────────────────────────────────────────────
# Background
BG_BASE    = "#0d1117"   # 최외곽 배경
BG_PANEL   = "#161b22"   # 패널 / 도크
BG_CARD    = "#1c2128"   # 카드 / 그룹박스
BG_INPUT   = "#21262d"   # 입력 필드

# Border
BORDER     = "#30363d"
BORDER_LT  = "#3d444d"

# Accent
ACCENT     = "#1f6feb"   # primary blue
ACCENT_HOV = "#388bfd"
CYAN       = "#58a6ff"

# Text
TEXT_PRI   = "#e6edf3"
TEXT_SEC   = "#8b949e"
TEXT_DIS   = "#484f58"

# Status
HIGH_CLR   = "#3fb950"   # High confidence / success
MED_CLR    = "#d29922"   # Medium / warning
LOW_CLR    = "#f85149"   # Low confidence / error


def load_style_sheet(theme_name: str = "dark_theme") -> str:
    """테마 이름과 무관하게 항상 내장 테마 반환 (파일 의존 제거)"""
    return _DARK_NAVY_QSS


_DARK_NAVY_QSS = f"""
/* ── 전체 기반 ──────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRI};
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

/* ── 탭 위젯 ────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG_PANEL};
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: {BG_CARD};
    color: {TEXT_SEC};
    padding: 8px 20px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-size: 12px;
    font-weight: 500;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    background-color: {BG_PANEL};
    color: {TEXT_PRI};
    border-color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background-color: {BG_PANEL};
    color: {TEXT_PRI};
}}

/* ── 그룹박스 (카드) ────────────────────────────────────────────── */
QGroupBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 18px;
    padding: 10px 8px 8px 8px;
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_SEC};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 2px;
    color: {TEXT_SEC};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── 버튼 ───────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER_LT};
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {BG_INPUT};
    border-color: {CYAN};
    color: {TEXT_PRI};
}}
QPushButton:pressed {{
    background-color: {ACCENT};
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
    color: white;
    border-color: {ACCENT};
    font-weight: 600;
}}
QPushButton[class="primary"]:hover {{
    background-color: {ACCENT_HOV};
    border-color: {ACCENT_HOV};
}}
QPushButton[class="primary"]:disabled {{
    background-color: #1a3a5c;
    color: #4a6a8a;
    border-color: #1a3a5c;
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
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 8px;
    min-height: 24px;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}

/* ── 슬라이더 ───────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background-color: {CYAN};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background-color: {ACCENT};
    border-radius: 2px;
}}

/* ── 테이블 ─────────────────────────────────────────────────────── */
QTableWidget, QTableView {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    gridline-color: {BORDER};
    selection-background-color: {ACCENT};
    selection-color: white;
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {BORDER};
}}
QTableWidget::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QHeaderView::section {{
    background-color: {BG_BASE};
    color: {TEXT_SEC};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}}

/* ── 리스트 ─────────────────────────────────────────────────────── */
QListWidget {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-size: 12px;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {BORDER};
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QListWidget::item:hover {{
    background-color: {BG_INPUT};
}}

/* ── 스크롤바 ───────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {BG_PANEL};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER_LT};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_SEC};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {BG_PANEL};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER_LT};
    border-radius: 4px;
    min-width: 30px;
}}

/* ── 메뉴바 ─────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {BG_BASE};
    color: {TEXT_PRI};
    border-bottom: 1px solid {BORDER};
    padding: 2px;
    font-size: 13px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {BG_CARD};
}}
QMenu {{
    background-color: {BG_CARD};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background-color: {BORDER};
    margin: 4px 8px;
}}

/* ── 툴바 ───────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {BG_BASE};
    border-bottom: 1px solid {BORDER};
    spacing: 4px;
    padding: 4px 8px;
}}
QToolBar::separator {{
    background-color: {BORDER};
    width: 1px;
    margin: 4px 6px;
}}

/* ── 도크 ───────────────────────────────────────────────────────── */
QDockWidget {{
    color: {TEXT_PRI};
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background-color: {BG_BASE};
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_SEC};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── 상태바 ─────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {BG_BASE};
    color: {TEXT_SEC};
    border-top: 1px solid {BORDER};
    font-size: 11px;
    padding: 2px 8px;
}}

/* ── 진행바 ─────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    color: {TEXT_PRI};
    font-size: 11px;
    min-height: 16px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}

/* ── 분리자 ─────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}

/* ── 라벨 클래스 ────────────────────────────────────────────────── */
QLabel[class="title"] {{
    color: {TEXT_PRI};
    font-size: 16px;
    font-weight: 700;
}}
QLabel[class="subtitle"] {{
    color: {TEXT_SEC};
    font-size: 12px;
}}
QLabel[class="stat-value"] {{
    color: {CYAN};
    font-size: 28px;
    font-weight: 700;
}}
QLabel[class="stat-label"] {{
    color: {TEXT_SEC};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}}
QLabel[class="metric"] {{
    color: {TEXT_PRI};
    font-size: 14px;
    font-weight: 600;
}}
QLabel[class="metric-label"] {{
    color: {TEXT_SEC};
    font-size: 12px;
}}
QLabel[class="disclaimer"] {{
    color: {MED_CLR};
    font-size: 11px;
    font-weight: 600;
}}
QLabel[class="warning"] {{
    color: {LOW_CLR};
    font-size: 11px;
    font-weight: 600;
}}
QLabel[class="success"] {{
    color: {HIGH_CLR};
    font-size: 11px;
    font-weight: 600;
}}
QLabel[class="section-header"] {{
    color: {TEXT_SEC};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── CheckBox ───────────────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT_PRI};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_LT};
    border-radius: 3px;
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
"""
