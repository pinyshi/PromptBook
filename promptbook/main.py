import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from promptbook.main_window import MainWindow
from promptbook.state import State
from promptbook.utils.file_utils import get_app_data_dir

def setup_app():
    """애플리케이션 초기 설정을 수행합니다."""
    # 앱 데이터 디렉토리 생성
    app_dir = get_app_data_dir()
    os.makedirs(app_dir, exist_ok=True)
    
    # 이미지 저장 디렉토리 생성
    images_dir = os.path.join(app_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # 백업 디렉토리 생성
    backup_dir = os.path.join(app_dir, "backup")
    os.makedirs(backup_dir, exist_ok=True)

def main():
    """프로그램의 메인 함수입니다."""
    # QApplication 인스턴스 생성
    app = QApplication(sys.argv)
    
    # 앱 정보 설정
    app.setApplicationName("PromptBook")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PinyShi")
    app.setOrganizationDomain("pinyshibook.com")
    
    # 앱 스타일 설정
    app.setStyle("Fusion")
    
    # 초기 설정
    setup_app()
    
    # 메인 윈도우 생성
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 시작
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 