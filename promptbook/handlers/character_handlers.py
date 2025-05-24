from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from datetime import datetime
import os, shutil
from ..features import sort_characters

class CharacterHandlers:
    """캐릭터 관련 이벤트 핸들러"""
    
    def on_character_selected(self, name):
        """캐릭터가 선택되었을 때의 처리"""
        if not self.current_book:
            return
            
        # 선택된 캐릭터 찾기
        for i, char in enumerate(self.state.characters):
            if char.get("name") == name:
                self.current_index = i
                self.character_editor_widget.set_data(char)
                if "image_path" in char:
                    self.character_editor_widget.set_image(char["image_path"])
                break
                
    def add_character(self):
        """새 캐릭터를 추가합니다."""
        if not self.current_book:
            return
            
        # 새 캐릭터 생성
        new_char = {
            "name": "새 캐릭터",
            "description": "",
            "tags": [],
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        }
        
        # 상태에 추가
        self.state.characters.append(new_char)
        self.state.books[self.current_book]["pages"] = self.state.characters
        
        # UI 갱신
        self.refresh_character_list(new_char["name"])
        self.save_to_file()
        
    def save_character(self):
        """현재 캐릭터를 저장합니다."""
        if not self.current_book or self.current_index < 0:
            return
            
        # 에디터의 데이터 가져오기
        data = self.character_editor_widget.get_data()
        
        # 기존 데이터와 병합
        char = self.state.characters[self.current_index]
        char.update(data)
        char["modified"] = datetime.now().isoformat()
        
        # 상태 저장
        self.state.books[self.current_book]["pages"] = self.state.characters
        self.refresh_character_list(char["name"])
        self.save_to_file()
        
    def delete_character(self):
        """현재 캐릭터를 삭제합니다."""
        if not self.current_book or self.current_index < 0:
            return
            
        # 캐릭터 삭제
        del self.state.characters[self.current_index]
        self.state.books[self.current_book]["pages"] = self.state.characters
        
        # UI 갱신
        self.current_index = -1
        self.character_editor_widget.clear()
        self.refresh_character_list()
        self.save_to_file()
        
    def duplicate_selected_character(self):
        """선택된 캐릭터를 복제합니다."""
        if not self.current_book or self.current_index < 0:
            return
            
        # 현재 캐릭터 복제
        original = self.state.characters[self.current_index]
        copy = original.copy()
        
        # 새로운 이름 생성
        base_name = original["name"]
        counter = 1
        while any(c["name"] == f"{base_name} (복사본{' ' + str(counter) if counter > 1 else ''})" 
                 for c in self.state.characters):
            counter += 1
        copy["name"] = f"{base_name} (복사본{' ' + str(counter) if counter > 1 else ''})"
        
        # 시간 정보 업데이트
        now = datetime.now().isoformat()
        copy["created"] = now
        copy["modified"] = now
        
        # 상태에 추가
        self.state.characters.append(copy)
        self.state.books[self.current_book]["pages"] = self.state.characters
        
        # UI 갱신
        self.refresh_character_list(copy["name"])
        self.save_to_file()
        
    def update_character_image(self, file_path):
        """캐릭터 이미지를 업데이트합니다."""
        if not self.current_book or self.current_index < 0:
            return
            
        # 현재 캐릭터의 이름으로 이미지 저장
        char = self.state.characters[self.current_index]
        saved_path = save_image(file_path, char["name"])
        
        if saved_path:
            # 이미지 경로 저장
            char["image_path"] = saved_path
            char["modified"] = datetime.now().isoformat()
            self.state.books[self.current_book]["pages"] = self.state.characters
            
            # 이미지 표시
            self.character_editor_widget.set_image(saved_path)
            self.save_to_file()
            
    def handle_character_sort(self, mode):
        """캐릭터 정렬 방식이 변경되었을 때의 처리"""
        if not self.current_book:
            return
            
        characters = self.state.characters
        selected_name = None if self.current_index < 0 else characters[self.current_index]["name"]
        
        if mode == "이름순":
            characters.sort(key=lambda x: x["name"])
        elif mode == "생성일순":
            characters.sort(key=lambda x: x["created"], reverse=True)
        elif mode == "수정일순":
            characters.sort(key=lambda x: x["modified"], reverse=True)
            
        self.state.books[self.current_book]["pages"] = characters
        self.refresh_character_list(selected_name)

    def save_to_file(self):
        """상태를 파일에 저장합니다."""
        # 파일 경로 설정
        file_path = os.path.join(self.state.books[self.current_book]["path"], "characters.json")
        
        # 상태를 파일에 저장
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.state.characters, f)

    def refresh_character_list(self, selected_name=None):
        """캐릭터 목록을 갱신합니다."""
        if not self.current_book:
            return
            
        # 캐릭터 목록 갱신
        self.char_list_widget.char_list.clear()
        for i, char in enumerate(self.state.characters):
            item = QListWidgetItem(f"{emoji} {char['name']}")
            item.setData(Qt.UserRole, char["name"])
            self.char_list_widget.char_list.addItem(item)
        
        # 선택된 캐릭터 설정
        if selected_name:
            for i in range(self.char_list_widget.char_list.count()):
                item = self.char_list_widget.char_list.item(i)
                if item.data(Qt.UserRole) == selected_name:
                    self.char_list_widget.char_list.setCurrentItem(item)
                    self.char_list_widget.char_list.scrollToItem(item)
                    break

    def toggle_favorite_star(self, item):
        """캐릭터의 즐겨찾기 상태를 토글합니다."""
        name = item.data(Qt.UserRole)
        
        # 현재 정렬 모드 저장
        current_mode = self.char_list_widget.get_current_sort_mode()
        
        # 캐릭터 찾기 및 즐겨찾기 토글
        for i, char in enumerate(self.state.characters):
            if char.get("name") == name:
                is_favorite = not char.get("favorite", False)
                char["favorite"] = is_favorite
                char["modified"] = datetime.now().isoformat()
                
                # 상태 업데이트
                self.state.books[self.current_book]["pages"] = self.state.characters
                self.state.books[self.current_book]["modified"] = datetime.now().isoformat()
                
                # 정렬 적용
                if not self.sort_mode_custom:
                    self.state.characters = sort_characters(self.state.characters, current_mode)
                
                # 리스트 갱신
                self.refresh_character_list(selected_name=name)
                self.save_to_file()
                break 