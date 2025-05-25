#!/usr/bin/env python3
"""
main.py 파일에서 self.state.books[self.current_book]["pages"] = self.state.characters 
패턴을 찾아 안전성 검사를 추가하는 스크립트
"""

import re

def fix_safety_checks():
    print("main.py 파일 읽는 중...")
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    fixed_lines = []
    changes_made = 0
    
    print(f"총 {len(lines)}줄 검사 중...")
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 이미 수정된 패턴인지 확인
        if 'if self.current_book and self.current_book in self.state.books:' in line:
            # 다음 줄이 self.state.books 할당인지 확인
            if i + 1 < len(lines) and 'self.state.books[self.current_book]["pages"] = self.state.characters' in lines[i + 1]:
                print(f"라인 {i+1}: 이미 수정됨 - 건너뜀")
                fixed_lines.append(line)
                i += 1
                continue
        
        # 수정이 필요한 패턴인지 확인
        if 'self.state.books[self.current_book]["pages"] = self.state.characters' in line and 'if self.current_book and self.current_book in self.state.books:' not in lines[i-1] if i > 0 else True:
            print(f"라인 {i+1}: 수정 필요 - {line.strip()}")
            
            # 들여쓰기 추출
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent
            
            # 안전성 검사 추가
            fixed_lines.append(f"{indent_str}if self.current_book and self.current_book in self.state.books:")
            fixed_lines.append(f"{indent_str}    self.state.books[self.current_book][\"pages\"] = self.state.characters")
            changes_made += 1
        else:
            fixed_lines.append(line)
        
        i += 1
    
    if changes_made > 0:
        print(f"\n{changes_made}개 위치 수정됨. 파일 저장 중...")
        # 파일에 쓰기
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(fixed_lines))
        print("안전성 검사 추가 완료!")
    else:
        print("수정할 위치가 없습니다.")

if __name__ == "__main__":
    fix_safety_checks() 