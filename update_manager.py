#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
자동 업데이트 관리자
GitHub 릴리스 API를 사용하여 최신 버전 확인 및 업데이트 기능 제공
"""

import os
import sys
import json
import zipfile
import tempfile
import subprocess
import webbrowser
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError, HTTPError
from packaging import version
import shutil

class UpdateManager:
    """자동 업데이트 관리 클래스"""
    
    def __init__(self, current_version, repo_owner="pinyshi", repo_name="PromptBook"):
        self.current_version = current_version.replace('v', '')  # v2.3.6 → 2.3.6
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        
    def check_for_updates(self):
        """
        최신 버전 확인
        Returns:
            dict: 업데이트 정보 또는 None
        """
        try:
            print(f"[UPDATE] 최신 버전 확인 중... (현재: v{self.current_version})")
            
            # GitHub API 호출
            with urlopen(self.api_url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data['tag_name'].replace('v', '')
            release_url = data['html_url']
            download_url = None
            
            # PromptBook ZIP 파일 찾기
            for asset in data.get('assets', []):
                if asset['name'].startswith('PromptBook_') and asset['name'].endswith('.zip'):
                    download_url = asset['browser_download_url']
                    break
            
            print(f"[UPDATE] 최신 버전: v{latest_version}")
            
            # 버전 비교
            if version.parse(latest_version) > version.parse(self.current_version):
                return {
                    'available': True,
                    'latest_version': latest_version,
                    'current_version': self.current_version,
                    'release_url': release_url,
                    'download_url': download_url,
                    'release_notes': data.get('body', ''),
                    'published_at': data.get('published_at', '')
                }
            else:
                print(f"[UPDATE] 최신 버전입니다!")
                return {'available': False}
                
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            print(f"[UPDATE] 업데이트 확인 실패: {e}")
            return None
        except Exception as e:
            print(f"[UPDATE] 예상치 못한 오류: {e}")
            return None
    
    def download_update(self, download_url, progress_callback=None):
        """
        업데이트 파일 다운로드
        Args:
            download_url (str): 다운로드 URL
            progress_callback (callable): 진행률 콜백 함수
        Returns:
            str: 다운로드된 파일 경로 또는 None
        """
        try:
            # 임시 디렉토리에 다운로드
            temp_dir = tempfile.mkdtemp()
            filename = download_url.split('/')[-1]
            temp_file = os.path.join(temp_dir, filename)
            
            print(f"[UPDATE] 다운로드 중: {filename}")
            
            def report_progress(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    downloaded = block_num * block_size
                    percent = min(100, (downloaded * 100) // total_size)
                    progress_callback(percent)
            
            urlretrieve(download_url, temp_file, reporthook=report_progress)
            
            print(f"[UPDATE] 다운로드 완료: {temp_file}")
            return temp_file
            
        except Exception as e:
            print(f"[UPDATE] 다운로드 실패: {e}")
            return None
    
    def extract_update(self, zip_path, extract_to=None):
        """
        업데이트 파일 압축 해제
        Args:
            zip_path (str): ZIP 파일 경로
            extract_to (str): 압축 해제 경로 (기본: 임시 폴더)
        Returns:
            str: 압축 해제된 폴더 경로 또는 None
        """
        try:
            if extract_to is None:
                extract_to = tempfile.mkdtemp()
            
            print(f"[UPDATE] 압축 해제 중: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            
            # PromptBook 폴더 찾기
            promptbook_folder = None
            for item in os.listdir(extract_to):
                item_path = os.path.join(extract_to, item)
                if os.path.isdir(item_path) and 'PromptBook' in item:
                    promptbook_folder = item_path
                    break
            
            if promptbook_folder:
                print(f"[UPDATE] 압축 해제 완료: {promptbook_folder}")
                return promptbook_folder
            else:
                print(f"[UPDATE] PromptBook 폴더를 찾을 수 없습니다")
                return None
                
        except Exception as e:
            print(f"[UPDATE] 압축 해제 실패: {e}")
            return None
    
    def apply_update(self, update_folder):
        """
        업데이트 적용
        Args:
            update_folder (str): 업데이트 파일들이 있는 폴더
        Returns:
            bool: 성공 여부
        """
        try:
            current_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
            
            print(f"[UPDATE] 업데이트 적용 중...")
            print(f"[UPDATE] 현재 디렉토리: {current_dir}")
            print(f"[UPDATE] 업데이트 폴더: {update_folder}")
            
            # 백업 폴더 생성
            backup_dir = os.path.join(current_dir, f"backup_v{self.current_version}")
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            os.makedirs(backup_dir)
            
            # 현재 파일들 백업
            for item in os.listdir(current_dir):
                if item not in ['backup', 'data', 'images'] and not item.startswith('backup_'):
                    src = os.path.join(current_dir, item)
                    dst = os.path.join(backup_dir, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        shutil.copytree(src, dst)
            
            # 새 파일들 복사
            for item in os.listdir(update_folder):
                src = os.path.join(update_folder, item)
                dst = os.path.join(current_dir, item)
                
                if os.path.exists(dst):
                    if os.path.isfile(dst):
                        os.remove(dst)
                    elif os.path.isdir(dst):
                        shutil.rmtree(dst)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst)
            
            print(f"[UPDATE] 업데이트 적용 완료!")
            return True
            
        except Exception as e:
            print(f"[UPDATE] 업데이트 적용 실패: {e}")
            return False
    
    def restart_application(self):
        """애플리케이션 재시작"""
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 실행 파일
                print(f"[UPDATE] 실행 파일 재시작 중...")
                subprocess.Popen([sys.executable])
                sys.exit(0)
            else:
                # 개발 환경 - 수동 재시작 안내
                print(f"[UPDATE] 개발 환경에서는 수동 재시작이 필요합니다.")
                print(f"[UPDATE] 프로그램을 종료하고 다시 실행해주세요.")
                return False
            
        except Exception as e:
            print(f"[UPDATE] 재시작 실패: {e}")
            return False
    
    def open_release_page(self):
        """GitHub 릴리스 페이지 열기"""
        url = f"https://github.com/{self.repo_owner}/{self.repo_name}/releases"
        webbrowser.open(url)


def test_update_manager():
    """테스트 함수"""
    manager = UpdateManager("2.3.5")  # 테스트용 낮은 버전
    
    print("=== 업데이트 확인 테스트 ===")
    update_info = manager.check_for_updates()
    
    if update_info is None:
        print("업데이트 확인 실패")
    elif update_info['available']:
        print(f"업데이트 가능: v{update_info['current_version']} → v{update_info['latest_version']}")
        print(f"다운로드 URL: {update_info['download_url']}")
    else:
        print("최신 버전입니다")


if __name__ == "__main__":
    test_update_manager() 