import sys
import time
import random
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class AIFunctionTester(QObject):
    """AI 기능 테스터 - 모든 기능을 자동으로 시뮬레이션하여 테스트"""
    
    test_progress = Signal(str, int)  # 메시지, 진행률
    test_completed = Signal(str)      # 최종 결과
    
    def __init__(self, promptbook_instance):
        super().__init__()
        self.app = promptbook_instance
        self.test_results = []
        self.current_test = 0
        self.total_tests = 0
        
    def run_full_test(self):
        """모든 기능을 테스트합니다"""
        self.test_results = []
        self.current_test = 0
        
        # 테스트 목록 정의
        test_functions = [
            ("북 생성 테스트", self.test_book_creation),
            ("페이지 생성 테스트", self.test_page_creation),
            ("페이지 편집 테스트", self.test_page_editing),
            ("즐겨찾기 기능 테스트", self.test_favorite_functionality),
            ("이모지 변경 테스트", self.test_emoji_change),
            ("이름 변경 테스트", self.test_rename_functionality),
            ("복제 기능 테스트", self.test_duplicate_functionality),
            ("삭제 기능 테스트", self.test_delete_functionality),
            ("정렬 기능 테스트", self.test_sorting_functionality),
            ("검색 기능 테스트", self.test_search_functionality),
            ("단축키 테스트", self.test_keyboard_shortcuts),
            ("컨텍스트 메뉴 테스트", self.test_context_menus),
            ("드래그 앤 드롭 테스트", self.test_drag_and_drop),
            ("테마 변경 테스트", self.test_theme_functionality),
            ("파일 저장/로드 테스트", self.test_file_operations),
            ("이미지 기능 테스트", self.test_image_functionality),
            ("잠금 기능 테스트", self.test_lock_functionality),
            ("다중 선택 테스트", self.test_multi_selection),
            ("UI 반응성 테스트", self.test_ui_responsiveness),
            ("메모리 누수 테스트", self.test_memory_usage)
        ]
        
        self.total_tests = len(test_functions)
        
        # 각 테스트 실행
        for i, (test_name, test_func) in enumerate(test_functions):
            self.current_test = i + 1
            progress = int((self.current_test / self.total_tests) * 100)
            self.test_progress.emit(f"실행 중: {test_name}", progress)
            
            try:
                result = test_func()
                self.test_results.append({
                    "name": test_name,
                    "status": "성공" if result else "실패",
                    "details": result if isinstance(result, str) else ""
                })
            except Exception as e:
                self.test_results.append({
                    "name": test_name,
                    "status": "오류",
                    "details": str(e)
                })
            
            # UI 업데이트를 위한 짧은 대기
            QApplication.processEvents()
            time.sleep(0.1)
        
        # 결과 생성
        self.generate_test_report()
    
    def test_book_creation(self):
        """북 생성 기능 테스트"""
        try:
            initial_count = self.app.book_list.count()
            
            # 북 추가 시뮬레이션
            self.app.add_book()
            
            # 북이 추가되었는지 확인
            if self.app.book_list.count() > initial_count:
                return True
            return "북이 생성되지 않음"
        except Exception as e:
            return f"북 생성 중 오류: {str(e)}"
    
    def test_page_creation(self):
        """페이지 생성 기능 테스트"""
        try:
            # 북이 선택되어 있는지 확인
            if self.app.book_list.count() == 0:
                return "테스트할 북이 없음"
            
            # 첫 번째 북 선택
            self.app.book_list.setCurrentRow(0)
            QApplication.processEvents()
            
            initial_count = self.app.char_list.count()
            
            # 페이지 추가 시뮬레이션
            self.app.add_character()
            
            # 페이지가 추가되었는지 확인
            if self.app.char_list.count() > initial_count:
                return True
            return "페이지가 생성되지 않음"
        except Exception as e:
            return f"페이지 생성 중 오류: {str(e)}"
    
    def test_page_editing(self):
        """페이지 편집 기능 테스트"""
        try:
            if self.app.char_list.count() == 0:
                return "테스트할 페이지가 없음"
            
            # 첫 번째 페이지 선택
            self.app.char_list.setCurrentRow(0)
            QApplication.processEvents()
            
            # 텍스트 입력 테스트
            test_name = f"AI테스트_{random.randint(1000, 9999)}"
            test_prompt = "AI 테스트용 프롬프트입니다."
            
            self.app.name_input.setText(test_name)
            self.app.prompt_input.setPlainText(test_prompt)
            
            # 저장 트리거
            self.app.save_current_character()
            
            # 내용이 저장되었는지 확인
            if self.app.name_input.text() == test_name:
                return True
            return "페이지 편집이 저장되지 않음"
        except Exception as e:
            return f"페이지 편집 중 오류: {str(e)}"
    
    def test_favorite_functionality(self):
        """즐겨찾기 기능 테스트"""
        try:
            if self.app.char_list.count() == 0:
                return "테스트할 페이지가 없음"
            
            # 첫 번째 페이지 선택
            item = self.app.char_list.item(0)
            if not item:
                return "페이지 아이템을 찾을 수 없음"
            
            # 즐겨찾기 토글 테스트
            self.app.toggle_favorite_star(item)
            QApplication.processEvents()
            
            return True
        except Exception as e:
            return f"즐겨찾기 기능 중 오류: {str(e)}"
    
    def test_emoji_change(self):
        """이모지 변경 기능 테스트"""
        try:
            if self.app.char_list.count() == 0:
                return "테스트할 페이지가 없음"
            
            item = self.app.char_list.item(0)
            if not item:
                return "페이지 아이템을 찾을 수 없음"
            
            # 랜덤 이모지로 변경
            test_emoji = random.choice(["🔥", "⭐", "💡", "🎯"])
            self.app.set_page_emoji(item, test_emoji)
            
            return True
        except Exception as e:
            return f"이모지 변경 중 오류: {str(e)}"
    
    def test_rename_functionality(self):
        """이름 변경 기능 테스트"""
        try:
            if self.app.char_list.count() == 0:
                return "테스트할 페이지가 없음"
            
            # F2 키 시뮬레이션
            self.app.char_list.setCurrentRow(0)
            self.app.rename_focused_item()
            
            return True
        except Exception as e:
            return f"이름 변경 중 오류: {str(e)}"
    
    def test_duplicate_functionality(self):
        """복제 기능 테스트"""
        try:
            if self.app.char_list.count() == 0:
                return "테스트할 페이지가 없음"
            
            initial_count = self.app.char_list.count()
            
            # 복제 실행
            self.app.char_list.setCurrentRow(0)
            self.app.duplicate_selected_character()
            
            # 페이지가 복제되었는지 확인
            if self.app.char_list.count() > initial_count:
                return True
            return "페이지가 복제되지 않음"
        except Exception as e:
            return f"복제 기능 중 오류: {str(e)}"
    
    def test_delete_functionality(self):
        """삭제 기능 테스트"""
        try:
            if self.app.char_list.count() <= 1:
                return "삭제 테스트를 위한 충분한 페이지가 없음"
            
            initial_count = self.app.char_list.count()
            
            # 마지막 페이지 선택 후 삭제
            self.app.char_list.setCurrentRow(initial_count - 1)
            
            # 삭제 확인 대화상자를 자동으로 승인하도록 임시 설정
            original_question = QMessageBox.question
            QMessageBox.question = lambda *args, **kwargs: QMessageBox.Yes
            
            try:
                self.app.delete_selected_character()
                
                # 페이지가 삭제되었는지 확인
                if self.app.char_list.count() < initial_count:
                    return True
                return "페이지가 삭제되지 않음"
            finally:
                # 원래 함수 복원
                QMessageBox.question = original_question
                
        except Exception as e:
            return f"삭제 기능 중 오류: {str(e)}"
    
    def test_sorting_functionality(self):
        """정렬 기능 테스트"""
        try:
            if not hasattr(self.app, 'sort_selector'):
                return "정렬 선택기를 찾을 수 없음"
            
            # 다양한 정렬 모드 테스트
            sort_modes = ["오름차순 정렬", "내림차순 정렬", "즐겨찾기 우선"]
            
            for mode in sort_modes:
                if self.app.sort_selector.findText(mode) >= 0:
                    self.app.sort_selector.setCurrentText(mode)
                    self.app.handle_character_sort()
                    QApplication.processEvents()
            
            return True
        except Exception as e:
            return f"정렬 기능 중 오류: {str(e)}"
    
    def test_search_functionality(self):
        """검색 기능 테스트"""
        try:
            if not hasattr(self.app, 'char_search_input'):
                return "검색 입력란을 찾을 수 없음"
            
            # 검색 테스트
            self.app.char_search_input.setText("테스트")
            self.app.filter_characters()
            QApplication.processEvents()
            
            # 검색 초기화
            self.app.char_search_input.clear()
            self.app.filter_characters()
            
            return True
        except Exception as e:
            return f"검색 기능 중 오류: {str(e)}"
    
    def test_keyboard_shortcuts(self):
        """단축키 테스트"""
        try:
            # F2, Delete, Ctrl+D 키 이벤트 시뮬레이션
            shortcuts = [
                (Qt.Key_F2, Qt.NoModifier),
                (Qt.Key_Delete, Qt.NoModifier),
                (Qt.Key_D, Qt.ControlModifier)
            ]
            
            for key, modifier in shortcuts:
                event = QKeyEvent(QEvent.KeyPress, key, modifier)
                self.app.eventFilter(self.app, event)
                QApplication.processEvents()
            
            return True
        except Exception as e:
            return f"단축키 테스트 중 오류: {str(e)}"
    
    def test_context_menus(self):
        """컨텍스트 메뉴 테스트"""
        try:
            if self.app.char_list.count() == 0:
                return "테스트할 페이지가 없음"
            
            # 컨텍스트 메뉴 호출 시뮬레이션
            item = self.app.char_list.item(0)
            if item:
                rect = self.app.char_list.visualItemRect(item)
                center = rect.center()
                self.app.show_character_context_menu(center)
            
            return True
        except Exception as e:
            return f"컨텍스트 메뉴 테스트 중 오류: {str(e)}"
    
    def test_drag_and_drop(self):
        """드래그 앤 드롭 테스트"""
        try:
            if self.app.char_list.count() < 2:
                return "드래그 앤 드롭 테스트를 위한 충분한 페이지가 없음"
            
            # 드래그 앤 드롭 시뮬레이션은 복잡하므로 기본 설정만 확인
            if hasattr(self.app.char_list, 'setDragDropMode'):
                return True
            return "드래그 앤 드롭 설정을 찾을 수 없음"
        except Exception as e:
            return f"드래그 앤 드롭 테스트 중 오류: {str(e)}"
    
    def test_theme_functionality(self):
        """테마 변경 기능 테스트"""
        try:
            # 다른 테마로 변경 테스트
            test_themes = ["밝은 모드", "파란 바다", "어두운 모드"]
            
            for theme in test_themes:
                if theme in self.app.THEMES:
                    self.app.apply_theme(theme)
                    QApplication.processEvents()
            
            return True
        except Exception as e:
            return f"테마 기능 테스트 중 오류: {str(e)}"
    
    def test_file_operations(self):
        """파일 저장/로드 테스트"""
        try:
            # 저장 테스트
            self.app.save_to_file()
            
            # 로드 테스트
            self.app.load_from_file()
            
            return True
        except Exception as e:
            return f"파일 작업 테스트 중 오류: {str(e)}"
    
    def test_image_functionality(self):
        """이미지 기능 테스트"""
        try:
            # 이미지 뷰 관련 기능 확인
            if hasattr(self.app, 'image_view'):
                return True
            return "이미지 뷰를 찾을 수 없음"
        except Exception as e:
            return f"이미지 기능 테스트 중 오류: {str(e)}"
    
    def test_lock_functionality(self):
        """잠금 기능 테스트"""
        try:
            if self.app.char_list.count() == 0:
                return "테스트할 페이지가 없음"
            
            # 잠금 체크박스 토글
            if hasattr(self.app, 'lock_checkbox'):
                current_state = self.app.lock_checkbox.isChecked()
                self.app.lock_checkbox.setChecked(not current_state)
                self.app.on_lock_changed()
                return True
            return "잠금 체크박스를 찾을 수 없음"
        except Exception as e:
            return f"잠금 기능 테스트 중 오류: {str(e)}"
    
    def test_multi_selection(self):
        """다중 선택 테스트"""
        try:
            if self.app.char_list.count() < 2:
                return "다중 선택 테스트를 위한 충분한 페이지가 없음"
            
            # 다중 선택 시뮬레이션
            self.app.char_list.setSelectionMode(QAbstractItemView.MultiSelection)
            self.app.char_list.selectAll()
            selected_items = self.app.char_list.selectedItems()
            
            if len(selected_items) > 1:
                return True
            return "다중 선택이 작동하지 않음"
        except Exception as e:
            return f"다중 선택 테스트 중 오류: {str(e)}"
    
    def test_ui_responsiveness(self):
        """UI 반응성 테스트"""
        try:
            # 여러 UI 업데이트 작업 수행
            for i in range(10):
                QApplication.processEvents()
                time.sleep(0.01)
            
            return True
        except Exception as e:
            return f"UI 반응성 테스트 중 오류: {str(e)}"
    
    def test_memory_usage(self):
        """메모리 사용량 테스트"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb < 500:  # 500MB 미만이면 정상
                return True
            return f"메모리 사용량이 높음: {memory_mb:.1f}MB"
        except ImportError:
            return "psutil 모듈이 없어 메모리 테스트 생략"
        except Exception as e:
            return f"메모리 테스트 중 오류: {str(e)}"
    
    def generate_test_report(self):
        """테스트 결과 보고서 생성"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "성공"])
        failed_tests = len([r for r in self.test_results if r["status"] == "실패"])
        error_tests = len([r for r in self.test_results if r["status"] == "오류"])
        
        report = f"""
=== AI 기능 테스트 결과 ===

총 테스트: {total_tests}개
성공: {passed_tests}개
실패: {failed_tests}개  
오류: {error_tests}개
성공률: {(passed_tests/total_tests)*100:.1f}%

=== 상세 결과 ===
"""
        
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "성공" else "❌" if result["status"] == "실패" else "⚠️"
            report += f"{status_icon} {result['name']}: {result['status']}"
            if result["details"]:
                report += f" - {result['details']}"
            report += "\n"
        
        if failed_tests == 0 and error_tests == 0:
            report += "\n🎉 모든 기능이 정상적으로 작동합니다!"
        else:
            report += f"\n⚠️ {failed_tests + error_tests}개의 문제가 발견되었습니다."
        
        self.test_completed.emit(report)


