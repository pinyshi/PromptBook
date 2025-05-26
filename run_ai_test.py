#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# main.py가 있는 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import PromptBookApp
from ai_tester import AITesterDialog

def run_ai_test():
    """AI 테스터를 실행합니다"""
    app = QApplication(sys.argv)
    
    # PromptBook 애플리케이션 인스턴스 생성
    promptbook = PromptBookApp()
    promptbook.show()
    
    # 애플리케이션이 완전히 로드될 때까지 잠시 대기
    def start_ai_test():
        try:
            # AI 테스터 대화상자 생성 및 실행
            ai_tester_dialog = AITesterDialog(promptbook, promptbook)
            ai_tester_dialog.show()
            
            # 자동으로 테스트 시작
            QTimer.singleShot(1000, ai_tester_dialog.start_test)
            
        except Exception as e:
            print(f"AI 테스터 실행 중 오류: {e}")
    
    # 1초 후 AI 테스터 시작
    QTimer.singleShot(1000, start_ai_test)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    print("🤖 AI 테스터를 시작합니다...")
    print("=" * 50)
    run_ai_test() 