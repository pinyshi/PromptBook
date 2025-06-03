#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
업데이트 다이얼로그
자동 업데이트 기능을 위한 GUI 인터페이스
"""

import os
import sys
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTextEdit, QPushButton, QProgressBar, QMessageBox,
                               QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon
from update_manager import UpdateManager


class UpdateCheckThread(QThread):
    """업데이트 확인 스레드"""
    update_checked = Signal(object)  # 업데이트 정보
    
    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        
    def run(self):
        manager = UpdateManager(self.current_version)
        update_info = manager.check_for_updates()
        self.update_checked.emit(update_info)


class UpdateDownloadThread(QThread):
    """업데이트 다운로드 스레드"""
    progress_updated = Signal(int)  # 진행률
    download_completed = Signal(str)  # 다운로드된 파일 경로
    download_failed = Signal(str)  # 오류 메시지
    
    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url
        
    def run(self):
        manager = UpdateManager("0.0.0")  # 버전은 다운로드에 필요없음
        
        def progress_callback(percent):
            self.progress_updated.emit(percent)
        
        file_path = manager.download_update(self.download_url, progress_callback)
        
        if file_path:
            self.download_completed.emit(file_path)
        else:
            self.download_failed.emit("다운로드에 실패했습니다.")


class UpdateDialog(QDialog):
    """업데이트 다이얼로그"""
    
    def __init__(self, parent=None, current_version="1.0.0"):
        super().__init__(parent)
        self.current_version = current_version
        self.update_info = None
        self.downloaded_file = None
        
        self.setWindowTitle("프롬프트북 업데이트")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        # 아이콘 설정
        if os.path.exists("images/icon.png"):
            self.setWindowIcon(QIcon("images/icon.png"))
        
        self.setup_ui()
        self.check_for_updates()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title_label = QLabel("프롬프트북 업데이트 확인")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 상태 라벨
        self.status_label = QLabel("업데이트를 확인하는 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 버전 정보 프레임
        self.version_frame = QFrame()
        self.version_frame.setVisible(False)
        version_layout = QVBoxLayout(self.version_frame)
        
        self.current_version_label = QLabel(f"현재 버전: v{self.current_version}")
        self.latest_version_label = QLabel("최신 버전: 확인 중...")
        
        version_layout.addWidget(self.current_version_label)
        version_layout.addWidget(self.latest_version_label)
        layout.addWidget(self.version_frame)
        
        # 릴리스 노트
        self.release_notes_label = QLabel("릴리스 노트:")
        self.release_notes_label.setVisible(False)
        layout.addWidget(self.release_notes_label)
        
        self.release_notes = QTextEdit()
        self.release_notes.setVisible(False)
        self.release_notes.setMaximumHeight(150)
        self.release_notes.setReadOnly(True)
        layout.addWidget(self.release_notes)
        
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 스페이서
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        self.update_button = QPushButton("업데이트")
        self.update_button.setVisible(False)
        self.update_button.clicked.connect(self.start_update)
        
        self.later_button = QPushButton("나중에")
        self.later_button.clicked.connect(self.reject)
        
        self.close_button = QPushButton("닫기")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.later_button)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def check_for_updates(self):
        """업데이트 확인"""
        self.check_thread = UpdateCheckThread(self.current_version)
        self.check_thread.update_checked.connect(self.on_update_checked)
        self.check_thread.start()
    
    def on_update_checked(self, update_info):
        """업데이트 확인 완료"""
        if update_info is None:
            self.status_label.setText("업데이트 확인에 실패했습니다.\n인터넷 연결을 확인해주세요.")
            self.later_button.setText("재시도")
            self.later_button.clicked.disconnect()
            self.later_button.clicked.connect(self.check_for_updates)
            
        elif update_info['available']:
            self.update_info = update_info
            self.show_update_available()
            
        else:
            self.status_label.setText("최신 버전을 사용하고 있습니다!")
            self.later_button.setVisible(False)
    
    def show_update_available(self):
        """업데이트 가능 상태 표시"""
        self.status_label.setText("새로운 업데이트가 있습니다!")
        
        # 버전 정보 표시
        self.version_frame.setVisible(True)
        self.latest_version_label.setText(f"최신 버전: v{self.update_info['latest_version']}")
        
        # 릴리스 노트 표시
        if self.update_info.get('release_notes'):
            self.release_notes_label.setVisible(True)
            self.release_notes.setVisible(True)
            self.release_notes.setPlainText(self.update_info['release_notes'])
        
        # 업데이트 버튼 표시
        self.update_button.setVisible(True)
    
    def start_update(self):
        """업데이트 시작"""
        if not self.update_info or not self.update_info.get('download_url'):
            QMessageBox.warning(self, "오류", "다운로드 URL을 찾을 수 없습니다.")
            return
        
        # UI 상태 변경
        self.status_label.setText("업데이트를 다운로드하는 중...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.update_button.setEnabled(False)
        
        # 다운로드 시작
        self.download_thread = UpdateDownloadThread(self.update_info['download_url'])
        self.download_thread.progress_updated.connect(self.on_progress_updated)
        self.download_thread.download_completed.connect(self.on_download_completed)
        self.download_thread.download_failed.connect(self.on_download_failed)
        self.download_thread.start()
    
    def on_progress_updated(self, percent):
        """다운로드 진행률 업데이트"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"업데이트를 다운로드하는 중... ({percent}%)")
    
    def on_download_completed(self, file_path):
        """다운로드 완료"""
        self.downloaded_file = file_path
        self.progress_bar.setValue(100)
        self.status_label.setText("다운로드 완료! 업데이트를 적용하시겠습니까?")
        
        # 버튼 상태 변경
        self.update_button.setText("적용")
        self.update_button.setEnabled(True)
        self.update_button.clicked.disconnect()
        self.update_button.clicked.connect(self.apply_update)
    
    def on_download_failed(self, error_message):
        """다운로드 실패"""
        self.status_label.setText(f"다운로드 실패: {error_message}")
        self.progress_bar.setVisible(False)
        self.update_button.setEnabled(True)
    
    def apply_update(self):
        """업데이트 적용"""
        if not self.downloaded_file:
            return
        
        reply = QMessageBox.question(
            self, 
            "업데이트 적용", 
            "업데이트를 적용하면 프롬프트북이 재시작됩니다.\n계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.status_label.setText("업데이트를 적용하는 중...")
            
            # 업데이트 적용
            manager = UpdateManager(self.current_version)
            
            # 압축 해제
            update_folder = manager.extract_update(self.downloaded_file)
            if not update_folder:
                QMessageBox.critical(self, "오류", "업데이트 파일 압축 해제에 실패했습니다.")
                return
            
            # 업데이트 적용
            if manager.apply_update(update_folder):
                # 재시작 시도
                restart_success = manager.restart_application()
                
                if restart_success is False:
                    # 개발 환경에서 수동 재시작 안내
                    QMessageBox.information(
                        self, 
                        "업데이트 완료", 
                        "업데이트가 성공적으로 적용되었습니다!\n\n"
                        "개발 환경에서는 자동 재시작이 지원되지 않습니다.\n"
                        "프로그램을 종료하고 다시 실행해주세요."
                    )
                    self.accept()  # 다이얼로그 닫기
                else:
                    # 빌드 환경에서 자동 재시작
                    QMessageBox.information(self, "완료", "업데이트가 적용되었습니다.\n프롬프트북을 재시작합니다.")
            else:
                QMessageBox.critical(self, "오류", "업데이트 적용에 실패했습니다.")


def show_update_dialog(parent=None, current_version="1.0.0"):
    """업데이트 다이얼로그 표시"""
    dialog = UpdateDialog(parent, current_version)
    return dialog.exec()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 테스트용 다이얼로그
    dialog = UpdateDialog(None, "2.3.5")  # 낮은 버전으로 테스트
    dialog.show()
    
    sys.exit(app.exec()) 