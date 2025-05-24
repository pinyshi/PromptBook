import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QCompleter
from PySide6.QtCore import QStringListModel, Qt

def load_prompts(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"'{filepath}' 파일을 찾을 수 없습니다.")
        return []

class CustomLineEdit(QLineEdit):
    def __init__(self, completer):
        super().__init__()
        self.completer = completer
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.textChanged.connect(self.update_completion)
        self.completer.activated.connect(self.insert_completion)

    def update_completion(self, text):
        cursor_pos = self.cursorPosition()
        current_text = self.text()[:cursor_pos]
        last_comma = current_text.rfind(',')
        prefix = current_text[last_comma + 1:].strip() if last_comma != -1 else current_text.strip()

        if prefix:
            self.completer.setCompletionPrefix(prefix)
            self.completer.complete()
        else:
            self.completer.popup().hide()

    def insert_completion(self, completion):
        cursor_pos = self.cursorPosition()
        text_before = self.text()[:cursor_pos]
        text_after = self.text()[cursor_pos:]

        last_comma = text_before.rfind(',')
        if last_comma != -1:
            new_text = text_before[:last_comma + 1] + ' ' + completion + text_after
        else:
            new_text = completion + text_after

        self.setText(new_text)
        self.setCursorPosition(len(text_before[:last_comma + 1] + ' ' + completion))

class AutoCompleteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("프롬프트 자동완성 입력기")
        self.setGeometry(100, 100, 500, 100)

        prompts = load_prompts("autocomplete.txt")

        layout = QVBoxLayout()
        completer = QCompleter()
        completer.setModel(QStringListModel(prompts))

        self.input_field = CustomLineEdit(completer)
        self.input_field.setPlaceholderText("프롬프트를 쉼표로 구분해서 입력하세요...")
        layout.addWidget(self.input_field)
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AutoCompleteApp()
    window.show()
    sys.exit(app.exec())
