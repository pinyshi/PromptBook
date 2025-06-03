#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UpdateDialog 호출 시 매개변수 순서를 수정하는 스크립트
"""

def fix_dialog_params():
    """UpdateDialog 호출 시 매개변수 순서 수정"""
    
    # main.py 파일 읽기
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # UpdateDialog 호출 부분 수정
    content = content.replace(
        'dialog = UpdateDialog(current_version, self)',
        'dialog = UpdateDialog(self, current_version)'
    )
    
    # 파일 저장
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ UpdateDialog 매개변수 순서가 수정되었습니다!")

if __name__ == "__main__":
    fix_dialog_params() 