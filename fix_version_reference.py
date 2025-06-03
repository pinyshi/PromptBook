#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py에서 VERSION 참조를 self.VERSION으로 수정하는 스크립트
"""

def fix_version_reference():
    """VERSION 참조를 self.VERSION으로 수정"""
    
    # main.py 파일 읽기
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # VERSION을 self.VERSION으로 수정
    content = content.replace(
        'current_version = VERSION',
        'current_version = self.VERSION'
    )
    
    # 파일 저장
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ VERSION 참조가 self.VERSION으로 수정되었습니다!")

if __name__ == "__main__":
    fix_version_reference() 