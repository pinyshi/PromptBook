from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QListWidgetItem, QMessageBox
from promptbook_utils import PromptBookUtils

class PromptBookEventHandlers:
    def handle_drag_drop_events(self, source, event, parent):
        """드래그 & 드롭 이벤트 처리"""
        if event.type() == QEvent.DragEnter:
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if PromptBookUtils.is_valid_image(url.toLocalFile()):
                        event.acceptProposedAction()
                        return True
            event.ignore()
            return True
            
        elif event.type() == QEvent.Drop:
            if not (0 <= parent.state.current_index < len(parent.state.characters)):
                return True
                
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if PromptBookUtils.is_valid_image(file_path):
                    new_path = PromptBookUtils.handle_image_copy(file_path)
                    if new_path:
                        parent.state.characters[parent.state.current_index]["image_path"] = new_path
                        parent.state.edited = True
                        parent.update_image_view(new_path)
                    break
            return True
            
        return False

    def handle_keyboard_events(self, source, event, parent):
        """키보드 이벤트 처리"""
        if event.type() != QEvent.KeyPress:
            return False
            
        if source == parent.book_list:
            return self._handle_book_list_keyboard(event, parent)
        elif source == parent.char_list:
            return self._handle_char_list_keyboard(event, parent)
            
        return False

    def _handle_book_list_keyboard(self, event, parent):
        """북 리스트 키보드 이벤트 처리"""
        if event.key() == Qt.Key_Delete:
            current_item = parent.book_list.currentItem()
            if current_item:
                book_name = PromptBookUtils.extract_book_name(current_item.text())
                if parent.state.books.get(book_name):
                    reply = QMessageBox.question(
                        parent,
                        "북 삭제 확인",
                        f"'{book_name}' 북을 삭제하시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        parent.state.delete_book(book_name)
                        parent.book_list.takeItem(parent.book_list.currentRow())
                        parent.save_to_file()
                return True
                
        elif event.key() == Qt.Key_F2:
            current_item = parent.book_list.currentItem()
            if current_item:
                parent.book_list.editItem(current_item)
                return True
                
        return False

    def _handle_char_list_keyboard(self, event, parent):
        """캐릭터 리스트 키보드 이벤트 처리"""
        if event.key() == Qt.Key_Delete:
            parent.delete_selected_character()
            return True
            
        elif event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:
            parent.duplicate_selected_character()
            return True
            
        return False

    def handle_star_click(self, item, parent):
        """즐겨찾기 별 클릭 처리"""
        name = item.text()[2:]  # 별 제외한 이름
        for char in parent.state.characters:
            if char.get("name") == name:
                char["favorite"] = not char.get("favorite", False)
                parent.refresh_character_list(selected_name=char["name"])
                parent.save_to_file()
                break 