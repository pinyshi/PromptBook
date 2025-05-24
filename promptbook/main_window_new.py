from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox,
    QMenu, QInputDialog, QLabel, QLineEdit, QTextEdit, QPushButton, QFormLayout,
    QGraphicsScene, QGraphicsPixmapItem, QFileDialog, QApplication, QToolTip,
    QListWidget, QListWidgetItem, QCompleter, QComboBox, QAbstractItemView,
    QMenuBar, QFrame, QListView, QStyledItemDelegate, QGraphicsView
)
from PySide6.QtGui import QPixmap, QAction, QImageReader, QPainter, QKeySequence, QShortcut, QIcon, QActionGroup, QTextCursor
from PySide6.QtCore import Qt, QSize, QStringListModel, QPoint, Signal, QRect
import os
import json
import csv
import shutil
import sys
from datetime import datetime
from zipfile import ZipFile
import tempfile

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
        
        # 드래그 앤 드롭 안내 라벨
        self.drop_hint = QLabel(self.viewport())
        self.drop_hint.setText("이미지 파일을 이곳에\n드래그 앤 드롭 하세요")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet("""
            QLabel {
                color: #666;
                background-color: transparent;
                font-size: 14px;
                padding: 20px;
                border: 2px dashed #666;
                border-radius: 10px;
            }
        """)
        self.update_drop_hint_position()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 부모 위젯 체인을 따라 MainWindow 인스턴스를 찾습니다
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, MainWindow):
                parent.update_image_fit()
                break
            parent = parent.parent()
        # 라벨 위치 업데이트
        self.update_drop_hint_position()
        
    def update_drop_hint_position(self):
        if not hasattr(self, 'drop_hint'):
            return
            
        # 뷰포트 크기 가져오기
        viewport_rect = self.viewport().rect()
        
        # 라벨 크기 계산
        hint_width = min(300, viewport_rect.width() - 40)  # 여백 20px
        hint_height = 80
        
        # 중앙 위치 계산
        x = (viewport_rect.width() - hint_width) // 2
        y = (viewport_rect.height() - hint_height) // 2
        
        # 라벨 위치와 크기 설정
        self.drop_hint.setGeometry(x, y, hint_width, hint_height)

class BookNameDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.DisplayRole)
        editor.setText(self.extract_book_name(text))

    def setModelData(self, editor, model, index):
        name = editor.text().strip()
        emoji = "📕"  # 기본 이모지
        if hasattr(self.parent(), "state") and name in self.parent().state.books:
            emoji = self.parent().state.books[name].get("emoji", "📕")
        model.setData(index, f"{emoji} {name}", Qt.DisplayRole)
        model.setData(index, name, Qt.UserRole)
        
    def extract_book_name(self, text):
        """이모지를 제외한 북 이름을 추출합니다."""
        if " " in text:
            return text.split(" ", 1)[1]
        return text

class CharacterList(QListWidget):
    character_moved = Signal(int, int)  # from_index, to_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setAcceptDrops(True)
        
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
            
            # 드롭 위치 계산
            drop_pos = event.pos()
            drop_item = self.itemAt(drop_pos)
            
            if not drop_item:
                # 리스트 끝에 드롭한 경우
                drop_index = self.count()
            else:
                drop_index = self.row(drop_item)
                
            # 드래그 중인 아이템 가져오기
            drag_item = self.currentItem()
            if not drag_item:
                return
                
            from_index = self.row(drag_item)
            
            # 이동 시그널 발생
            self.character_moved.emit(from_index, drop_index)
        else:
            event.ignore()
            
    def keyPressEvent(self, event):
        """키 입력 이벤트를 처리합니다."""
        if event.key() == Qt.Key_Delete and self.currentItem():
            print("[DEBUG] CharacterList: Delete 키 이벤트 처리")
            # 현재 선택된 아이템의 이름으로 인덱스 찾기
            name = self.currentItem().text()
            parent = self.parent()
            while parent is not None:
                if isinstance(parent, MainWindow):
                    for i, char in enumerate(parent.state.characters):
                        if char.get("name") == name:
                            parent.current_index = i
                            print(f"[DEBUG] 삭제할 캐릭터 인덱스: {i}, 이름: {name}")
                            parent.delete_selected_character()
                            break
                    break
                parent = parent.parent()
        else:
            super().keyPressEvent(event)

