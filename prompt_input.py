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
    
    # 즐겨찾기 추가 신호
    favoriteRequested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._completer = None
        self.prompt_display_map = {}
        
        # 텍스트 에디트 설정
        self.setAcceptRichText(False)  # 서식 있는 텍스트 비활성화
        self.setLineWrapMode(QTextEdit.WidgetWidth)  # 자동 줄바꿈 활성화
        self.setWordWrapMode(QTextOption.WrapAnywhere)  # 어디서든 줄바꿈 (텍스트 위주)
        
        # 컨텍스트 메뉴 활성화
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
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

    def show_context_menu(self, position):
        """컨텍스트 메뉴 표시"""
        cursor = self.textCursor()
        
        # 선택된 텍스트가 있는지 확인
        if cursor.hasSelection():
            selected_text = cursor.selectedText().strip()
            
            # 양끝 공백과 쉼표만 제거 (중간 쉼표는 유지)
            cleaned_text = selected_text.strip(' ,')
            
            if cleaned_text:  # 유효한 텍스트가 있을 때만 메뉴 표시
                context_menu = QMenu(self)
                
                # 기본 컨텍스트 메뉴 액션들 추가
                standard_menu = self.createStandardContextMenu()
                for action in standard_menu.actions():
                    context_menu.addAction(action)
                
                context_menu.addSeparator()
                
                # 즐겨찾기 등록 액션 추가 (전체 텍스트를 하나로 등록)
                favorite_action = QAction("⭐ 즐겨찾기 등록", self)
                favorite_action.triggered.connect(lambda: self.favoriteRequested.emit(cleaned_text))
                favorite_action.setToolTip("선택된 텍스트 전체를 하나의 즐겨찾기로 등록합니다")
                context_menu.addAction(favorite_action)
                
                # 메뉴 표시
                context_menu.exec(self.mapToGlobal(position))
            else:
                # 기본 컨텍스트 메뉴 표시
                self.createStandardContextMenu().exec(self.mapToGlobal(position))
        else:
            # 기본 컨텍스트 메뉴 표시
            self.createStandardContextMenu().exec(self.mapToGlobal(position))


class FavoritesListWidget(QListWidget):
    """즐겨찾기 전용 리스트 위젯 (DEL키 삭제 지원)"""
    
    # 삭제 요청 신호
    deleteRequested = Signal(QListWidgetItem)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def keyPressEvent(self, event):
        """키 입력 이벤트 처리"""
        if event.key() == Qt.Key_Delete:
            # DEL 키가 눌렸을 때 현재 선택된 항목 삭제
            current_item = self.currentItem()
            if current_item:
                self.deleteRequested.emit(current_item)
                return
        
        # 기본 키 이벤트 처리
        super().keyPressEvent(event)


