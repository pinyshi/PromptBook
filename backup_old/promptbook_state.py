from typing import Dict, List, Any, Optional

class PromptBookState:
    def __init__(self):
        self.books: Dict[str, Any] = {}
        self.characters: List[Dict[str, Any]] = []
        self.current_book: Optional[str] = None
        self.current_index: int = -1
        self.sort_mode_custom: bool = False
        self.edited: bool = False
        self._initial_loading: bool = True
        
    def reset(self):
        """상태 초기화"""
        self.__init__()
        
    def set_current_book(self, book_name: str) -> None:
        """현재 북 설정"""
        self.current_book = book_name
        self.characters = self.books.get(book_name, {}).get("pages", [])
        self.current_index = -1
        
    def add_book(self, name: str, emoji: str = "📕") -> None:
        """새 북 추가"""
        self.books[name] = {
            "emoji": emoji,
            "pages": []
        }
        
    def rename_book(self, old_name: str, new_name: str) -> bool:
        """북 이름 변경"""
        if old_name in self.books and new_name not in self.books:
            self.books[new_name] = self.books.pop(old_name)
            if self.current_book == old_name:
                self.current_book = new_name
            return True
        return False
        
    def delete_book(self, name: str) -> bool:
        """북 삭제"""
        if name in self.books:
            del self.books[name]
            if self.current_book == name:
                self.reset()
            return True
        return False
        
    def get_current_character(self) -> Optional[Dict[str, Any]]:
        """현재 선택된 캐릭터 데이터 반환"""
        if 0 <= self.current_index < len(self.characters):
            return self.characters[self.current_index]
        return None
        
    def update_current_character(self, data: Dict[str, Any]) -> None:
        """현재 캐릭터 데이터 업데이트"""
        if 0 <= self.current_index < len(self.characters):
            self.characters[self.current_index].update(data)
            if self.current_book:
                self.books[self.current_book]["pages"] = self.characters
                
    def is_loading(self) -> bool:
        """초기 로딩 중인지 여부 반환"""
        return self._initial_loading
        
    def finish_loading(self) -> None:
        """초기 로딩 완료 설정"""
        self._initial_loading = False 