class MainWindow(QMainWindow):
    # 클래스 레벨 상수 정의
    SAVE_FILE = "character_data.json"
    SETTINGS_FILE = "ui_settings.json"
    DELETED_PAGES_FILE = "deleted_pages.json"  # 삭제된 페이지 저장 파일
    
    emoji_options = [
        "📕", "📘", "📙", "📗", "📓", "📔", "📒", "📚", "📖", "📝",
        "🌟", "✨", "🔥", "🎯", "🚀", "🧩", "🎨", "💡", "❤️", "💀",
        "👑", "🎵", "🐉", "🦄", "🐱", "👻", "🍀", "🪐", "😀", "😎",
        "🥳", "😈", "🤖", "👽", "👾", "🙈", "😺", "🫠", "👧", "👩",
        "🧒", "👸", "💃", "🧝‍♀️", "🧚‍♀️", "🧞‍♀️", "👩‍🎤", "👩‍🔬"
    ]

    def __init__(self):
        """PromptBook 애플리케이션을 초기화합니다."""
        super().__init__()
        
        # 상태 초기화
        self.state = type('State', (), {'books': {}, 'characters': []})()
        
        # 창 설정
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(800, 600)
        self.resize(1000, 600)  # 기본 창 크기: 1000x600
        self.setAcceptDrops(True)
        
        # 크기 조절 관련 변수
        self.resizing = False
        self.resize_start = None
        self.resize_type = None
        
        # 삭제된 페이지 저장소 초기화
        self.deleted_pages = {}  # book_name -> [deleted_pages]
        
        # 상태 변수 초기화
        self.current_book = None
        self.current_index = -1
        self.block_save = False
        self.edited = False
        self._initial_loading = True
        self.sort_mode_custom = False  # 기본값: 오름차순 정렬
        self.book_sort_custom = False
        
        # UI 관련 변수 초기화
        self.book_list = None
        self.character_list = None
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
        
        # 테마 설정
        self.setup_theme()
        
        # UI 구성
        self.setup_ui()
        
        # 저장된 설정이 있다면 적용
        if os.path.exists(self.SETTINGS_FILE):
            self.load_ui_settings()
            
        # 데이터 로드
        self.load_from_file()

    def setup_theme(self):
        """애플리케이션의 테마를 설정합니다."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit, QTextEdit {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #4a4a4a;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #666666;
            }
            QPushButton {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #666666;
            }
            QPushButton:pressed {
                background-color: #2b2b2b;
            }
            QPushButton:disabled {
                background-color: #2b2b2b;
                color: #666666;
                border: 1px solid #3b3b3b;
            }
            QListWidget {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #4a4a4a;
            }
            QListWidget::item {
                padding: 4px;
                border-radius: 2px;
            }
            QListWidget::item:selected {
                background-color: #4a4a4a;
            }
            QListWidget::item:hover {
                background-color: #444444;
            }
            QComboBox {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
            }
            QComboBox:on {
                background-color: #4a4a4a;
            }
            QComboBox QAbstractItemView {
                background-color: #3b3b3b;
                color: #ffffff;
                selection-background-color: #4a4a4a;
                border: 1px solid #555555;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #2b2b2b;
                height: 12px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #555555;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QSplitter::handle {
                background-color: #555555;
                width: 1px;
            }
            QSplitter::handle:hover {
                background-color: #666666;
            }
            QMenu {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 4px 20px;
            }
            QMenu::item:selected {
                background-color: #4a4a4a;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555555;
                margin: 4px 0px;
            }
            QToolTip {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
            }
        """)

    def setup_central_widget(self):
        """중앙 위젯을 설정합니다."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 타이틀바
        title_bar = QWidget()
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #1b1b1b;
                color: #ffffff;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 0;
                min-width: 32px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton#close_button:hover {
                background-color: #e81123;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 0, 0, 0)
        title_layout.setSpacing(0)
        
        # 타이틀 라벨
        title_layout.addStretch()
        title_label = QLabel("프롬프트 북")
        title_label.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            padding: 0 32px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 윈도우 컨트롤 버튼
        minimize_btn = QPushButton("─")
        minimize_btn.setFixedSize(32, 32)
        minimize_btn.clicked.connect(self.showMinimized)
        
        maximize_btn = QPushButton("□")
        maximize_btn.setFixedSize(32, 32)
        maximize_btn.clicked.connect(self.toggle_maximize)
        
        close_btn = QPushButton("×")
        close_btn.setObjectName("close_button")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.close)
        
        title_layout.addWidget(minimize_btn)
        title_layout.addWidget(maximize_btn)
        title_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)
        
        # 메인 스플리터 생성 및 인스턴스 변수로 저장
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # 왼쪽 패널
        left_panel = QWidget()
        self.left_layout = QVBoxLayout(left_panel)
        self.main_splitter.addWidget(left_panel)
        
        # 중앙 패널
        center_panel = QWidget()
        self.middle_layout = QVBoxLayout(center_panel)
        self.main_splitter.addWidget(center_panel)
        
        # 오른쪽 패널
        right_panel = QWidget()
        self.right_layout = QVBoxLayout(right_panel)
        self.main_splitter.addWidget(right_panel)
        
        # 스플리터 비율 설정 [196, 346, 430]
        self.main_splitter.setSizes([196, 346, 430])
        
        # 마우스 이벤트 처리를 위한 설정
        title_bar.mousePressEvent = self.titlebar_mouse_press
        title_bar.mouseMoveEvent = self.titlebar_mouse_move
        title_bar.mouseDoubleClickEvent = self.titlebar_double_click

    def change_sort_mode(self, mode):
        """페이지 정렬 모드를 변경합니다."""
        if hasattr(self, 'sort_selector'):
            self.sort_selector.setCurrentText(mode)
            self.handle_character_sort()

    def change_book_sort_mode(self, mode):
        """북 정렬 모드를 변경합니다."""
        if hasattr(self, 'book_sort_selector'):
            self.book_sort_selector.setCurrentText(mode)
            self.handle_book_sort()

    def titlebar_mouse_press(self, event):
        """타이틀바 마우스 클릭 이벤트"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def titlebar_mouse_move(self, event):
        """타이틀바 마우스 드래그 이벤트"""
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def titlebar_double_click(self, event):
        """타이틀바 더블클릭 이벤트"""
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()

    def toggle_maximize(self):
        """윈도우 최대화/복원 토글"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 마우스 위치 확인
            pos = event.position().toPoint()
            rect = self.rect()
            edge = 5  # 크기 조절 가능한 가장자리 영역

            # 가장자리 영역 확인
            at_left = pos.x() <= edge
            at_right = pos.x() >= rect.width() - edge
            at_top = pos.y() <= edge
            at_bottom = pos.y() >= rect.height() - edge

            # 크기 조절 시작
            if at_left or at_right or at_top or at_bottom:
                self.resizing = True
                self.resize_start = event.globalPosition().toPoint()
                self.resize_type = ''
                if at_left: self.resize_type += 'left'
                elif at_right: self.resize_type += 'right'
                if at_top: self.resize_type += 'top'
                elif at_bottom: self.resize_type += 'bottom'
                self.window_rect = self.geometry()
            else:
                # 창 이동 시작
                self.drag_start = event.globalPosition().toPoint()
                self.window_pos = self.pos()

    def mouseMoveEvent(self, event):
        if not hasattr(self, 'resize_start'):
            # 마우스 커서 모양 설정
            pos = event.position().toPoint()
            rect = self.rect()
            edge = 5

            at_left = pos.x() <= edge
            at_right = pos.x() >= rect.width() - edge
            at_top = pos.y() <= edge
            at_bottom = pos.y() >= rect.height() - edge

            if (at_left and at_top) or (at_right and at_bottom):
                self.setCursor(Qt.SizeFDiagCursor)
            elif (at_right and at_top) or (at_left and at_bottom):
                self.setCursor(Qt.SizeBDiagCursor)
            elif at_left or at_right:
                self.setCursor(Qt.SizeHorCursor)
            elif at_top or at_bottom:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            return

        if event.buttons() == Qt.LeftButton:
            if self.resizing and hasattr(self, 'resize_start'):
                # 크기 조절 처리
                delta = event.globalPosition().toPoint() - self.resize_start
                new_geo = self.window_rect
                min_width = self.minimumWidth()
                min_height = self.minimumHeight()

                if 'left' in self.resize_type:
                    new_width = new_geo.width() - delta.x()
                    if new_width >= min_width:
                        new_geo.setLeft(new_geo.left() + delta.x())
                elif 'right' in self.resize_type:
                    new_width = new_geo.width() + delta.x()
                    if new_width >= min_width:
                        new_geo.setRight(new_geo.right() + delta.x())

                if 'top' in self.resize_type:
                    new_height = new_geo.height() - delta.y()
                    if new_height >= min_height:
                        new_geo.setTop(new_geo.top() + delta.y())
                elif 'bottom' in self.resize_type:
                    new_height = new_geo.height() + delta.y()
                    if new_height >= min_height:
                        new_geo.setBottom(new_geo.bottom() + delta.y())

                self.setGeometry(new_geo)
            elif hasattr(self, 'drag_start'):
                # 창 이동 처리
                delta = event.globalPosition().toPoint() - self.drag_start
                self.move(self.window_pos + delta)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        self.resize_start = None
        self.resize_type = None
        if hasattr(self, 'drag_start'):
            delattr(self, 'drag_start')
        if hasattr(self, 'window_pos'):
            delattr(self, 'window_pos')
        if hasattr(self, 'window_rect'):
            delattr(self, 'window_rect')
        self.setCursor(Qt.ArrowCursor)

    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)  # 기본 타이틀바 제거
        self.setAttribute(Qt.WA_TranslucentBackground)  # 투명 배경 허용
        self.setup_central_widget()
        self.setup_menubar()  # 메뉴바 설정 추가
        self.setup_book_list()
        self.setup_character_list()
        self.setup_input_fields()
        self.setup_image_view()
        self.setup_buttons()
        self.update_all_buttons_state()
        
    def setup_menubar(self):
        """메뉴바를 설정합니다."""
        menubar = QMenuBar()
        self.setMenuBar(menubar)
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        # 리스트 저장/불러오기 메뉴
        list_menu = menubar.addMenu("리스트")
        save_list_action = list_menu.addAction("리스트 저장")
        save_list_action.triggered.connect(self.export_character_list)
        load_list_action = list_menu.addAction("리스트 불러오기")
        load_list_action.triggered.connect(self.import_character_list)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")

    def export_character_list(self):
        """현재 북의 페이지 리스트를 ZIP 파일로 저장합니다."""
        if not self.current_book:
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "리스트 저장", "character_list.zip", "Zip Files (*.zip)")
        if path:
            try:
                with ZipFile(path, 'w') as zipf:
                    for book_name, book_data in self.state.books.items():
                        characters = book_data.get("pages", [])
                        export_data = []
                        for i, char in enumerate(characters):
                            char_copy = dict(char)
                            img_path = char.get("image_path")
                            if img_path and os.path.exists(img_path):
                                filename = f"images/{book_name}_{i}_{os.path.basename(img_path)}"
                                zipf.write(img_path, filename)
                                char_copy["image_path"] = filename
                            export_data.append(char_copy)
                            
                        # 캐릭터 데이터를 JSON 파일로 저장
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                            json.dump(export_data, f, ensure_ascii=False, indent=2)
                            temp_path = f.name
                            
                        zipf.write(temp_path, f"{book_name}.json")
                        os.unlink(temp_path)  # 임시 파일 삭제
                        
                QMessageBox.information(self, "완료", "리스트가 저장되었습니다.")
            except Exception as e:
                QMessageBox.warning(self, "오류", f"리스트 저장 중 오류가 발생했습니다:\n{str(e)}")

    def import_character_list(self):
        """ZIP 파일에서 페이지 리스트를 불러옵니다."""
        if not self.current_book:
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "리스트 불러오기", "", "Zip Files (*.zip)")
        if path:
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    with ZipFile(path, 'r') as zipf:
                        zipf.extractall(temp_dir)
                        
                        # JSON 파일 찾기
                        for file_name in os.listdir(temp_dir):
                            if file_name.endswith('.json'):
                                # JSON 파일에서 데이터 로드
                                with open(os.path.join(temp_dir, file_name), 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    for char in data:
                                        rel_path = char.get("image_path")
                                        if rel_path:
                                            full_path = os.path.join(temp_dir, rel_path)
                                            if os.path.exists(full_path):
                                                os.makedirs("images", exist_ok=True)
                                                dest_path = os.path.join("images", os.path.basename(full_path))
                                                shutil.copy(full_path, dest_path)
                                                char["image_path"] = dest_path
                                            else:
                                                char["image_path"] = ""
                                                
                                    # 현재 북의 페이지 리스트 업데이트
                                    self.state.characters = data
                                    self.state.books[self.current_book]["pages"] = data
                                    self.refresh_character_list()
                                    self.save_to_file()
                                    break
                                    
                QMessageBox.information(self, "완료", "리스트를 불러왔습니다.")
            except Exception as e:
                QMessageBox.warning(self, "오류", f"리스트 불러오기 중 오류가 발생했습니다:\n{str(e)}")

    def setup_book_list(self):
        try:
            # 북 리스트 위젯 설정
            self.book_list = QListWidget()
            self.book_list.setObjectName("book_list")
            self.book_list.setDragDropMode(QAbstractItemView.InternalMove)
            self.book_list.setDefaultDropAction(Qt.MoveAction)
            self.book_list.setSelectionMode(QAbstractItemView.SingleSelection)
            self.book_list.itemClicked.connect(self.book_selected)
            self.book_list.model().rowsMoved.connect(self.on_book_moved)
            
            # 북 정렬 선택기 설정
            self.book_sort_selector = QComboBox()
            self.book_sort_selector.addItems(["커스텀 정렬", "오름차순 정렬", "내림차순 정렬"])
            self.book_sort_selector.currentTextChanged.connect(self.handle_book_sort)
            
            # 북 리스트에 아이템 추가
            for book_name, book_data in self.state.books.items():
                emoji = book_data.get("emoji", "📕")
                item = QListWidgetItem(f"{emoji} {book_name}")
                item.setData(Qt.UserRole, book_name)
                self.book_list.addItem(item)
                
            # 아이템 편집을 위한 delegate 설정
            self.book_list.setItemDelegate(BookNameDelegate())
            
            # 정렬 모드 적용
            self.handle_book_sort()
            
            # 저장된 UI 설정 불러오기
            self.load_ui_settings()
            
        except Exception as e:
            print(f"북 리스트 설정 중 오류 발생: {e}")
            # 오류 발생 시 기본 설정 적용
            self.book_list = QListWidget()
            self.book_sort_selector = QComboBox()
            self.book_sort_selector.addItems(["커스텀 정렬", "오름차순 정렬", "내림차순 정렬"])

    def setup_character_list(self):
        """캐릭터 리스트를 설정합니다."""
        try:
            # 캐릭터 리스트 위젯 설정
            self.character_list = CharacterList()
            self.character_list.setObjectName("character_list")
            self.character_list.setDragDropMode(QAbstractItemView.InternalMove)
            self.character_list.setDefaultDropAction(Qt.MoveAction)
            self.character_list.setSelectionMode(QAbstractItemView.SingleSelection)
            self.character_list.itemClicked.connect(self.character_selected)
            self.character_list.character_moved.connect(self.on_character_moved)
            
            # 캐릭터 정렬 선택기 설정
            self.sort_selector = QComboBox()
            self.sort_selector.addItems(["커스텀 정렬", "오름차순 정렬", "내림차순 정렬"])
            self.sort_selector.currentTextChanged.connect(self.handle_character_sort)
            
            # 캐릭터 리스트에 아이템 추가
            if self.current_book and self.current_book in self.state.books:
                self.state.characters = self.state.books[self.current_book].get("pages", [])
                for character in self.state.characters:
                    item = QListWidgetItem(character.get("name", ""))
                    self.character_list.addItem(item)
                    
                # 정렬 모드 복원
                sort_mode = self.state.books[self.current_book].get("sort_mode", "커스텀 정렬")
                self.sort_selector.setCurrentText(sort_mode)
                self.sort_mode_custom = (sort_mode == "커스텀 정렬")
                
                if not self.sort_mode_custom:
                    self.character_list.setDragDropMode(QAbstractItemView.NoDragDrop)
                    
        except Exception as e:
            print(f"캐릭터 리스트 설정 실패: {e}")
            # 기본 위젯 설정
            self.character_list = CharacterList()
            self.sort_selector = QComboBox()
            self.sort_selector.addItems(["커스텀 정렬", "오름차순 정렬", "내림차순 정렬"])
            self.state.characters = []

    def setup_input_fields(self):
        """입력 필드를 설정합니다."""
        try:
            # 이름 입력 필드
            self.name_input = QLineEdit()
            self.name_input.setObjectName("name_input")
            self.name_input.setPlaceholderText("캐릭터 이름")
            self.name_input.textChanged.connect(self.on_name_changed)
            
            # 태그 입력 필드
            self.tag_input = QLineEdit()
            self.tag_input.setObjectName("tag_input")
            self.tag_input.setPlaceholderText("태그 (쉼표로 구분)")
            self.tag_input.textChanged.connect(self.on_tag_changed)
            
            # 설명 입력 필드
            self.desc_input = QTextEdit()
            self.desc_input.setObjectName("desc_input")
            self.desc_input.setPlaceholderText("캐릭터 설명")
            self.desc_input.textChanged.connect(self.on_desc_changed)
            
            # 프롬프트 입력 필드
            self.prompt_input = QTextEdit()
            self.prompt_input.setObjectName("prompt_input")
            self.prompt_input.setPlaceholderText("프롬프트")
            self.prompt_input.textChanged.connect(self.on_prompt_changed)
            
            # 이미지 뷰어 설정
            self.image_scene = QGraphicsScene()
            self.image_view = ImageView()
            self.image_view.setScene(self.image_scene)
            self.image_view.setObjectName("image_view")
            
            # 입력 필드 초기화
            self.clear_input_fields()
            
        except Exception as e:
            print(f"입력 필드 설정 실패: {e}")
            # 기본 위젯 설정
            self.name_input = QLineEdit()
            self.tag_input = QLineEdit()
            self.desc_input = QTextEdit()
            self.prompt_input = QTextEdit()
            self.image_scene = QGraphicsScene()
            self.image_view = ImageView()
            self.image_view.setScene(self.image_scene)

    def setup_image_view(self):
        """이미지 뷰어를 설정합니다."""
        try:
            # 이미지 뷰어는 setup_input_fields에서 이미 설정됨
            # 추가 설정이 필요한 경우 여기에 구현
            pass
        except Exception as e:
            print(f"이미지 뷰어 설정 실패: {e}")

    def setup_buttons(self):
        """버튼들을 설정합니다."""
        try:
            # 버튼 설정 로직을 여기에 구현
            # 필요한 경우 추가 구현
            pass
        except Exception as e:
            print(f"버튼 설정 실패: {e}")

    def update_all_buttons_state(self):
        """모든 버튼의 상태를 업데이트합니다."""
        try:
            # 버튼 상태 업데이트 로직
            pass
        except Exception as e:
            print(f"버튼 상태 업데이트 실패: {e}")

    def book_selected(self, item):
        """북이 선택되었을 때 호출됩니다."""
        try:
            book_name = item.data(Qt.UserRole)
            if book_name and book_name in self.state.books:
                self.current_book = book_name
                self.state.characters = self.state.books[book_name].get("pages", [])
                self.refresh_character_list()
                self.current_index = -1
                self.clear_input_fields()
        except Exception as e:
            print(f"북 선택 처리 실패: {e}")

    def character_selected(self, item):
        """캐릭터가 선택되었을 때 호출됩니다."""
        try:
            character_name = item.text()
            for i, char in enumerate(self.state.characters):
                if char.get("name") == character_name:
                    self.current_index = i
                    self.load_character_data(char)
                    break
        except Exception as e:
            print(f"캐릭터 선택 처리 실패: {e}")

    def load_character_data(self, character):
        """캐릭터 데이터를 UI에 로드합니다."""
        try:
            self.block_save = True
            self.name_input.setText(character.get("name", ""))
            self.tag_input.setText(character.get("tags", ""))
            self.desc_input.setText(character.get("description", ""))
            self.prompt_input.setText(character.get("prompt", ""))
            
            # 이미지 로드
            image_path = character.get("image_path", "")
            if image_path and os.path.exists(image_path):
                self.load_image(image_path)
            else:
                self.image_scene.clear()
                self.image_view.drop_hint.setVisible(True)
            
            self.block_save = False
        except Exception as e:
            print(f"캐릭터 데이터 로드 실패: {e}")

    def load_image(self, image_path):
        """이미지를 로드하고 표시합니다."""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.image_scene.clear()
                self.image_scene.addPixmap(pixmap)
                self.image_view.drop_hint.setVisible(False)
                self.update_image_fit()
        except Exception as e:
            print(f"이미지 로드 실패: {e}")

    def update_image_fit(self):
        """이미지를 뷰에 맞게 조정합니다."""
        try:
            if self.image_scene.items():
                self.image_view.fitInView(self.image_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        except Exception as e:
            print(f"이미지 크기 조정 실패: {e}")

    def on_name_changed(self):
        """이름 입력이 변경되었을 때 호출됩니다."""
        if not self.block_save and self.current_index >= 0:
            self.save_current_character()

    def on_tag_changed(self):
        """태그 입력이 변경되었을 때 호출됩니다."""
        if not self.block_save and self.current_index >= 0:
            self.save_current_character()

    def on_desc_changed(self):
        """설명 입력이 변경되었을 때 호출됩니다."""
        if not self.block_save and self.current_index >= 0:
            self.save_current_character()

    def on_prompt_changed(self):
        """프롬프트 입력이 변경되었을 때 호출됩니다."""
        if not self.block_save and self.current_index >= 0:
            self.save_current_character()

    def save_current_character(self):
        """현재 캐릭터 데이터를 저장합니다."""
        try:
            if self.current_index >= 0 and not self.block_save:
                character = self.state.characters[self.current_index]
                character["name"] = self.name_input.text()
                character["tags"] = self.tag_input.text()
                character["description"] = self.desc_input.toPlainText()
                character["prompt"] = self.prompt_input.toPlainText()
                
                # 캐릭터 리스트에서 이름 업데이트
                if hasattr(self, 'character_list'):
                    item = self.character_list.item(self.current_index)
                    if item:
                        item.setText(character["name"])
                
                self.save_to_file()
        except Exception as e:
            print(f"캐릭터 저장 실패: {e}")

    def on_book_moved(self, from_index, to_index):
        """북이 이동되었을 때 호출됩니다."""
        try:
            # 북 이동 처리 로직
            pass
        except Exception as e:
            print(f"북 이동 처리 실패: {e}")

    def on_character_moved(self, from_index, to_index):
        """캐릭터가 이동되었을 때 호출됩니다."""
        try:
            if from_index != to_index and 0 <= from_index < len(self.state.characters):
                # 캐릭터 순서 변경
                character = self.state.characters.pop(from_index)
                self.state.characters.insert(to_index, character)
                
                # 현재 인덱스 업데이트
                if self.current_index == from_index:
                    self.current_index = to_index
                elif from_index < self.current_index <= to_index:
                    self.current_index -= 1
                elif to_index <= self.current_index < from_index:
                    self.current_index += 1
                
                self.save_to_file()
        except Exception as e:
            print(f"캐릭터 이동 처리 실패: {e}")

    def handle_character_sort(self):
        """캐릭터 정렬을 처리합니다."""
        try:
            if not hasattr(self, 'sort_selector'):
                return
                
            mode = self.sort_selector.currentText()
            self.sort_mode_custom = (mode == "커스텀 정렬")
            
            if self.sort_mode_custom:
                self.character_list.setDragDropMode(QAbstractItemView.InternalMove)
            else:
                self.character_list.setDragDropMode(QAbstractItemView.NoDragDrop)
                # 정렬 적용
                self.state.characters = self.sort_characters(self.state.characters, mode)
                self.refresh_character_list()
            
            # 정렬 모드 저장
            if self.current_book:
                self.state.books[self.current_book]["sort_mode"] = mode
                self.save_to_file()
        except Exception as e:
            print(f"캐릭터 정렬 처리 실패: {e}")

    def sort_characters(self, characters, mode):
        """캐릭터 리스트를 정렬합니다."""
        if mode == "오름차순 정렬":
            return sorted(characters, key=lambda x: (not x.get("favorite", False), x.get("name", "").lower()))
        elif mode == "내림차순 정렬":
            return sorted(characters, key=lambda x: (not x.get("favorite", False), x.get("name", "").lower()), reverse=True)
        else:  # 커스텀 정렬 또는 기본값
            return characters

    def handle_book_sort(self):
        try:
            if not hasattr(self, 'book_sort_selector'):
                return
                
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
                    name = self.extract_book_name(item.text())
                    emoji = item.text().split()[0] if item.text().split() else "📕"
                    items.append((name, emoji, item.data(Qt.UserRole)))
                
                # 정렬
                items.sort(key=lambda x: x[0].lower(), reverse=(mode == "내림차순 정렬"))
                
                # 리스트 업데이트
                self.book_list.clear()
                for name, emoji, user_data in items:
                    item = QListWidgetItem(f"{emoji} {name}")
                    item.setData(Qt.UserRole, user_data)
                    self.book_list.addItem(item)
            
            # UI 설정 저장
            self.save_ui_settings()
        except Exception as e:
            print(f"북 정렬 처리 실패: {e}")

    def extract_book_name(self, text):
        """북 이름에서 이모지를 제외한 실제 이름만 추출합니다."""
        parts = text.split()
        return ' '.join(parts[1:]) if len(parts) > 1 else text

    def refresh_character_list(self, selected_name=None):
        """캐릭터 리스트를 새로고침합니다."""
        try:
            if not hasattr(self, 'character_list'):
                return
                
            self.character_list.clear()
            
            for character in self.state.characters:
                item = QListWidgetItem(character.get("name", ""))
                self.character_list.addItem(item)
            
            # 선택된 캐릭터 복원
            if selected_name:
                for i in range(self.character_list.count()):
                    if self.character_list.item(i).text() == selected_name:
                        self.character_list.setCurrentRow(i)
                        break
        except Exception as e:
            print(f"캐릭터 리스트 새로고침 실패: {e}")

    def clear_input_fields(self):
        """입력 필드를 초기화합니다."""
        try:
            self.block_save = True
            if hasattr(self, 'name_input'):
                self.name_input.clear()
            if hasattr(self, 'tag_input'):
                self.tag_input.clear()
            if hasattr(self, 'desc_input'):
                self.desc_input.clear()
            if hasattr(self, 'prompt_input'):
                self.prompt_input.clear()
            if hasattr(self, 'image_scene'):
                self.image_scene.clear()
            if hasattr(self, 'image_view'):
                self.image_view.drop_hint.setVisible(True)
            self.block_save = False
        except Exception as e:
            print(f"입력 필드 초기화 실패: {e}")

    def load_from_file(self):
        """파일에서 데이터를 로드합니다."""
        try:
            if os.path.exists(self.SAVE_FILE):
                with open(self.SAVE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state.books = data.get("books", {})
                    
            # 삭제된 페이지 로드
            if os.path.exists(self.DELETED_PAGES_FILE):
                with open(self.DELETED_PAGES_FILE, 'r', encoding='utf-8') as f:
                    self.deleted_pages = json.load(f)
        except Exception as e:
            print(f"파일 로드 실패: {e}")

    def save_to_file(self):
        """파일에 데이터를 저장합니다."""
        try:
            data = {"books": self.state.books}
            with open(self.SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"파일 저장 실패: {e}")

    def load_ui_settings(self):
        """UI 설정을 로드합니다."""
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                    # 윈도우 크기와 위치 복원
                    if "window_geometry" in settings:
                        geo = settings["window_geometry"]
                        self.setGeometry(geo["x"], geo["y"], geo["width"], geo["height"])
                    
                    # 스플리터 크기 복원
                    if "splitter_sizes" in settings and hasattr(self, 'main_splitter'):
                        self.main_splitter.setSizes(settings["splitter_sizes"])
        except Exception as e:
            print(f"UI 설정 로드 실패: {e}")

    def save_ui_settings(self):
        """UI 설정을 저장합니다."""
        try:
            settings = {
                "window_geometry": {
                    "x": self.x(),
                    "y": self.y(),
                    "width": self.width(),
                    "height": self.height()
                }
            }
            
            # 스플리터 크기 저장
            if hasattr(self, 'main_splitter'):
                settings["splitter_sizes"] = self.main_splitter.sizes()
            
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"UI 설정 저장 실패: {e}")

    def delete_selected_character(self):
        """선택된 캐릭터를 삭제합니다."""
        if not self.current_book or self.current_index < 0:
            return
            
        # 삭제 확인 대화상자
        reply = QMessageBox.question(
            self, 
            "페이지 삭제 확인",
            "현재 페이지를 삭제하시겠습니다?\n삭제된 페이지는 나중에 복구할 수 있습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 삭제할 페이지 데이터 저장
            deleted_page = self.state.characters[self.current_index].copy()
            deleted_page["deleted_time"] = datetime.now().isoformat()
            
            # 삭제된 페이지 저장소에 추가
            if self.current_book not in self.deleted_pages:
                self.deleted_pages[self.current_book] = []
            self.deleted_pages[self.current_book].append(deleted_page)
            
            # 삭제된 페이지 저장
            self.save_deleted_pages()
            
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

    def save_deleted_pages(self):
        """삭제된 페이지 목록을 파일에 저장합니다."""
        try:
            with open(self.DELETED_PAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.deleted_pages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"삭제된 페이지 저장 실패: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()

    from PySide6.QtGui import QShortcut, QKeySequence
    QShortcut(QKeySequence("Ctrl+S"), window).activated.connect(lambda: (window.save_current_character(), QToolTip.showText(window.mapToGlobal(window.rect().center()), "페이지가 저장되었습니다.")))

    window.show()
    sys.exit(app.exec()) 