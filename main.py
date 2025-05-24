from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from promptbook_widgets import CustomLineEdit, ImageView
from promptbook_utils import PromptBookUtils
from promptbook_state import PromptBookState
from promptbook_handlers import PromptBookEventHandlers
import os, json, csv, shutil, sys

class ImageView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 고품질 렌더링을 위한 설정
        self.setRenderHints(
            QPainter.Antialiasing |            # 안티앨리어싱
            QPainter.SmoothPixmapTransform |   # 부드러운 이미지 변환
            QPainter.TextAntialiasing          # 텍스트 안티앨리어싱
        )
        
        # 뷰포트 업데이트 모드 설정
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # 스크롤바 숨기기
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 프레임 제거
        self.setFrameShape(QFrame.NoFrame)
        
        # 드래그 모드 설정
        self.setDragMode(QGraphicsView.NoDrag)
        
        # 변환 최적화
        self.setOptimizationFlags(
            QGraphicsView.DontSavePainterState |
            QGraphicsView.DontAdjustForAntialiasing
        )
        
        # 캐시 모드 설정
        self.setCacheMode(QGraphicsView.CacheBackground)
        
        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)
        
        # 드래그 앤 드롭 안내 라벨
        self.drop_hint = QLabel(self.viewport())
        self.drop_hint.setText("이미지 파일을 여기에\n드래그 앤 드롭하세요\n\n지원 형식: PNG, JPG, JPEG, BMP, GIF")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet("""
            QLabel {
                color: #888;
                background-color: rgba(240, 240, 240, 50);
                font-size: 14px;
                padding: 30px;
                border: 2px dashed #bbb;
                border-radius: 10px;
            }
        """)
        self.update_drop_hint_position()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 부모 위젯 체인을 따라 PromptBook 인스턴스를 찾습니다
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, PromptBook):
                parent.update_image_fit()
                break
            parent = parent.parent()
        # 라벨 위치 및 가시성 업데이트
        self.update_drop_hint_position()
        self.update_drop_hint_visibility()
        
    def update_drop_hint_position(self):
        if not hasattr(self, 'drop_hint'):
            return
            
        # 뷰포트 크기 가져오기
        viewport_rect = self.viewport().rect()
        
        # 라벨 크기 계산
        hint_width = min(350, viewport_rect.width() - 40)  # 여백 20px
        hint_height = 120  # 텍스트가 늘어났으므로 높이 증가
        
        # 중앙 위치 계산
        x = (viewport_rect.width() - hint_width) // 2
        y = (viewport_rect.height() - hint_height) // 2
        
        # 라벨 위치와 크기 설정
        self.drop_hint.setGeometry(x, y, hint_width, hint_height)
    
    def set_drop_hint_visible(self, visible):
        """드롭 힌트 표시/숨김 제어"""
        if hasattr(self, 'drop_hint'):
            self.drop_hint.setVisible(visible)
    
    def update_drop_hint_visibility(self):
        """드롭 힌트 표시 여부를 상태에 따라 업데이트"""
        if not hasattr(self, 'drop_hint'):
            return
            
        # 부모 PromptBook 인스턴스 찾기
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, PromptBook):
                # 페이지가 선택되어 있고 이미지가 없을 때만 표시
                has_page_selected = (parent.current_index >= 0 and 
                                   0 <= parent.current_index < len(parent.state.characters))
                has_image = (has_page_selected and 
                           parent.state.characters[parent.current_index].get("image_path") and
                           os.path.exists(parent.state.characters[parent.current_index]["image_path"]))
                
                # 페이지가 선택되어 있고 이미지가 없을 때만 드롭 힌트 표시
                should_show = has_page_selected and not has_image
                self.drop_hint.setVisible(should_show)
                return
            parent = parent.parent()
        
        # PromptBook을 찾지 못한 경우 숨김
        self.drop_hint.setVisible(False)
    
    def dragEnterEvent(self, event):
        """드래그 엔터 이벤트 처리"""
        if event.mimeData().hasUrls():
            # URL이 있는지 확인하고 이미지 파일인지 검사
            urls = event.mimeData().urls()
            if urls and len(urls) == 1:  # 하나의 파일만 허용
                file_path = urls[0].toLocalFile()
                if self.is_image_file(file_path):
                    event.acceptProposedAction()
                    # 드래그 중일 때 시각적 피드백
                    self.drop_hint.setStyleSheet("""
                        QLabel {
                            color: #2c5aa0;
                            background-color: rgba(44, 90, 160, 30);
                            font-size: 14px;
                            padding: 30px;
                            border: 2px dashed #2c5aa0;
                            border-radius: 10px;
                        }
                    """)
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """드래그 리브 이벤트 처리"""
        # 원래 스타일로 복원
        self.drop_hint.setStyleSheet("""
            QLabel {
                color: #888;
                background-color: rgba(240, 240, 240, 50);
                font-size: 14px;
                padding: 30px;
                border: 2px dashed #bbb;
                border-radius: 10px;
            }
        """)
        event.accept()
    
    def dragMoveEvent(self, event):
        """드래그 무브 이벤트 처리"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and len(urls) == 1:
                file_path = urls[0].toLocalFile()
                if self.is_image_file(file_path):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event):
        """드롭 이벤트 처리"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and len(urls) == 1:
                file_path = urls[0].toLocalFile()
                if self.is_image_file(file_path):
                    # 부모 PromptBook 인스턴스 찾기
                    parent = self.parent()
                    while parent is not None:
                        if isinstance(parent, PromptBook):
                            # 이미지 로드 기능 호출
                            parent.load_image_from_path(file_path)
                            break
                        parent = parent.parent()
                    
                    # 원래 스타일로 복원
                    self.drop_hint.setStyleSheet("""
                        QLabel {
                            color: #888;
                            background-color: rgba(240, 240, 240, 50);
                            font-size: 14px;
                            padding: 30px;
                            border: 2px dashed #bbb;
                            border-radius: 10px;
                        }
                    """)
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def is_image_file(self, file_path):
        """이미지 파일인지 확인"""
        if not file_path or not os.path.exists(file_path):
            return False
        
        # 지원하는 이미지 확장자
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp'}
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in image_extensions



class ClickableLabel(QLabel):
    """클릭 가능한 라벨"""
    clicked = Signal()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class PageItemWidget(QWidget):
    def __init__(self, name, is_favorite=False, emoji="📄", parent=None):
        super().__init__(parent)
        self.page_name = name  # 페이지 이름 저장
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)  # 여백 줄이기
        layout.setSpacing(2)  # 간격 대폭 줄이기
        
        # 별 표시 라벨 (클릭 가능)
        self.star_label = ClickableLabel()
        self.star_label.setFixedWidth(16)  # 폭 줄이기
        self.star_label.setAlignment(Qt.AlignCenter)
        self.star_label.setCursor(Qt.PointingHandCursor)  # 마우스 커서 변경
        self.star_label.setToolTip("클릭하여 즐겨찾기 토글")
        self.star_label.clicked.connect(self.toggle_favorite)
        
        # 페이지 아이콘 라벨
        self.page_label = QLabel(emoji)
        self.page_label.setFixedWidth(16)  # 폭 줄이기
        
        # 페이지 이름 라벨
        self.name_label = QLabel(name)
        
        # 레이아웃에 추가
        layout.addWidget(self.star_label)
        layout.addWidget(self.page_label)
        layout.addWidget(self.name_label)
        layout.addStretch()  # 오른쪽 여백
        
        # 즐겨찾기 상태 설정
        self.set_favorite(is_favorite)
    
    def toggle_favorite(self):
        """즐겨찾기 토글 - 부모 PromptBook 인스턴스 찾아서 처리"""
        # 부모 위젯 체인을 따라 PromptBook 인스턴스 찾기
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, PromptBook):
                # 현재 페이지에 대해 즐겨찾기 토글
                for char in parent.state.characters:
                    if char.get("name") == self.page_name:
                        is_favorite = not char.get("favorite", False)
                        char["favorite"] = is_favorite
                        
                        # 상태 업데이트
                        if parent.current_book:
                            parent.state.books[parent.current_book]["pages"] = parent.state.characters
                        
                        # 정렬 적용 및 리스트 갱신
                        if not parent.sort_mode_custom:
                            current_mode = parent.sort_selector.currentText() if hasattr(parent, "sort_selector") else "오름차순 정렬"
                            from promptbook_features import sort_characters
                            parent.state.characters = sort_characters(parent.state.characters, current_mode)
                        
                        parent.refresh_character_list(selected_name=self.page_name)
                        parent.save_to_file()
                        return
                break
            parent = parent.parent()
    
    def set_favorite(self, is_favorite):
        self.star_label.setText("⭐" if is_favorite else "")
    
    def set_name(self, name):
        self.name_label.setText(name)
    
    def set_emoji(self, emoji):
        self.page_label.setText(emoji)

