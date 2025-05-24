import json
import os
from datetime import datetime

class State:
    """프롬프트북의 상태를 관리하는 클래스입니다."""
    
    def __init__(self, file_path="data/promptbook.json"):
        """상태 관리자를 초기화합니다."""
        self.file_path = file_path
        self.books = {}  # 북 데이터
        self.characters = []  # 현재 선택된 북의 캐릭터 목록
        self.current_book = None  # 현재 선택된 북
        self.current_character = None  # 현재 선택된 캐릭터
        self.load()
        
    def load(self):
        """파일에서 상태를 로드합니다."""
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            # 파일이 있으면 로드
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "books" in data:
                            self.books = data["books"]
                        else:
                            self.books = data  # 이전 버전 호환성
                    else:
                        self.books = {}
                    
                    # 시간 정보가 없는 경우 추가
                    now = datetime.now().isoformat()
                    for book in self.books.values():
                        if "created" not in book:
                            book["created"] = now
                        if "modified" not in book:
                            book["modified"] = now
                        for page in book.get("pages", []):
                            if "created" not in page:
                                page["created"] = now
                            if "modified" not in page:
                                page["modified"] = now
            else:
                # 파일이 없으면 기본 상태 생성
                self.create_default_state()
                self.save()
        except Exception as e:
            print(f"상태 로드 실패: {e}")
            # 로드 실패 시 기본 상태 생성
            self.create_default_state()
            
    def save(self):
        """현재 상태를 파일에 저장합니다."""
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            # 상태 저장
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.books, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"상태 저장 실패: {e}")
            
    def create_default_state(self):
        """기본 상태를 생성합니다."""
        now = datetime.now().isoformat()
        self.books = {
            "샘플 북": {
                "emoji": "📕",
                "pages": [
                    {
                        "name": "샘플 페이지",
                        "tags": "샘플, 예시",
                        "desc": "이것은 샘플 페이지입니다.",
                        "prompt": "샘플 프롬프트입니다.",
                        "favorite": False,
                        "created": now,
                        "modified": now
                    }
                ],
                "created": now,
                "modified": now
            }
        }
        
    def backup(self):
        """현재 상태를 백업합니다."""
        if not os.path.exists(self.file_path):
            return
            
        # 백업 파일 경로 생성
        backup_dir = os.path.join(os.path.dirname(self.file_path), "backup")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"promptbook_{timestamp}.json")
        
        try:
            # 현재 파일을 백업
            with open(self.file_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
        except Exception as e:
            print(f"백업 실패: {e}")
            
    def restore_backup(self, backup_path):
        """백업에서 상태를 복원합니다."""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.books = data.get("books", {})
                self.save()
                return True
        except Exception as e:
            print(f"백업 복원 실패: {e}")
            return False

    def add_book(self, name, data):
        """북을 추가합니다."""
        self.books[name] = data
        
    def remove_book(self, name):
        """북을 제거합니다."""
        if name in self.books:
            del self.books[name]
            
    def rename_book(self, old_name, new_name):
        """북의 이름을 변경합니다."""
        if old_name in self.books:
            self.books[new_name] = self.books.pop(old_name)
            
    def get_book(self, name):
        """북 데이터를 가져옵니다."""
        return self.books.get(name)
        
    def set_current_book(self, name):
        """현재 북을 설정합니다."""
        self.current_book = name
        if name in self.books:
            self.characters = self.books[name].get("pages", [])
        else:
            self.characters = []
            
    def add_character(self, data):
        """캐릭터를 추가합니다."""
        self.characters.append(data)
        if self.current_book:
            self.books[self.current_book]["pages"] = self.characters
            
    def remove_character(self, index):
        """캐릭터를 제거합니다."""
        if 0 <= index < len(self.characters):
            del self.characters[index]
            if self.current_book:
                self.books[self.current_book]["pages"] = self.characters
                
    def update_character(self, index, data):
        """캐릭터를 업데이트합니다."""
        if 0 <= index < len(self.characters):
            self.characters[index].update(data)
            if self.current_book:
                self.books[self.current_book]["pages"] = self.characters
                
    def get_character(self, index):
        """캐릭터 데이터를 가져옵니다."""
        if 0 <= index < len(self.characters):
            return self.characters[index]
        return None
        
    def set_current_character(self, index):
        """현재 캐릭터를 설정합니다."""
        if 0 <= index < len(self.characters):
            self.current_character = self.characters[index]
        else:
            self.current_character = None
            
    def sort_characters(self, key_func):
        """캐릭터를 정렬합니다."""
        self.characters.sort(key=key_func)
        if self.current_book:
            self.books[self.current_book]["pages"] = self.characters
            
    def sort_books(self, key_func):
        """북을 정렬합니다."""
        sorted_items = sorted(self.books.items(), key=key_func)
        self.books = dict(sorted_items) 