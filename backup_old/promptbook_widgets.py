
from PySide6.QtWidgets import QPlainTextEdit, QGraphicsView, QCompleter, QApplication
from PySide6.QtGui import QKeyEvent, QPainter, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, QTimer, QEvent

class CustomLineEdit(QPlainTextEdit):
    def __init__(self, completer=None):
        super().__init__()
        self._completer = None
        self.prompt_display_map = {}
        self.set_custom_completer(completer)
        self.textChanged.connect(lambda: self.update_completion(self.toPlainText()))

    def set_custom_completer(self, completer):
        self._completer = completer
        if self._completer:
            self._completer.setWidget(self)
            self._completer.setCompletionMode(QCompleter.PopupCompletion)
            self._completer.setCaseSensitivity(Qt.CaseInsensitive)
            self._completer.activated.connect(lambda display_text: self.insert_completion(self.prompt_display_map.get(display_text, display_text)))

    def update_completion(self, text=''):
        if not self._completer:
            return
        if QApplication.focusWidget() != self:
            self._completer.popup().hide()
            return
        if not self._completer or QApplication.focusWidget() != self:
            self._completer.popup().hide()
            return

        cursor_pos = self.textCursor().position()
        current_text = self.toPlainText()[:cursor_pos]
        last_comma = current_text.rfind(',')
        prefix = current_text[last_comma + 1:].strip() if last_comma != -1 else current_text.strip()

        if prefix:
            self._completer.setCompletionPrefix(prefix)
            popup = self._completer.popup()
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
            popup.show()
            prefix_start_pos = last_comma + 1 if last_comma != -1 else 0
            cursor = self.textCursor()
            cursor.setPosition(prefix_start_pos)
            rect = self.cursorRect(cursor)
            QTimer.singleShot(0, lambda: popup.move(self.mapToGlobal(rect.bottomLeft())))
            popup.raise_()
        else:
            self._completer.popup().hide()

    def insert_completion(self, completion):
        cursor_pos = self.textCursor().position()
        text_before = self.toPlainText()[:cursor_pos]
        text_after = self.toPlainText()[cursor_pos:]

        last_comma = text_before.rfind(',')
        if last_comma != -1:
            new_text = text_before[:last_comma + 1] + ' ' + completion + ', ' + text_after
        else:
            new_text = completion + ', ' + text_after

        self.setPlainText(new_text)
        new_cursor = self.textCursor()
        new_pos = len(text_before[:last_comma + 1] + ' ' + completion + ', ') if last_comma != -1 else len(completion + ', ')
        new_cursor.setPosition(new_pos)
        self.setTextCursor(new_cursor)

    def keyPressEvent(self, event):
        if self._completer and self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                index = self._completer.popup().currentIndex()
                completion = index.data(Qt.DisplayRole)
                self._completer.activated.emit(completion)
                return
        super().keyPressEvent(event)

class ImageView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        parent = self.parentWidget()
        if hasattr(parent, 'current_index') and 0 <= parent.current_index < len(parent.characters):
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                    parent.characters[parent.current_index]["image_path"] = file_path
                    parent.edited = True
                    parent.update_image_buttons_state()
                    parent.update_image_view(file_path)
                    break
