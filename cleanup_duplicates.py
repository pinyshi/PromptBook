#!/usr/bin/env python3
"""
중복된 안전성 검사를 정리하는 스크립트
"""

def cleanup_duplicates():
    print("main.py 파일 읽는 중...")
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    cleaned_lines = []
    i = 0
    removed_count = 0
    
    print(f"총 {len(lines)}줄 검사 중...")
    
    while i < len(lines):
        line = lines[i]
        
        # 중복된 패턴 확인: 연속된 두 줄이 같은 안전성 검사인 경우
        if ('if self.current_book and self.current_book in self.state.books:' in line and 
            i + 1 < len(lines) and 
            'if self.current_book and self.current_book in self.state.books:' in lines[i + 1]):
            
            print(f"라인 {i+1}: 중복된 안전성 검사 발견 - 제거")
            print(f"  현재: {line.strip()}")
            print(f"  다음: {lines[i + 1].strip()}")
            # 첫 번째 것만 유지하고 두 번째는 건너뜀
            cleaned_lines.append(line)
            i += 1  # 다음 줄(중복)은 건너뜀
            removed_count += 1
            
        # 중복된 할당문 확인
        elif ('self.state.books[self.current_book]["pages"] = self.state.characters' in line and
              i + 1 < len(lines) and
              'self.state.books[self.current_book]["pages"] = self.state.characters' in lines[i + 1]):
            
            print(f"라인 {i+1}: 중복된 할당문 발견 - 제거")
            print(f"  현재: {line.strip()}")
            print(f"  다음: {lines[i + 1].strip()}")
            # 첫 번째 것만 유지하고 두 번째는 건너뜀
            cleaned_lines.append(line)
            i += 1  # 다음 줄(중복)은 건너뜀
            removed_count += 1
            
        else:
            cleaned_lines.append(line)
        
        i += 1
    
    if removed_count > 0:
        print(f"\n{removed_count}개 중복 제거됨. 파일 저장 중...")
        # 파일에 쓰기
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(cleaned_lines))
        print("중복 정리 완료!")
    else:
        print("중복이 없습니다.")

if __name__ == "__main__":
    cleanup_duplicates() 