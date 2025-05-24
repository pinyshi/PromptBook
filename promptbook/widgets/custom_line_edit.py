from PySide6.QtWidgets import QLineEdit, QCompleter, QApplication
from PySide6.QtCore import Qt, QTimer

class CustomLineEdit(QLineEdit):
    """자동 완성 기능이 있는 라인 에디트"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._completer = None
        self.prompt_display_map = {}
        
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
        
    def update_completion(self, text=''):
        """자동 완성을 업데이트합니다."""
        if not self._completer:
            return
            
        # 포커스 체크 - 포커스가 없으면 팝업 숨기기
        if QApplication.focusWidget() != self:
            self._completer.popup().hide()
            return
            
        # 현재 커서 위치까지의 텍스트 가져오기
        text = self.text()[:self.cursorPosition()]
        last_comma = text.rfind(",")
        if last_comma >= 0:
            text = text[last_comma + 1:].strip()
        else:
            text = text.strip()
            
        # 빈 텍스트이거나 공백만 있는 경우 팝업 숨기기
        if not text:
            self._completer.popup().hide()
            return
            
        # 자동완성 업데이트
        self._completer.setCompletionPrefix(text)
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        
        # 현재 단어의 시작 위치로 커서 이동
        prefix_start_pos = last_comma + 1 if last_comma >= 0 else 0
        saved_pos = self.cursorPosition()
        self.setCursorPosition(prefix_start_pos)
        
        # 팝업 위치 및 크기 설정
        rect = self.cursorRect()
        popup_width = popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width()
        rect.setWidth(popup_width)
        
        # 원래 커서 위치 복원
        self.setCursorPosition(saved_pos)
        
        # 팝업 표시 위치 조정 (비동기로 처리)
        global_pos = self.mapToGlobal(rect.bottomLeft())
        QTimer.singleShot(0, lambda: (
            popup.move(global_pos),
            popup.show()
        ))
        
    def insert_completion(self, completion):
        """자동 완성 텍스트를 삽입합니다."""
        # 실제로 삽입할 텍스트 (매핑된 값이 있으면 사용)
        insert_text = self.prompt_display_map.get(completion, completion)
        
        # 현재 커서 위치 기준으로 앞뒤 텍스트 가져오기
        text_before = self.text()[:self.cursorPosition()]
        text_after = self.text()[self.cursorPosition():]
        
        # 마지막 쉼표 위치 찾기
        last_comma = text_before.rfind(",")
        if last_comma >= 0:
            # 쉼표 이후의 텍스트만 교체하고 쉼표 추가
            text_before = text_before[:last_comma + 1] + " " + insert_text + ", "
        else:
            # 전체 텍스트 교체하고 쉼표 추가
            text_before = insert_text + ", "
            
        # 새 텍스트 설정 (text_after의 시작 부분에 쉼표가 있으면 제거)
        if text_after.lstrip().startswith(","):
            text_after = text_after.lstrip()[1:].lstrip()
        self.setText(text_before + text_after)
        
        # 커서를 삽입된 텍스트 끝으로 이동
        self.setCursorPosition(len(text_before))
        
    def keyPressEvent(self, event):
        """키 입력 이벤트 처리"""
        # Tab 키로 자동 완성 선택
        if event.key() == Qt.Key_Tab and self._completer and self._completer.popup().isVisible():
            self._completer.popup().setCurrentIndex(self._completer.popup().currentIndex())
            self.insert_completion(self._completer.currentCompletion())
            self._completer.popup().hide()
            return
            
        super().keyPressEvent(event) 