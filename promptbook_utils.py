import os
import shutil
from typing import Set, Dict, Any

class PromptBookUtils:
    @staticmethod
    def extract_book_name(text: str) -> str:
        """이모지를 제외한 북 이름만 추출"""
        parts = text.strip().split(maxsplit=1)
        if len(parts) > 1 and parts[0] in ["📕", "📘", "📙", "📗", "📓", "📔", "📒", "📚", "📖", "📝"]:
            return parts[1]
        return text.strip()

    @staticmethod
    def ensure_unique_name(base_name: str, existing_names: Set[str], prefix: str = "") -> str:
        """중복되지 않는 고유한 이름 생성"""
        if prefix:
            base_name = f"{prefix} {base_name}"
            
        if base_name not in existing_names:
            return base_name
            
        for i in range(1, 1000):
            candidate = f"{base_name} ({i})"
            if candidate not in existing_names:
                return candidate
        return f"{base_name} (1000+)"

    @staticmethod
    def handle_image_copy(src_path: str, dest_dir: str = "images") -> str:
        """이미지 파일을 지정된 디렉토리로 복사"""
        if not src_path or not os.path.exists(src_path):
            return ""
            
        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(src_path)
        dest_path = os.path.join(dest_dir, filename)
        
        try:
            shutil.copy(src_path, dest_path)
            return dest_path
        except Exception as e:
            print(f"이미지 복사 실패: {e}")
            return ""

    @staticmethod
    def is_valid_image(file_path: str) -> bool:
        """유효한 이미지 파일인지 확인"""
        if not file_path:
            return False
            
        valid_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
        return os.path.exists(file_path) and \
               os.path.splitext(file_path)[1].lower() in valid_extensions

    @staticmethod
    def create_empty_character() -> Dict[str, Any]:
        """새로운 빈 캐릭터 데이터 생성"""
        return {
            "name": "",
            "tags": "",
            "desc": "",
            "prompt": "",
            "image_path": "",
            "favorite": False
        } 