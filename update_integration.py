#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py에 업데이트 기능을 통합하는 스크립트
"""

import re

def integrate_update_feature():
    """main.py에 업데이트 기능을 통합"""
    
    # main.py 파일 읽기
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. check_for_updates 메서드 추가
    method_code = '''
    def check_for_updates(self):
        """업데이트 확인 및 다운로드"""
        try:
            # 현재 버전 가져오기
            current_version = VERSION
            
            # 업데이트 다이얼로그 표시
            from update_dialog import UpdateDialog
            dialog = UpdateDialog(current_version, self)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "업데이트 확인 오류",
                f"업데이트 확인 중 오류가 발생했습니다:\\n{str(e)}"
            )
'''
    
    # show_ai_tester 메서드 바로 앞에 추가
    if '# def show_ai_tester(self):' in content:
        content = content.replace(
            '    # def show_ai_tester(self):',
            method_code + '\n    # def show_ai_tester(self):'
        )
    
    # 2. 메뉴에 업데이트 확인 항목 추가
    menu_pattern = r'(menu\.addAction\(donate_action\))\s*\n\s*\n\s*(# AI 기능 테스터)'
    menu_replacement = r'''\1
        
        # 업데이트 확인
        update_action = QAction("🔄 업데이트 확인", self)
        update_action.triggered.connect(self.check_for_updates)
        menu.addAction(update_action)
        
        \2'''
    
    content = re.sub(menu_pattern, menu_replacement, content)
    
    # 파일 저장
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 업데이트 기능이 main.py에 성공적으로 통합되었습니다!")
    print("📋 추가된 기능:")
    print("   - check_for_updates() 메서드")
    print("   - 햄버거 메뉴에 '🔄 업데이트 확인' 항목")

if __name__ == "__main__":
    integrate_update_feature() 