class PromptInput(QMainWindow):
    """AI Prompt Studio 메인 윈도우"""
    
    VERSION = "Pro v2.0"
    
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
        
        # 즐겨찾기 관련 변수
        self.favorites = []
        self.favorites_file = os.path.join(get_app_directory(), "favorites.json")
        
        # 설정 관련 변수
        self.settings = {}
        self.settings_file = os.path.join(get_app_directory(), "prompt_input_settings.json")
        
        # 현재 테마
        self.current_theme = "default"
        
        # 모든 에러 대화상자 차단
        self.disable_all_error_dialogs()
        
        # 설정 데이터 로드
        self.load_settings()
        
        # 즐겨찾기 데이터 로드
        self.load_favorites()
        
        self.setup_ui()
        self.setup_autocomplete()
        self.setup_shortcuts()
        self.setup_system_tray()
        
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle(f"AI Prompt Studio {self.VERSION}")
        
        # 윈도우 스타일 설정 - 더 현대적인 스타일
        self.setWindowFlags(
            Qt.Window | 
            Qt.WindowCloseButtonHint | 
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |  # 최대화 버튼 추가
            Qt.WindowSystemMenuHint
        )
        
        # 저장된 설정에서 값 가져오기
        self.compact_height = 220  # 최소 높이 (옵션 숨김 시) - 버튼들이 들어갈 충분한 공간
        self.expanded_height = 380  # 옵션 표시 시 최소 높이
        self.options_visible = self.settings.get('options_visible', False)
        self.window_opacity = self.settings.get('window_opacity', 1.0)
        self.always_on_top = self.settings.get('always_on_top', False)
        self.stay_in_tray = self.settings.get('stay_in_tray', False)
        
        # 윈도우 크기와 위치 설정
        window_width = self.settings.get('window_width', 650)
        window_height = self.settings.get('window_height', 170)
        window_x = self.settings.get('window_x', -1)
        window_y = self.settings.get('window_y', -1)
        
        self.setMinimumSize(500, self.compact_height)  # 최소 크기를 더 작게 설정
        self.resize(window_width, window_height)  # 저장된 크기로 설정
        
        # 윈도우 위치 설정 (-1이면 화면 중앙에 배치)
        if window_x >= 0 and window_y >= 0:
            self.move(window_x, window_y)
        # 투명도 설정
        self.setWindowOpacity(self.window_opacity)
        
        # 상태바 숨기기
        self.statusBar().hide()
        
        # 아이콘 설정 (AI Prompt Studio 전용 아이콘)
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
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 수평 스플리터 (왼쪽: 입력창+버튼, 오른쪽: 즐겨찾기)
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # 왼쪽 영역 (기존 입력창 + 버튼들)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(0, 0, 5, 0)  # 오른쪽 여백 추가
        
        # 프롬프트 입력란 (메모장 스타일 텍스트 에디트)
        self.prompt_input = CustomTextEdit()
        self.prompt_input.setPlaceholderText("프롬프트를 쉼표로 구분해서 입력하세요.")
        self.prompt_input.setMinimumHeight(100)  # 더 컴팩트하게 조정
        # 즐겨찾기 신호 연결
        self.prompt_input.favoriteRequested.connect(self.add_to_favorites)
        left_layout.addWidget(self.prompt_input)
        
        # 메인 버튼 레이아웃 (항상 보이는 부분)
        main_button_layout = QHBoxLayout()
        main_button_layout.setSpacing(8)
        
        # 복사 버튼
        self.copy_button = QPushButton("📋 복사")
        self.copy_button.clicked.connect(self.copy_prompt_to_clipboard)
        self.copy_button.setFixedHeight(30)
        self.copy_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.copy_button.setToolTip("프롬프트를 클립보드에 복사합니다 (Ctrl+Shift+C)")
        main_button_layout.addWidget(self.copy_button)
        
        # 저장 버튼
        self.save_button = QPushButton("💾 저장")
        self.save_button.clicked.connect(self.save_to_txt_file)
        self.save_button.setFixedHeight(30)
        self.save_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.save_button.setToolTip("프롬프트를 txt 파일로 저장합니다 (Ctrl+S)")
        main_button_layout.addWidget(self.save_button)
        
        # 불러오기 버튼
        self.load_button = QPushButton("📂 열기")
        self.load_button.clicked.connect(self.load_from_txt_file)
        self.load_button.setFixedHeight(30)
        self.load_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.load_button.setToolTip("txt 파일에서 프롬프트를 불러옵니다 (Ctrl+O)")
        main_button_layout.addWidget(self.load_button)
        
        # 옵션 토글 버튼
        self.toggle_button = QPushButton("⚙️ 옵션")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(self.options_visible)
        self.toggle_button.clicked.connect(self.toggle_options)
        self.toggle_button.setFixedHeight(30)
        self.toggle_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.toggle_button.setToolTip("고급 옵션을 표시/숨김합니다 (Ctrl+Alt+O)")
        main_button_layout.addWidget(self.toggle_button)
        
        # 여백 추가
        main_button_layout.addStretch()
        
        left_layout.addLayout(main_button_layout)
        
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
        self.pin_button.setFixedHeight(30)
        self.pin_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.pin_button.setToolTip("창을 다른 모든 창 위에 고정합니다 (Ctrl+T)")
        pin_layout.addWidget(self.pin_button)
        pin_layout.addStretch()
        options_layout.addLayout(pin_layout)
        
        # 투명도 조절
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("🔍 투명도:")
        opacity_label.setMinimumWidth(50)
        opacity_label.setFixedHeight(30)
        opacity_label.setAlignment(Qt.AlignVCenter)
        opacity_layout.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(30)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(self.window_opacity * 100))
        self.opacity_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.opacity_slider.setFixedHeight(30)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.opacity_slider.setToolTip("창의 투명도를 조절합니다 (30% ~ 100%)\nCtrl+Plus: 투명도 증가, Ctrl+Minus: 투명도 감소, Ctrl+0: 리셋")
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_value_label = QLabel(f"{int(self.window_opacity * 100)}%")
        self.opacity_value_label.setMinimumWidth(35)
        self.opacity_value_label.setFixedHeight(30)
        self.opacity_value_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        opacity_layout.addWidget(self.opacity_value_label)
        
        opacity_layout.addStretch()
        options_layout.addLayout(opacity_layout)
        
        # 시스템 트레이 옵션
        tray_layout = QHBoxLayout()
        self.tray_checkbox = QCheckBox("🔽 시스템 트레이에 상주")
        self.tray_checkbox.setChecked(self.stay_in_tray)
        self.tray_checkbox.setFixedHeight(30)
        self.tray_checkbox.toggled.connect(self.toggle_system_tray)
        self.tray_checkbox.setToolTip("체크하면 X로 닫아도 프로그램이 종료되지 않고 시스템 트레이에 남아있습니다")
        tray_layout.addWidget(self.tray_checkbox)
        tray_layout.addStretch()
        options_layout.addLayout(tray_layout)
        
        # 테마 선택 옵션
        theme_layout = QHBoxLayout()
        theme_label = QLabel("🎨 테마:")
        theme_label.setMinimumWidth(50)
        theme_label.setFixedHeight(30)
        theme_label.setAlignment(Qt.AlignVCenter)
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            "기본 테마",
            "프로페셔널 다크",
            "엔터프라이즈", 
            "디자이너",
            "미니멀 프로",
            "사이버펑크"
        ])
        self.theme_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.theme_combo.setFixedHeight(30)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        self.theme_combo.setToolTip("UI 테마를 선택합니다")
        theme_layout.addWidget(self.theme_combo)
        
        theme_layout.addStretch()
        options_layout.addLayout(theme_layout)
        
        left_layout.addWidget(self.options_widget)
        
        # 왼쪽 영역을 메인 레이아웃에 추가
        self.main_splitter.addWidget(left_widget)
        
        # 오른쪽 영역 (즐겨찾기)
        right_widget = QWidget()
        right_widget.setMinimumWidth(200)  # 최소 너비로 변경
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(5)
        right_layout.setContentsMargins(5, 0, 0, 0)  # 왼쪽 여백 추가
        
        # 즐겨찾기 제목
        favorites_label = QLabel("⭐ 즐겨찾기")
        favorites_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        right_layout.addWidget(favorites_label)
        
        # 즐겨찾기 리스트
        self.favorites_list = FavoritesListWidget()
        self.favorites_list.setMinimumHeight(80)  # 최소 높이를 더 작게 조정
        self.favorites_list.itemDoubleClicked.connect(self.insert_favorite_to_input)
        # 컨텍스트 메뉴 설정 (즐겨찾기 삭제용)
        self.favorites_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.favorites_list.customContextMenuRequested.connect(self.show_favorites_context_menu)
        # DEL키 삭제 신호 연결
        self.favorites_list.deleteRequested.connect(self.delete_favorite)
        right_layout.addWidget(self.favorites_list)
        
        # 즐겨찾기 관리 버튼들
        favorites_button_layout = QHBoxLayout()
        
        # 저장 버튼
        save_favorites_button = QPushButton("💾 저장")
        save_favorites_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        save_favorites_button.setFixedHeight(30)
        save_favorites_button.clicked.connect(self.save_favorites_to_txt)
        save_favorites_button.setToolTip("즐겨찾기를 txt 파일로 저장합니다")
        favorites_button_layout.addWidget(save_favorites_button)
        
        # 불러오기 버튼
        load_favorites_button = QPushButton("📂 열기")
        load_favorites_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        load_favorites_button.setFixedHeight(30)
        load_favorites_button.clicked.connect(self.load_favorites_from_txt)
        load_favorites_button.setToolTip("txt 파일에서 즐겨찾기를 불러옵니다")
        favorites_button_layout.addWidget(load_favorites_button)
        
        # 전체 삭제 버튼
        clear_favorites_button = QPushButton("🗑️ 전체삭제")
        clear_favorites_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        clear_favorites_button.setFixedHeight(30)
        clear_favorites_button.clicked.connect(self.clear_all_favorites)
        clear_favorites_button.setToolTip("모든 즐겨찾기를 삭제합니다")
        favorites_button_layout.addWidget(clear_favorites_button)
        
        favorites_button_layout.addStretch()
        right_layout.addLayout(favorites_button_layout)
        
        # 여백 추가
        right_layout.addStretch()
        
        # 오른쪽 영역을 메인 레이아웃에 추가
        self.main_splitter.addWidget(right_widget)
        
        # 스플리터 설정
        self.main_splitter.setCollapsible(0, False)  # 왼쪽 영역 접기 방지
        self.main_splitter.setCollapsible(1, False)  # 오른쪽 영역 접기 방지
        # 저장된 스플리터 크기 사용
        saved_splitter_sizes = self.settings.get('splitter_sizes', [450, 200])
        self.main_splitter.setSizes(saved_splitter_sizes)
        self.main_splitter.setStretchFactor(0, 1)  # 왼쪽 영역이 더 많이 늘어나도록 설정
        self.main_splitter.setStretchFactor(1, 0)  # 오른쪽 영역은 고정 비율 유지
        
        # 즐겨찾기 리스트 업데이트
        self.update_favorites_list()
        
        # 저장된 설정에 따라 UI 상태 복원
        # 옵션 패널 상태 설정
        self.options_widget.setVisible(self.options_visible)
        if self.options_visible:
            self.toggle_button.setText("⚙️ 숨기기")
            self.toggle_button.setChecked(True)
        else:
            self.toggle_button.setText("⚙️ 옵션")
            self.toggle_button.setChecked(False)
        
        # 창 고정 상태 설정
        if self.always_on_top:
            self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowSystemMenuHint | Qt.WindowStaysOnTopHint)
            self.pin_button.setText("📌 맨 위에 고정됨")
            self.pin_button.setChecked(True)
        else:
            self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowSystemMenuHint)
            self.pin_button.setText("📌 맨 위에 고정")
            self.pin_button.setChecked(False)
        
        # 투명도 슬라이더 설정
        opacity_value = int(self.window_opacity * 100)
        self.opacity_slider.setValue(opacity_value)
        self.opacity_value_label.setText(f"{opacity_value}%")
        
        # 시스템 트레이 설정
        self.tray_checkbox.setChecked(self.stay_in_tray)
        
        # 저장된 테마 적용
        saved_theme = self.settings.get('current_theme', 'default')
        if saved_theme == 'default':
            theme_index = 0
        elif saved_theme == '프로페셔널 다크':
            theme_index = 1
        elif saved_theme == '엔터프라이즈':
            theme_index = 2
        elif saved_theme == '디자이너':
            theme_index = 3
        elif saved_theme == '미니멀 프로':
            theme_index = 4
        elif saved_theme == '사이버펑크':
            theme_index = 5
        else:
            theme_index = 0
        
        self.theme_combo.setCurrentIndex(theme_index)
        self.current_theme = saved_theme
        self.change_theme(saved_theme)
    
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
            new_flags = (Qt.Window | Qt.WindowCloseButtonHint | 
                        Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint |
                        Qt.WindowSystemMenuHint | Qt.WindowStaysOnTopHint)
            self.pin_button.setText("📌 맨 위에 고정됨")
        else:
            # 맨 위에 고정 플래그 제거 (기본 플래그만 유지)
            new_flags = (Qt.Window | Qt.WindowCloseButtonHint | 
                        Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint |
                        Qt.WindowSystemMenuHint)
            self.pin_button.setText("📌 맨 위에 고정")
        
        # 창 플래그 업데이트
        self.setWindowFlags(new_flags)
        
        # 창을 다시 표시 (플래그 변경 후 필요)
        self.show()
        
        print(f"[DEBUG] AI Prompt Studio - 창 맨 위에 고정: {'활성화' if self.always_on_top else '비활성화'}")
    
    def toggle_options(self):
        """옵션 패널 표시/숨김 토글"""
        self.options_visible = not self.options_visible
        self.options_widget.setVisible(self.options_visible)
        
        # 창 크기 조절 (현재 너비 유지, 높이만 조절)
        current_width = self.width()
        if self.options_visible:
            self.setMinimumSize(500, self.expanded_height)
            if current_width < 500:
                current_width = 650  # 기본 너비로 설정
            target_height = max(self.expanded_height, self.height())
            self.resize(current_width, target_height)
            self.toggle_button.setText("⚙️ 숨기기")
        else:
            self.setMinimumSize(500, self.compact_height)
            if current_width < 500:
                current_width = 650  # 기본 너비로 설정
            self.resize(current_width, self.compact_height)
            self.toggle_button.setText("⚙️ 옵션")
        
        # 레이아웃 강제 업데이트
        self.centralWidget().updateGeometry()
        self.adjustSize()
        
        # 지연 후 크기 재조정 (레이아웃이 완전히 적용된 후)
        QTimer.singleShot(10, lambda: self._finalize_resize())
        
        print(f"[DEBUG] AI Prompt Studio - 옵션 패널: {'표시' if self.options_visible else '숨김'}")
    
    def _finalize_resize(self):
        """옵션 토글 후 최종 크기 조정"""
        current_width = self.width()
        if self.options_visible:
            final_height = max(self.expanded_height, self.sizeHint().height())
        else:
            final_height = self.compact_height
        
        self.resize(current_width, final_height)
    
    def change_opacity(self, value):
        """윈도우 투명도 변경"""
        # 슬라이더 값 (30-100)을 투명도 값 (0.3-1.0)으로 변환
        self.window_opacity = value / 100.0
        
        # 윈도우 투명도 적용
        self.setWindowOpacity(self.window_opacity)
        
        # 라벨 업데이트
        self.opacity_value_label.setText(f"{value}%")
        

        
        print(f"[DEBUG] AI Prompt Studio - 투명도 변경: {value}%")
    
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
        
        # 트레이 아이콘 설정 (AI Prompt Studio 전용 아이콘)
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
        self.tray_icon.setToolTip("AI Prompt Studio")
        
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
        # 현재 설정 저장
        self.save_settings()
        
        if self.stay_in_tray and self.tray_icon.isVisible():
            # 트레이에 상주하는 경우 창만 숨기기
            event.ignore()
            self.hide()
        else:
            # 트레이에 상주하지 않는 경우 완전 종료
            event.accept()
            self.quit_application()
    
    def resizeEvent(self, event):
        """윈도우 크기 변경 이벤트 처리"""
        super().resizeEvent(event)
        # 설정 저장 (너무 자주 저장하지 않도록 QTimer 사용)
        if hasattr(self, '_save_timer'):
            self._save_timer.stop()
        else:
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self.save_settings)
        self._save_timer.start(1000)  # 1초 후 저장
    
    def moveEvent(self, event):
        """윈도우 위치 변경 이벤트 처리"""
        super().moveEvent(event)
        # 설정 저장 (너무 자주 저장하지 않도록 QTimer 사용)
        if hasattr(self, '_save_timer'):
            self._save_timer.stop()
        else:
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self.save_settings)
        self._save_timer.start(1000)  # 1초 후 저장
    
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

    def load_settings(self):
        """설정 데이터를 파일에서 로드"""
        try:
            if os.path.exists(self.settings_file):
                import json
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                # 설정에서 테마 정보 불러오기
                self.current_theme = self.settings.get('current_theme', 'default')
            else:
                # 기본 설정값
                self.settings = {
                    'window_width': 650,
                    'window_height': 170,
                    'window_x': -1,  # -1이면 화면 중앙에 배치
                    'window_y': -1,
                    'splitter_sizes': [450, 200],
                    'options_visible': False,
                    'window_opacity': 1.0,
                    'always_on_top': False,
                    'stay_in_tray': False,
                    'current_theme': 'default'
                }
        except Exception as e:
            print(f"설정 로드 실패: {e}")
            # 기본 설정값으로 초기화
            self.settings = {
                'window_width': 650,
                'window_height': 170,
                'window_x': -1,
                'window_y': -1,
                'splitter_sizes': [450, 200],
                'options_visible': False,
                'window_opacity': 1.0,
                'always_on_top': False,
                'stay_in_tray': False,
                'current_theme': 'default'
            }
    
    def save_settings(self):
        """현재 설정을 파일에 저장"""
        try:
            # 현재 창 상태를 설정에 저장
            self.settings['window_width'] = self.width()
            self.settings['window_height'] = self.height()
            self.settings['window_x'] = self.x()
            self.settings['window_y'] = self.y()
            self.settings['splitter_sizes'] = self.main_splitter.sizes()
            self.settings['options_visible'] = self.options_visible
            self.settings['window_opacity'] = self.window_opacity
            self.settings['always_on_top'] = self.always_on_top
            self.settings['stay_in_tray'] = self.stay_in_tray
            self.settings['current_theme'] = self.current_theme
            
            import json
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"설정 저장 실패: {e}")
    
    def get_theme_stylesheet(self, theme_name):
        """테마별 스타일시트 반환"""
        if theme_name == "프로페셔널 다크":
            return """
                QMainWindow {
                    background: #0d1117;
                    color: #f0f6fc;
                    border-radius: 12px;
                }
                QWidget {
                    background: transparent;
                    color: #f0f6fc;
                    font-family: 'Segoe UI', system-ui, sans-serif;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #21262d, stop:1 #161b22);
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    color: #f0f6fc;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 13px;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #30363d, stop:1 #21262d);
                    border-color: #58a6ff;
                }
                QPushButton:pressed {
                    background: #161b22;
                    border-color: #1f6feb;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1f6feb, stop:1 #1158c7);
                    border-color: #58a6ff;
                    color: #ffffff;
                }
                QTextEdit {
                    background: #0d1117;
                    border: 1px solid #21262d;
                    border-radius: 8px;
                    color: #f0f6fc;
                    padding: 12px;
                    font-size: 14px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    selection-background-color: #1f6feb;
                }
                QTextEdit:focus {
                    border-color: #58a6ff;
                }
                QListWidget {
                    background: #0d1117;
                    border: 1px solid #21262d;
                    border-radius: 8px;
                    color: #f0f6fc;
                    padding: 6px;
                    outline: none;
                }
                QListWidget::item {
                    border-radius: 6px;
                    padding: 8px 12px;
                    margin: 2px 0px;
                    border: none;
                }
                QListWidget::item:hover {
                    background: #21262d;
                }
                QListWidget::item:selected {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1f6feb, stop:1 #1158c7);
                    color: #ffffff;
                }
                QLabel {
                    color: #f0f6fc;
                    font-weight: 500;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #21262d;
                    height: 8px;
                    background: #161b22;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #58a6ff, stop:1 #1f6feb);
                    border: 1px solid #1158c7;
                    width: 20px;
                    border-radius: 10px;
                    margin: -6px 0;
                }
                QSlider::handle:horizontal:hover {
                    background: #58a6ff;
                }
                QComboBox {
                    background: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    color: #f0f6fc;
                    padding: 6px 12px;
                    min-height: 20px;
                }
                QComboBox:hover {
                    border-color: #58a6ff;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #f0f6fc;
                    margin-right: 5px;
                }
                QCheckBox {
                    color: #f0f6fc;
                    font-weight: 500;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 1px solid #30363d;
                    border-radius: 4px;
                    background: #21262d;
                }
                QCheckBox::indicator:checked {
                    background: #1f6feb;
                    border-color: #1158c7;
                    image: none;
                }
                QCheckBox::indicator:checked:after {
                    content: "✓";
                    color: white;
                    font-weight: bold;
                }
                QSplitter::handle {
                    background: #30363d;
                    width: 2px;
                }
                QSplitter::handle:hover {
                    background: #58a6ff;
                }
            """
        
        elif theme_name == "엔터프라이즈":
            return """
                QMainWindow {
                    background: #f8f9fa;
                    color: #495057;
                }
                QWidget {
                    background: transparent;
                    color: #495057;
                    font-family: 'Segoe UI', system-ui, sans-serif;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ffffff, stop:1 #f8f9fa);
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    color: #495057;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 13px;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f8f9fa, stop:1 #e9ecef);
                    border-color: #adb5bd;
                }
                QPushButton:pressed {
                    background: #e9ecef;
                    border-color: #6c757d;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0d6efd, stop:1 #0b5ed7);
                    border-color: #0a58ca;
                    color: #ffffff;
                }
                QTextEdit {
                    background: #ffffff;
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                    color: #212529;
                    padding: 12px;
                    font-size: 14px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    selection-background-color: #b6d7ff;
                }
                QTextEdit:focus {
                    border-color: #86b7fe;
                }
                QListWidget {
                    background: #ffffff;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    color: #212529;
                    padding: 6px;
                    outline: none;
                }
                QListWidget::item {
                    border-radius: 4px;
                    padding: 8px 12px;
                    margin: 1px 0px;
                    border: none;
                }
                QListWidget::item:hover {
                    background: #f8f9fa;
                }
                QListWidget::item:selected {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0d6efd, stop:1 #0b5ed7);
                    color: #ffffff;
                }
                QLabel {
                    color: #495057;
                    font-weight: 600;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #dee2e6;
                    height: 6px;
                    background: #e9ecef;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0d6efd, stop:1 #0b5ed7);
                    border: 1px solid #0a58ca;
                    width: 18px;
                    border-radius: 9px;
                    margin: -6px 0;
                }
                QComboBox {
                    background: #ffffff;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    color: #495057;
                    padding: 6px 12px;
                    min-height: 20px;
                }
                QComboBox:hover {
                    border-color: #86b7fe;
                }
                QCheckBox {
                    color: #495057;
                    font-weight: 500;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid #adb5bd;
                    border-radius: 3px;
                    background: #ffffff;
                }
                QCheckBox::indicator:checked {
                    background: #0d6efd;
                    border-color: #0b5ed7;
                }
            """
        
        elif theme_name == "디자이너":
            return """
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
                    color: #ffffff;
                }
                QWidget {
                    background: transparent;
                    color: #ffffff;
                    font-family: 'Segoe UI', system-ui, sans-serif;
                }
                QPushButton {
                    background: rgba(255, 255, 255, 0.15);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 12px;
                    color: #ffffff;
                    padding: 10px 20px;
                    font-weight: 600;
                    font-size: 13px;
                    min-height: 16px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.25);
                    border-color: rgba(255, 255, 255, 0.5);
                }
                QPushButton:pressed {
                    background: rgba(255, 255, 255, 0.1);
                }
                QPushButton:checked {
                    background: rgba(255, 255, 255, 0.3);
                    border-color: rgba(255, 255, 255, 0.6);
                }
                QTextEdit {
                    background: rgba(255, 255, 255, 0.9);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 12px;
                    color: #2d3748;
                    padding: 15px;
                    font-size: 14px;
                    font-family: 'Consolas', 'Monaco', monospace;
                }
                QTextEdit:focus {
                    border-color: rgba(255, 255, 255, 0.6);
                }
                QListWidget {
                    background: rgba(255, 255, 255, 0.9);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 12px;
                    color: #2d3748;
                    padding: 8px;
                }
                QListWidget::item {
                    border-radius: 8px;
                    padding: 10px 15px;
                    margin: 2px 0px;
                    border: none;
                }
                QListWidget::item:hover {
                    background: rgba(255, 255, 255, 0.3);
                    color: #ffffff;
                }
                QListWidget::item:selected {
                    background: rgba(255, 255, 255, 0.4);
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    font-weight: 600;
                }
                QSlider::groove:horizontal {
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    height: 8px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: rgba(255, 255, 255, 0.8);
                    border: 1px solid rgba(255, 255, 255, 0.5);
                    width: 20px;
                    border-radius: 10px;
                    margin: -6px 0;
                }
                QComboBox {
                    background: rgba(255, 255, 255, 0.15);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 8px;
                    color: #ffffff;
                    padding: 6px 12px;
                    min-height: 20px;
                }
                QCheckBox {
                    color: #ffffff;
                    font-weight: 500;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid rgba(255, 255, 255, 0.4);
                    border-radius: 4px;
                    background: rgba(255, 255, 255, 0.1);
                }
                QCheckBox::indicator:checked {
                    background: rgba(255, 255, 255, 0.8);
                    border-color: rgba(255, 255, 255, 0.9);
                }
            """
        
        elif theme_name == "미니멀 프로":
            return """
                QMainWindow {
                    background: #fafafa;
                    color: #2e3440;
                }
                QWidget {
                    background: transparent;
                    color: #2e3440;
                    font-family: 'Segoe UI', system-ui, sans-serif;
                }
                QPushButton {
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    color: #374151;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 13px;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background: #f9fafb;
                    border-color: #d1d5db;
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    background: #f3f4f6;
                    transform: translateY(0px);
                }
                QPushButton:checked {
                    background: #3b82f6;
                    border-color: #2563eb;
                    color: #ffffff;
                }
                QTextEdit {
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    color: #1f2937;
                    padding: 16px;
                    font-size: 14px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    selection-background-color: #dbeafe;
                }
                QTextEdit:focus {
                    border-color: #3b82f6;
                }
                QListWidget {
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    color: #1f2937;
                    padding: 8px;
                }
                QListWidget::item {
                    border-radius: 8px;
                    padding: 10px 14px;
                    margin: 2px 0px;
                    border: none;
                }
                QListWidget::item:hover {
                    background: #f3f4f6;
                }
                QListWidget::item:selected {
                    background: #3b82f6;
                    color: #ffffff;
                }
                QLabel {
                    color: #374151;
                    font-weight: 600;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #e5e7eb;
                    height: 6px;
                    background: #f3f4f6;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #3b82f6;
                    border: none;
                    width: 20px;
                    border-radius: 10px;
                    margin: -7px 0;
                }
                QComboBox {
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    color: #374151;
                    padding: 6px 12px;
                    min-height: 20px;
                }
                QCheckBox {
                    color: #374151;
                    font-weight: 500;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    background: #ffffff;
                }
                QCheckBox::indicator:checked {
                    background: #3b82f6;
                    border-color: #2563eb;
                }
            """
        
        elif theme_name == "사이버펑크":
            return """
                QMainWindow {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #0f0f23, stop:0.5 #1a1a2e, stop:1 #16213e);
                    color: #00f5ff;
                }
                QWidget {
                    background: transparent;
                    color: #00f5ff;
                    font-family: 'Consolas', 'Monaco', monospace;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #16213e, stop:1 #0f0f23);
                    border: 1px solid #00f5ff;
                    border-radius: 6px;
                    color: #00f5ff;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 12px;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1a1a2e, stop:1 #16213e);
                    border-color: #ff0080;
                    color: #ff0080;
                }
                QPushButton:pressed {
                    background: #0f0f23;
                    border-color: #ffff00;
                    color: #ffff00;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff0080, stop:1 #8000ff);
                    border-color: #ff0080;
                    color: #ffffff;
                }
                QTextEdit {
                    background: #0f0f23;
                    border: 1px solid #00f5ff;
                    border-radius: 8px;
                    color: #00f5ff;
                    padding: 12px;
                    font-size: 13px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    selection-background-color: #ff0080;
                }
                QTextEdit:focus {
                    border-color: #ff0080;
                }
                QListWidget {
                    background: #0f0f23;
                    border: 1px solid #00f5ff;
                    border-radius: 8px;
                    color: #00f5ff;
                    padding: 6px;
                }
                QListWidget::item {
                    border-radius: 4px;
                    padding: 8px 12px;
                    margin: 2px 0px;
                    border: none;
                }
                QListWidget::item:hover {
                    background: #1a1a2e;
                    color: #ff0080;
                }
                QListWidget::item:selected {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff0080, stop:1 #8000ff);
                    color: #ffffff;
                }
                QLabel {
                    color: #00f5ff;
                    font-weight: bold;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #00f5ff;
                    height: 6px;
                    background: #16213e;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ff0080, stop:1 #8000ff);
                    border: 1px solid #ff0080;
                    width: 18px;
                    border-radius: 9px;
                    margin: -6px 0;
                }
                QComboBox {
                    background: #16213e;
                    border: 1px solid #00f5ff;
                    border-radius: 6px;
                    color: #00f5ff;
                    padding: 6px 12px;
                    min-height: 20px;
                }
                QCheckBox {
                    color: #00f5ff;
                    font-weight: bold;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid #00f5ff;
                    border-radius: 3px;
                    background: #0f0f23;
                }
                QCheckBox::indicator:checked {
                    background: #ff0080;
                    border-color: #ff0080;
                }
            """
        
        else:  # 기본 테마
            return ""
    
    def change_theme(self, theme_name):
        """테마 변경"""
        self.current_theme = theme_name
        stylesheet = self.get_theme_stylesheet(theme_name)
        self.setStyleSheet(stylesheet)
        
        # 설정 저장
        self.save_settings()
        
        print(f"[DEBUG] 테마 변경: {theme_name}")
    
    def load_favorites(self):
        """즐겨찾기 데이터를 파일에서 로드"""
        try:
            if os.path.exists(self.favorites_file):
                import json
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    self.favorites = json.load(f)
            else:
                self.favorites = []
        except Exception as e:
            print(f"즐겨찾기 로드 실패: {e}")
            self.favorites = []
    
    def save_favorites(self):
        """즐겨찾기 데이터를 파일에 저장"""
        try:
            import json
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"즐겨찾기 저장 실패: {e}")
    
    def add_to_favorites(self, text):
        """즐겨찾기에 텍스트 추가"""
        if text and text not in self.favorites:
            self.favorites.append(text)
            self.save_favorites()
            self.update_favorites_list()
            QToolTip.showText(
                QCursor.pos(),
                f"'{text}' 가 즐겨찾기에 추가되었습니다."
            )
        elif text in self.favorites:
            QToolTip.showText(
                QCursor.pos(),
                "이미 즐겨찾기에 있습니다."
            )
    
    def update_favorites_list(self):
        """즐겨찾기 리스트 위젯 업데이트"""
        self.favorites_list.clear()
        for favorite in self.favorites:
            item = QListWidgetItem(favorite)
            item.setToolTip(f"더블클릭: 입력창에 추가\nDEL키: 삭제\n우클릭: 삭제 메뉴\n\n내용: {favorite}")
            self.favorites_list.addItem(item)
    
    def insert_favorite_to_input(self, item):
        """즐겨찾기 항목을 입력창에 삽입 (끝에 쉼표와 공백 추가)"""
        text = item.text()
        current_text = self.prompt_input.toPlainText()
        
        # 현재 텍스트가 비어있지 않고 끝에 쉼표가 없으면 쉼표와 공백 추가
        if current_text and not current_text.rstrip().endswith(','):
            new_text = current_text + ', ' + text + ', '
        else:
            new_text = current_text + text + ', '
        
        self.prompt_input.setPlainText(new_text)
        # 커서를 끝으로 이동
        cursor = self.prompt_input.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.prompt_input.setTextCursor(cursor)
        self.prompt_input.setFocus()
    
    def show_favorites_context_menu(self, position):
        """즐겨찾기 리스트의 컨텍스트 메뉴 표시 (삭제 기능)"""
        item = self.favorites_list.itemAt(position)
        if item:
            context_menu = QMenu(self)
            
            delete_action = QAction("🗑️ 삭제", self)
            delete_action.triggered.connect(lambda: self.delete_favorite(item))
            context_menu.addAction(delete_action)
            
            context_menu.exec(self.favorites_list.mapToGlobal(position))
    
    def delete_favorite(self, item):
        """특정 즐겨찾기 항목 삭제"""
        text = item.text()
        if text in self.favorites:
            self.favorites.remove(text)
            self.save_favorites()
            self.update_favorites_list()
            QToolTip.showText(
                QCursor.pos(),
                f"'{text}' 가 즐겨찾기에서 삭제되었습니다."
            )
    
    def clear_all_favorites(self):
        """모든 즐겨찾기 삭제"""
        if self.favorites:
            reply = QMessageBox.question(
                self, 
                "즐겨찾기 전체 삭제",
                "모든 즐겨찾기를 삭제하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.favorites.clear()
                self.save_favorites()
                self.update_favorites_list()
                QToolTip.showText(
                    QCursor.pos(),
                    "모든 즐겨찾기가 삭제되었습니다."
                )
    
    def save_favorites_to_txt(self):
        """즐겨찾기를 txt 파일로 저장"""
        try:
            if not self.favorites:
                QToolTip.showText(
                    QCursor.pos(),
                    "저장할 즐겨찾기가 없습니다."
                )
                return
            
            # 파일 저장 대화상자
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "즐겨찾기 저장",
                "favorites.txt",
                "텍스트 파일 (*.txt);;모든 파일 (*.*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for favorite in self.favorites:
                        f.write(favorite + '\n')
                
                QToolTip.showText(
                    QCursor.pos(),
                    f"즐겨찾기 {len(self.favorites)}개가 저장되었습니다."
                )
                print(f"[DEBUG] 즐겨찾기 저장 완료: {file_path}")
                
        except Exception as e:
            QToolTip.showText(
                QCursor.pos(),
                f"저장 실패: {str(e)}"
            )
            print(f"[DEBUG] 즐겨찾기 저장 실패: {e}")
    
    def load_favorites_from_txt(self):
        """txt 파일에서 즐겨찾기 불러오기"""
        try:
            # 파일 열기 대화상자
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "즐겨찾기 불러오기",
                "",
                "텍스트 파일 (*.txt);;모든 파일 (*.*)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                
                if not lines:
                    QToolTip.showText(
                        QCursor.pos(),
                        "파일에 유효한 즐겨찾기가 없습니다."
                    )
                    return
                
                # 현재 즐겨찾기가 있으면 확인
                if self.favorites:
                    reply = QMessageBox.question(
                        self,
                        "즐겨찾기 불러오기",
                        f"파일에서 {len(lines)}개의 즐겨찾기를 찾았습니다.\n기존 즐겨찾기에 추가하시겠습니까?\n\n'예': 기존에 추가\n'아니오': 기존 내용 삭제 후 교체",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Cancel:
                        return
                    elif reply == QMessageBox.No:
                        # 기존 내용 삭제 후 교체
                        self.favorites.clear()
                
                # 중복 확인하면서 추가
                added_count = 0
                duplicate_count = 0
                
                for line in lines:
                    if line and line not in self.favorites:
                        self.favorites.append(line)
                        added_count += 1
                    elif line in self.favorites:
                        duplicate_count += 1
                
                # 변경사항 저장 및 리스트 업데이트
                self.save_favorites()
                self.update_favorites_list()
                
                # 결과 메시지
                if added_count > 0 and duplicate_count > 0:
                    message = f"{added_count}개의 즐겨찾기가 추가되었습니다.\n({duplicate_count}개는 이미 존재함)"
                elif added_count > 0:
                    message = f"{added_count}개의 즐겨찾기가 불러와졌습니다."
                elif duplicate_count > 0:
                    message = f"모든 항목이 이미 존재합니다. ({duplicate_count}개)"
                else:
                    message = "불러올 수 있는 새로운 즐겨찾기가 없습니다."
                
                QToolTip.showText(
                    QCursor.pos(),
                    message
                )
                print(f"[DEBUG] 즐겨찾기 불러오기 완료: {file_path}")
                
        except Exception as e:
            QToolTip.showText(
                QCursor.pos(),
                f"불러오기 실패: {str(e)}"
            )
            print(f"[DEBUG] 즐겨찾기 불러오기 실패: {e}")


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
        app.setApplicationName("AI Prompt Studio")
        app.setApplicationVersion("Pro v2.0")
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
                        print("[DEBUG] 내장된 아이콘 파일을 찾을 수 없습니다.")
            else:
                # 개발 환경에서는 로컬 아이콘 파일 사용
                if os.path.exists("prompt_input_icon.ico"):
                    app.setWindowIcon(QIcon("prompt_input_icon.ico"))
                elif os.path.exists("icon.ico"):
                    app.setWindowIcon(QIcon("icon.ico"))
                elif os.path.exists("icon.png"):
                    app.setWindowIcon(QIcon("icon.png"))
                else:
                    print("[DEBUG] 개발 환경: 아이콘 파일을 찾을 수 없습니다.")
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
            "AI Prompt Studio 시작 오류",
            f"프로그램 시작 중 오류가 발생했습니다:\n{str(e)}",
            error_details
        )
        sys.exit(1)


if __name__ == "__main__":
    main() 