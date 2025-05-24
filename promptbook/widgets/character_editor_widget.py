from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QFileDialog, 
    QToolBar, QToolButton, QFormLayout,
    QGraphicsScene
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from ..utils.image_utils import load_image, save_image
from .image_view import ImageView
import os

class CharacterEditorWidget(QWidget):
    """캐릭터 편집을 위한 위젯입니다."""
    
    # 시그널 정의
    save_clicked = Signal()  # 저장 버튼이 클릭되었을 때
    delete_clicked = Signal()  # 삭제 버튼이 클릭되었을 때
    image_changed = Signal(str)  # 이미지가 변경되었을 때
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """UI를 초기화합니다."""
        layout = QVBoxLayout(self)
        
        # 도구 모음
        toolbar = QToolBar()
        
        # 저장 버튼
        save_button = QToolButton()
        save_button.setText("💾")
        save_button.setToolTip("저장")
        save_button.clicked.connect(self.save_clicked)
        toolbar.addWidget(save_button)
        
        # 삭제 버튼
        delete_button = QToolButton()
        delete_button.setText("🗑")
        delete_button.setToolTip("삭제")
        delete_button.clicked.connect(self.delete_clicked)
        toolbar.addWidget(delete_button)
        
        layout.addWidget(toolbar)
        
        # 이미지 뷰어
        self.image_scene = QGraphicsScene()
        self.image_view = ImageView()
        self.image_view.setScene(self.image_scene)
        self.image_view.image_dropped.connect(self._on_image_dropped)
        layout.addWidget(self.image_view)
        
        # 에디터 영역
        editor_layout = QFormLayout()
        
        # 이름 입력
        self.name_edit = QLineEdit()
        editor_layout.addRow("이름:", self.name_edit)
        
        # 설명 입력
        self.description_edit = QTextEdit()
        editor_layout.addRow("설명:", self.description_edit)
        
        # 태그 입력
        self.tags_edit = QLineEdit()
        editor_layout.addRow("태그:", self.tags_edit)
        
        layout.addLayout(editor_layout)
        
    def _on_image_dropped(self, file_path):
        """이미지가 드롭되었을 때의 처리"""
        self.image_changed.emit(file_path)
        
    def get_data(self):
        """현재 입력된 데이터를 반환합니다."""
        return {
            "name": self.name_edit.text(),
            "description": self.description_edit.toPlainText(),
            "tags": [tag.strip() for tag in self.tags_edit.text().split(",") if tag.strip()]
        }
        
    def set_data(self, data):
        """데이터를 위젯에 설정합니다."""
        self.name_edit.setText(data.get("name", ""))
        self.description_edit.setPlainText(data.get("description", ""))
        self.tags_edit.setText(", ".join(data.get("tags", [])))
        
    def clear(self):
        """입력 필드를 초기화합니다."""
        self.name_edit.clear()
        self.description_edit.clear()
        self.tags_edit.clear()
        self.image_scene.clear()
        self.image_view.drop_hint.setVisible(True)

    def set_image(self, image_path):
        """이미지를 설정합니다."""
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.image_scene.clear()
            self.image_scene.addPixmap(pixmap)
            self.image_view.fitInView(self.image_scene.sceneRect(), Qt.KeepAspectRatio)
            self.image_view.drop_hint.setVisible(False)
        else:
            self.image_scene.clear()
            self.image_view.drop_hint.setVisible(True) 