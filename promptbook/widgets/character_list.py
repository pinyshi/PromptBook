from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication

class CharacterList(QListWidget):
    """캐릭터 리스트를 표시하는 위젯입니다."""
    
    character_moved = Signal(int, int)  # from_index, to_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event):
        # 내부 항목 이동인 경우만 허용
        if event.source() == self:
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """드래그 앤 드롭 이벤트 처리"""
        if not event.source() == self:
            return
            
        # 드롭 위치 계산
        drop_pos = event.pos()
        drop_item = self.itemAt(drop_pos)
        
        if not drop_item:
            # 리스트 끝에 드롭한 경우
            drop_index = self.count()
        else:
            drop_index = self.row(drop_item)
            
        # 드래그 중인 아이템 가져오기
        drag_item = self.currentItem()
        if not drag_item:
            return
            
        from_index = self.row(drag_item)
        
        # 기본 드롭 이벤트 처리
        super().dropEvent(event)
        
        # 이동 시그널 발생
        self.character_moved.emit(from_index, drop_index)
            
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        super().mouseMoveEvent(event)

    def get_items(self):
        """모든 아이템의 데이터를 반환"""
        items = []
        for i in range(self.count()):
            item = self.item(i)
            items.append({
                'text': item.text(),
                'data': item.data(Qt.UserRole)
            })
        return items 