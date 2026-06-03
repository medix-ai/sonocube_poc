"""SonoCube PoC — 메인 진입점"""
import os
import sys
import traceback

# PyInstaller 패키징 환경에서 matplotlib이 MacOSX 백엔드를 선택하면
# Qt5Agg 위젯과 충돌하므로 Agg로 강제 지정
os.environ.setdefault("MPLBACKEND", "Agg")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from utils.constants import APP_NAME, APP_VERSION
from utils.logger import get_logger


def _install_excepthook(log):
    """PyQt5 슬롯에서 발생한 미처리 예외를 qFatal 대신 다이얼로그로 처리."""
    def handler(exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log.error(f"Unhandled exception:\n{msg}")
        try:
            dlg = QMessageBox()
            dlg.setIcon(QMessageBox.Critical)
            dlg.setWindowTitle("Unexpected Error")
            dlg.setText(str(exc_value))
            dlg.setDetailedText(msg)
            dlg.exec_()
        except Exception:
            pass
    sys.excepthook = handler


def main():
    log = get_logger("sonocube")
    log.info(f"Application started — {APP_NAME} v{APP_VERSION}")
    _install_excepthook(log)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("SonoCube")

    from gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    code = app.exec_()
    log.info("Application exited")
    sys.exit(code)


if __name__ == "__main__":
    main()

