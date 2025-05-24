from PySide6.QtWidgets import QStyledItemDelegate, QLineEdit
from PySide6.QtCore import Qt

class BookNameDelegate(QStyledItemDelegate):
    """북 이름 편집을 위한 델리게이트"""
    
    def createEditor(self, parent, option, index):
        """에디터 생성"""
        editor = QLineEdit(parent)
        editor.setFrame(False)
        return editor
        
    def setEditorData(self, editor, index):
        """에디터에 데이터 설정"""
        value = index.model().data(index, Qt.DisplayRole)
        if " " in value:  # 이모지가 있는 경우
            value = value.split(" ", 1)[1]  # 이모지 제외
        editor.setText(value)
        
    def setModelData(self, editor, model, index):
        """모델 데이터 설정"""
        value = editor.text()
        current_text = model.data(index, Qt.DisplayRole)
        if " " in current_text:  # 이모지가 있는 경우
            emoji = current_text.split(" ", 1)[0]
            value = f"{emoji} {value}"
        model.setData(index, value, Qt.EditRole)
        
    def updateEditorGeometry(self, editor, option, index):
        """에디터 위치/크기 설정"""
        editor.setGeometry(option.rect) 