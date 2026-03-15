"""
SonoCube PoC 메인 진입점
"""
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from gui.main_window import MainWindow


def main():
    """애플리케이션 실행"""
    # 고해상도 디스플레이 지원
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("SonoCube PoC")
    app.setOrganizationName("SonoCube")
    app.setApplicationVersion("1.0.0")
    
    # 예외 처리 설정
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 메인 윈도우 생성 및 표시
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"Application error: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"Application failed to start:\n{str(e)}\n\nPlease check the logs."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

