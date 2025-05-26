#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import random
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class ManualTester:
    """수동 테스트를 위한 도구들"""
    
    def __init__(self):
        self.test_data = {
            "book_names": ["소설 아이디어", "캐릭터 설정", "세계관 설정", "대화 스타일", "플롯 구조"],
            "page_names": ["주인공", "조연", "악역", "멘토", "라이벌"],
            "prompts": [
                "당신은 창의적인 소설가입니다. 독창적인 스토리를 만들어주세요.",
                "캐릭터의 성격과 배경을 자세히 설명해주세요.",
                "이 세계의 독특한 규칙과 문화를 설명해주세요.",
                "자연스럽고 매력적인 대화를 작성해주세요.",
                "흥미진진한 플롯 전개를 제안해주세요."
            ],
            "emojis": ["📚", "👤", "🌍", "💬", "📖", "⭐", "🔥", "💡", "🎯", "✨"]
        }
    
    def create_test_books(self, count=5):
        """테스트용 북들을 생성합니다"""
        print(f"📚 {count}개의 테스트 북을 생성합니다...")
        for i in range(count):
            book_name = f"{random.choice(self.test_data['book_names'])} {i+1}"
            print(f"  - {book_name}")
    
    def create_test_pages(self, count=10):
        """테스트용 페이지들을 생성합니다"""
        print(f"📄 {count}개의 테스트 페이지를 생성합니다...")
        for i in range(count):
            page_name = f"{random.choice(self.test_data['page_names'])} {i+1}"
            prompt = random.choice(self.test_data['prompts'])
            emoji = random.choice(self.test_data['emojis'])
            print(f"  - {emoji} {page_name}")
    
    def test_clipboard_operations(self):
        """클립보드 기능 테스트"""
        print("📋 클립보드 기능 테스트:")
        print("  1. 페이지 선택 후 Ctrl+C (복사)")
        print("  2. 다른 북 선택 후 Ctrl+V (붙여넣기)")
        print("  3. 페이지 선택 후 Ctrl+X (잘라내기)")
        print("  4. 다른 북 선택 후 Ctrl+V (붙여넣기)")
        print("  5. 다중 선택 후 복사/잘라내기 테스트")
    
    def test_keyboard_shortcuts(self):
        """키보드 단축키 테스트"""
        print("⌨️ 키보드 단축키 테스트:")
        shortcuts = {
            "Ctrl+N": "새 북 생성",
            "Ctrl+Shift+N": "새 페이지 생성",
            "Ctrl+D": "복제",
            "Delete": "삭제",
            "F2": "이름 변경",
            "Ctrl+F": "검색",
            "Ctrl+S": "저장",
            "Ctrl+C": "복사",
            "Ctrl+X": "잘라내기",
            "Ctrl+V": "붙여넣기",
            "F11": "전체화면",
            "Ctrl+T": "테마 변경"
        }
        for key, action in shortcuts.items():
            print(f"  - {key}: {action}")
    
    def test_context_menus(self):
        """컨텍스트 메뉴 테스트"""
        print("🖱️ 컨텍스트 메뉴 테스트:")
        print("  북 우클릭 메뉴:")
        print("    - 새 페이지 추가, 이름 변경, 복제, 삭제, 붙여넣기")
        print("  페이지 우클릭 메뉴:")
        print("    - 복제, 삭제, 이름 변경, 즐겨찾기, 잠금, 복사, 잘라내기")
        print("  이모지 우클릭 메뉴:")
        print("    - 이모지 변경")
    
    def test_sorting_and_search(self):
        """정렬 및 검색 기능 테스트"""
        print("🔍 정렬 및 검색 기능 테스트:")
        print("  1. 오름차순/내림차순 정렬 버튼 클릭")
        print("  2. 즐겨찾기 우선 정렬 테스트")
        print("  3. 검색창에 키워드 입력")
        print("  4. 검색 결과 확인")
        print("  5. 검색 초기화")
    
    def test_theme_and_ui(self):
        """테마 및 UI 테스트"""
        print("🎨 테마 및 UI 테스트:")
        print("  1. 다크/라이트 테마 전환")
        print("  2. 창 크기 조절")
        print("  3. 스플리터 위치 조절")
        print("  4. 전체화면 모드")
        print("  5. 버튼 호버 효과 확인")
    
    def test_data_persistence(self):
        """데이터 지속성 테스트"""
        print("💾 데이터 지속성 테스트:")
        print("  1. 데이터 생성 후 애플리케이션 종료")
        print("  2. 애플리케이션 재시작")
        print("  3. 데이터 복원 확인")
        print("  4. 설정 값 유지 확인")
    
    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        print("⚠️ 엣지 케이스 테스트:")
        print("  1. 매우 긴 이름 입력")
        print("  2. 특수 문자 포함 이름")
        print("  3. 빈 이름으로 저장 시도")
        print("  4. 대량의 텍스트 입력")
        print("  5. 동일한 이름 중복 생성")
        print("  6. 잠긴 페이지 편집 시도")
    
    def run_stress_test(self):
        """스트레스 테스트"""
        print("🔥 스트레스 테스트:")
        print("  1. 대량의 북/페이지 생성 (100개+)")
        print("  2. 빠른 연속 클릭")
        print("  3. 메모리 사용량 모니터링")
        print("  4. 응답 시간 측정")
    
    def show_test_menu(self):
        """테스트 메뉴 표시"""
        print("\n" + "="*60)
        print("🧪 PromptBook 수동 테스트 도구")
        print("="*60)
        print("1. 📚 테스트 데이터 생성")
        print("2. 📋 클립보드 기능 테스트")
        print("3. ⌨️ 키보드 단축키 테스트")
        print("4. 🖱️ 컨텍스트 메뉴 테스트")
        print("5. 🔍 정렬 및 검색 테스트")
        print("6. 🎨 테마 및 UI 테스트")
        print("7. 💾 데이터 지속성 테스트")
        print("8. ⚠️ 엣지 케이스 테스트")
        print("9. 🔥 스트레스 테스트")
        print("0. 종료")
        print("="*60)

def main():
    tester = ManualTester()
    
    while True:
        tester.show_test_menu()
        choice = input("\n테스트할 항목을 선택하세요 (0-9): ").strip()
        
        if choice == "0":
            print("테스트를 종료합니다.")
            break
        elif choice == "1":
            tester.create_test_books()
            tester.create_test_pages()
        elif choice == "2":
            tester.test_clipboard_operations()
        elif choice == "3":
            tester.test_keyboard_shortcuts()
        elif choice == "4":
            tester.test_context_menus()
        elif choice == "5":
            tester.test_sorting_and_search()
        elif choice == "6":
            tester.test_theme_and_ui()
        elif choice == "7":
            tester.test_data_persistence()
        elif choice == "8":
            tester.test_edge_cases()
        elif choice == "9":
            tester.run_stress_test()
        else:
            print("잘못된 선택입니다.")
        
        input("\nEnter를 눌러 계속...")

if __name__ == "__main__":
    main() 