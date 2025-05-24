from PySide6.QtWidgets import QStyledItemDelegate, QLineEdit
from PySide6.QtCore import Qt

class BookNameDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.DisplayRole)
        # 이모지를 제외한 실제 이름만 추출
        name = text.split(" ", 1)[1] if " " in text else text
        editor.setText(name)

    def setModelData(self, editor, model, index):
        name = editor.text().strip()
        emoji = "📕"  # 기본 이모지
        
        # 부모 위젯에서 상태 정보 가져오기
        if hasattr(self.parent(), "state") and name in self.parent().state.books:
            emoji = self.parent().state.books[name].get("emoji", "📕")
            
        model.setData(index, f"{emoji} {name}", Qt.DisplayRole)
        model.setData(index, name, Qt.UserRole)

    def extract_book_name(self, text):
        """북 이름에서 이모지를 제외한 실제 이름만 추출합니다."""
        parts = text.split()
        return ' '.join(parts[1:]) if len(parts) > 1 else text 