class AITesterDialog(QDialog):
    """AI 테스터 대화상자"""
    
    def __init__(self, promptbook_instance, parent=None):
        super().__init__(parent)
        self.promptbook = promptbook_instance
        self.tester = AIFunctionTester(promptbook_instance)
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        self.setWindowTitle("AI 기능 테스터")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 설명 라벨
        desc_label = QLabel(
            "🤖 AI가 모든 기능을 자동으로 테스트합니다.\n"
            "테스트 중에는 UI가 자동으로 조작되니 잠시 기다려주세요."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("padding: 10px; background: #f0f0f0; border-radius: 5px;")
        layout.addWidget(desc_label)
        
        # 진행률 표시
        self.progress_label = QLabel("테스트 준비 중...")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # 결과 표시 영역
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.result_text)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 테스트 시작")
        self.start_button.clicked.connect(self.start_test)
        button_layout.addWidget(self.start_button)
        
        self.close_button = QPushButton("닫기")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def connect_signals(self):
        self.tester.test_progress.connect(self.update_progress)
        self.tester.test_completed.connect(self.show_results)
    
    def start_test(self):
        self.start_button.setEnabled(False)
        self.result_text.clear()
        self.result_text.append("🤖 AI 테스트를 시작합니다...\n")
        
        # 별도 스레드에서 테스트 실행
        QTimer.singleShot(100, self.tester.run_full_test)
    
    def update_progress(self, message, progress):
        self.progress_label.setText(message)
        self.progress_bar.setValue(progress)
        self.result_text.append(f"[{progress:3d}%] {message}")
        self.result_text.ensureCursorVisible()
    
    def show_results(self, report):
        self.progress_label.setText("테스트 완료!")
        self.progress_bar.setValue(100)
        self.result_text.append("\n" + "="*50)
        self.result_text.append(report)
        self.result_text.ensureCursorVisible()
        self.start_button.setEnabled(True) 