from PySide6.QtWidgets import QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt
from datetime import datetime

class BookHandlers:
    def add_book(self):
        """새 북을 추가합니다."""
        base_name = "새 북"
        existing_names = {self.extract_book_name(self.book_list_widget.book_list.item(i).text()) 
                        for i in range(self.book_list_widget.book_list.count())}
        
        # 고유한 이름 생성
        if base_name not in existing_names:
            unique_name = base_name
        else:
            for i in range(1, 1000):
                candidate = f"{base_name} ({i})"
                if candidate not in existing_names:
                    unique_name = candidate
                    break

        # 새 북 데이터 생성
        self.state.books[unique_name] = {
            "emoji": "📕",
            "pages": [],
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        }
        
        # 리스트에 아이템 추가
        item = QListWidgetItem(f"📕 {unique_name}")
        item.setData(Qt.UserRole, unique_name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.book_list_widget.book_list.addItem(item)
        
        # 현재 정렬 모드가 커스텀이 아니면 정렬 적용
        if not self.book_sort_custom:
            self.handle_book_sort()
        
        # 새로 추가된 북 선택
        self.book_list_widget.book_list.setCurrentItem(item)
        self.on_book_selected(self.book_list_widget.book_list.row(item))
        
        self.save_to_file()

    def delete_book(self, item):
        """북을 삭제합니다."""
        name = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, 
            "북 삭제 확인",
            f"'{name}' 북을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 현재 선택된 북이 삭제되는 경우 처리
            if self.current_book == name:
                self.current_book = None
                self.state.characters = []
                self.char_list_widget.clear()
                self.editor_widget.clear_all()
                
            # 북 삭제
            del self.state.books[name]
            row = self.book_list_widget.book_list.row(item)
            self.book_list_widget.book_list.takeItem(row)
            
            # UI 상태 업데이트
            self.save_to_file()
            
            # 다른 북이 있다면 첫 번째 북 선택
            if self.book_list_widget.book_list.count() > 0:
                self.book_list_widget.book_list.setCurrentRow(0)
                self.on_book_selected(0)

    def rename_book(self, item):
        """북의 이름을 변경합니다."""
        old_name = item.data(Qt.UserRole)
        new_text = item.text().strip()
        new_name = self.extract_book_name(new_text)
        
        # 이름이 비어있거나 변경되지 않은 경우
        if not new_name or old_name == new_name:
            # 원래 이름으로 복원
            emoji = self.state.books[old_name].get("emoji", "📕")
            item.setText(f"{emoji} {old_name}")
            return
            
        # 이미 존재하는 이름인 경우
        if new_name in self.state.books and new_name != old_name:
            QMessageBox.warning(self, "이름 변경 실패", "이미 존재하는 북 이름입니다.")
            # 원래 이름으로 복원
            emoji = self.state.books[old_name].get("emoji", "📕")
            item.setText(f"{emoji} {old_name}")
            return
            
        if old_name and new_name and old_name != new_name:
            # 이모지 유지
            emoji = self.state.books[old_name].get("emoji", "📕")
            # 북 데이터 이동
            self.state.books[new_name] = self.state.books.pop(old_name)
            self.state.books[new_name]["modified"] = datetime.now().isoformat()
            
            if self.current_book == old_name:
                self.current_book = new_name
                
            # 새 이름과 이모지로 텍스트 설정
            item.setText(f"{emoji} {new_name}")
            item.setData(Qt.UserRole, new_name)
            
            # 현재 정렬 모드가 커스텀이 아니면 정렬 적용
            if not self.book_sort_custom:
                self.handle_book_sort()
                
            self.save_to_file()

    def set_book_emoji(self, item, emoji):
        """북의 이모지를 변경합니다."""
        name = item.data(Qt.UserRole)
        if name in self.state.books:
            self.state.books[name]["emoji"] = emoji
            self.state.books[name]["modified"] = datetime.now().isoformat()
            item.setText(f"{emoji} {name}")
            self.save_to_file()

    def extract_book_name(self, text):
        """북 이름에서 이모지를 제외한 실제 이름만 추출합니다."""
        parts = text.split()
        return ' '.join(parts[1:]) if len(parts) > 1 else text 