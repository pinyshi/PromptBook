import os
import shutil
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QSize
from .file_utils import get_images_dir, ensure_directory, get_safe_path, copy_file

def save_image(source_path, target_name):
    """이미지를 앱의 이미지 디렉토리에 저장합니다."""
    if not os.path.exists(source_path):
        return None
        
    # 이미지 확장자 가져오기
    _, ext = os.path.splitext(source_path)
    if not ext:
        ext = '.png'  # 기본 확장자
        
    # 대상 경로 생성
    images_dir = get_images_dir()
    target_path = os.path.join(images_dir, f"{target_name}{ext}")
    
    # 이미 존재하는 경우 번호 붙이기
    counter = 1
    while os.path.exists(target_path):
        target_path = os.path.join(images_dir, f"{target_name}_{counter:03d}{ext}")
        counter += 1
    
    try:
        shutil.copy2(source_path, target_path)
        return target_path
    except Exception as e:
        print(f"이미지 저장 실패: {e}")
        return None

def load_image(path, target_size=None):
    """이미지를 로드합니다."""
    if not os.path.exists(path):
        return None
        
    try:
        pixmap = QPixmap(path)
        if not pixmap.isNull() and target_size:
            return pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        return pixmap
    except:
        return None

def get_scaled_size(original_size, max_size):
    """원본 크기를 유지하면서 최대 크기에 맞게 조정된 크기를 반환합니다."""
    if original_size.width() <= max_size.width() and original_size.height() <= max_size.height():
        return original_size
        
    ratio = min(max_size.width() / original_size.width(),
                max_size.height() / original_size.height())
                
    return QSize(int(original_size.width() * ratio),
                int(original_size.height() * ratio))

def resize_image(pixmap, target_size):
    """이미지 크기를 조정합니다."""
    if pixmap.isNull():
        return pixmap
        
    return pixmap.scaled(
        target_size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

def create_thumbnail(src_path, size=QSize(200, 200)):
    """썸네일을 생성합니다."""
    if not os.path.exists(src_path):
        return None
        
    try:
        pixmap = QPixmap(src_path)
        if not pixmap.isNull():
            return resize_image(pixmap, size)
    except:
        pass
        
    return None

def is_valid_image(path):
    """유효한 이미지 파일인지 확인합니다."""
    if not os.path.exists(path):
        return False
        
    try:
        image = QImage(path)
        return not image.isNull()
    except:
        return False
        
def get_image_format(path):
    """이미지 포맷을 반환합니다."""
    if not os.path.exists(path):
        return None
        
    try:
        image = QImage(path)
        if not image.isNull():
            return image.format()
    except:
        pass
        
    return None
    
def get_image_size(path):
    """이미지 크기를 반환합니다."""
    if not os.path.exists(path):
        return None
        
    try:
        image = QImage(path)
        if not image.isNull():
            return QSize(image.width(), image.height())
    except:
        pass
        
    return None 