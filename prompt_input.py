import sys
import os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

def get_app_directory():
    """실행 파일의 디렉토리를 반환합니다."""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 exe 파일인 경우
        return os.path.dirname(sys.executable)
    else:
        # 개발 환경에서 실행하는 경우
        return os.path.dirname(os.path.abspath(__file__))

class CustomTextEdit(QTextEdit):
    """메모장 스타일의 자동완성 텍스트 에디트 (프롬프트북 로직 적용)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._completer = None
        self.prompt_display_map = {}
        
        # 텍스트 에디트 설정
        self.setAcceptRichText(False)  # 서식 있는 텍스트 비활성화
        self.setLineWrapMode(QTextEdit.WidgetWidth)  # 자동 줄바꿈 활성화
        self.setWordWrapMode(QTextOption.WrapAnywhere)  # 어디서든 줄바꿈 (텍스트 위주)
        
    def set_custom_completer(self, completer):
        """자동 완성기를 설정합니다."""
        if self._completer:
            self._completer.disconnect(self)
            
        self._completer = completer
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.activated.connect(self.insert_completion)
        
        # 텍스트 변경 시 자동완성 업데이트 연결
        self.textChanged.connect(self.update_completion)
        
    def update_completion(self):
        """자동 완성을 업데이트합니다. (현재 줄 기준으로 처리)"""
        if not self._completer:
            return
            
        # 포커스 체크 - 포커스가 없으면 팝업 숨기기
        if QApplication.focusWidget() != self:
            self._completer.popup().hide()
            return
            
        # 현재 커서와 줄 정보 가져오기
        cursor = self.textCursor()
        current_pos = cursor.position()
        
        # 현재 줄의 시작 위치와 텍스트 가져오기
        temp_cursor = QTextCursor(cursor)
        temp_cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        line_start_pos = temp_cursor.selectionStart()
        line_text = temp_cursor.selectedText()
        
        # 현재 줄에서 커서 위치까지의 텍스트
        text_before_cursor = line_text[:current_pos - line_start_pos]
        last_comma = text_before_cursor.rfind(",")
        
        if last_comma >= 0:
            text = text_before_cursor[last_comma + 1:].strip()
            prefix_start_pos = line_start_pos + last_comma + 1
        else:
            text = text_before_cursor.strip()
            prefix_start_pos = line_start_pos
            
        # 빈 텍스트이거나 공백만 있는 경우 팝업 숨기기
        if not text:
            self._completer.popup().hide()
            return
            
        # 자동완성 업데이트
        self._completer.setCompletionPrefix(text)
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        
        # 공백 건너뛰기
        while prefix_start_pos < current_pos and self.toPlainText()[prefix_start_pos].isspace():
            prefix_start_pos += 1
        
        # 팝업 위치 계산을 위한 임시 커서
        temp_cursor = QTextCursor(self.document())
        temp_cursor.setPosition(prefix_start_pos)
        
        # 팝업 위치 및 크기 설정
        rect = self.cursorRect(temp_cursor)
        popup_width = popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width()
        popup_height = min(popup.sizeHint().height(), 200)  # 최대 높이 제한
        
        # 커서 위치의 전역 좌표
        cursor_global_pos = self.mapToGlobal(rect.bottomLeft())
        
        # 화면 크기 가져오기
        screen = QApplication.primaryScreen().geometry()
        
        # 아래쪽에 팝업을 표시할 공간이 충분한지 확인
        space_below = screen.bottom() - cursor_global_pos.y()
        space_above = cursor_global_pos.y() - screen.top()
        
        # 팝업 위치 결정
        if space_below >= popup_height + 10:  # 아래쪽에 충분한 공간이 있으면
            popup_pos = cursor_global_pos
            popup_pos.setY(popup_pos.y() + 5)  # 커서 아래 5픽셀 여백
        elif space_above >= popup_height + 10:  # 위쪽에 충분한 공간이 있으면
            popup_pos = self.mapToGlobal(rect.topLeft())
            popup_pos.setY(popup_pos.y() - popup_height - 5)  # 커서 위 5픽셀 여백
        else:  # 공간이 부족하면 아래쪽에 표시하되 화면 안에 맞춤
            popup_pos = cursor_global_pos
            popup_pos.setY(min(popup_pos.y() + 5, screen.bottom() - popup_height))
        
        # X 좌표도 화면 안에 맞춤
        popup_pos.setX(min(popup_pos.x(), screen.right() - popup_width))
        popup_pos.setX(max(popup_pos.x(), screen.left()))
        
        # 팝업 표시 위치 조정 (비동기로 처리)
        QTimer.singleShot(0, lambda: (
            popup.move(popup_pos),
            popup.show(),
            popup.raise_()
        ))
        
    def insert_completion(self, completion):
        """자동 완성 텍스트를 삽입합니다. (QTextEdit 커서 위치 보존)"""
        # 실제로 삽입할 텍스트 (매핑된 값이 있으면 사용)
        insert_text = self.prompt_display_map.get(completion, completion)
        
        # 현재 커서 가져오기
        cursor = self.textCursor()
        current_pos = cursor.position()
        
        # 현재 줄의 시작 위치 찾기
        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        line_start_pos = cursor.selectionStart()
        line_text = cursor.selectedText()
        
        # 커서를 원래 위치로 복원
        cursor.setPosition(current_pos)
        
        # 현재 줄에서 마지막 쉼표 위치 찾기
        text_before_cursor = line_text[:current_pos - line_start_pos]
        last_comma = text_before_cursor.rfind(",")
        
        if last_comma >= 0:
            # 쉼표 이후의 텍스트 선택하여 교체
            start_pos = line_start_pos + last_comma + 1
            # 공백 건너뛰기
            while start_pos < current_pos and self.toPlainText()[start_pos].isspace():
                start_pos += 1
            
            # 교체할 범위 선택
            cursor.setPosition(start_pos)
            cursor.setPosition(current_pos, QTextCursor.KeepAnchor)
            
            # 선택된 텍스트를 자동완성 텍스트로 교체하고 쉼표 추가
            cursor.insertText(insert_text + ", ")
        else:
            # 현재 줄의 시작부터 커서까지 선택하여 교체
            cursor.setPosition(line_start_pos)
            cursor.setPosition(current_pos, QTextCursor.KeepAnchor)
            cursor.insertText(insert_text + ", ")
        
        # 커서 위치는 insertText 후 자동으로 적절한 위치에 설정됨
        
    def keyPressEvent(self, event):
        """키 입력 이벤트 처리"""
        # 자동완성 팝업이 표시되어 있을 때의 키 처리
        if self._completer and self._completer.popup().isVisible():
            # Enter, Return, Tab 키로 자동 완성 선택
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                # 현재 선택된 항목의 텍스트를 가져오기
                popup = self._completer.popup()
                current_index = popup.currentIndex()
                if current_index.isValid():
                    # 선택된 항목의 실제 텍스트 가져오기
                    selected_text = current_index.data(Qt.DisplayRole)
                    self.insert_completion(selected_text)
                else:
                    # 선택된 항목이 없으면 첫 번째 항목 사용
                    self.insert_completion(self._completer.currentCompletion())
                popup.hide()
                return
            # Escape 키로 자동완성 팝업 닫기
            elif event.key() == Qt.Key_Escape:
                self._completer.popup().hide()
                return
            
        super().keyPressEvent(event)


class PromptInput(QMainWindow):
    """프롬프트 입력기 메인 윈도우"""
    
    VERSION = "v1.5"
    
    def __init__(self):
        super().__init__()
        # 창 고정 상태 변수
        self.always_on_top = False
        # 시스템 트레이 상주 상태 변수
        self.stay_in_tray = False
        # 윈도우 투명도 (0.0 ~ 1.0, 기본값 1.0 = 불투명)
        self.window_opacity = 1.0
        # 옵션 패널 표시 상태
        self.options_visible = False
        
        # 모든 에러 대화상자 차단
        self.disable_all_error_dialogs()
        
        self.setup_ui()
        self.setup_autocomplete()
        self.setup_shortcuts()
        self.setup_system_tray()
        
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle(f"프롬프트 입력기 {self.VERSION}")
        # 초기 크기를 컴팩트하게 설정 (옵션 숨김 상태)
        self.compact_height = 170  # 상태바 제거로 더 작게
        self.expanded_height = 280  # 상태바 제거로 더 작게
        self.setFixedSize(600, self.compact_height)
        
        # 상태바 숨기기
        self.statusBar().hide()
        
        # 아이콘 설정 (프롬프트 입력기 전용 아이콘)
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 exe에서는 임시 폴더의 아이콘 사용
                icon_path = os.path.join(sys._MEIPASS, "prompt_input_icon.ico")
                if os.path.exists(icon_path):
                    self.setWindowIcon(QIcon(icon_path))
                else:
                    # 대체 아이콘 시도
                    fallback_path = os.path.join(sys._MEIPASS, "icon.ico")
                    if os.path.exists(fallback_path):
                        self.setWindowIcon(QIcon(fallback_path))
                    else:
                        print("[DEBUG] 내장된 아이콘 파일을 찾을 수 없습니다.")
            else:
                # 개발 환경에서는 로컬 아이콘 파일 사용
                if os.path.exists("prompt_input_icon.ico"):
                    self.setWindowIcon(QIcon("prompt_input_icon.ico"))
                elif os.path.exists("icon.ico"):
                    self.setWindowIcon(QIcon("icon.ico"))
                elif os.path.exists("icon.png"):
                    self.setWindowIcon(QIcon("icon.png"))
                else:
                    print("[DEBUG] 개발 환경: 아이콘 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"[DEBUG] 아이콘 설정 실패: {e}")
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 레이아웃
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(8)  # 간격 줄임
        layout.setContentsMargins(10, 10, 10, 10)  # 여백 줄임
        
        # 프롬프트 입력란 (메모장 스타일 텍스트 에디트)
        self.prompt_input = CustomTextEdit()
        self.prompt_input.setPlaceholderText("프롬프트를 쉼표로 구분해서 입력하세요.")
        self.prompt_input.setMinimumHeight(120)  # 더 컴팩트하게
        layout.addWidget(self.prompt_input)
        
        # 메인 버튼 레이아웃 (항상 보이는 부분)
        main_button_layout = QHBoxLayout()
        main_button_layout.setSpacing(8)
        
        # 복사 버튼
        self.copy_button = QPushButton("📋 복사")
        self.copy_button.clicked.connect(self.copy_prompt_to_clipboard)
        self.copy_button.setMinimumHeight(28)
        self.copy_button.setMaximumWidth(70)
        self.copy_button.setToolTip("프롬프트를 클립보드에 복사합니다 (Ctrl+Shift+C)")
        main_button_layout.addWidget(self.copy_button)
        
        # 저장 버튼
        self.save_button = QPushButton("💾 저장")
        self.save_button.clicked.connect(self.save_to_txt_file)
        self.save_button.setMinimumHeight(28)
        self.save_button.setMaximumWidth(70)
        self.save_button.setToolTip("프롬프트를 txt 파일로 저장합니다 (Ctrl+S)")
        main_button_layout.addWidget(self.save_button)
        
        # 불러오기 버튼
        self.load_button = QPushButton("📂 열기")
        self.load_button.clicked.connect(self.load_from_txt_file)
        self.load_button.setMinimumHeight(28)
        self.load_button.setMaximumWidth(70)
        self.load_button.setToolTip("txt 파일에서 프롬프트를 불러옵니다 (Ctrl+O)")
        main_button_layout.addWidget(self.load_button)
        
        # 옵션 토글 버튼
        self.toggle_button = QPushButton("⚙️ 옵션")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(self.options_visible)
        self.toggle_button.clicked.connect(self.toggle_options)
        self.toggle_button.setMinimumHeight(28)
        self.toggle_button.setMaximumWidth(70)
        self.toggle_button.setToolTip("고급 옵션을 표시/숨김합니다 (Ctrl+Alt+O)")
        main_button_layout.addWidget(self.toggle_button)
        
        # 여백 추가
        main_button_layout.addStretch()
        
        layout.addLayout(main_button_layout)
        
        # 옵션 패널 (숨김/표시 가능)
        self.options_widget = QWidget()
        self.options_widget.setVisible(self.options_visible)
        
        options_layout = QVBoxLayout(self.options_widget)
        options_layout.setSpacing(6)
        options_layout.setContentsMargins(0, 5, 0, 0)
        
        # 창 고정 옵션
        pin_layout = QHBoxLayout()
        self.pin_button = QPushButton("📌 맨 위에 고정")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(self.always_on_top)
        self.pin_button.clicked.connect(self.toggle_always_on_top)
        self.pin_button.setMinimumHeight(26)
        self.pin_button.setMaximumWidth(110)
        self.pin_button.setToolTip("창을 다른 모든 창 위에 고정합니다 (Ctrl+T)")
        pin_layout.addWidget(self.pin_button)
        pin_layout.addStretch()
        options_layout.addLayout(pin_layout)
        
        # 투명도 조절
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("🔍 투명도:")
        opacity_label.setMinimumWidth(50)
        opacity_layout.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(30)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(self.window_opacity * 100))
        self.opacity_slider.setMaximumWidth(120)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.opacity_slider.setToolTip("창의 투명도를 조절합니다 (30% ~ 100%)\nCtrl+Plus: 투명도 증가, Ctrl+Minus: 투명도 감소, Ctrl+0: 리셋")
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_value_label = QLabel(f"{int(self.window_opacity * 100)}%")
        self.opacity_value_label.setMinimumWidth(35)
        self.opacity_value_label.setAlignment(Qt.AlignCenter)
        opacity_layout.addWidget(self.opacity_value_label)
        
        opacity_layout.addStretch()
        options_layout.addLayout(opacity_layout)
        
        # 시스템 트레이 옵션
        tray_layout = QHBoxLayout()
        self.tray_checkbox = QCheckBox("🔽 시스템 트레이에 상주")
        self.tray_checkbox.setChecked(self.stay_in_tray)
        self.tray_checkbox.toggled.connect(self.toggle_system_tray)
        self.tray_checkbox.setToolTip("체크하면 X로 닫아도 프로그램이 종료되지 않고 시스템 트레이에 남아있습니다")
        tray_layout.addWidget(self.tray_checkbox)
        tray_layout.addStretch()
        options_layout.addLayout(tray_layout)
        
        layout.addWidget(self.options_widget)
        
    def setup_autocomplete(self):
        """자동완성 설정 (프롬프트북과 완전히 동일)"""
        try:
            autocomplete_path = os.path.join(get_app_directory(), "autocomplete.txt")
            with open(autocomplete_path, 'r', encoding='utf-8') as f:
                prompts = [line.strip() for line in f if line.strip()]
            completer = QCompleter(prompts)
            self.prompt_input.set_custom_completer(completer)

        except Exception as e:
            print(f"자동완성 목록 로드 실패: {e}")
            # 기본 자동완성 목록 사용
            default_prompts = ["masterpiece", "best quality", "ultra-detailed", "8k uhd", "highres"]
            completer = QCompleter(default_prompts)
            self.prompt_input.set_custom_completer(completer)

    
    def copy_prompt_to_clipboard(self):
        """프롬프트를 클립보드에 복사 (프롬프트북과 동일)"""
        QApplication.clipboard().setText(self.prompt_input.toPlainText())
        QToolTip.showText(self.copy_button.mapToGlobal(self.copy_button.rect().center()), "프롬프트가 복사되었습니다.")
    
    def save_to_txt_file(self):
        """프롬프트를 txt 파일로 저장"""
        try:
            text = self.prompt_input.toPlainText().strip()
            if not text:
                QToolTip.showText(self.save_button.mapToGlobal(self.save_button.rect().center()), "저장할 내용이 없습니다.")
                return
            
            # 파일 저장 대화상자
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "프롬프트 저장",
                "prompt.txt",
                "텍스트 파일 (*.txt);;모든 파일 (*.*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                QToolTip.showText(self.save_button.mapToGlobal(self.save_button.rect().center()), "파일이 저장되었습니다.")
                print(f"[DEBUG] 프롬프트 저장 완료: {file_path}")
                
        except Exception as e:
            QToolTip.showText(self.save_button.mapToGlobal(self.save_button.rect().center()), f"저장 실패: {str(e)}")
            print(f"[DEBUG] 프롬프트 저장 실패: {e}")
    
    def load_from_txt_file(self):
        """txt 파일에서 프롬프트 불러오기"""
        try:
            # 파일 열기 대화상자
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "프롬프트 불러오기",
                "",
                "텍스트 파일 (*.txt);;모든 파일 (*.*)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 현재 내용이 있으면 확인
                current_text = self.prompt_input.toPlainText().strip()
                if current_text:
                    reply = QMessageBox.question(
                        self,
                        "프롬프트 불러오기",
                        "현재 내용을 덮어쓰시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        return
                
                self.prompt_input.setPlainText(content)
                QToolTip.showText(self.load_button.mapToGlobal(self.load_button.rect().center()), "파일이 불러와졌습니다.")
                print(f"[DEBUG] 프롬프트 불러오기 완료: {file_path}")
                
        except Exception as e:
            QToolTip.showText(self.load_button.mapToGlobal(self.load_button.rect().center()), f"불러오기 실패: {str(e)}")
            print(f"[DEBUG] 프롬프트 불러오기 실패: {e}")
    
    def setup_shortcuts(self):
        """단축키 설정"""
        # 창 고정 단축키 (Ctrl+T)
        pin_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        pin_shortcut.activated.connect(self.toggle_always_on_top)
        
        # 복사 단축키 (Ctrl+C는 기본 복사와 겹치므로 Ctrl+Shift+C 사용)
        copy_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        copy_shortcut.activated.connect(self.copy_prompt_to_clipboard)
        
        # 파일 저장 단축키
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_to_txt_file)
        
        # 파일 열기 단축키
        open_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        open_shortcut.activated.connect(self.load_from_txt_file)
        
        # 투명도 조절 단축키
        opacity_up_shortcut = QShortcut(QKeySequence("Ctrl+Plus"), self)
        opacity_up_shortcut.activated.connect(self.increase_opacity)
        
        opacity_down_shortcut = QShortcut(QKeySequence("Ctrl+Minus"), self)
        opacity_down_shortcut.activated.connect(self.decrease_opacity)
        
        # 투명도 리셋 단축키
        opacity_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        opacity_reset_shortcut.activated.connect(self.reset_opacity)
        
        # 옵션 토글 단축키 (Ctrl+O가 파일 열기와 겹치므로 변경)
        options_toggle_shortcut = QShortcut(QKeySequence("Ctrl+Alt+O"), self)
        options_toggle_shortcut.activated.connect(self.toggle_options)
    
    def toggle_always_on_top(self):
        """창 맨 위에 고정 토글"""
        self.always_on_top = not self.always_on_top
        
        # 버튼 상태 업데이트
        self.pin_button.setChecked(self.always_on_top)
        
        if self.always_on_top:
            # 맨 위에 고정 플래그 추가 (기본 플래그 유지)
            new_flags = Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowStaysOnTopHint
            self.pin_button.setText("📌 맨 위에 고정됨")
        else:
            # 맨 위에 고정 플래그 제거 (기본 플래그만 유지)
            new_flags = Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint
            self.pin_button.setText("📌 맨 위에 고정")
        
        # 창 플래그 업데이트
        self.setWindowFlags(new_flags)
        
        # 창을 다시 표시 (플래그 변경 후 필요)
        self.show()
        
        print(f"[DEBUG] 프롬프트 입력기 - 창 맨 위에 고정: {'활성화' if self.always_on_top else '비활성화'}")
    
    def toggle_options(self):
        """옵션 패널 표시/숨김 토글"""
        self.options_visible = not self.options_visible
        self.options_widget.setVisible(self.options_visible)
        
        # 창 크기 조절
        if self.options_visible:
            self.setFixedSize(600, self.expanded_height)
            self.toggle_button.setText("⚙️ 숨기기")
        else:
            self.setFixedSize(600, self.compact_height)
            self.toggle_button.setText("⚙️ 옵션")
        
        print(f"[DEBUG] 프롬프트 입력기 - 옵션 패널: {'표시' if self.options_visible else '숨김'}")
    
    def change_opacity(self, value):
        """윈도우 투명도 변경"""
        # 슬라이더 값 (30-100)을 투명도 값 (0.3-1.0)으로 변환
        self.window_opacity = value / 100.0
        
        # 윈도우 투명도 적용
        self.setWindowOpacity(self.window_opacity)
        
        # 라벨 업데이트
        self.opacity_value_label.setText(f"{value}%")
        

        
        print(f"[DEBUG] 프롬프트 입력기 - 투명도 변경: {value}%")
    
    def increase_opacity(self):
        """투명도 증가 (더 불투명하게)"""
        current_value = self.opacity_slider.value()
        new_value = min(100, current_value + 10)
        self.opacity_slider.setValue(new_value)
    
    def decrease_opacity(self):
        """투명도 감소 (더 투명하게)"""
        current_value = self.opacity_slider.value()
        new_value = max(30, current_value - 10)
        self.opacity_slider.setValue(new_value)
    
    def reset_opacity(self):
        """투명도 리셋 (100% 불투명)"""
        self.opacity_slider.setValue(100)
    
    def setup_system_tray(self):
        """시스템 트레이 설정"""
        # 시스템 트레이 지원 확인
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[DEBUG] 시스템 트레이를 사용할 수 없습니다.")
            self.tray_checkbox.setEnabled(False)
            return
        
        # 트레이 아이콘 생성
        self.tray_icon = QSystemTrayIcon(self)
        
        # 트레이 아이콘 설정 (프롬프트 입력기 전용 아이콘)
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 exe에서는 임시 폴더의 아이콘 사용
                icon_path = os.path.join(sys._MEIPASS, "prompt_input_icon.ico")
                if os.path.exists(icon_path):
                    self.tray_icon.setIcon(QIcon(icon_path))
                else:
                    # 대체 아이콘 시도
                    fallback_path = os.path.join(sys._MEIPASS, "icon.ico")
                    if os.path.exists(fallback_path):
                        self.tray_icon.setIcon(QIcon(fallback_path))
                    else:
                        # 기본 아이콘 사용
                        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            else:
                # 개발 환경에서는 로컬 아이콘 파일 사용
                if os.path.exists("prompt_input_icon.ico"):
                    self.tray_icon.setIcon(QIcon("prompt_input_icon.ico"))
                elif os.path.exists("icon.ico"):
                    self.tray_icon.setIcon(QIcon("icon.ico"))
                elif os.path.exists("icon.png"):
                    self.tray_icon.setIcon(QIcon("icon.png"))
                else:
                    # 기본 아이콘 사용
                    self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        except Exception as e:
            print(f"[DEBUG] 트레이 아이콘 설정 실패: {e}")
            # 기본 아이콘 사용
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 트레이 메뉴 생성
        tray_menu = QMenu()
        
        # 창 보이기/숨기기
        show_action = QAction("창 보이기", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("창 숨기기", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        # 프롬프트 복사
        copy_action = QAction("📋 프롬프트 복사", self)
        copy_action.triggered.connect(self.copy_prompt_to_clipboard)
        tray_menu.addAction(copy_action)
        
        # 파일 저장
        save_action = QAction("💾 파일 저장", self)
        save_action.triggered.connect(self.save_to_txt_file)
        tray_menu.addAction(save_action)
        
        # 파일 불러오기
        load_action = QAction("📂 파일 열기", self)
        load_action.triggered.connect(self.load_from_txt_file)
        tray_menu.addAction(load_action)
        
        tray_menu.addSeparator()
        
        # 종료
        quit_action = QAction("종료", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("프롬프트 입력기")
        
        # 트레이 아이콘 더블클릭 시 창 보이기
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def toggle_system_tray(self, checked):
        """시스템 트레이 상주 토글"""
        self.stay_in_tray = checked
        
        if checked:
            # 트레이 아이콘 표시
            self.tray_icon.show()
        else:
            # 트레이 아이콘 숨기기
            self.tray_icon.hide()
    
    def tray_icon_activated(self, reason):
        """트레이 아이콘 클릭 처리"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()
    
    def show_window(self):
        """창 보이기"""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def quit_application(self):
        """애플리케이션 완전 종료"""
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        QApplication.quit()
    
    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        if self.stay_in_tray and self.tray_icon.isVisible():
            # 트레이에 상주하는 경우 창만 숨기기
            event.ignore()
            self.hide()
        else:
            # 트레이에 상주하지 않는 경우 완전 종료
            event.accept()
            self.quit_application()
    
    def disable_all_error_dialogs(self):
        """모든 에러 대화상자를 시스템 레벨에서 차단"""
        try:
            import ctypes
            from ctypes import wintypes
            import warnings
            import tempfile
            import atexit
            import shutil
            import os
            
            # 1. 모든 Python 경고 완전 무시
            warnings.filterwarnings("ignore")
            
            # 2. Windows 시스템 에러 대화상자 완전 차단
            try:
                # SetErrorMode - 모든 시스템 에러 대화상자 차단
                SEM_FAILCRITICALERRORS = 0x0001      # 중요한 에러 대화상자 차단
                SEM_NOGPFAULTERRORBOX = 0x0002       # GPF 에러 대화상자 차단  
                SEM_NOOPENFILEERRORBOX = 0x8000      # 파일 열기 에러 대화상자 차단
                SEM_NOALIGNMENTFAULTEXCEPT = 0x0004  # 정렬 오류 예외 차단
                
                error_mode = (SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | 
                             SEM_NOOPENFILEERRORBOX | SEM_NOALIGNMENTFAULTEXCEPT)
                ctypes.windll.kernel32.SetErrorMode(error_mode)
                
                # SetThreadErrorMode - 현재 스레드의 에러 모드 설정
                try:
                    old_mode = wintypes.DWORD()
                    ctypes.windll.kernel32.SetThreadErrorMode(error_mode, ctypes.byref(old_mode))
                except:
                    pass
                
                # 추가: 프로세스 에러 모드 설정
                try:
                    ctypes.windll.kernel32.SetProcessErrorMode(error_mode)
                except:
                    pass
                    
            except Exception:
                pass
            
            # 3. 모든 파일/폴더 관련 함수 래핑
            try:
                # tempfile 정리 함수 무력화
                def dummy_cleanup(*args, **kwargs):
                    pass
                tempfile._cleanup = dummy_cleanup
                
                # shutil.rmtree 무력화
                original_rmtree = shutil.rmtree
                def silent_rmtree(*args, **kwargs):
                    try:
                        return original_rmtree(*args, **kwargs)
                    except:
                        pass
                shutil.rmtree = silent_rmtree
                
                # os.remove 래핑
                original_remove = os.remove
                def silent_remove(*args, **kwargs):
                    try:
                        return original_remove(*args, **kwargs)
                    except:
                        pass
                os.remove = silent_remove
                
                # os.rmdir 래핑
                original_rmdir = os.rmdir
                def silent_rmdir(*args, **kwargs):
                    try:
                        return original_rmdir(*args, **kwargs)
                    except:
                        pass
                os.rmdir = silent_rmdir
                
            except Exception:
                pass
            
            # 4. atexit 핸들러 완전 무력화
            try:
                atexit._clear()
                # 빈 핸들러만 등록
                atexit.register(lambda: None)
            except Exception:
                pass
            
            # 5. 환경 변수로 에러 무시 설정
            try:
                os.environ['PYTHONIOENCODING'] = 'utf-8'
                os.environ['PYTHONUNBUFFERED'] = '1'
                os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
            except Exception:
                pass
                
        except Exception:
            # 모든 에러 무시
            pass


