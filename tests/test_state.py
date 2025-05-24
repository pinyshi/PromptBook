import os
import json
import tempfile
import unittest
from datetime import datetime
from promptbook.state import State

class TestState(unittest.TestCase):
    def setUp(self):
        """각 테스트 전에 실행됩니다."""
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.test_dir, "test_state.json")
        self.state = State(self.state_file)
        
    def tearDown(self):
        """각 테스트 후에 실행됩니다."""
        # 임시 파일 삭제
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        os.rmdir(self.test_dir)
        
    def test_initial_state(self):
        """초기 상태가 올바르게 생성되는지 테스트합니다."""
        self.assertTrue(isinstance(self.state.books, dict))
        self.assertTrue(isinstance(self.state.characters, list))
        self.assertTrue(len(self.state.books) > 0)  # 기본 샘플 북이 있어야 함
        
    def test_save_and_load(self):
        """상태 저장 및 로드가 올바르게 작동하는지 테스트합니다."""
        # 테스트용 데이터 생성
        test_book = {
            "emoji": "📘",
            "pages": [],
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        }
        self.state.books["테스트 북"] = test_book
        
        # 저장
        self.state.save()
        
        # 새 상태 객체 생성하여 로드
        new_state = State(self.state_file)
        
        # 데이터 검증
        self.assertIn("테스트 북", new_state.books)
        self.assertEqual(new_state.books["테스트 북"]["emoji"], "📘")
        
    def test_backup_and_restore(self):
        """백업 및 복원이 올바르게 작동하는지 테스트합니다."""
        # 테스트용 데이터 생성
        test_book = {
            "emoji": "📙",
            "pages": [],
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        }
        self.state.books["백업 테스트"] = test_book
        self.state.save()
        
        # 백업
        self.state.backup()
        
        # 백업 파일 찾기
        backup_dir = os.path.join(os.path.dirname(self.state_file), "backup")
        backup_files = os.listdir(backup_dir)
        self.assertTrue(len(backup_files) > 0)
        
        # 백업 파일에서 복원
        backup_path = os.path.join(backup_dir, backup_files[0])
        success = self.state.restore_backup(backup_path)
        
        # 검증
        self.assertTrue(success)
        self.assertIn("백업 테스트", self.state.books)
        self.assertEqual(self.state.books["백업 테스트"]["emoji"], "📙")
        
    def test_default_state_creation(self):
        """기본 상태가 올바르게 생성되는지 테스트합니다."""
        # 상태 파일 삭제
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
            
        # 새 상태 객체 생성
        new_state = State(self.state_file)
        
        # 기본 상태 검증
        self.assertIn("샘플 북", new_state.books)
        self.assertEqual(new_state.books["샘플 북"]["emoji"], "📕")
        self.assertTrue(len(new_state.books["샘플 북"]["pages"]) > 0)
        
if __name__ == '__main__':
    unittest.main() 