import sys
import os
import logging
import traceback
from datetime import datetime
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

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
        self.setup_ui()
        self.setup_autocomplete()
        
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle(f"프롬프트 입력기 {self.VERSION}")
        self.setFixedSize(600, 300)
        
        # 아이콘 설정 (프롬프트북과 동일)
        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))
        elif os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
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
        
        # 복사 버튼
        self.copy_button = QPushButton("📋 복사")
        self.copy_button.clicked.connect(self.copy_prompt_to_clipboard)
        self.copy_button.setMinimumHeight(35)
        layout.addWidget(self.copy_button)
        
        # 상태바
        self.statusBar().showMessage("프롬프트를 입력하고 복사 버튼을 클릭하세요.")
        
    def setup_autocomplete(self):
        """자동완성 설정 (프롬프트북과 완전히 동일)"""
        try:
            with open("autocomplete.txt", 'r', encoding='utf-8') as f:
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


def setup_logging():
    """로깅 설정 - 오류 발생 시 로그 파일에 기록"""
    log_filename = f"promptinput_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # 콘솔에도 출력
        ]
    )
    
    return log_filename

def handle_exception(exc_type, exc_value, exc_traceback):
    """전역 예외 처리기 - 모든 예외를 로그 파일에 기록"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Ctrl+C 인터럽트는 정상 종료로 처리
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # 예외 정보를 로그에 기록
    error_msg = f"프롬프트 입력기 오류 발생:\n"
    error_msg += f"오류 타입: {exc_type.__name__}\n"
    error_msg += f"오류 메시지: {str(exc_value)}\n"
    error_msg += f"발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    error_msg += f"상세 스택 트레이스:\n"
    error_msg += ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    logging.error(error_msg)
    
    # 사용자에게 오류 알림 (GUI가 가능한 경우)
    try:
        from PySide6.QtWidgets import QMessageBox, QApplication
        app = QApplication.instance()
        if app is not None:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("프롬프트 입력기 오류")
            msg_box.setText("프로그램에서 예상치 못한 오류가 발생했습니다.")
            msg_box.setDetailedText(f"오류 내용: {str(exc_value)}\n\n자세한 로그는 다음 파일에서 확인할 수 있습니다:\n{log_filename}")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
    except:
        # GUI 표시 실패 시 콘솔에만 출력
        print(f"오류가 발생했습니다. 로그 파일을 확인해주세요: {log_filename}")

def main():
    """메인 함수"""
    # 로깅 설정
    log_filename = setup_logging()
    
    # 전역 예외 처리기 설정
    sys.excepthook = handle_exception
    
    try:
        app = QApplication(sys.argv)
        
        # 애플리케이션 정보 설정
        app.setApplicationName("프롬프트 입력기")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("PromptBook")
        
        # 메인 윈도우 생성 및 표시
        window = PromptInput()
        window.show()
        
        # 프로그램 시작 로그
        logging.info("프롬프트 입력기가 성공적으로 시작되었습니다.")
        
        # 이벤트 루프 시작
        sys.exit(app.exec())
        
    except Exception as e:
        # 메인 실행 중 오류 발생 시
        error_msg = f"프롬프트 입력기 시작 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        print(f"프로그램 시작 실패. 로그 파일을 확인해주세요: {log_filename}")
        sys.exit(1)


if __name__ == "__main__":
    main() 