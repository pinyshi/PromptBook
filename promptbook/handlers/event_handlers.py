import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from ..utils import load_image
from ..features import sort_characters

class EventHandlers:
    """UI 이벤트 핸들러 클래스"""
    
    def on_book_selected(self, index):
        """북이 선택되었을 때의 이벤트를 처리합니다."""
        if index < 0:
            self.current_book = None
            self.state.characters = []
            self.char_list_widget.clear()
            self.editor_widget.clear_all()
            return
            
        item = self.book_list_widget.book_list.item(index)
        name = item.data(Qt.UserRole)
        
        if name != self.current_book:
            self.current_book = name
            self.state.characters = self.state.books[name].get("pages", [])
            self.refresh_character_list()
            
            # 캐릭터가 있으면 첫 번째 캐릭터 선택
            if self.state.characters:
                self.char_list_widget.set_current_row(0)
                self.on_character_selected(0)
            else:
                self.current_index = -1
                self.editor_widget.clear_all()
                
    def on_character_selected(self, index):
        """캐릭터가 선택되었을 때의 이벤트를 처리합니다."""
        if index < 0 or not self.state.characters:
            self.current_index = -1
            self.editor_widget.clear_all()
            return
            
        self.current_index = index
        self.editor_widget.set_data(self.state.characters[index])
        
        # 이미지가 있으면 표시
        if "image_path" in self.state.characters[index] and os.path.exists(self.state.characters[index]["image_path"]):
            pixmap = load_image(self.state.characters[index]["image_path"], QSize(400, 400))
            if pixmap:
                self.editor_widget.image_scene.clear()
                self.editor_widget.image_scene.addPixmap(pixmap)
                self.editor_widget.image_view.fitInView(
                    self.editor_widget.image_scene.sceneRect(),
                    Qt.KeepAspectRatio
                )
                self.editor_widget.image_view.drop_hint.setVisible(False)
        else:
            self.editor_widget.image_scene.clear()
            self.editor_widget.image_view.drop_hint.setVisible(True)
            
    def handle_book_sort(self, mode=None):
        """북 정렬 이벤트를 처리합니다."""
        if mode is None:
            mode = self.book_list_widget.get_current_sort_mode()
            
        if mode == "이름순":
            self.book_sort_custom = False
            books = dict(sorted(self.state.books.items()))
            self.state.books = books
            self.load_books()
        elif mode == "최근 수정순":
            self.book_sort_custom = False
            books = dict(sorted(self.state.books.items(), 
                key=lambda x: x[1].get("modified", ""), reverse=True))
            self.state.books = books
            self.load_books()
        else:  # 커스텀
            self.book_sort_custom = True
            
    def handle_character_sort(self, mode=None):
        """캐릭터 정렬 이벤트를 처리합니다."""
        if not self.current_book:
            return
            
        if mode is None:
            mode = self.char_list_widget.get_current_sort_mode()
            
        if mode == "커스텀":
            self.sort_mode_custom = True
        else:
            self.sort_mode_custom = False
            self.state.characters = sort_characters(self.state.characters, mode)
            self.refresh_character_list()
            
    def save_to_file(self):
        """현재 상태를 파일에 저장합니다."""
        self.state.save()
        
    def load_character_image(self, file_path):
        """캐릭터 이미지를 로드합니다."""
        if not self.current_book or self.current_index < 0:
            return
            
        # 현재 캐릭터의 이름으로 이미지 저장
        char_name = self.state.characters[self.current_index]["name"]
        saved_path = save_image(file_path, char_name)
        
        if saved_path:
            # 이미지 경로 저장
            self.state.characters[self.current_index]["image_path"] = saved_path
            self.state.books[self.current_book]["pages"] = self.state.characters
            
            # 이미지 표시
            self.editor_widget.set_image(saved_path)
            self.save_to_file()
            
    def delete_character_image(self):
        """캐릭터 이미지를 삭제합니다."""
        if not self.current_book or self.current_index < 0:
            return
            
        # 이미지 파일 삭제
        image_path = self.state.characters[self.current_index].get("image_path")
        if image_path:
            try:
                os.remove(image_path)
            except:
                pass
                
        # 이미지 경로 제거
        self.state.characters[self.current_index].pop("image_path", None)
        self.state.books[self.current_book]["pages"] = self.state.characters
        
        # UI 업데이트
        self.editor_widget.set_image("")
        self.save_to_file() 