"""SonoCube PoC — 메인 진입점"""
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from utils.constants import APP_NAME, APP_VERSION
from utils.logger import get_logger


def main():
    log = get_logger("sonocube")
    log.info(f"Application started — {APP_NAME} v{APP_VERSION}")

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