class LogDialog(QDialog):
    """로그 표시용 팝업 대화상자"""
    
    def __init__(self, title, message, details=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(500, 400)
        
        # 레이아웃
        layout = QVBoxLayout(self)
        
        # 메인 메시지
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(message_label)
        
        # 상세 정보 (있는 경우)
        if details:
            details_text = QTextEdit()
            details_text.setPlainText(details)
            details_text.setReadOnly(True)
            details_text.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 10px;")
            layout.addWidget(details_text)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)
        close_button.setMinimumWidth(80)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)

def show_error_popup(title, message, details=None):
    """오류 팝업창 표시"""
    try:
        app = QApplication.instance()
        if app is not None:
            dialog = LogDialog(title, message, details)
            dialog.exec()
        else:
            # GUI가 없는 경우 콘솔에 출력
            print(f"{title}: {message}")
            if details:
                print(f"상세 정보:\n{details}")
    except Exception as e:
        # 팝업 표시 실패 시 콘솔에 출력
        print(f"{title}: {message}")
        if details:
            print(f"상세 정보:\n{details}")
        print(f"팝업 표시 실패: {e}")

def main():
    """메인 함수"""
    try:
        app = QApplication(sys.argv)
        
        # 애플리케이션 정보 설정
        app.setApplicationName("프롬프트 입력기")
        app.setApplicationVersion("1.5")
        app.setOrganizationName("PromptBook")
        
        # 애플리케이션 아이콘 설정 (작업표시줄 아이콘)
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 exe에서는 임시 폴더의 아이콘 사용
                icon_path = os.path.join(sys._MEIPASS, "prompt_input_icon.ico")
                if os.path.exists(icon_path):
                    app.setWindowIcon(QIcon(icon_path))
                else:
                    # 대체 아이콘 시도
                    fallback_path = os.path.join(sys._MEIPASS, "icon.ico")
                    if os.path.exists(fallback_path):
                        app.setWindowIcon(QIcon(fallback_path))
            else:
                # 개발 환경에서는 로컬 아이콘 파일 사용
                if os.path.exists("prompt_input_icon.ico"):
                    app.setWindowIcon(QIcon("prompt_input_icon.ico"))
                elif os.path.exists("icon.ico"):
                    app.setWindowIcon(QIcon("icon.ico"))
        except Exception as e:
            print(f"[DEBUG] 애플리케이션 아이콘 설정 실패: {e}")
        
        # 메인 윈도우 생성 및 표시
        window = PromptInput()
        window.show()
        
        # 이벤트 루프 시작
        sys.exit(app.exec())
        
    except Exception as e:
        # 메인 실행 중 오류 발생 시 팝업으로 표시
        import traceback
        error_details = traceback.format_exc()
        show_error_popup(
            "프롬프트 입력기 시작 오류",
            f"프로그램 시작 중 오류가 발생했습니다:\n{str(e)}",
            error_details
        )
        sys.exit(1)


if __name__ == "__main__":
    main() 