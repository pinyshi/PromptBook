import sys
import os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

def get_app_directory():
    """실행 파일의 디렉토리를 반환합니다."""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 exe 파일인 경우
        return os.path.dirname(sys.executable)
    else:
        # 개발 환경에서 실행하는 경우
        return os.path.dirname(os.path.abspath(__file__))

class CustomTextEdit(QTextEdit):
    """메모장 스타일의 자동완성 텍스트 에디트 (프롬프트북 로직 적용)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._completer = None
        self.prompt_display_map = {}
        
        # 텍스트 에디트 설정
        self.setAcceptRichText(False)  # 서식 있는 텍스트 비활성화
        self.setLineWrapMode(QTextEdit.WidgetWidth)  # 자동 줄바꿈 활성화
        self.setWordWrapMode(QTextOption.WrapAnywhere)  # 어디서든 줄바꿈 (텍스트 위주)
        
    def set_custom_completer(self, completer):
        """자동 완성기를 설정합니다."""
        if self._completer:
            self._completer.disconnect(self)
            
        self._completer = completer
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.activated.connect(self.insert_completion)
        
        # 텍스트 변경 시 자동완성 업데이트 연결
        self.textChanged.connect(self.update_completion)
        
    def update_completion(self):
        """자동 완성을 업데이트합니다. (현재 줄 기준으로 처리)"""
        if not self._completer:
            return
            
        # 포커스 체크 - 포커스가 없으면 팝업 숨기기
        if QApplication.focusWidget() != self:
            self._completer.popup().hide()
            return
            
        # 현재 커서와 줄 정보 가져오기
        cursor = self.textCursor()
        current_pos = cursor.position()
        
        # 현재 줄의 시작 위치와 텍스트 가져오기
        temp_cursor = QTextCursor(cursor)
        temp_cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        line_start_pos = temp_cursor.selectionStart()
        line_text = temp_cursor.selectedText()
        
        # 현재 줄에서 커서 위치까지의 텍스트
        text_before_cursor = line_text[:current_pos - line_start_pos]
        last_comma = text_before_cursor.rfind(",")
        
        if last_comma >= 0:
            text = text_before_cursor[last_comma + 1:].strip()
            prefix_start_pos = line_start_pos + last_comma + 1
        else:
            text = text_before_cursor.strip()
            prefix_start_pos = line_start_pos
            
        # 빈 텍스트이거나 공백만 있는 경우 팝업 숨기기
        if not text:
            self._completer.popup().hide()
            return
            
        # 자동완성 업데이트
        self._completer.setCompletionPrefix(text)
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        
        # 공백 건너뛰기
        while prefix_start_pos < current_pos and self.toPlainText()[prefix_start_pos].isspace():
            prefix_start_pos += 1
        
        # 팝업 위치 계산을 위한 임시 커서
        temp_cursor = QTextCursor(self.document())
        temp_cursor.setPosition(prefix_start_pos)
        
        # 팝업 위치 및 크기 설정
        rect = self.cursorRect(temp_cursor)
        popup_width = popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width()
        popup_height = min(popup.sizeHint().height(), 200)  # 최대 높이 제한
        
        # 커서 위치의 전역 좌표
        cursor_global_pos = self.mapToGlobal(rect.bottomLeft())
        
        # 화면 크기 가져오기
        screen = QApplication.primaryScreen().geometry()
        
        # 아래쪽에 팝업을 표시할 공간이 충분한지 확인
        space_below = screen.bottom() - cursor_global_pos.y()
        space_above = cursor_global_pos.y() - screen.top()
        
        # 팝업 위치 결정
        if space_below >= popup_height + 10:  # 아래쪽에 충분한 공간이 있으면
            popup_pos = cursor_global_pos
            popup_pos.setY(popup_pos.y() + 5)  # 커서 아래 5픽셀 여백
        elif space_above >= popup_height + 10:  # 위쪽에 충분한 공간이 있으면
            popup_pos = self.mapToGlobal(rect.topLeft())
            popup_pos.setY(popup_pos.y() - popup_height - 5)  # 커서 위 5픽셀 여백
        else:  # 공간이 부족하면 아래쪽에 표시하되 화면 안에 맞춤
            popup_pos = cursor_global_pos
            popup_pos.setY(min(popup_pos.y() + 5, screen.bottom() - popup_height))
        
        # X 좌표도 화면 안에 맞춤
        popup_pos.setX(min(popup_pos.x(), screen.right() - popup_width))
        popup_pos.setX(max(popup_pos.x(), screen.left()))
        
        # 팝업 표시 위치 조정 (비동기로 처리)
        QTimer.singleShot(0, lambda: (
            popup.move(popup_pos),
            popup.show(),
            popup.raise_()
        ))
        
    def insert_completion(self, completion):
        """자동 완성 텍스트를 삽입합니다. (QTextEdit 커서 위치 보존)"""
        # 실제로 삽입할 텍스트 (매핑된 값이 있으면 사용)
        insert_text = self.prompt_display_map.get(completion, completion)
        
        # 현재 커서 가져오기
        cursor = self.textCursor()
        current_pos = cursor.position()
        
        # 현재 줄의 시작 위치 찾기
        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        line_start_pos = cursor.selectionStart()
        line_text = cursor.selectedText()
        
        # 커서를 원래 위치로 복원
        cursor.setPosition(current_pos)
        
        # 현재 줄에서 마지막 쉼표 위치 찾기
        text_before_cursor = line_text[:current_pos - line_start_pos]
        last_comma = text_before_cursor.rfind(",")
        
        if last_comma >= 0:
            # 쉼표 이후의 텍스트 선택하여 교체
            start_pos = line_start_pos + last_comma + 1
            # 공백 건너뛰기
            while start_pos < current_pos and self.toPlainText()[start_pos].isspace():
                start_pos += 1
            
            # 교체할 범위 선택
            cursor.setPosition(start_pos)
            cursor.setPosition(current_pos, QTextCursor.KeepAnchor)
            
            # 선택된 텍스트를 자동완성 텍스트로 교체하고 쉼표 추가
            cursor.insertText(insert_text + ", ")
        else:
            # 현재 줄의 시작부터 커서까지 선택하여 교체
            cursor.setPosition(line_start_pos)
            cursor.setPosition(current_pos, QTextCursor.KeepAnchor)
            cursor.insertText(insert_text + ", ")
        
        # 커서 위치는 insertText 후 자동으로 적절한 위치에 설정됨
        
    def keyPressEvent(self, event):
        """키 입력 이벤트 처리"""
        # 자동완성 팝업이 표시되어 있을 때의 키 처리
        if self._completer and self._completer.popup().isVisible():
            # Enter, Return, Tab 키로 자동 완성 선택
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                self._completer.popup().setCurrentIndex(self._completer.popup().currentIndex())
                self.insert_completion(self._completer.currentCompletion())
                self._completer.popup().hide()
                return
            # Escape 키로 자동완성 팝업 닫기
            elif event.key() == Qt.Key_Escape:
                self._completer.popup().hide()
                return
            
        super().keyPressEvent(event)


class PromptInput(QMainWindow):
    """프롬프트 입력기 메인 윈도우"""
    
    VERSION = "v1.0"
    
    def __init__(self):
        super().__init__()
        # 창 고정 상태 변수
        self.always_on_top = False
        
        # PyInstaller 임시 폴더 정리 에러 무시 설정
        self.suppress_temp_cleanup_errors()
        
        self.setup_ui()
        self.setup_autocomplete()
        self.setup_shortcuts()
        
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle(f"프롬프트 입력기 {self.VERSION}")
        self.setFixedSize(600, 300)
        
        # 아이콘 설정 (PyInstaller 리소스 포함)
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 exe에서는 임시 폴더의 아이콘 사용
                icon_path = os.path.join(sys._MEIPASS, "icon.ico")
                if os.path.exists(icon_path):
                    self.setWindowIcon(QIcon(icon_path))
                else:
                    print("[DEBUG] 내장된 아이콘 파일을 찾을 수 없습니다.")
            else:
                # 개발 환경에서는 로컬 아이콘 파일 사용
                if os.path.exists("icon.ico"):
                    self.setWindowIcon(QIcon("icon.ico"))
                elif os.path.exists("icon.png"):
                    self.setWindowIcon(QIcon("icon.png"))
                else:
                    print("[DEBUG] 개발 환경: 아이콘 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"[DEBUG] 아이콘 설정 실패: {e}")
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 레이아웃
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 프롬프트 입력란 (메모장 스타일 텍스트 에디트)
        self.prompt_input = CustomTextEdit()
        self.prompt_input.setPlaceholderText("프롬프트를 쉼표로 구분해서 입력하세요.")
        self.prompt_input.setMinimumHeight(200)
        layout.addWidget(self.prompt_input)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 복사 버튼
        self.copy_button = QPushButton("📋 복사")
        self.copy_button.clicked.connect(self.copy_prompt_to_clipboard)
        self.copy_button.setMinimumHeight(35)
        self.copy_button.setToolTip("프롬프트를 클립보드에 복사합니다 (Ctrl+Shift+C)")
        button_layout.addWidget(self.copy_button)
        
        # 창 고정 버튼
        self.pin_button = QPushButton("📌 맨 위에 고정")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(self.always_on_top)
        self.pin_button.clicked.connect(self.toggle_always_on_top)
        self.pin_button.setMinimumHeight(35)
        self.pin_button.setToolTip("창을 다른 모든 창 위에 고정합니다 (Ctrl+T)")
        button_layout.addWidget(self.pin_button)
        
        layout.addLayout(button_layout)
        
        # 상태바
        self.statusBar().showMessage("프롬프트를 입력하고 복사 버튼을 클릭하세요.")
        
    def setup_autocomplete(self):
        """자동완성 설정 (프롬프트북과 완전히 동일)"""
        try:
            autocomplete_path = os.path.join(get_app_directory(), "autocomplete.txt")
            with open(autocomplete_path, 'r', encoding='utf-8') as f:
                prompts = [line.strip() for line in f if line.strip()]
            completer = QCompleter(prompts)
            self.prompt_input.set_custom_completer(completer)
            self.statusBar().showMessage(f"자동완성 목록 로드 완료 ({len(prompts)}개 항목)")
        except Exception as e:
            print(f"자동완성 목록 로드 실패: {e}")
            # 기본 자동완성 목록 사용
            default_prompts = ["masterpiece", "best quality", "ultra-detailed", "8k uhd", "highres"]
            completer = QCompleter(default_prompts)
            self.prompt_input.set_custom_completer(completer)
            self.statusBar().showMessage("기본 자동완성 목록 사용 중")
    
    def copy_prompt_to_clipboard(self):
        """프롬프트를 클립보드에 복사 (프롬프트북과 동일)"""
        QApplication.clipboard().setText(self.prompt_input.toPlainText())
        QToolTip.showText(self.copy_button.mapToGlobal(self.copy_button.rect().center()), "프롬프트가 복사되었습니다.")
    
    def setup_shortcuts(self):
        """단축키 설정"""
        # 창 고정 단축키 (Ctrl+T)
        pin_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        pin_shortcut.activated.connect(self.toggle_always_on_top)
        
        # 복사 단축키 (Ctrl+C는 기본 복사와 겹치므로 Ctrl+Shift+C 사용)
        copy_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        copy_shortcut.activated.connect(self.copy_prompt_to_clipboard)
    
    def toggle_always_on_top(self):
        """창 맨 위에 고정 토글"""
        self.always_on_top = not self.always_on_top
        
        # 버튼 상태 업데이트
        self.pin_button.setChecked(self.always_on_top)
        
        if self.always_on_top:
            # 맨 위에 고정 플래그 추가 (기본 플래그 유지)
            new_flags = Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowStaysOnTopHint
            self.pin_button.setText("📌 맨 위에 고정됨")
        else:
            # 맨 위에 고정 플래그 제거 (기본 플래그만 유지)
            new_flags = Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint
            self.pin_button.setText("📌 맨 위에 고정")
        
        # 창 플래그 업데이트
        self.setWindowFlags(new_flags)
        
        # 창을 다시 표시 (플래그 변경 후 필요)
        self.show()
        
        # 상태 메시지 표시
        status_text = "활성화" if self.always_on_top else "비활성화"
        self.statusBar().showMessage(f"창 맨 위에 고정: {status_text}")
        print(f"[DEBUG] 프롬프트 입력기 - 창 맨 위에 고정: {status_text}")
    
    def suppress_temp_cleanup_errors(self):
        """PyInstaller 임시 폴더 정리 에러를 무시하도록 설정"""
        try:
            import tempfile
            import atexit
            import warnings
            
            # 임시 폴더 관련 경고 무시
            warnings.filterwarnings("ignore", category=ResourceWarning)
            warnings.filterwarnings("ignore", message=".*temporary directory.*")
            
            # PyInstaller 관련 임시 폴더 정리 에러 무시
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller 환경에서 실행 중일 때
                original_cleanup = tempfile._cleanup
                
                def silent_cleanup(*args, **kwargs):
                    try:
                        return original_cleanup(*args, **kwargs)
                    except (OSError, PermissionError, FileNotFoundError):
                        # 임시 폴더 정리 에러 무시
                        pass
                
                tempfile._cleanup = silent_cleanup
                
                # atexit 핸들러도 에러 무시하도록 수정
                def silent_exit_handler():
                    try:
                        # 기존 atexit 핸들러들 실행
                        pass
                    except (OSError, PermissionError, FileNotFoundError):
                        # 종료 시 임시 폴더 정리 에러 무시
                        pass
                
                atexit.register(silent_exit_handler)
                
        except Exception as e:
            # 에러 무시 설정 자체가 실패해도 프로그램은 계속 실행
            print(f"[DEBUG] 임시 폴더 에러 무시 설정 실패: {e}")


class LogDialog(QDialog):
    """로그 표시용 팝업 대화상자"""
    
    def __init__(self, title, message, details=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(500, 400)
        
        # 레이아웃
        layout = QVBoxLayout(self)
        
        # 메인 메시지
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(message_label)
        
        # 상세 정보 (있는 경우)
        if details:
            details_text = QTextEdit()
            details_text.setPlainText(details)
            details_text.setReadOnly(True)
            details_text.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 10px;")
            layout.addWidget(details_text)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)
        close_button.setMinimumWidth(80)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)

def show_error_popup(title, message, details=None):
    """오류 팝업창 표시"""
    try:
        app = QApplication.instance()
        if app is not None:
            dialog = LogDialog(title, message, details)
            dialog.exec()
        else:
            # GUI가 없는 경우 콘솔에 출력
            print(f"{title}: {message}")
            if details:
                print(f"상세 정보:\n{details}")
    except Exception as e:
        # 팝업 표시 실패 시 콘솔에 출력
        print(f"{title}: {message}")
        if details:
            print(f"상세 정보:\n{details}")
        print(f"팝업 표시 실패: {e}")

def main():
    """메인 함수"""
    try:
        app = QApplication(sys.argv)
        
        # 애플리케이션 정보 설정
        app.setApplicationName("프롬프트 입력기")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("PromptBook")
        
        # 메인 윈도우 생성 및 표시
        window = PromptInput()
        window.show()
        
        # 이벤트 루프 시작
        sys.exit(app.exec())
        
    except Exception as e:
        # 메인 실행 중 오류 발생 시 팝업으로 표시
        import traceback
        error_details = traceback.format_exc()
        show_error_popup(
            "프롬프트 입력기 시작 오류",
            f"프로그램 시작 중 오류가 발생했습니다:\n{str(e)}",
            error_details
        )
        sys.exit(1)


if __name__ == "__main__":
    main() 