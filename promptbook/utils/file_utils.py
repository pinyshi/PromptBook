import os
import json
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QStandardPaths
import shutil
from datetime import datetime

def get_app_data_dir():
    """앱 데이터 디렉토리 경로를 반환합니다."""
    app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

def get_images_dir():
    """이미지 저장 디렉토리 경로를 반환합니다."""
    images_dir = os.path.join(get_app_data_dir(), "images")
    os.makedirs(images_dir, exist_ok=True)
    return images_dir

def load_json_file(file_path, default_value=None):
    """JSON 파일을 로드합니다."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        QMessageBox.warning(None, "파일 로드 실패", f"파일을 로드하는 중 오류가 발생했습니다:\n{str(e)}")
    return default_value if default_value is not None else {}

def save_json_file(file_path, data):
    """JSON 파일을 저장합니다."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        QMessageBox.warning(None, "파일 저장 실패", f"파일을 저장하는 중 오류가 발생했습니다:\n{str(e)}")
        return False

def load_text_file(file_path, default_value=""):
    """텍스트 파일을 로드합니다."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        QMessageBox.warning(None, "파일 로드 실패", f"파일을 로드하는 중 오류가 발생했습니다:\n{str(e)}")
    return default_value

def save_text_file(file_path, text):
    """텍스트 파일을 저장합니다."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        QMessageBox.warning(None, "파일 저장 실패", f"파일을 저장하는 중 오류가 발생했습니다:\n{str(e)}")
        return False

def ensure_directory(path):
    """디렉토리가 없으면 생성합니다."""
    os.makedirs(path, exist_ok=True)
    
def get_safe_path(base_dir, name, ext):
    """중복되지 않는 안전한 파일 경로를 생성합니다."""
    # 파일 이름에서 사용할 수 없는 문자 제거
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')
    
    # 기본 파일 경로
    base_path = os.path.join(base_dir, f"{safe_name}{ext}")
    
    # 이미 존재하는 경우 번호 추가
    if os.path.exists(base_path):
        counter = 1
        while True:
            new_path = os.path.join(base_dir, f"{safe_name}_{counter}{ext}")
            if not os.path.exists(new_path):
                return new_path
            counter += 1
    
    return base_path
    
def copy_file(src, dst):
    """파일을 복사합니다."""
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"파일 복사 실패: {e}")
        return False
        
def delete_file(path):
    """파일을 삭제합니다."""
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
    except Exception as e:
        print(f"파일 삭제 실패: {e}")
    return False
    
def move_file(src, dst):
    """파일을 이동합니다."""
    try:
        shutil.move(src, dst)
        return True
    except Exception as e:
        print(f"파일 이동 실패: {e}")
        return False
        
def get_file_info(path):
    """파일 정보를 반환합니다."""
    try:
        stat = os.stat(path)
        return {
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "exists": True
        }
    except:
        return {
            "size": 0,
            "created": "",
            "modified": "",
            "exists": False
        }
        
def clean_empty_dirs(path):
    """빈 디렉토리를 삭제합니다."""
    try:
        for root, dirs, files in os.walk(path, topdown=False):
            for name in dirs:
                dir_path = os.path.join(root, name)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
        return True
    except Exception as e:
        print(f"빈 디렉토리 정리 실패: {e}")
        return False 