class BookItemWidget(QWidget):
    def __init__(self, name, is_favorite=False, emoji="📕", parent=None):
        super().__init__(parent)
        self.book_name = name  # 북 이름 저장
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)  # 여백 줄이기
        layout.setSpacing(2)  # 간격 대폭 줄이기
        
        # 별 표시 라벨 (클릭 가능)
        self.star_label = ClickableLabel()
        self.star_label.setFixedWidth(16)  # 폭 줄이기
        self.star_label.setAlignment(Qt.AlignCenter)
        self.star_label.setCursor(Qt.PointingHandCursor)  # 마우스 커서 변경
        self.star_label.setToolTip("클릭하여 즐겨찾기 토글")
        self.star_label.clicked.connect(self.toggle_favorite)
        
        # 북 아이콘 라벨
        self.book_label = QLabel(emoji)
        self.book_label.setFixedWidth(16)  # 폭 줄이기
        
        # 북 이름 라벨
        self.name_label = QLabel(name)
        
        # 레이아웃에 추가
        layout.addWidget(self.star_label)
        layout.addWidget(self.book_label)
        layout.addWidget(self.name_label)
        layout.addStretch()  # 오른쪽 여백
        
        # 즐겨찾기 상태 설정
        self.set_favorite(is_favorite)
    
    def toggle_favorite(self):
        """즐겨찾기 토글 - 부모 PromptBook 인스턴스 찾아서 처리"""
        # 부모 위젯 체인을 따라 PromptBook 인스턴스 찾기
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, PromptBook):
                # 현재 북에 대해 즐겨찾기 토글
                if self.book_name in parent.state.books:
                    is_favorite = not parent.state.books[self.book_name].get("favorite", False)
                    parent.state.books[self.book_name]["favorite"] = is_favorite
                    
                    # 정렬 적용 및 리스트 갱신
                    if not parent.book_sort_custom:
                        current_mode = parent.book_sort_selector.currentText() if hasattr(parent, "book_sort_selector") else "오름차순 정렬"
                        parent.handle_book_sort()
                    else:
                        # 현재 위젯만 업데이트
                        self.set_favorite(is_favorite)
                    
                    parent.save_to_file()
                    return
                break
            parent = parent.parent()
    
    def set_favorite(self, is_favorite):
        self.star_label.setText("⭐" if is_favorite else "")
    
    def set_name(self, name):
        self.name_label.setText(name)
        self.book_name = name
    
    def set_emoji(self, emoji):
        self.book_label.setText(emoji)

class BookList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(False)  # 외부 드롭 비활성화
        
    def dragEnterEvent(self, event):
        # 내부 항목 이동인 경우만 허용
        if event.source() == self:
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        # 내부 항목 이동인 경우만 처리
        if event.source() == self:
            super().dropEvent(event)
        else:
            event.ignore()

class CharacterList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(False)  # 외부 드롭 비활성화
        
    def dragEnterEvent(self, event):
        # 내부 항목 이동인 경우만 허용
        if event.source() == self:
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        # 내부 항목 이동인 경우만 처리
        if event.source() == self:
            super().dropEvent(event)
        else:
            event.ignore()

