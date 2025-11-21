"""
SonoCube PoC 메인 진입점
"""
import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """애플리케이션 실행"""
    app = QApplication(sys.argv)
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

