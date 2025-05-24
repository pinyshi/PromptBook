from PySide6.QtWidgets import QTextEdit, QLineEdit, QCompleter
from PySide6.QtCore import Qt, Signal, QStringListModel

class CustomTextEdit(QTextEdit):
    textEdited = Signal()  # 텍스트 변경 시그널

    def __init__(self, parent=None):
        super().__init__(parent)
        self._completer = None
        self.textChanged.connect(lambda: self.textEdited.emit())
        self.setAcceptRichText(False)  # 서식 있는 텍스트 비활성화
        self.setLineWrapMode(QTextEdit.WidgetWidth)  # 자동 줄바꿈 활성화
        self.setMinimumHeight(100)  # 최소 높이 설정
        self.setMaximumHeight(150)  # 최대 높이 설정

    def set_custom_completer(self, completer):
        """커스텀 자동완성 설정"""
        if self._completer:
            self._completer.disconnect(self)
        self._completer = completer
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)

    def handle_text_edited(self):
        """텍스트 편집 시 자동완성 처리"""
        if not self._completer:
            return

        text = self.toPlainText().strip()
        if not text:
            self._completer.popup().hide()
            return

        # 현재 커서 위치의 단어 찾기
        cursor = self.textCursor()
        text_before_cursor = self.toPlainText()[:cursor.position()]
        words = text_before_cursor.split(',')
        current_word = words[-1].strip() if words else ""

        if not current_word:
            self._completer.popup().hide()
            return

        # 자동완성 모델에서 현재 단어와 매칭되는 항목 찾기
        model = self._completer.model()
        matches = []
        for i in range(model.rowCount()):
            item = model.data(model.index(i, 0), Qt.DisplayRole)
            if current_word.lower() in item.lower():
                matches.append(item)

        if not matches:
            self._completer.popup().hide()
            return

        # 매칭된 항목으로 새 모델 생성 (원본 순서 유지)
        new_model = QStringListModel(matches)
        self._completer.setModel(new_model)

        # 자동완성 팝업 표시
        cursor_rect = self.cursorRect()
        cursor_rect.setWidth(self._completer.popup().sizeHintForColumn(0) + 
                           self._completer.popup().verticalScrollBar().sizeHint().width())
        cursor_rect.moveTopLeft(self.viewport().mapToGlobal(cursor_rect.topLeft()))
        self._completer.complete(cursor_rect)

    def keyPressEvent(self, event):
        """키 입력 이벤트 처리"""
        if self._completer and self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab):
                event.ignore()
                return

        super().keyPressEvent(event)

        # 쉼표 입력 시 자동으로 공백 추가
        if event.text() == ',':
            cursor = self.textCursor()
            cursor.insertText(' ') 