class PromptBook(QMainWindow):
    # 클래스 레벨 상수 정의
    SAVE_FILE = "character_data.json"
    SETTINGS_FILE = "ui_settings.json"
    
    emoji_options = [
        "📕", "📘", "📙", "📗", "📓", "📔", "📒", "📚", "📖", "📝",
        "🌟", "✨", "🔥", "🎯", "🚀", "🧩", "🎨", "💡", "❤️", "💀",
        "👑", "🎵", "🐉", "🦄", "🐱", "👻", "🍀", "🪐", "😀", "😎",
        "🥳", "😈", "🤖", "👽", "👾", "🙈", "😺", "🫠", "👧", "👩",
        "🧒", "👸", "💃", "🧝‍♀️", "🧚‍♀️", "🧞‍♀️", "👩‍🎤", "👩‍🔬"
    ]
    
    # 페이지용 이모지 옵션 (북 관련 이모지 제외)
    page_emoji_options = [
        "📄", "📃", "🗒️", "📑", "🧾", "📰", "🗞️", "📋", "📌", "📎",
        "🌟", "✨", "🔥", "🎯", "🚀", "🧩", "🎨", "💡", "❤️", "💀",
        "👑", "🎵", "🐉", "🦄", "🐱", "👻", "🍀", "🪐", "😀", "😎",
        "🥳", "😈", "🤖", "👽", "👾", "🙈", "😺", "🫠", "👧", "👩",
        "🧒", "👸", "💃", "🧝‍♀️", "🧚‍♀️", "🧞‍♀️", "👩‍🎤", "👩‍🔬"
    ]

    def __init__(self):
        # 부모 클래스 초기화
        super().__init__()
        
        # 상태 및 핸들러 초기화
        self.state = PromptBookState()
        self.handlers = PromptBookEventHandlers()
        
        # 상태 변수 초기화
        self.current_book = None
        self.current_index = -1
        self.block_save = False
        self.edited = False
        self._initial_loading = True
        self.sort_mode_custom = False
        self.book_sort_custom = False  # 북 정렬 모드 추가
        
        # UI 관련 변수 초기화
        self.book_list = None
        self.char_list = None
        self.name_input = None
        self.tag_input = None
        self.desc_input = None
        self.prompt_input = None
        self.image_view = None
        self.image_scene = None
        self.left_layout = None
        self.middle_layout = None
        self.right_layout = None
        self.sort_selector = None
        self.book_sort_selector = None
        
        # 기본 윈도우 설정
        self.setWindowTitle("프롬프트 북")
        self.setMinimumSize(1000, 600)  # 최소 크기 설정
        self.resize(1000, 600)  # 기본 크기 설정
        self.setAcceptDrops(True)
        
        # UI 구성
        self.setup_ui()
        
        # 저장된 설정이 있다면 적용
        if os.path.exists(self.SETTINGS_FILE):
            self.load_ui_settings()
            
        # 데이터 로드
        self.load_from_file()

    def setup_ui(self):
        self.setWindowTitle("프롬프트 북")
        self.setMinimumSize(1000, 600)
        self.setup_menubar()
        self.setup_central_widget()
        self.setup_book_list()
        self.setup_character_list()
        self.setup_input_fields()
        self.setup_image_view()
        self.setup_buttons()
        self.update_all_buttons_state()

    def setup_menubar(self):
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        # 선택된 북 저장하기
        save_book_action = QAction("선택된 북 저장하기", self)
        save_book_action.triggered.connect(self.save_selected_book)
        file_menu.addAction(save_book_action)
        
        # 저장된 북 불러오기
        load_book_action = QAction("저장된 북 불러오기", self)
        load_book_action.triggered.connect(self.load_saved_book)
        file_menu.addAction(load_book_action)
        
        # 테마 메뉴
        theme_menu = menubar.addMenu("테마")
        
        # 정보 메뉴
        info_menu = menubar.addMenu("정보")

    def setup_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 메인 스플리터 생성
        self.main_splitter = QSplitter(Qt.Horizontal)  # 인스턴스 변수로 변경
        layout.addWidget(self.main_splitter)
        
        # 기본 스플리터 크기 설정
        self.main_splitter.setSizes([200, 400, 372])

        # Left panel
        left_widget = QWidget()
        self.left_layout = QVBoxLayout(left_widget)
        self.main_splitter.addWidget(left_widget)
        
        # Middle panel
        middle_widget = QWidget()
        self.middle_layout = QVBoxLayout(middle_widget)
        self.main_splitter.addWidget(middle_widget)
        
        # Right panel
        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        self.main_splitter.addWidget(right_widget)

    def setup_book_list(self):
        # 북 검색 입력란 추가
        self.book_search_input = QLineEdit()
        self.book_search_input.setPlaceholderText("북 이름으로 검색...")
        self.book_search_input.textChanged.connect(self.filter_books)
        
        self.book_list = BookList()  # BookList 사용
        self.book_list.setSelectionMode(QListWidget.SingleSelection)
        self.book_list.setFocusPolicy(Qt.StrongFocus)
        # 델리게이트 제거 - 커스텀 위젯 사용할 예정
        self.book_list.installEventFilter(self)
        self.book_list.itemClicked.connect(lambda item: self.on_book_selected(self.book_list.row(item)))
        self.book_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.book_list.customContextMenuRequested.connect(self.show_book_context_menu)
        
        # 북 정렬 선택기 추가
        self.book_sort_selector = QComboBox()
        self.book_sort_selector.addItems(["오름차순 정렬", "내림차순 정렬", "커스텀 정렬"])
        self.book_sort_selector.currentIndexChanged.connect(self.handle_book_sort)
        
        self.left_layout.addWidget(QLabel("북 리스트"))
        self.left_layout.addWidget(self.book_search_input)
        self.left_layout.addWidget(self.book_sort_selector)
        self.left_layout.addWidget(self.book_list)
        
        self.book_add_button = QPushButton("➕ 북 추가")
        self.book_add_button.clicked.connect(self.add_book)
        self.left_layout.addWidget(self.book_add_button)

    def setup_character_list(self):
        # 페이지 검색 입력란 추가
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("이름 또는 태그로 검색...")
        self.search_input.textChanged.connect(self.filter_characters)
        
        self.char_list = CharacterList()  # QListWidget 대신 CharacterList 사용
        # 기본적으로 드래그 앤 드롭 비활성화
        self.char_list.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.char_list.itemClicked.connect(self.on_character_clicked)
        self.char_list.model().rowsMoved.connect(self.on_character_reordered)
        self.char_list.installEventFilter(self)
        self.char_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.char_list.customContextMenuRequested.connect(self.show_character_context_menu)
        
        # 페이지 정렬 선택기 추가
        self.sort_selector = QComboBox()
        self.sort_selector.addItems(["오름차순 정렬", "내림차순 정렬", "커스텀 정렬"])
        self.sort_selector.currentIndexChanged.connect(self.handle_character_sort)
        
        self.left_layout.addWidget(QLabel("페이지 리스트"))
        self.left_layout.addWidget(self.search_input)
        self.left_layout.addWidget(self.sort_selector)
        self.left_layout.addWidget(self.char_list)
        
        # 페이지 추가 버튼
        self.add_button = QPushButton("➕ 페이지 추가")
        self.add_button.clicked.connect(self.add_character)
        self.add_button.setEnabled(False)
        self.left_layout.addWidget(self.add_button)



    def setup_input_fields(self):
        self.name_input = QLineEdit()
        self.tag_input = QLineEdit()
        self.desc_input = QTextEdit()
        self.desc_input.setAcceptDrops(False)  # 설명 입력칸 드래그 앤 드롭 비활성화
        
        # 프롬프트 입력란에 자동완성 기능 추가
        self.prompt_input = CustomLineEdit()
        self.prompt_input.setAcceptDrops(False)  # 드래그 앤 드롭 비활성화
        try:
            with open("autocomplete.txt", 'r', encoding='utf-8') as f:
                prompts = [line.strip() for line in f if line.strip()]
            completer = QCompleter(prompts)
            self.prompt_input.set_custom_completer(completer)
        except Exception as e:
            print(f"자동완성 목록 로드 실패: {e}")
            # 기본 자동완성 목록 사용
            default_prompts = ["masterpiece", "best quality", "ultra-detailed", "8k uhd", "highres"]
            completer = QCompleter(default_prompts)
            self.prompt_input.set_custom_completer(completer)
        
        # 페이지 잠금 체크박스
        self.lock_checkbox = QCheckBox("🔓 페이지 잠금")
        self.lock_checkbox.setToolTip("잠금된 페이지는 삭제할 수 없습니다")
        self.lock_checkbox.setEnabled(False)
        self.lock_checkbox.stateChanged.connect(self.on_lock_changed)
        
        self.middle_layout.addWidget(QLabel("이름"))
        
        # 이름 입력란과 잠금 체크박스를 한 줄에 배치
        name_layout = QHBoxLayout()
        name_layout.addWidget(self.name_input)
        name_layout.addWidget(self.lock_checkbox)
        self.middle_layout.addLayout(name_layout)
        
        self.middle_layout.addWidget(QLabel("태그"))
        self.middle_layout.addWidget(self.tag_input)
        self.middle_layout.addWidget(QLabel("설명"))
        self.middle_layout.addWidget(self.desc_input)
        self.middle_layout.addWidget(QLabel("프롬프트"))
        self.middle_layout.addWidget(self.prompt_input)

    def setup_image_view(self):
        self.image_view = ImageView(self)
        self.image_scene = QGraphicsScene()
        self.image_view.setScene(self.image_scene)
        self.image_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_view.setRenderHint(QPainter.SmoothPixmapTransform)
        
        self.right_layout.addWidget(self.image_view)

    def setup_buttons(self):
        # 페이지 관리 버튼들
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("💾 저장")
        self.save_button.clicked.connect(lambda: (self.save_current_character(), QToolTip.showText(self.save_button.mapToGlobal(self.save_button.rect().center()), "페이지가 저장되었습니다.")))
        self.save_button.setEnabled(False)
        
        self.copy_button = QPushButton("📋 프롬프트 복사")
        self.copy_button.clicked.connect(self.copy_prompt_to_clipboard)
        self.copy_button.setEnabled(False)
        
        self.duplicate_button = QPushButton("📄 페이지 복제")
        self.duplicate_button.clicked.connect(self.duplicate_selected_character_with_tooltip)
        self.duplicate_button.setEnabled(False)
        
        self.delete_button = QPushButton("🗑️ 페이지 삭제")
        self.delete_button.clicked.connect(self.delete_selected_character_with_tooltip)
        self.delete_button.setEnabled(False)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.duplicate_button)
        button_layout.addWidget(self.delete_button)
        
        self.middle_layout.addLayout(button_layout)
        
        # 이미지 관리 버튼들
        image_button_layout = QHBoxLayout()
        
        self.image_load_btn = QPushButton("🖼️ 이미지 불러오기")
        self.image_load_btn.clicked.connect(self.load_preview_image)
        self.image_load_btn.setEnabled(False)
        
        self.image_remove_btn = QPushButton("🗑️ 이미지 제거")
        self.image_remove_btn.clicked.connect(self.remove_preview_image)
        self.image_remove_btn.setEnabled(False)
        
        image_button_layout.addWidget(self.image_load_btn)
        image_button_layout.addWidget(self.image_remove_btn)
        
        self.right_layout.addLayout(image_button_layout)

    def update_image_view(self, path):
        if not os.path.exists(path):
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            return

        # 이미지 리더 설정
        reader = QImageReader(path)
        reader.setAutoTransform(True)  # EXIF 정보 기반 자동 회전
        reader.setDecideFormatFromContent(True)  # 파일 내용 기반으로 포맷 결정
        reader.setQuality(100)  # 최고 품질 설정
        
        # 이미지 로드 전 크기 확인
        original_size = reader.size()
        if not original_size.isValid():
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            return

        # 고품질 이미지 로딩
        image = reader.read()
        if image.isNull():
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            return

        # 이미지 품질 향상을 위한 변환 설정
        pixmap = QPixmap.fromImage(image, Qt.PreferDither | Qt.AutoColor)
        
        # 씬 초기화 및 이미지 추가
        self.image_scene.clear()
        pixmap_item = QGraphicsPixmapItem()
        pixmap_item.setPixmap(pixmap)
        pixmap_item.setTransformationMode(Qt.SmoothTransformation)  # 부드러운 변환 모드 설정
        pixmap_item.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)  # 성능 최적화
        self.image_scene.addItem(pixmap_item)
        
        # 이미지 상태에 따라 힌트 가시성 업데이트
        self.image_view.update_drop_hint_visibility()
        
        # 이미지 크기 및 위치 조정
        self.update_image_fit()

    def update_image_fit(self):
        if not self.image_scene.items():
            return
            
        # 현재 이미지 아이템 가져오기
        image_item = None
        for item in self.image_scene.items():
            if isinstance(item, QGraphicsPixmapItem):
                image_item = item
                break
                
        if not image_item:
            return
            
        # 뷰포트와 씬 크기 가져오기
        viewport_rect = self.image_view.viewport().rect()
        viewport_width = viewport_rect.width()
        viewport_height = viewport_rect.height()
        
        # 이미지 크기 가져오기
        pixmap = image_item.pixmap()
        image_width = pixmap.width()
        image_height = pixmap.height()
        
        # 이미지와 뷰포트의 비율 계산
        scale_width = viewport_width / image_width
        scale_height = viewport_height / image_height
        scale = min(scale_width, scale_height)
        
        # 변환 매트릭스 초기화 및 스케일 설정
        self.image_view.resetTransform()
        self.image_view.scale(scale, scale)
        
        # 이미지 중앙 위치 계산
        scaled_width = image_width * scale
        scaled_height = image_height * scale
        x_offset = (viewport_width - scaled_width) / 2
        y_offset = (viewport_height - scaled_height) / 2
        
        # 씬 크기 설정 및 중앙 정렬
        self.image_scene.setSceneRect(image_item.boundingRect())
        self.image_view.centerOn(image_item)
        
        # 스크롤바 위치 조정으로 정확한 중앙 정렬
        self.image_view.horizontalScrollBar().setValue(
            int(self.image_view.horizontalScrollBar().maximum() / 2)
        )
        self.image_view.verticalScrollBar().setValue(
            int(self.image_view.verticalScrollBar().maximum() / 2)
        )

    def copy_prompt_to_clipboard(self):
        QApplication.clipboard().setText(self.prompt_input.toPlainText())
        QToolTip.showText(self.copy_button.mapToGlobal(self.copy_button.rect().center()), "프롬프트가 복사되었습니다.")

    def toggle_favorite_star(self, item):
        print("[DEBUG] toggle_favorite_star 호출됨")
        name = item.data(Qt.UserRole)
        print(f"[DEBUG] 아이템 이름: {name}")
        
        # 현재 정렬 모드 저장
        current_mode = self.sort_selector.currentText() if hasattr(self, "sort_selector") else "기본 정렬"
        print(f"[DEBUG] 현재 정렬 모드: {current_mode}")
        
        # 캐릭터 찾기 및 즐겨찾기 토글
        for i, char in enumerate(self.state.characters):
            if char.get("name") == name:
                print(f"[DEBUG] 캐릭터 찾음: {char}")
                is_favorite = not char.get("favorite", False)
                char["favorite"] = is_favorite
                
                # 상태 업데이트
                self.state.books[self.current_book]["pages"] = self.state.characters
                
                # 정렬 적용
                from promptbook_features import sort_characters
                self.state.characters = sort_characters(self.state.characters, current_mode)
                
                # 리스트 갱신 전 디버그 출력
                print("[DEBUG] 정렬 후 캐릭터 순서:")
                for c in self.state.characters:
                    print(f"  - {c.get('name')} (즐겨찾기: {c.get('favorite', False)})")
                
                # 리스트 갱신
                self.refresh_character_list(selected_name=name)
                self.save_to_file()
                break

    def on_character_reordered(self):
        print("[DEBUG] on_character_reordered 호출됨")
        self.sort_mode_custom = True
        new_order = []
        for i in range(self.char_list.count()):
            name = self.char_list.item(i).data(Qt.UserRole)
            for char in self.state.characters:
                if char.get("name") == name:
                    new_order.append(char)
                    break
        self.state.characters = new_order
        self.state.books[self.current_book]["pages"] = self.state.characters
        print("[DEBUG] 새로운 순서로 저장됨")
        self.save_to_file()

    def filter_characters(self):
        query = self.search_input.text().strip().lower()
        self.char_list.blockSignals(True)
        self.char_list.clear()
        for i, char in enumerate(self.state.characters):
            name = char.get("name", "").lower()
            tags = char.get("tags", "").lower()
            if query in name or query in tags:
                item = QListWidgetItem()
                text = char.get("name", "(이름 없음)")
                is_favorite = char.get("favorite", False)
                emoji = char.get("emoji", "📄")
                
                # 커스텀 위젯 생성
                widget = PageItemWidget(text, is_favorite, emoji)
                item.setData(Qt.UserRole, text)
                
                self.char_list.addItem(item)
                self.char_list.setItemWidget(item, widget)
                item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, i)
        self.char_list.blockSignals(False)

    def filter_books(self):
        """북 검색 필터링"""
        self.refresh_book_list()

    def refresh_book_list(self, selected_name=None):
        """북 리스트 갱신"""
        # 검색어가 있으면 필터링, 없으면 전체 표시
        query = self.book_search_input.text().strip().lower() if hasattr(self, "book_search_input") else ""
        
        self.book_list.blockSignals(True)
        self.book_list.clear()
        
        for name, data in self.state.books.items():
            if isinstance(data, dict):  # 딕셔너리 형식 확인
                book_name_lower = name.lower()
                if not query or query in book_name_lower:
                    emoji = data.get("emoji", "📕")
                    is_favorite = data.get("favorite", False)
                    item = QListWidgetItem()
                    
                    # 커스텀 위젯 생성
                    widget = BookItemWidget(name, is_favorite, emoji)
                    item.setData(Qt.UserRole, name)
                    
                    self.book_list.addItem(item)
                    self.book_list.setItemWidget(item, widget)
                    item.setSizeHint(widget.sizeHint())
        
        # 선택 상태 복원
        if selected_name:
            for i in range(self.book_list.count()):
                item = self.book_list.item(i)
                if item.data(Qt.UserRole) == selected_name:
                    self.book_list.setCurrentItem(item)
                    break
        
        self.book_list.blockSignals(False)

    def save_current_character(self):
        if self.current_book and 0 <= self.current_index < len(self.state.characters):
            data = self.state.characters[self.current_index]
            data["name"] = self.name_input.text()
            data["tags"] = self.tag_input.text()
            data["desc"] = self.desc_input.toPlainText()
            data["prompt"] = self.prompt_input.toPlainText()
            self.state.books[self.current_book]["pages"] = self.state.characters
            
            # 현재 아이템의 위젯 업데이트
            item = self.char_list.item(self.current_index)
            if item:
                widget = self.char_list.itemWidget(item)
                if isinstance(widget, PageItemWidget):
                    widget.set_name(data["name"])
                    widget.set_favorite(data.get("favorite", False))
                    widget.set_emoji(data.get("emoji", "📄"))
            
            self.save_to_file()

    def on_character_selected(self, index):
        print(f"[DEBUG] on_character_selected: index={index}")
        self.update_all_buttons_state()  # 입력창 상태 갱신
        
        if 0 <= index < self.char_list.count():
            item = self.char_list.item(index)
            if not item:
                return
                
            name = item.data(Qt.UserRole)
            print(f"[DEBUG] 선택된 페이지 이름: {name}")
            
            # characters 리스트에서 해당 페이지 찾기
            for i, char in enumerate(self.state.characters):
                if char.get("name") == name:
                    print(f"[DEBUG] 페이지 데이터 찾음: {char}")
                    self.current_index = i
                    
                    # 입력 필드 업데이트
                    self.name_input.setText(char.get("name", ""))
                    self.tag_input.setText(char.get("tags", ""))
                    self.desc_input.setPlainText(char.get("desc", ""))
                    self.prompt_input.setPlainText(char.get("prompt", ""))
                    
                    # 잠금 상태 표시
                    is_locked = char.get('locked', False)
                    self.lock_checkbox.setChecked(is_locked)
                    self.lock_checkbox.setEnabled(True)
                    
                    # 체크박스 텍스트 업데이트
                    if is_locked:
                        self.lock_checkbox.setText("🔒 페이지 잠금")
                    else:
                        self.lock_checkbox.setText("🔓 페이지 잠금")
                    
                    # 이미지 업데이트
                    if "image_path" in char and os.path.exists(char["image_path"]):
                        self.update_image_view(char["image_path"])
                    else:
                        self.image_scene.clear()
                        self.image_view.update_drop_hint_visibility()
                    break
        else:
            print("[DEBUG] 페이지 선택 해제")
            self.current_index = -1
            self.name_input.clear()
            self.tag_input.clear()
            self.desc_input.clear()
            self.prompt_input.clear()
            self.lock_checkbox.setChecked(False)
            self.lock_checkbox.setText("🔓 페이지 잠금")
            self.lock_checkbox.setEnabled(False)
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            
        self.update_all_buttons_state()
    
    def on_lock_changed(self):
        """잠금 상태가 변경되었을 때 실행되는 함수"""
        if self.current_index >= 0 and self.current_index < len(self.state.characters):
            is_locked = self.lock_checkbox.isChecked()
            self.state.characters[self.current_index]['locked'] = is_locked
            
            # 체크박스 텍스트 업데이트
            if is_locked:
                self.lock_checkbox.setText("🔒 페이지 잠금")
            else:
                self.lock_checkbox.setText("🔓 페이지 잠금")
            
            self.update_all_buttons_state()
            self.save_current_character()

    def save_ui_settings(self):
        settings = {
            "width": self.width(),
            "height": self.height(),
            "splitter_sizes": self.main_splitter.sizes() if hasattr(self, "main_splitter") else [200, 400, 372],
            "sort_mode": self.sort_selector.currentText() if hasattr(self, "sort_selector") else "오름차순 정렬",
            "sort_mode_custom": self.sort_mode_custom,
            "book_sort_mode": self.book_sort_selector.currentText() if hasattr(self, "book_sort_selector") else "오름차순 정렬",
            "book_sort_custom": getattr(self, "book_sort_custom", False)
        }
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"[ERROR] UI 설정 저장 실패: {e}")

    def load_ui_settings(self):
        try:
            with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
                # 윈도우 크기 복원
                if "width" in settings and "height" in settings:
                    self.resize(settings["width"], settings["height"])
                
                # 스플리터 크기 복원
                if "splitter_sizes" in settings and hasattr(self, "main_splitter"):
                    self.main_splitter.setSizes(settings["splitter_sizes"])
                    
                # 페이지 정렬 상태 복원
                if hasattr(self, "sort_selector"):
                    sort_mode = settings.get("sort_mode", "오름차순 정렬")
                    index = self.sort_selector.findText(sort_mode)
                    if index >= 0:
                        self.sort_selector.setCurrentIndex(index)
                    self.sort_mode_custom = settings.get("sort_mode_custom", False)
                    
                # 북 정렬 상태 복원
                if hasattr(self, "book_sort_selector"):
                    book_sort_mode = settings.get("book_sort_mode", "오름차순 정렬")
                    index = self.book_sort_selector.findText(book_sort_mode)
                    if index >= 0:
                        self.book_sort_selector.setCurrentIndex(index)
                    self.book_sort_custom = settings.get("book_sort_custom", False)
                    
                    # 현재 북 정렬 모드 적용
                    if not self.book_sort_custom:
                        self.handle_book_sort()
                    
                    # 현재 북이 선택되어 있고 페이지가 있다면 정렬 적용
                    if self.current_book and self.state.characters:
                        from promptbook_features import sort_characters
                        self.state.characters = sort_characters(self.state.characters, sort_mode)
                        self.refresh_character_list()
                        
        except Exception as e:
            print(f"[ERROR] UI 설정 불러오기 실패: {e}")

    def clear_page_list(self):
        self.state.characters = []
        self.char_list.clear()
        self.current_book = None
        self.image_scene.clear()
        self.image_view.update_drop_hint_visibility()
        self.update_all_buttons_state()

    def closeEvent(self, event):
        self.save_ui_settings()
        super().closeEvent(event)

    def update_all_buttons_state(self):
        enabled = self.current_book is not None
        self.add_button.setEnabled(enabled)
        
        # 정렬 선택기 활성화/비활성화
        if hasattr(self, "sort_selector"):
            self.sort_selector.setEnabled(enabled)
        
        page_enabled = enabled and self.current_index >= 0
        self.name_input.setEnabled(page_enabled)
        self.tag_input.setEnabled(page_enabled)
        self.desc_input.setEnabled(page_enabled)
        self.prompt_input.setEnabled(page_enabled)
        self.save_button.setEnabled(page_enabled)
        self.copy_button.setEnabled(page_enabled)
        self.duplicate_button.setEnabled(page_enabled)
        self.image_load_btn.setEnabled(page_enabled)
        self.image_remove_btn.setEnabled(page_enabled)
        
        # 잠금 상태에 따른 삭제 버튼 비활성화
        if page_enabled and self.current_index >= 0 and self.current_index < len(self.state.characters):
            is_locked = self.state.characters[self.current_index].get('locked', False)
            self.delete_button.setEnabled(not is_locked)
        else:
            self.delete_button.setEnabled(page_enabled)

    def refresh_character_list(self, selected_name=None, should_save=True):
        print("[DEBUG] refresh_character_list 시작")
        print(f"[DEBUG] 선택된 이름: {selected_name}")
        
        if not self.current_book:
            print("[DEBUG] current_book 없음 → 페이지 리스트 표시 생략")
            self.state.characters = []
            self.char_list.clear()
            self.update_all_buttons_state()
            return

        # 검색어 가져오기
        query = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        print(f"[DEBUG] 검색어: {query}")
        
        # 리스트 갱신 준비
        self.char_list.blockSignals(True)
        self.char_list.clear()
        
        # 현재 정렬 상태 출력
        print("[DEBUG] 현재 캐릭터 순서:")
        for c in self.state.characters:
            print(f"  - {c.get('name')} (즐겨찾기: {c.get('favorite', False)})")
        
        # 필터링 및 아이템 추가
        selected_index = -1
        for i, char in enumerate(self.state.characters):
            name = char.get("name", "").lower()
            tags = char.get("tags", "").lower()
            
            if not query or query in name or query in tags:
                item = QListWidgetItem()
                text = char.get("name", "(이름 없음)")
                is_favorite = char.get("favorite", False)
                emoji = char.get("emoji", "📄")
                
                # 커스텀 위젯 생성
                widget = PageItemWidget(text, is_favorite, emoji)
                item.setData(Qt.UserRole, text)
                
                self.char_list.addItem(item)
                self.char_list.setItemWidget(item, widget)
                item.setSizeHint(widget.sizeHint())
                
                if text == selected_name:
                    selected_index = self.char_list.count() - 1
                    print(f"[DEBUG] 선택된 항목 찾음: 인덱스 {selected_index}")

        self.char_list.blockSignals(False)

        # 선택 상태 복원
        if selected_index >= 0:
            print(f"[DEBUG] 선택 상태 복원: 인덱스 {selected_index}")
            self.char_list.setCurrentRow(selected_index)
            self.current_index = selected_index
        elif self.char_list.count() > 0:
            print("[DEBUG] 첫 번째 항목 선택")
            self.char_list.setCurrentRow(0)
            self.current_index = 0

        self.update_all_buttons_state()
        
        # 상태가 변경되었으면 저장
        if should_save:
            print("[DEBUG] 상태 저장")
            self.state.books[self.current_book]["pages"] = self.state.characters
            self.save_to_file()
            
        print("[DEBUG] refresh_character_list 완료")

    def on_book_selected(self, index):
        self.sort_mode_custom = False
        if 0 <= index < self.book_list.count():
            item = self.book_list.item(index)
            book_name = item.data(Qt.UserRole) if item else None
            self.current_book = book_name
            book_data = self.state.books.get(book_name, {})
            self.state.characters = book_data.get("pages", [])
            
            # 현재 정렬 모드 적용 (커스텀 정렬이 아닌 경우)
            if hasattr(self, 'sort_selector') and not self.sort_mode_custom and self.state.characters:
                current_sort_mode = self.sort_selector.currentText()
                print(f"[DEBUG] 북 선택 시 정렬 적용: {current_sort_mode}")
                from promptbook_features import sort_characters
                self.state.characters = sort_characters(self.state.characters, current_sort_mode)
                self.state.books[self.current_book]["pages"] = self.state.characters
            
            # 버튼 활성화
            self.add_button.setEnabled(True)
            
            # 페이지 리스트 업데이트 (선택된 페이지 없음)
            self.refresh_character_list(selected_name=None)
            
            # 입력 필드 초기화 및 선택 상태 해제
            self.current_index = -1
            self.char_list.clearSelection()  # 선택 상태 해제
            self.name_input.clear()
            self.tag_input.clear()
            self.desc_input.clear()
            self.prompt_input.clear()
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()  # 드롭 힌트 가시성 업데이트
        else:
            # 북이 선택되지 않은 경우
            self.current_book = None
            self.state.characters = []
            self.char_list.clear()
            self.add_button.setEnabled(False)
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()  # 드롭 힌트 가시성 업데이트
            
        self.update_all_buttons_state()

    def save_to_file(self):
        print("[DEBUG] save_to_file 호출됨")
        if getattr(self, '_initial_loading', False):
            return
        try:
            with open(self.SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state.books, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 저장 실패: {e}")

    def load_from_file(self):
        print("[DEBUG] load_from_file 호출됨")
        if os.path.exists(self.SAVE_FILE):
            try:
                with open(self.SAVE_FILE, 'r', encoding='utf-8') as f:
                    self.state.books = json.load(f)
                # 북 리스트 갱신
                self.refresh_book_list()

                self.current_book = None
                self.state.characters = []
                self.char_list.clear()
                self.name_input.clear()
                self.tag_input.clear()
                self.desc_input.clear()
                self.prompt_input.clear()
                self.image_scene.clear()
                self.update_all_buttons_state()

            except Exception as e:
                print(f"불러오기 실패: {e}")
                QMessageBox.warning(self, "오류", f"파일 불러오기 중 오류가 발생했습니다:\n{str(e)}")
        self._initial_loading = False

    def change_character(self, new_index):
        selected_name = None
        if new_index != -1 and self.char_list.item(new_index):
            selected_name = self.char_list.item(new_index).data(Qt.UserRole)

        new_index = -1
        for i, char in enumerate(self.state.characters):
            if char["name"] == selected_name:
                new_index = i
                break

        self.current_index = new_index
        self.load_character(new_index)

    def copy_prompt_to_clipboard(self):
        QApplication.clipboard().setText(self.prompt_input.toPlainText())
        QToolTip.showText(self.copy_button.mapToGlobal(self.copy_button.rect().center()), "프롬프트가 복사되었습니다.")

    def duplicate_selected_character_with_tooltip(self):
        self.duplicate_selected_character()
        QToolTip.showText(self.duplicate_button.mapToGlobal(self.duplicate_button.rect().center()), "페이지가 복제되었습니다.")

    def delete_selected_character_with_tooltip(self):
        self.delete_selected_character()
        QToolTip.showText(self.delete_button.mapToGlobal(self.delete_button.rect().center()), "페이지가 삭제되었습니다.")

    def load_preview_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "이미지 불러오기", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.load_image_from_path(file_path)
    
    def load_image_from_path(self, file_path):
        """파일 경로로부터 이미지를 로드하는 공통 메서드"""
        if not file_path or not os.path.exists(file_path):
            print(f"[ERROR] 이미지 파일이 존재하지 않습니다: {file_path}")
            return
            
        # 현재 페이지가 선택되어 있는지 확인
        if not (0 <= self.current_index < len(self.state.characters)):
            QMessageBox.warning(self, "이미지 로드 실패", "먼저 페이지를 선택해 주세요.")
            return
            
        # 이미지 파일 경로 저장
        self.state.characters[self.current_index]["image_path"] = file_path
        self.edited = True
        self.update_image_buttons_state()
        
        # 이미지 뷰 업데이트
        self.update_image_view(file_path)
        
        # 상태 저장
        if self.current_book:
            self.state.books[self.current_book]["pages"] = self.state.characters
            self.save_to_file()
            
        print(f"[DEBUG] 이미지 로드 완료: {file_path}")

    def load_character(self, index):
        if 0 <= index < len(self.state.characters):
            self.block_save = True
            self.current_index = index
            data = self.state.characters[index]
            self.name_input.setText(data["name"])
            self.tag_input.setText(data["tags"])
            self.desc_input.setPlainText(data["desc"])
            self.prompt_input.setPlainText(data["prompt"])

            if "image_path" in data and os.path.exists(data["image_path"]):
                self.update_image_view(data["image_path"])
            else:
                self.image_scene.clear()

            self.block_save = False
            self.edited = False
        else:
            self.name_input.clear()
            self.tag_input.clear()
            self.desc_input.clear()
            self.prompt_input.clear()
            self.image_scene.clear()

        self.name_input.setEnabled(index != -1)
        self.tag_input.setEnabled(index != -1)
        self.desc_input.setEnabled(index != -1)
        self.prompt_input.setEnabled(index != -1)
        self.save_button.setEnabled(index != -1)
        self.copy_button.setEnabled(index != -1)
        self.delete_button.setEnabled(index != -1)
        self.image_load_btn.setEnabled(index != -1)
        self.image_remove_btn.setEnabled(index != -1)
        self.update_image_buttons_state()

    def on_character_clicked(self, item):
        print("[DEBUG] on_character_clicked 호출됨")
        index = self.char_list.row(item)
        print(f"[DEBUG] 클릭된 인덱스: {index}")
        self.on_character_selected(index)

    def handle_character_sort(self):
        mode = self.sort_selector.currentText()
        print(f"[DEBUG] 정렬 모드: {mode}")

        # 현재 북이 없으면 정렬하지 않음
        if not self.current_book:
            print("[DEBUG] 현재 선택된 북이 없음")
            return

        if mode == "커스텀 정렬":
            self.sort_mode_custom = True
            self.char_list.setDragDropMode(QAbstractItemView.InternalMove)
            self.char_list.setDefaultDropAction(Qt.MoveAction)
        else:
            self.sort_mode_custom = False
            self.char_list.setDragDropMode(QAbstractItemView.NoDragDrop)

        # 정렬 적용
        from promptbook_features import sort_characters
        self.state.characters = sort_characters(self.state.characters, mode)
        
        # 상태 저장
        if self.current_book in self.state.books:
            self.state.books[self.current_book]["pages"] = self.state.characters
            
            # 리스트 갱신 및 저장
            self.refresh_character_list(should_save=True)
            
            # UI 설정 저장
            self.save_ui_settings()
            
            print(f"[DEBUG] 정렬 후 캐릭터 순서:")
            for char in self.state.characters:
                print(f"  - {char.get('name')} (즐겨찾기: {char.get('favorite', False)})")
        else:
            print(f"[DEBUG] 현재 북 '{self.current_book}'이(가) books에 없음")

    def add_book(self):
        print("[DEBUG] add_book 메서드 호출됨")  # 디버그 추가
        base_name = "새 북"
        existing_names = set()
        for i in range(self.book_list.count()):
            item = self.book_list.item(i)
            if item:
                existing_names.add(item.data(Qt.UserRole))
        
        # 고유한 이름 생성
        if base_name not in existing_names:
            unique_name = base_name
        else:
            for i in range(1, 1000):
                candidate = f"{base_name} ({i})"
                if candidate not in existing_names:
                    unique_name = candidate
                    break

        print(f"[DEBUG] 새 북 이름: {unique_name}")  # 디버그 추가
        
        # 새 북 데이터 생성
        self.state.books[unique_name] = {
            "emoji": "📕",
            "pages": []
        }
        print(f"[DEBUG] 새 북 데이터 생성 완료, 현재 북 수: {len(self.state.books)}")  # 디버그 추가
        
        # 리스트에 아이템 추가
        item = QListWidgetItem()
        
        # 커스텀 위젯 생성
        widget = BookItemWidget(unique_name, False, "📕")
        item.setData(Qt.UserRole, unique_name)
        
        self.book_list.addItem(item)
        self.book_list.setItemWidget(item, widget)
        item.setSizeHint(widget.sizeHint())
        print(f"[DEBUG] 북 리스트에 아이템 추가 완료")  # 디버그 추가
        
        # 현재 정렬 모드가 커스텀이 아니면 정렬 적용
        if hasattr(self, 'book_sort_selector') and not self.book_sort_custom:
            self.handle_book_sort()
            # 정렬 후 새로 생성된 아이템 찾기
            item = None
            for i in range(self.book_list.count()):
                book_item = self.book_list.item(i)
                if book_item.data(Qt.UserRole) == unique_name:
                    item = book_item
                    break
        
        # 새로 추가된 북 선택
        if item:
            self.book_list.setCurrentItem(item)
            self.on_book_selected(self.book_list.row(item))
            print(f"[DEBUG] 새 북 선택 완료")  # 디버그 추가
        else:
            print(f"[DEBUG] 새 북 아이템을 찾을 수 없음")  # 디버그 추가
        
        self.save_to_file()
        print(f"[DEBUG] add_book 완료")  # 디버그 추가

    def save_selected_book(self):
        """선택된 북을 zip 파일로 저장합니다."""
        if not self.current_book:
            QMessageBox.warning(self, "저장 실패", "선택된 북이 없습니다.")
            return
            
        # 파일 저장 대화상자
        default_name = f"{self.current_book}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "북 저장", default_name, "Zip Files (*.zip)")
        if not path:
            return
            
        try:
            from zipfile import ZipFile
            
            with ZipFile(path, 'w') as zipf:
                # 현재 북 데이터 가져오기
                book_data = self.state.books[self.current_book]
                pages = book_data.get("pages", [])
                
                # 내보낼 데이터 준비
                export_data = {
                    "book_name": self.current_book,
                    "emoji": book_data.get("emoji", "📕"),
                    "pages": []
                }
                
                # 각 페이지 처리
                for i, page in enumerate(pages):
                    page_copy = dict(page)
                    
                    # 이미지가 있으면 zip에 포함
                    img_path = page.get("image_path")
                    if img_path and os.path.exists(img_path):
                        # zip 내부 경로 생성
                        filename = f"images/{i}_{os.path.basename(img_path)}"
                        zipf.write(img_path, filename)
                        page_copy["image_path"] = filename
                    else:
                        page_copy["image_path"] = ""
                        
                    export_data["pages"].append(page_copy)
                
                # 북 데이터를 JSON으로 저장
                zipf.writestr("book_data.json", json.dumps(export_data, ensure_ascii=False, indent=2))
                
            QMessageBox.information(self, "저장 완료", f"'{self.current_book}' 북이 성공적으로 저장되었습니다.")
            print(f"[DEBUG] 선택된 북 저장 완료: {self.current_book} -> {path}")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"북 저장 중 오류가 발생했습니다:\n{str(e)}")
            print(f"[ERROR] 북 저장 실패: {e}")

    def load_saved_book(self):
        """저장된 북을 zip 파일에서 불러옵니다."""
        # 파일 열기 대화상자
        path, _ = QFileDialog.getOpenFileName(self, "북 불러오기", "", "Zip Files (*.zip)")
        if not path:
            return
            
        try:
            from zipfile import ZipFile
            import tempfile
            
            # 임시 디렉토리에 압축 해제
            temp_dir = tempfile.mkdtemp()
            
            with ZipFile(path, 'r') as zipf:
                zipf.extractall(temp_dir)
                
                # 새 형식 확인: book_data.json 파일
                json_path = os.path.join(temp_dir, "book_data.json")
                if os.path.exists(json_path):
                    # 새 형식 처리
                    self._load_new_format_book(temp_dir, json_path)
                else:
                    # 기존 형식 확인: character_list.zip 구조
                    json_files = [f for f in os.listdir(temp_dir) if f.endswith('.json')]
                    if json_files:
                        # 기존 형식 처리
                        self._load_legacy_format_book(temp_dir, json_files)
                    else:
                        QMessageBox.warning(self, "불러오기 실패", "올바른 북 파일이 아닙니다.")
                        return
                        
        except Exception as e:
            QMessageBox.critical(self, "불러오기 실패", f"북 불러오기 중 오류가 발생했습니다:\n{str(e)}")
            print(f"[ERROR] 북 불러오기 실패: {e}")

    def _load_new_format_book(self, temp_dir, json_path):
        """새 형식 북 파일 불러오기 (book_data.json)"""
        with open(json_path, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
        
        # 북 이름 중복 체크
        original_name = book_data.get("book_name", "불러온 북")
        book_name = original_name
        existing_names = set(self.state.books.keys())
        
        if book_name in existing_names:
            # 중복된 북 이름이 있을 때 사용자에게 선택권 제공
            msgBox = QMessageBox()
            msgBox.setWindowTitle("북 이름 중복")
            msgBox.setText(f"'{original_name}' 북이 이미 존재합니다.")
            msgBox.setInformativeText("어떻게 하시겠습니까?")
            
            overwrite_btn = msgBox.addButton("덮어쓰기", QMessageBox.AcceptRole)
            add_new_btn = msgBox.addButton("새로 추가", QMessageBox.ActionRole)
            cancel_btn = msgBox.addButton("취소", QMessageBox.RejectRole)
            
            msgBox.setDefaultButton(cancel_btn)
            msgBox.exec()
            
            if msgBox.clickedButton() == overwrite_btn:
                # 기존 북 덮어쓰기
                book_name = original_name
                print(f"[DEBUG] 기존 북 덮어쓰기: {book_name}")
            elif msgBox.clickedButton() == add_new_btn:
                # 새 이름으로 추가
                for i in range(1, 1000):
                    candidate = f"{original_name} ({i})"
                    if candidate not in existing_names:
                        book_name = candidate
                        break
                print(f"[DEBUG] 새 이름으로 추가: {book_name}")
            else:
                # 취소
                print("[DEBUG] 북 불러오기 취소")
                return
        
        # 이미지 파일들을 images 폴더로 복사
        pages = book_data.get("pages", [])
        for page in pages:
            rel_path = page.get("image_path")
            if rel_path:
                full_path = os.path.join(temp_dir, rel_path)
                if os.path.exists(full_path):
                    # images 폴더 생성
                    os.makedirs("images", exist_ok=True)
                    # 고유한 파일명 생성
                    dest_filename = f"{book_name}_{os.path.basename(full_path)}"
                    dest_path = os.path.join("images", dest_filename)
                    
                    # 파일명 중복 방지
                    counter = 1
                    while os.path.exists(dest_path):
                        name, ext = os.path.splitext(dest_filename)
                        dest_filename = f"{name}_{counter}{ext}"
                        dest_path = os.path.join("images", dest_filename)
                        counter += 1
                    
                    shutil.copy(full_path, dest_path)
                    page["image_path"] = dest_path
                else:
                    page["image_path"] = ""
        
        # 새 북을 books에 추가
        emoji = book_data.get("emoji", "📕")
        self.state.books[book_name] = {
            "emoji": emoji,
            "pages": pages
        }
        
        self._add_book_to_ui(book_name, emoji)
        
        QMessageBox.information(self, "불러오기 완료", f"'{book_name}' 북이 성공적으로 불러와졌습니다.")
        print(f"[DEBUG] 새 형식 북 불러오기 완료: {book_name}")

    def _load_legacy_format_book(self, temp_dir, json_files):
        """기존 형식 북 파일 불러오기 (character_list.zip 구조)"""
        # 모든 페이지를 하나의 북에 통합
        all_pages = []
        
        for json_file in json_files:
            json_path = os.path.join(temp_dir, json_file)
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    pages = json.load(f)
                    if isinstance(pages, list):
                        all_pages.extend(pages)
            except Exception as e:
                print(f"[ERROR] JSON 파일 읽기 실패 {json_file}: {e}")
                continue
        
        if not all_pages:
            QMessageBox.warning(self, "불러오기 실패", "불러올 페이지가 없습니다.")
            return
        
        # 새 북 이름 생성
        base_name = "불러온 북"
        book_name = base_name
        existing_names = set(self.state.books.keys())
        
        if book_name in existing_names:
            # 중복된 북 이름이 있을 때 사용자에게 선택권 제공
            msgBox = QMessageBox()
            msgBox.setWindowTitle("북 이름 중복")
            msgBox.setText(f"'{base_name}' 북이 이미 존재합니다.")
            msgBox.setInformativeText("어떻게 하시겠습니까?")
            
            overwrite_btn = msgBox.addButton("덮어쓰기", QMessageBox.AcceptRole)
            add_new_btn = msgBox.addButton("새로 추가", QMessageBox.ActionRole)
            cancel_btn = msgBox.addButton("취소", QMessageBox.RejectRole)
            
            msgBox.setDefaultButton(cancel_btn)
            msgBox.exec()
            
            if msgBox.clickedButton() == overwrite_btn:
                # 기존 북 덮어쓰기
                book_name = base_name
                print(f"[DEBUG] 기존 북 덮어쓰기: {book_name}")
            elif msgBox.clickedButton() == add_new_btn:
                # 새 이름으로 추가
                for i in range(1, 1000):
                    candidate = f"{base_name} ({i})"
                    if candidate not in existing_names:
                        book_name = candidate
                        break
                print(f"[DEBUG] 새 이름으로 추가: {book_name}")
            else:
                # 취소
                print("[DEBUG] 북 불러오기 취소")
                return
        
        # 이미지 파일들을 images 폴더로 복사
        for page in all_pages:
            rel_path = page.get("image_path")
            if rel_path:
                full_path = os.path.join(temp_dir, rel_path)
                if os.path.exists(full_path):
                    # images 폴더 생성
                    os.makedirs("images", exist_ok=True)
                    # 고유한 파일명 생성
                    dest_filename = f"{book_name}_{os.path.basename(full_path)}"
                    dest_path = os.path.join("images", dest_filename)
                    
                    # 파일명 중복 방지
                    counter = 1
                    while os.path.exists(dest_path):
                        name, ext = os.path.splitext(dest_filename)
                        dest_filename = f"{name}_{counter}{ext}"
                        dest_path = os.path.join("images", dest_filename)
                        counter += 1
                    
                    shutil.copy(full_path, dest_path)
                    page["image_path"] = dest_path
                else:
                    page["image_path"] = ""
        
        # 새 북을 books에 추가
        emoji = "📚"  # 기존 형식은 특별한 이모지 사용
        self.state.books[book_name] = {
            "emoji": emoji,
            "pages": all_pages
        }
        
        self._add_book_to_ui(book_name, emoji)
        
        QMessageBox.information(self, "불러오기 완료", f"'{book_name}' 북이 성공적으로 불러와졌습니다.\n({len(all_pages)}개 페이지)")
        print(f"[DEBUG] 기존 형식 북 불러오기 완료: {book_name} ({len(all_pages)}개 페이지)")

    def _add_book_to_ui(self, book_name, emoji):
        """북을 UI에 추가하는 공통 메서드"""
        # 북 리스트 UI 업데이트
        item = QListWidgetItem()
        
        # 커스텀 위젯 생성
        is_favorite = self.state.books[book_name].get("favorite", False)
        widget = BookItemWidget(book_name, is_favorite, emoji)
        item.setData(Qt.UserRole, book_name)
        
        self.book_list.addItem(item)
        self.book_list.setItemWidget(item, widget)
        item.setSizeHint(widget.sizeHint())
        
        # 북 정렬 적용
        if hasattr(self, 'book_sort_selector') and not self.book_sort_custom:
            self.handle_book_sort()
            # 정렬 후 새로 생성된 아이템 찾기
            for i in range(self.book_list.count()):
                book_item = self.book_list.item(i)
                if book_item.data(Qt.UserRole) == book_name:
                    item = book_item
                    break
        
        # 새로 불러온 북 선택
        if item:
            self.book_list.setCurrentItem(item)
            self.on_book_selected(self.book_list.row(item))
            
            # 불러온 북의 페이지들을 현재 정렬 모드에 맞게 정렬
            if hasattr(self, 'sort_selector') and not self.sort_mode_custom:
                current_sort_mode = self.sort_selector.currentText()
                print(f"[DEBUG] 불러온 북에 정렬 적용: {current_sort_mode}")
                from promptbook_features import sort_characters
                self.state.characters = sort_characters(self.state.characters, current_sort_mode)
                self.state.books[self.current_book]["pages"] = self.state.characters
                self.refresh_character_list()
        
        # 데이터 저장
        self.save_to_file()

    def add_character(self):
        if not self.current_book:
            return

        base_name = "새 페이지"
        existing_names = {char["name"] for char in self.state.characters}
        
        if base_name not in existing_names:
            unique_name = base_name
        else:
            for i in range(1, 1000):
                candidate = f"{base_name} ({i})"
                if candidate not in existing_names:
                    unique_name = candidate
                    break

        new_data = {
            "name": unique_name,
            "tags": "",
            "desc": "",
            "prompt": "",
            "emoji": "📄"
        }

        self.state.characters.append(new_data)
        
        if not self.sort_mode_custom:
            from promptbook_features import sort_characters
            self.state.characters = sort_characters(self.state.characters, self.sort_selector.currentText())

        self.state.books[self.current_book]["pages"] = self.state.characters
        self.refresh_character_list(selected_name=unique_name)
        
        # 새로 추가된 페이지 찾기
        for i in range(self.char_list.count()):
            item = self.char_list.item(i)
            if item.data(Qt.UserRole) == unique_name:
                self.char_list.setCurrentItem(item)
                self.char_list.scrollToItem(item)
                # 새 페이지의 내용 표시
                self.on_character_selected(i)
                self.name_input.setFocus()  # 이름 입력란에 포커스
                break
                
        self.save_to_file()



    def show_character_context_menu(self, position):
        item = self.char_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        # 메뉴 여백 최적화
        menu.setStyleSheet("""
            QMenu {
                padding: 2px;
            }
            QMenu::item {
                padding: 4px 16px 4px 4px;
                margin: 0px;
            }
            QMenu::item:selected {
                background-color: #505050;
                color: white;
            }
            QMenu::item:hover {
                background-color: #505050;
                color: white;
            }
        """)
        name = item.data(Qt.UserRole)
        is_favorite = False
        
        # 현재 즐겨찾기 상태 확인
        for char in self.state.characters:
            if char.get("name") == name:
                is_favorite = char.get("favorite", False)
                break
        
        # 즐겨찾기 액션 추가
        if is_favorite:
            favorite_action = menu.addAction("❌ 즐겨찾기 해제")
        else:
            favorite_action = menu.addAction("⭐ 즐겨찾기")
        
        # 구분선 추가
        menu.addSeparator()
        
        # 이모지 변경 서브메뉴
        emoji_menu = QMenu("🔄 이모지 변경")
        emoji_menu.setStyleSheet("""
            QMenu {
                padding: 2px;
            }
            QMenu::item {
                padding: 4px 16px 4px 4px;
                margin: 0px;
            }
            QMenu::item:selected {
                background-color: #505050;
                color: white;
            }
            QMenu::item:hover {
                background-color: #505050;
                color: white;
            }
        """)
        menu.addMenu(emoji_menu)
        
        # 페이지용 이모지 옵션 그룹화
        page_emoji_groups = {
            "페이지": ["📄", "📃", "🗒️", "📑", "🧾", "📰", "🗞️", "📋", "📌", "📎"],
            "특수": ["🌟", "✨", "🔥", "🎯", "🚀", "🧩", "🎨", "💡", "❤️", "💀"],
            "동물": ["🐉", "🦄", "🐱", "👻", "🍀", "🪐", "😺"],
            "표정": ["😀", "😎", "🥳", "😈", "🤖", "👽", "👾", "🙈"],
            "사람": ["👧", "👩", "🧒", "👸", "💃", "🧝‍♀️", "🧚‍♀️", "🧞‍♀️", "👩‍🎤", "👩‍🔬"]
        }
        
        for group_name, emojis in page_emoji_groups.items():
            group_menu = QMenu(group_name)
            group_menu.setStyleSheet("""
                QMenu {
                    padding: 2px;
                }
                QMenu::item {
                    padding: 4px 16px 4px 4px;
                    margin: 0px;
                }
                QMenu::item:selected {
                    background-color: #505050;
                    color: white;
                }
                QMenu::item:hover {
                    background-color: #505050;
                    color: white;
                }
            """)
            emoji_menu.addMenu(group_menu)
            for emoji in emojis:
                action = group_menu.addAction(emoji)
                action.triggered.connect(lambda checked, e=emoji, i=item: self.set_page_emoji(i, e))
        
        # 구분선 추가
        menu.addSeparator()
        
        # 기타 액션들 추가
        duplicate_action = menu.addAction("📋 페이지 복제")
        delete_action = menu.addAction("🗑️ 페이지 삭제")
        
        # 메뉴 표시 및 액션 처리
        action = menu.exec_(self.char_list.mapToGlobal(position))
        if action == favorite_action:
            self.toggle_favorite_star(item)
        elif action == duplicate_action:
            self.duplicate_selected_character()
        elif action == delete_action:
            self.delete_selected_character()
    
    def set_page_emoji(self, item, emoji):
        """페이지 이모지를 변경합니다."""
        name = item.data(Qt.UserRole)
        
        # 해당 페이지 찾아서 이모지 업데이트
        for i, char in enumerate(self.state.characters):
            if char.get("name") == name:
                char["emoji"] = emoji
                
                # 리스트 위젯의 아이템 업데이트
                widget = self.char_list.itemWidget(item)
                if isinstance(widget, PageItemWidget):
                    widget.set_emoji(emoji)
                
                # 상태 저장
                self.state.books[self.current_book]["pages"] = self.state.characters
                self.save_to_file()
                break

    def show_book_context_menu(self, position):
        item = self.book_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        # 메뉴 여백 최적화
        menu.setStyleSheet("""
            QMenu {
                padding: 2px;
            }
            QMenu::item {
                padding: 4px 16px 4px 4px;
                margin: 0px;
            }
            QMenu::item:selected {
                background-color: #505050;
                color: white;
            }
            QMenu::item:hover {
                background-color: #505050;
                color: white;
            }
        """)
        
        name = item.data(Qt.UserRole)
        is_favorite = False
        
        # 현재 즐겨찾기 상태 확인
        if name in self.state.books:
            is_favorite = self.state.books[name].get("favorite", False)
        
        # 즐겨찾기 액션 추가
        if is_favorite:
            favorite_action = menu.addAction("❌ 즐겨찾기 해제")
        else:
            favorite_action = menu.addAction("⭐ 즐겨찾기")
        
        # 구분선 추가
        menu.addSeparator()
        
        # 기본 메뉴 항목 추가
        rename_action = menu.addAction("📝 이름 변경")
        delete_action = menu.addAction("🗑️ 북 삭제")
        menu.addSeparator()
        
        # 이모지 변경 서브메뉴
        emoji_menu = QMenu("🔄 이모지 변경")
        emoji_menu.setStyleSheet("""
            QMenu {
                padding: 2px;
            }
            QMenu::item {
                padding: 4px 16px 4px 4px;
                margin: 0px;
            }
            QMenu::item:selected {
                background-color: #505050;
                color: white;
            }
            QMenu::item:hover {
                background-color: #505050;
                color: white;
            }
        """)
        menu.addMenu(emoji_menu)
        
        # 이모지 옵션 그룹화
        emoji_groups = {
            "책": ["📕", "📘", "📙", "📗", "📓", "📔", "📒", "📚", "📖", "📝"],
            "특수": ["🌟", "✨", "🔥", "🎯", "🚀", "🧩", "🎨", "💡", "❤️", "💀"],
            "동물": ["🐉", "🦄", "🐱", "👻", "🍀", "🪐", "😺"],
            "표정": ["😀", "😎", "🥳", "😈", "🤖", "👽", "👾", "🙈"],
            "사람": ["👧", "👩", "🧒", "👸", "💃", "🧝‍♀️", "🧚‍♀️", "🧞‍♀️", "👩‍🎤", "👩‍🔬"]
        }
        
        for group_name, emojis in emoji_groups.items():
            group_menu = QMenu(group_name)
            group_menu.setStyleSheet("""
                QMenu {
                    padding: 2px;
                }
                QMenu::item {
                    padding: 4px 16px 4px 4px;
                    margin: 0px;
                }
                QMenu::item:selected {
                    background-color: #505050;
                    color: white;
                }
                QMenu::item:hover {
                    background-color: #505050;
                    color: white;
                }
            """)
            emoji_menu.addMenu(group_menu)
            for emoji in emojis:
                action = group_menu.addAction(emoji)
                action.triggered.connect(lambda checked, e=emoji, i=item: self.set_book_emoji(i, e))
        
        # 메뉴 실행 및 액션 처리
        action = menu.exec_(self.book_list.mapToGlobal(position))
        if action == favorite_action:
            self.toggle_book_favorite(item)
        elif action == rename_action:
            self.rename_book_dialog(item)
        elif action == delete_action:
            self.delete_book(item)
    
    def set_book_emoji(self, item, emoji):
        """북 이모지를 변경합니다."""
        name = item.data(Qt.UserRole)
        
        # 해당 북의 이모지 업데이트
        if name in self.state.books:
            self.state.books[name]["emoji"] = emoji
            
            # 위젯의 이모지 업데이트
            widget = self.book_list.itemWidget(item)
            if isinstance(widget, BookItemWidget):
                widget.set_emoji(emoji)
            
            # 상태 저장
            self.save_to_file()

    def toggle_book_favorite(self, item):
        """북 즐겨찾기 토글"""
        name = item.data(Qt.UserRole)
        
        if name in self.state.books:
            is_favorite = not self.state.books[name].get("favorite", False)
            self.state.books[name]["favorite"] = is_favorite
            
            # 위젯 업데이트
            widget = self.book_list.itemWidget(item)
            if isinstance(widget, BookItemWidget):
                widget.set_favorite(is_favorite)
            
            # 정렬 적용
            if not self.book_sort_custom:
                current_mode = self.book_sort_selector.currentText()
                self.handle_book_sort()
            else:
                # 커스텀 정렬 모드에서는 현재 위젯만 업데이트
                self.refresh_book_list(selected_name=name)
            
            self.save_to_file()

    def rename_book_dialog(self, item):
        """북 이름 변경 대화상자"""
        old_name = item.data(Qt.UserRole)
        new_name, ok = QInputDialog.getText(self, "북 이름 변경", "새 이름:", text=old_name)
        
        if ok and new_name.strip():
            new_name = new_name.strip()
            
            # 이름이 변경되지 않은 경우
            if old_name == new_name:
                return
                
            # 이미 존재하는 이름인 경우
            if new_name in self.state.books:
                QMessageBox.warning(self, "이름 변경 실패", "이미 존재하는 북 이름입니다.")
                return
                
            # 북 데이터 이동
            self.state.books[new_name] = self.state.books.pop(old_name)
            if self.current_book == old_name:
                self.current_book = new_name
            
            # 위젯 업데이트
            widget = self.book_list.itemWidget(item)
            if isinstance(widget, BookItemWidget):
                widget.set_name(new_name)
            
            item.setData(Qt.UserRole, new_name)
            self.save_to_file()

    def delete_book(self, item):
        name = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, 
            "북 삭제 확인",
            f"'{name}' 북을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 현재 선택된 북이 삭제되는 경우 처리
            if self.current_book == name:
                self.current_book = None
                self.state.characters = []
                self.char_list.clear()
                self.name_input.clear()
                self.tag_input.clear()
                self.desc_input.clear()
                self.prompt_input.clear()
                self.image_scene.clear()
            # 북 삭제
            del self.state.books[name]
            row = self.book_list.row(item)
            self.book_list.takeItem(row)
            
            # UI 상태 업데이트
            self.update_all_buttons_state()
            self.save_to_file()
            
            # 다른 북이 있다면 첫 번째 북 선택
            if self.book_list.count() > 0:
                self.book_list.setCurrentRow(0)
                self.on_book_selected(0)

    def update_image_buttons_state(self):
        enabled = self.current_book is not None
        self.image_load_btn.setEnabled(enabled)
        self.image_remove_btn.setEnabled(enabled)

    def apply_sorting(self):
        from promptbook_features import sort_characters
        self.state.characters = sort_characters(self.state.characters, self.sort_selector.currentText())
        self.refresh_character_list()

    def handle_book_sort(self):
        mode = self.book_sort_selector.currentText()
        print(f"[DEBUG] 북 정렬 모드: {mode}")

        if mode == "커스텀 정렬":
            self.book_sort_custom = True
            self.book_list.setDragDropMode(QAbstractItemView.InternalMove)
            self.book_list.setDefaultDropAction(Qt.MoveAction)
        else:
            self.book_sort_custom = False
            self.book_list.setDragDropMode(QAbstractItemView.NoDragDrop)
            
            # 북 목록 정렬
            items = []
            for i in range(self.book_list.count()):
                item = self.book_list.item(i)
                widget = self.book_list.itemWidget(item)
                if isinstance(widget, BookItemWidget):
                    name = widget.book_name
                    emoji = widget.book_label.text()
                    items.append((name, emoji, item.data(Qt.UserRole)))
            
            # 정렬 (즐겨찾기 우선, 그 다음 이름순)
            def sort_key(item):
                name = item[0]
                is_favorite = self.state.books[name].get("favorite", False)
                return (not is_favorite, name.lower())  # 즐겨찾기가 먼저 오도록
            
            items.sort(key=sort_key, reverse=(mode == "내림차순 정렬"))
            
            # 리스트 업데이트
            self.book_list.clear()
            for name, emoji, user_data in items:
                item = QListWidgetItem()
                
                # 커스텀 위젯 생성
                is_favorite = self.state.books[name].get("favorite", False)
                widget = BookItemWidget(name, is_favorite, emoji)
                item.setData(Qt.UserRole, user_data)
                
                self.book_list.addItem(item)
                self.book_list.setItemWidget(item, widget)
                item.setSizeHint(widget.sizeHint())
        
        # UI 설정 저장
        self.save_ui_settings()

    def remove_preview_image(self):
        if 0 <= self.current_index < len(self.state.characters):
            self.state.characters[self.current_index]["image_path"] = ""
            self.state.books[self.current_book]["pages"] = self.state.characters
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            self.save_to_file()



    def duplicate_selected_character(self):
        if not self.current_book or self.current_index < 0:
            return
            
        # 현재 선택된 페이지 데이터 복사
        original_data = self.state.characters[self.current_index].copy()
        
        # 이름 중복 방지
        base_name = original_data["name"]
        existing_names = {char["name"] for char in self.state.characters}
        
        # 새 이름 생성 (예: "캐릭터" -> "캐릭터 (1)")
        if base_name in existing_names:
            for i in range(1, 1000):
                candidate = f"{base_name} ({i})"
                if candidate not in existing_names:
                    base_name = candidate
                    break
                    
        # 새 데이터 생성
        new_data = original_data.copy()
        new_data["name"] = base_name
        
        # 이미지가 있는 경우 복사
        if "image_path" in original_data and os.path.exists(original_data["image_path"]):
            original_path = original_data["image_path"]
            file_name, ext = os.path.splitext(os.path.basename(original_path))
            new_file_name = f"{file_name}_001{ext}"  # 복제본은 _001 접미사 추가
            new_path = os.path.join(os.path.dirname(original_path), new_file_name)
            
            try:
                shutil.copy2(original_path, new_path)
                new_data["image_path"] = new_path
            except Exception as e:
                print(f"이미지 복사 실패: {e}")
                new_data["image_path"] = ""
        
        # 새 페이지 추가
        self.state.characters.append(new_data)
        
        # 정렬 모드가 커스텀이 아닌 경우 정렬 적용
        if not self.sort_mode_custom:
            from promptbook_features import sort_characters
            self.state.characters = sort_characters(self.state.characters, self.sort_selector.currentText())
        
        # 상태 업데이트 및 저장
        self.state.books[self.current_book]["pages"] = self.state.characters
        self.refresh_character_list(selected_name=base_name)
        self.save_to_file()

    def delete_selected_character(self):
        if not self.current_book or self.current_index < 0:
            return
            
        # 잠금 상태 확인
        if self.state.characters[self.current_index].get('locked', False):
            QMessageBox.warning(
                self,
                "삭제 불가",
                "잠금된 페이지는 삭제할 수 없습니다.\n잠금을 해제한 후 다시 시도해주세요."
            )
            return
            
        # 삭제 확인 대화상자
        reply = QMessageBox.question(
            self, 
            "페이지 삭제 확인",
            "현재 페이지를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 이미지 파일이 있다면 삭제
            if "image_path" in self.state.characters[self.current_index]:
                image_path = self.state.characters[self.current_index]["image_path"]
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"이미지 파일 삭제 실패: {e}")
            
            # 페이지 삭제
            del self.state.characters[self.current_index]
            self.state.books[self.current_book]["pages"] = self.state.characters
            
            # UI 업데이트
            self.refresh_character_list()
            
            # 입력 필드 초기화
            if not self.state.characters:
                self.current_index = -1
                self.name_input.clear()
                self.tag_input.clear()
                self.desc_input.clear()
                self.prompt_input.clear()
                self.image_scene.clear()
                self.image_view.drop_hint.setVisible(True)
            
            self.save_to_file()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PromptBook()

    from PySide6.QtGui import QShortcut, QKeySequence
    QShortcut(QKeySequence("Ctrl+S"), window).activated.connect(lambda: (window.save_current_character(), QToolTip.showText(window.save_button.mapToGlobal(window.save_button.rect().center()), "페이지가 저장되었습니다.")))

    window.show()
    sys.exit(app.exec())
