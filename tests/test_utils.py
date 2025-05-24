import os
import tempfile
import unittest
from PySide6.QtCore import QSize
from promptbook.utils.file_utils import (
    ensure_directory,
    get_safe_path,
    copy_file,
    delete_file,
    move_file,
    get_file_info,
    clean_empty_dirs
)
from promptbook.utils.image_utils import (
    load_image,
    resize_image,
    create_thumbnail,
    is_valid_image,
    get_image_format,
    get_image_size
)

class TestFileUtils(unittest.TestCase):
    def setUp(self):
        """각 테스트 전에 실행됩니다."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("테스트 내용")
            
    def tearDown(self):
        """각 테스트 후에 실행됩니다."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
            
    def test_ensure_directory(self):
        """디렉토리 생성 테스트"""
        test_path = os.path.join(self.test_dir, "new_dir")
        ensure_directory(test_path)
        self.assertTrue(os.path.exists(test_path))
        os.rmdir(test_path)
        
    def test_get_safe_path(self):
        """안전한 파일 경로 생성 테스트"""
        base_name = "test file"
        ext = ".txt"
        path = get_safe_path(self.test_dir, base_name, ext)
        self.assertTrue(path.endswith("test_file.txt"))
        
    def test_file_operations(self):
        """파일 작업 테스트"""
        # 복사 테스트
        copy_path = os.path.join(self.test_dir, "copy.txt")
        self.assertTrue(copy_file(self.test_file, copy_path))
        self.assertTrue(os.path.exists(copy_path))
        
        # 이동 테스트
        move_path = os.path.join(self.test_dir, "moved.txt")
        self.assertTrue(move_file(copy_path, move_path))
        self.assertFalse(os.path.exists(copy_path))
        self.assertTrue(os.path.exists(move_path))
        
        # 삭제 테스트
        self.assertTrue(delete_file(move_path))
        self.assertFalse(os.path.exists(move_path))
        
    def test_get_file_info(self):
        """파일 정보 조회 테스트"""
        info = get_file_info(self.test_file)
        self.assertTrue(info["exists"])
        self.assertTrue(info["size"] > 0)
        self.assertTrue(info["created"])
        self.assertTrue(info["modified"])
        
    def test_clean_empty_dirs(self):
        """빈 디렉토리 정리 테스트"""
        empty_dir = os.path.join(self.test_dir, "empty")
        os.makedirs(empty_dir)
        self.assertTrue(clean_empty_dirs(self.test_dir))
        self.assertFalse(os.path.exists(empty_dir))

class TestImageUtils(unittest.TestCase):
    def setUp(self):
        """각 테스트 전에 실행됩니다."""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """각 테스트 후에 실행됩니다."""
        for root, dirs, files in os.walk(self.test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.test_dir)
        
    def create_test_image(self):
        """테스트용 이미지를 생성합니다."""
        from PIL import Image
        image_path = os.path.join(self.test_dir, "test.png")
        img = Image.new('RGB', (100, 100), color='red')
        img.save(image_path)
        return image_path
        
    def test_image_operations(self):
        """이미지 작업 테스트"""
        image_path = self.create_test_image()
        
        # 이미지 로드 테스트
        pixmap = load_image(image_path)
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        
        # 크기 조정 테스트
        resized = resize_image(pixmap, QSize(50, 50))
        self.assertEqual(resized.width(), 50)
        
        # 썸네일 생성 테스트
        thumb = create_thumbnail(image_path)
        self.assertIsNotNone(thumb)
        self.assertLessEqual(thumb.width(), 200)
        self.assertLessEqual(thumb.height(), 200)
        
        # 이미지 유효성 검사 테스트
        self.assertTrue(is_valid_image(image_path))
        self.assertFalse(is_valid_image("non_existent.png"))
        
        # 이미지 정보 조회 테스트
        size = get_image_size(image_path)
        self.assertEqual(size.width(), 100)
        self.assertEqual(size.height(), 100)
        
if __name__ == '__main__':
    unittest.main() 