from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPushButton, QComboBox,
    QLabel, QToolBar, QToolButton, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from .book_delegate import BookNameDelegate

class BookListWidget(QWidget):
    """북 리스트를 표시하는 위젯입니다."""
    
    # 시그널 정의
    book_selected = Signal(str)  # 북이 선택되었을 때
    book_sort_changed = Signal(str)  # 정렬 방식이 변경되었을 때
    add_book_clicked = Signal()  # 북 추가 버튼이 클릭되었을 때
    book_moved = Signal(int, int)  # 북이 이동되었을 때 (from_index, to_index)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """UI를 초기화합니다."""
        layout = QVBoxLayout(self)
        
        # 도구 모음
        toolbar = QToolBar()
        
        # 정렬 콤보박스
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["오름차순 정렬", "내림차순 정렬", "커스텀 정렬"])
        self.sort_combo.currentTextChanged.connect(self.book_sort_changed)
        toolbar.addWidget(self.sort_combo)
        
        # 북 추가 버튼
        add_button = QToolButton()
        add_button.setText("+")
        add_button.setToolTip("새 북 추가")
        add_button.clicked.connect(self.add_book_clicked)
        toolbar.addWidget(add_button)
        
        layout.addWidget(toolbar)
        
        # 북 리스트
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.currentTextChanged.connect(self._on_selection_changed)
        
        # 드래그 앤 드롭 설정
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        
        layout.addWidget(self.list_widget)
        
    def _on_selection_changed(self, text):
        """선택이 변경되었을 때의 처리"""
        if text:
            # 이모지 제거
            name = text.split(" ", 1)[1] if " " in text else text
            self.book_selected.emit(name)
            
    def _on_rows_moved(self, parent, start, end, destination, row):
        """아이템이 이동되었을 때의 처리"""
        # 사용자 지정 정렬로 변경
        self.sort_combo.setCurrentText("커스텀 정렬")
        # 이동 시그널 발생
        self.book_moved.emit(start, row)
        
    def add_item(self, text, data=None):
        """아이템을 추가합니다."""
        item = QListWidgetItem(text)
        if data:
            item.setData(Qt.UserRole, data)
        self.list_widget.addItem(item)
        return item
        
    def clear(self):
        """모든 아이템을 제거합니다."""
        self.list_widget.clear()
        
    def get_items(self):
        """모든 아이템의 데이터를 반환합니다."""
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            items.append({
                'text': item.text(),
                'data': item.data(Qt.UserRole)
            })
        return items 