from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from promptbook_widgets import CustomLineEdit, ImageView
from promptbook_utils import PromptBookUtils
from promptbook_state import PromptBookState
from promptbook_handlers import PromptBookEventHandlers
import os, json, csv, shutil, sys

# 휴지통 기능을 위한 모듈 추가
try:
    from send2trash import send2trash
except ImportError:
    print("send2trash 모듈이 설치되지 않았습니다. pip install send2trash로 설치해 주세요.")
    send2trash = None

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
        # 기본 스타일 설정 (나중에 테마에 따라 업데이트됨)
        self.update_drop_hint_style()
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
    
    def update_drop_hint_style(self, theme=None):
        """드롭 힌트 스타일을 테마에 맞춰 업데이트"""
        if not hasattr(self, 'drop_hint'):
            return
            
        # 기본 테마 (어두운 모드)
        if theme is None:
            text_color = "#cccccc"
            bg_color = "rgba(60, 60, 60, 80)"
            border_color = "#555555"
        else:
            text_color = theme.get('text_secondary', '#cccccc')
            # surface 색상을 기반으로 반투명 배경 생성
            surface = theme.get('surface', '#3c3c3c')
            # 16진수 색상을 RGB로 변환하여 투명도 적용
            surface_rgb = surface.lstrip('#')
            r = int(surface_rgb[0:2], 16)
            g = int(surface_rgb[2:4], 16)
            b = int(surface_rgb[4:6], 16)
            bg_color = f"rgba({r}, {g}, {b}, 80)"
            border_color = theme.get('border', '#555555')
        
        style = f"""
            QLabel {{
                color: {text_color};
                background-color: {bg_color};
                font-size: 14px;
                padding: 30px;
                border: 2px dashed {border_color};
                border-radius: 10px;
            }}
        """
        self.drop_hint.setStyleSheet(style)
    
    def update_drop_hint_drag_style(self):
        """드래그 중일 때 스타일 (현재 테마의 primary 색상 사용)"""
        if not hasattr(self, 'drop_hint'):
            return
            
        # 부모 PromptBook에서 현재 테마 가져오기
        theme = self.get_current_theme()
        if theme:
            primary_color = theme.get('primary', '#0078d4')
            # primary 색상을 RGB로 변환하여 반투명 배경 생성
            primary_rgb = primary_color.lstrip('#')
            r = int(primary_rgb[0:2], 16)
            g = int(primary_rgb[2:4], 16)
            b = int(primary_rgb[4:6], 16)
            bg_color = f"rgba({r}, {g}, {b}, 50)"
        else:
            # 기본값
            primary_color = "#0078d4"
            bg_color = "rgba(0, 120, 212, 50)"
        
        style = f"""
            QLabel {{
                color: {primary_color};
                background-color: {bg_color};
                font-size: 14px;
                padding: 30px;
                border: 2px dashed {primary_color};
                border-radius: 10px;
            }}
        """
        self.drop_hint.setStyleSheet(style)
    
    def restore_drop_hint_style(self):
        """드롭 힌트를 원래 스타일로 복원"""
        theme = self.get_current_theme()
        self.update_drop_hint_style(theme)
    
    def get_current_theme(self):
        """부모 PromptBook에서 현재 테마 정보 가져오기"""
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, PromptBook):
                current_theme_name = getattr(parent, 'current_theme', '어두운 모드')
                return parent.THEMES.get(current_theme_name)
            parent = parent.parent()
        return None
    
    def dragEnterEvent(self, event):
        """드래그 엔터 이벤트 처리"""
        if event.mimeData().hasUrls():
            # URL이 있는지 확인하고 이미지 파일인지 검사
            urls = event.mimeData().urls()
            if urls and len(urls) == 1:  # 하나의 파일만 허용
                file_path = urls[0].toLocalFile()
                if self.is_image_file(file_path):
                    event.acceptProposedAction()
                    # 드래그 중일 때 시각적 피드백 (현재 테마의 primary 색상 사용)
                    self.update_drop_hint_drag_style()
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """드래그 리브 이벤트 처리"""
        # 원래 스타일로 복원
        self.restore_drop_hint_style()
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
                    self.restore_drop_hint_style()
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
            event.accept()  # 이벤트 전파를 막아서 부모 리스트의 선택을 방지
            # 이벤트를 완전히 소비하여 부모로 전파되지 않도록 함
            return
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        # 마우스 릴리즈 이벤트도 차단
        if event.button() == Qt.LeftButton:
            event.accept()
            return
        super().mouseReleaseEvent(event)

class PageItemWidget(QWidget):
    def __init__(self, name, is_favorite=False, emoji="📄", is_locked=False, parent=None):
        super().__init__(parent)
        self.page_name = name
        
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
        
        # 잠금 상태 라벨
        self.lock_label = QLabel()
        self.lock_label.setFixedWidth(16)  # 폭 줄이기
        self.lock_label.setAlignment(Qt.AlignCenter)
        
        # 레이아웃에 추가
        layout.addWidget(self.star_label)
        layout.addWidget(self.page_label)
        layout.addWidget(self.name_label)
        layout.addStretch()  # 오른쪽 여백
        layout.addWidget(self.lock_label)
        
        # 초기 상태 설정
        self.set_favorite(is_favorite)
        self.set_locked(is_locked)
    
    def mousePressEvent(self, event):
        """마우스 이벤트 처리 - Ctrl/Shift 키가 눌린 상태에서는 즐겨찾기 토글 방지"""
        if event.button() == Qt.LeftButton:
            modifiers = event.modifiers()
            
            # Ctrl이나 Shift 키가 눌린 상태에서는 즐겨찾기 토글하지 않고 선택만 처리
            if modifiers & (Qt.ControlModifier | Qt.ShiftModifier):
                # 이벤트를 부모로 전파하여 다중 선택 처리
                super().mousePressEvent(event)
                return
        
        # 일반 클릭인 경우 기본 동작
        super().mousePressEvent(event)
    
    def set_locked(self, is_locked):
        """잠금 상태 설정"""
        self.lock_label.setText("🔒" if is_locked else "")

    def toggle_favorite(self):
        """즐겨찾기 토글 - 부모 PromptBook 인스턴스 찾아서 처리"""
        # 부모 위젯 체인을 따라 PromptBook 인스턴스 찾기
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, PromptBook):
                # 즐겨찾기 토글 중임을 표시하는 플래그 설정
                parent._toggling_favorite = True
                
                # 이벤트 처리를 일시적으로 차단
                parent.book_list.blockSignals(True)
                
                try:
                    # 현재 페이지에 대해 즐겨찾기 토글
                    for char in parent.state.characters:
                        if char.get("name") == self.page_name:
                            is_favorite = not char.get("favorite", False)
                            char["favorite"] = is_favorite
                            
                            # 상태 업데이트
                            if parent.current_book:
                                parent.state.books[parent.current_book]["pages"] = parent.state.characters
                            
                            # 위젯 업데이트
                            self.set_favorite(is_favorite)
                            
                            # 정렬 적용 후 선택 해제하여 페이지 내용 숨기기
                            if not parent.sort_mode_custom:
                                current_mode = parent.sort_selector.currentText() if hasattr(parent, "sort_selector") else "오름차순 정렬"
                                from promptbook_features import sort_characters
                                parent.state.characters = sort_characters(parent.state.characters, current_mode)
                                
                                # refresh_character_list 대신 직접 리스트 업데이트
                                parent.char_list.blockSignals(True)
                                parent.char_list.clear()
                                
                                # 정렬된 캐릭터로 리스트 다시 생성
                                from PySide6.QtWidgets import QListWidgetItem
                                from PySide6.QtCore import Qt
                                for i, char in enumerate(parent.state.characters):
                                    text = char.get("name", "(이름 없음)")
                                    is_favorite = char.get("favorite", False)
                                    emoji = char.get("emoji", "📄")
                                    is_locked = char.get("locked", False)
                                    
                                    # 새 아이템 생성
                                    item = QListWidgetItem()
                                    widget = PageItemWidget(text, is_favorite, emoji, is_locked)
                                    item.setData(Qt.UserRole, text)
                                    
                                    parent.char_list.addItem(item)
                                    parent.char_list.setItemWidget(item, widget)
                                    item.setSizeHint(widget.sizeHint())
                                
                                parent.char_list.blockSignals(False)
                                parent.char_list.clearSelection()  # 선택 해제
                                
                                # 페이지 선택만 해제하고 페이지 내용만 숨기기 (페이지 리스트는 유지)
                                parent.current_index = -1
                                parent.name_input.clear()
                                parent.tag_input.clear()
                                parent.desc_input.clear()
                                parent.prompt_input.clear()
                                parent.image_scene.clear()
                                parent.image_view.update_drop_hint_visibility()
                            else:
                                # 커스텀 모드에서도 선택 해제하고 페이지 내용만 숨기기
                                parent.char_list.clearSelection()
                                parent.current_index = -1
                                parent.name_input.clear()
                                parent.tag_input.clear()
                                parent.desc_input.clear()
                                parent.prompt_input.clear()
                                parent.image_scene.clear()
                                parent.image_view.update_drop_hint_visibility()
                            
                            # 버튼 상태 업데이트
                            parent.update_all_buttons_state()
                            parent.update_image_buttons_state()
                            
                            # 즐겨찾기 토글 완료 후 저장
                            if parent.current_book and parent.current_book in parent.state.books:
                                parent.state.books[parent.current_book]["pages"] = parent.state.characters
                                parent.save_to_file()
                            break
                finally:
                    # 이벤트 처리 복원
                    parent.book_list.blockSignals(False)
                    # 즐겨찾기 토글 플래그를 약간 지연시켜 해제 (이벤트 큐 처리 완료 대기)
                    from PySide6.QtCore import QTimer
                    def clear_flag():
                        parent._toggling_favorite = False
                    QTimer.singleShot(500, clear_flag)  # 500ms로 지연 시간 증가
                
                return
            parent = parent.parent()
    
    def set_favorite(self, is_favorite):
        self.star_label.setText("❤️" if is_favorite else "🖤")
    
    def set_name(self, name):
        self.name_label.setText(name)
        self.page_name = name
    
    def set_emoji(self, emoji):
        self.page_label.setText(emoji)
        
    def set_locked(self, is_locked):
        """잠금 상태 설정"""
        self.lock_label.setText("🔒" if is_locked else "")

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
                # 이벤트 처리를 일시적으로 차단
                parent.book_list.blockSignals(True)
                
                try:
                    # 현재 북에 대해 즐겨찾기 토글
                    if self.book_name in parent.state.books:
                        is_favorite = not parent.state.books[self.book_name].get("favorite", False)
                        parent.state.books[self.book_name]["favorite"] = is_favorite
                        
                        # 위젯 업데이트
                        self.set_favorite(is_favorite)
                        
                        # 정렬 적용 후 선택 해제하여 북 내용 숨기기
                        if not parent.book_sort_custom:
                            parent.handle_book_sort()
                            # 북 선택 해제
                            parent.book_list.clearSelection()
                            parent.current_book = None
                            parent.state.characters = []
                            parent.char_list.clear()
                            parent.current_index = -1
                            parent.clear_page_list()
                        else:
                            # 커스텀 모드에서도 선택 해제
                            parent.book_list.clearSelection()
                            parent.current_book = None
                            parent.state.characters = []
                            parent.char_list.clear()
                            parent.current_index = -1
                            parent.clear_page_list()
                        
                        # 버튼 상태 업데이트
                        parent.update_all_buttons_state()
                        parent.update_image_buttons_state()
                        
                        parent.save_to_file()
                finally:
                    # 이벤트 처리 복원
                    parent.book_list.blockSignals(False)
                
                return
            parent = parent.parent()
    
    def set_favorite(self, is_favorite):
        self.star_label.setText("❤️" if is_favorite else "🖤")
    
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
            # 다중 선택 이동 시 북 순서 업데이트
            self.update_book_order()
        else:
            event.ignore()
    
    def update_book_order(self):
        """북 순서 업데이트"""
        # 부모 PromptBook 인스턴스 찾기
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, 'handle_book_reorder'):
                parent.handle_book_reorder()
                break
            parent = parent.parent()

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
            # 다중 선택 이동 시 페이지 순서 업데이트
            self.update_character_order()
        else:
            event.ignore()
    
    def update_character_order(self):
        """페이지 순서 업데이트"""
        # 부모 PromptBook 인스턴스 찾기
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, 'on_character_reordered'):
                parent.on_character_reordered()
                break
            parent = parent.parent()

class CustomSplitterHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 부모 스플리터에서 현재 테마 가져오기
        main_window = self.parent()
        while main_window and not isinstance(main_window, PromptBook):
            main_window = main_window.parent()
        
        if main_window:
            current_theme = getattr(main_window, 'current_theme', '어두운 모드')
            theme = main_window.THEMES.get(current_theme, main_window.THEMES['어두운 모드'])
            
            # 배경색을 메인 배경색과 통일
            bg_color = QColor(theme['background'])
            painter.fillRect(self.rect(), bg_color)
            
            rect = self.rect()
            center_x = rect.width() // 2
            center_y = rect.height() // 2
            
            if self.orientation() == Qt.Horizontal:
                # 세로 스플리터: 작은 점들로 그립 표시 (상하 중앙에)
                grip_color = QColor(theme['text_secondary'])
                if current_theme in ["블루 네온", "핑크 네온"]:
                    grip_color = QColor(theme['primary'])
                
                painter.setBrush(QBrush(grip_color))
                painter.setPen(Qt.NoPen)
                
                # 3개의 작은 원형 점들
                dot_size = 2
                spacing = 6
                
                for i in range(3):
                    y = center_y - spacing + (i * spacing)
                    painter.drawEllipse(center_x - dot_size//2, y - dot_size//2, dot_size, dot_size)
            else:
                # 가로 스플리터: 작은 점들로 그립 표시
                grip_color = QColor(theme['text_secondary'])
                if current_theme in ["블루 네온", "핑크 네온"]:
                    grip_color = QColor(theme['primary'])
                
                painter.setBrush(QBrush(grip_color))
                painter.setPen(Qt.NoPen)
                
                # 3개의 작은 원형 점들
                dot_size = 2
                spacing = 6
                
                for i in range(3):
                    x = center_x - spacing + (i * spacing)
                    painter.drawEllipse(x - dot_size//2, center_y - dot_size//2, dot_size, dot_size)

class CustomSplitter(QSplitter):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setHandleWidth(6)  # 더 작게 조정
        self.setChildrenCollapsible(False)
    
    def createHandle(self):
        return CustomSplitterHandle(self.orientation(), self)

class ResizeHandle(QWidget):
    """투명한 윈도우 리사이즈 핸들"""
    def __init__(self, direction, parent=None):
        super().__init__(parent)
        self.direction = direction
        self.parent_window = parent
        self.dragging = False
        self.drag_start_pos = None
        self.drag_start_geo = None
        
        # 기본 설정
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # 커서 설정
        self.setup_cursor()
        
        # 초기 스타일 (완전 투명)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
    
    def setup_cursor(self):
        """방향에 따른 커서 설정"""
        if self.direction in ['top', 'bottom']:
            self.setCursor(Qt.SizeVerCursor)
        elif self.direction in ['left', 'right']:
            self.setCursor(Qt.SizeHorCursor)
        elif self.direction in ['top-left', 'bottom-right']:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.direction in ['top-right', 'bottom-left']:
            self.setCursor(Qt.SizeBDiagCursor)
    
    def enterEvent(self, event):
        """마우스 호버 시 약간 보이게"""
        if not self.parent_window.isMaximized():
            # 현재 테마에 맞는 색상으로 호버 효과
            current_theme = getattr(self.parent_window, 'current_theme', '어두운 모드')
            theme = self.parent_window.THEMES.get(current_theme, self.parent_window.THEMES['어두운 모드'])
            
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme['primary']};
                    border: none;
                    opacity: 0.3;
                }}
            """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """마우스 벗어나면 다시 투명하게"""
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """리사이즈 시작"""
        if event.button() == Qt.LeftButton and not self.parent_window.isMaximized():
            self.dragging = True
            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_start_geo = self.parent_window.geometry()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """리사이즈 처리"""
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.handle_resize(event.globalPosition().toPoint())
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """리사이즈 종료"""
        self.dragging = False
        self.drag_start_pos = None
        self.drag_start_geo = None
    
    def handle_resize(self, global_pos):
        """실제 리사이즈 수행"""
        if not self.drag_start_pos or not self.drag_start_geo:
            return
            
        # 마우스 이동 거리 계산
        delta = global_pos - self.drag_start_pos
        dx, dy = delta.x(), delta.y()
        
        # 원래 지오메트리
        old_geo = self.drag_start_geo
        new_x, new_y = old_geo.x(), old_geo.y()
        new_width, new_height = old_geo.width(), old_geo.height()
        
        # 최소 크기 제한
        min_width, min_height = 400, 300
        
        # 최소 크기 체크
        proposed_width = new_width
        proposed_height = new_height
        width_at_limit = False
        height_at_limit = False
        
        # 방향에 따른 리사이즈 처리 (정상적인 윈도우 동작)
        if 'left' in self.direction:
            # 왼쪽에서 리사이즈: 왼쪽으로 드래그하면 왼쪽으로 늘어남
            proposed_width = old_geo.width() - dx
            if proposed_width >= min_width:
                new_width = proposed_width
                new_x = old_geo.x() + dx  # 왼쪽 가장자리 이동
            else:
                # 최소 크기에 도달하면 더 이상 축소하지 않음
                width_at_limit = True
        elif 'right' in self.direction:
            # 오른쪽에서 리사이즈: 오른쪽으로 드래그하면 오른쪽으로 늘어남
            proposed_width = old_geo.width() + dx
            if proposed_width >= min_width:
                new_width = proposed_width
            else:
                width_at_limit = True
            
        if 'top' in self.direction:
            # 위쪽에서 리사이즈: 위로 드래그하면 위로 늘어남
            proposed_height = old_geo.height() - dy
            if proposed_height >= min_height:
                new_height = proposed_height
                new_y = old_geo.y() + dy  # 위쪽 가장자리 이동
            else:
                # 최소 크기에 도달하면 더 이상 축소하지 않음
                height_at_limit = True
        elif 'bottom' in self.direction:
            # 아래쪽에서 리사이즈: 아래로 드래그하면 아래로 늘어남
            proposed_height = old_geo.height() + dy
            if proposed_height >= min_height:
                new_height = proposed_height
            else:
                height_at_limit = True
        
        # 최소 크기에 도달하지 않았을 때만 지오메트리 적용
        if not width_at_limit and not height_at_limit:
            self.parent_window.setGeometry(new_x, new_y, new_width, new_height)

class PromptBook(QMainWindow):
    # 클래스 레벨 상수 정의
    VERSION = "v2.2.1"
    SAVE_FILE = "character_data.json"
    SETTINGS_FILE = "ui_settings.json"
    
    # 테마 정의
    THEMES = {
        "어두운 모드": {
            "background": "#2b2b2b",
            "surface": "#3c3c3c", 
            "primary": "#8a8a8a",
            "text": "#ffffff",
            "text_secondary": "#cccccc",
            "border": "#555555",
            "hover": "#4a4a4a",
            "selected": "#8a8a8a",
            "button": "#404040",
            "button_hover": "#525252"
        },
        "밝은 모드": {
            "background": "#ffffff",
            "surface": "#f5f5f5",
            "primary": "#999999", 
            "text": "#000000",
            "text_secondary": "#666666",
            "border": "#d0d0d0",
            "hover": "#e0e0e0",
            "selected": "#999999",
            "button": "#e1e1e1",
            "button_hover": "#d8d8d8"
        },
        "파란 바다": {
            "background": "#1a2332",
            "surface": "#233447",
            "primary": "#4fa8da",
            "text": "#e8f4fd",
            "text_secondary": "#b8d4ea",
            "border": "#4a6b8a",
            "hover": "#2d4a61",
            "selected": "#4fa8da",
            "button": "#2a3f56",
            "button_hover": "#355070"
        },
        "숲속": {
            "background": "#1a2e1a",
            "surface": "#254725",
            "primary": "#4caf50",
            "text": "#e8f5e8",
            "text_secondary": "#b8e6b8",
            "border": "#4a7c4a",
            "hover": "#2d5a2d",
            "selected": "#4caf50",
            "button": "#2a4a2a",
            "button_hover": "#356535"
        },
        "보라 우주": {
            "background": "#2a1a2e",
            "surface": "#3d2547", 
            "primary": "#9c27b0",
            "text": "#f3e8f5",
            "text_secondary": "#d1b8d6",
            "border": "#7a4a7c",
            "hover": "#512d5a",
            "selected": "#9c27b0",
            "button": "#4a2a4a",
            "button_hover": "#653565"
        },
        "황혼": {
            "background": "#2e221a",
            "surface": "#473525",
            "primary": "#ff9800",
            "text": "#fff2e8",
            "text_secondary": "#e6c8b8",
            "border": "#7c5a4a",
            "hover": "#5a3d2d",
            "selected": "#ff9800", 
            "button": "#4a3a2a",
            "button_hover": "#654535"
        },
        "벚꽃": {
            "background": "#2e1a26",
            "surface": "#472535",
            "primary": "#e91e63",
            "text": "#fde8f0",
            "text_secondary": "#e6b8ca",
            "border": "#7c4a5f",
            "hover": "#5a2d41",
            "selected": "#e91e63",
            "button": "#4a2a38",
            "button_hover": "#65354a"
        },
        "민트": {
            "background": "#1a4d40",
            "surface": "#2d6659",
            "primary": "#66ffcc",
            "text": "#f0fff0",
            "text_secondary": "#99ffdd",
            "border": "#80ffcc",
            "hover": "#40a085",
            "selected": "#66ffcc",
            "button": "#40a085",
            "button_hover": "#66ffcc"
        },
        "블루 네온": {
            "background": "#0a0a0a",
            "surface": "#1a1a1a",
            "primary": "#00ffff",
            "text": "#ffffff",
            "text_secondary": "#80ffff",
            "border": "#00cccc",
            "hover": "#2a2a2a",
            "selected": "#00ffff",
            "button": "#1a1a1a",
            "button_hover": "#2a2a2a"
        },
        "핑크 네온": {
            "background": "#0a0a0a",
            "surface": "#1a1a1a",
            "primary": "#ff00ff",
            "text": "#ffffff",
            "text_secondary": "#ff80ff",
            "border": "#cc00cc",
            "hover": "#2a2a2a",
            "selected": "#ff00ff",
            "button": "#1a1a1a",
            "button_hover": "#2a2a2a"
        }
    }
    
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
        self.setWindowTitle(f"프롬프트 북 {self.VERSION}")
        self.setMinimumSize(1000, 600)  # 최소 크기 설정
        self.resize(1000, 600)  # 기본 크기 설정
        self.setAcceptDrops(True)
        
        # 앱 아이콘 설정
        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))
        else:
            print("[DEBUG] icon.png 파일을 찾을 수 없습니다.")
        
        # 프레임리스 윈도우로 설정 (커스텀 타이틀 바를 위해)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # 마우스 트래킹 활성화 (마우스 버튼을 누르지 않아도 이벤트 받기)
        self.setMouseTracking(True)
        
        # 드래그 관련 변수
        self.drag_position = None
        
        # 둥근 모서리를 위한 변수
        self.border_radius = 12
        
        # 리사이즈 핸들들
        self.resize_handles = {}
        
        # 저장된 설정 먼저 로드 (테마 정보 포함)
        self.load_ui_settings_early()
        
        # 테마 관련 초기화 (apply_theme 호출 전에 필요)
        self.theme_group = QActionGroup(self)
        
        # UI 구성
        self.setup_ui()
        
        # UI 구성 후 나머지 설정 적용
        if os.path.exists(self.SETTINGS_FILE):
            self.load_ui_settings_late()
            
        # 데이터 로드
        self.load_from_file()
        
        # 저장된 테마 적용 또는 기본 테마 적용
        self.apply_theme(getattr(self, 'current_theme', '어두운 모드'))
            
        # 단축키 설정
        self.setup_shortcuts()
        
        # 리사이즈 핸들 설정
        self.setup_resize_handles()

    def setup_ui(self):
        self.setWindowTitle("프롬프트 북")
        self.setMinimumSize(1000, 600)
        # self.setup_menubar()  # 메뉴바는 커스텀 타이틀바에 통합
        self.setup_theme_actions()  # 테마 액션들 설정
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
        
        # 테마 액션 그룹 (라디오 버튼처럼 동작)
        self.theme_group = QActionGroup(self)
        
        for theme_name in self.THEMES.keys():
            theme_action = QAction(theme_name, self)
            theme_action.setCheckable(True)
            theme_action.triggered.connect(lambda checked, name=theme_name: self.apply_theme(name))
            self.theme_group.addAction(theme_action)
            theme_menu.addAction(theme_action)
            
            # 기본 테마 설정
            if theme_name == "어두운 모드":
                theme_action.setChecked(True)
        
        # 현재 테마 저장용 변수
        self.current_theme = "어두운 모드"
        
        # 도구 메뉴 추가
        tools_menu = menubar.addMenu("🔧 도구")
        
        # 이미지 정리 메뉴 항목 추가
        cleanup_action = tools_menu.addAction("🗑️ 사용하지 않는 이미지 정리")
        cleanup_action.triggered.connect(self.cleanup_unused_images)
        cleanup_action.setToolTip("현재 페이지들에서 사용되지 않는 이미지를 휴지통으로 이동합니다")
        
        # 정보 메뉴
        info_menu = menubar.addMenu("정보")

    def setup_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        
        # 커스텀 타이틀 바 추가
        self.setup_custom_title_bar(layout)
        
        # 메인 스플리터 생성 (커스텀 스플리터 사용)
        self.main_splitter = CustomSplitter(Qt.Horizontal)  # 커스텀 스플리터 사용
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
        self.book_list.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 다중 선택 모드 활성화
        self.book_list.setFocusPolicy(Qt.StrongFocus)
        # 델리게이트 제거 - 커스텀 위젯 사용할 예정
        self.book_list.installEventFilter(self)
        self.book_list.itemClicked.connect(lambda item: self.on_book_selected(self.book_list.row(item)))
        self.book_list.itemSelectionChanged.connect(self.on_book_selection_changed)  # 다중 선택 변경 감지
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
        self.char_list.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 다중 선택 모드 활성화
        self.char_list.itemClicked.connect(self.on_character_clicked)
        self.char_list.itemSelectionChanged.connect(self.on_character_selection_changed)  # 다중 선택 변경 감지
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
        
        self.duplicate_button = QPushButton("📄 복제")
        self.duplicate_button.clicked.connect(self.duplicate_selected_character_with_tooltip)
        self.duplicate_button.setEnabled(False)
        
        self.delete_button = QPushButton("🗑️ 삭제")
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
        
        # 이미지 정리 버튼 추가
        self.image_cleanup_btn = QPushButton("🧹 이미지 정리")
        self.image_cleanup_btn.clicked.connect(self.cleanup_unused_images)
        self.image_cleanup_btn.setToolTip("사용하지 않는 이미지를 휴지통으로 이동")
        
        image_button_layout.addWidget(self.image_load_btn)
        image_button_layout.addWidget(self.image_remove_btn)
        image_button_layout.addWidget(self.image_cleanup_btn)
        
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
        """페이지 즐겨찾기 토글 - 사용하지 않음 (PageItemWidget.toggle_favorite 사용)"""
        # 이 메서드는 더 이상 사용하지 않습니다.
        # PageItemWidget.toggle_favorite()에서 모든 처리를 담당합니다.
        pass

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
        if self.current_book and self.current_book in self.state.books:
                self.state.books[self.current_book]["pages"] = self.state.characters
        print("[DEBUG] 새로운 순서로 저장됨")
        self.save_to_file()

    def filter_characters(self):
        query = self.search_input.text().strip().lower()
        
        # 검색어가 비어있으면 전체 리스트 갱신 (선택 없이)
        if not query:
            self.refresh_character_list(selected_name=None)  # 명시적으로 None 전달
            # 선택 상태 완전히 초기화
            self.current_index = -1
            self.char_list.clearSelection()
            if hasattr(self, 'name_input'):
                self.name_input.clear()
            if hasattr(self, 'tag_input'):
                self.tag_input.clear()
            if hasattr(self, 'desc_input'):
                self.desc_input.clear()
            if hasattr(self, 'prompt_input'):
                self.prompt_input.clear()
            if hasattr(self, 'lock_checkbox'):
                self.lock_checkbox.setChecked(False)
                self.lock_checkbox.setText("🔓 페이지 잠금")
                self.lock_checkbox.setEnabled(False)
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            self.update_all_buttons_state()
            self.update_image_buttons_state()
            return
            
        self.char_list.blockSignals(True)
        self.char_list.clear()
        
        # 검색 시 현재 선택 상태 초기화
        self.current_index = -1
        if hasattr(self, 'name_input'):
            self.name_input.clear()
        if hasattr(self, 'tag_input'):
            self.tag_input.clear()
        if hasattr(self, 'desc_input'):
            self.desc_input.clear()
        if hasattr(self, 'prompt_input'):
            self.prompt_input.clear()
        if hasattr(self, 'lock_checkbox'):
            self.lock_checkbox.setChecked(False)
            self.lock_checkbox.setText("🔓 페이지 잠금")
            self.lock_checkbox.setEnabled(False)
        self.image_scene.clear()
        self.image_view.update_drop_hint_visibility()
        
        for i, char in enumerate(self.state.characters):
            name = char.get("name", "").lower()
            tags = char.get("tags", "").lower()
            if query in name or query in tags:
                item = QListWidgetItem()
                text = char.get("name", "(이름 없음)")
                is_favorite = char.get("favorite", False)
                emoji = char.get("emoji", "📄")
                is_locked = char.get("locked", False)  # 잠금 상태 가져오기
                
                # 커스텀 위젯 생성
                widget = PageItemWidget(text, is_favorite, emoji, is_locked)  # is_locked 전달
                item.setData(Qt.UserRole, text)
                
                self.char_list.addItem(item)
                self.char_list.setItemWidget(item, widget)
                item.setSizeHint(widget.sizeHint())
                
        self.char_list.blockSignals(False)
        
        # 버튼 상태 업데이트
        self.update_all_buttons_state()
        self.update_image_buttons_state()

    def filter_books(self):
        """북 검색 필터링"""
        query = self.book_search_input.text().strip().lower() if hasattr(self, "book_search_input") else ""
        
        # 검색 시 현재 북과 페이지 상태 초기화
        self.current_book = None
        self.state.characters = []
        self.char_list.clear()
        self.current_index = -1
        
        # 입력 필드 비우기
        if hasattr(self, 'name_input'):
            self.name_input.clear()
        if hasattr(self, 'tag_input'):
            self.tag_input.clear()
        if hasattr(self, 'desc_input'):
            self.desc_input.clear()
        if hasattr(self, 'prompt_input'):
            self.prompt_input.clear()
        if hasattr(self, 'lock_checkbox'):
            self.lock_checkbox.setChecked(False)
            self.lock_checkbox.setText("🔓 페이지 잠금")
            self.lock_checkbox.setEnabled(False)
        self.image_scene.clear()
        self.image_view.update_drop_hint_visibility()
        
        # 북 리스트 갱신
        self.refresh_book_list()
        
        # 버튼 상태 업데이트
        self.update_all_buttons_state()
        self.update_image_buttons_state()

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
        book_found = False
        if selected_name:
            for i in range(self.book_list.count()):
                item = self.book_list.item(i)
                if item.data(Qt.UserRole) == selected_name:
                    self.book_list.setCurrentItem(item)
                    book_found = True
                    break
        
        # 선택된 북이 검색 결과에 없으면 선택 해제
        if not book_found:
            self.book_list.clearSelection()
            # 검색으로 인해 현재 북이 보이지 않으면 페이지 리스트도 비우기
            if self.current_book and selected_name and self.current_book == selected_name:
                self.current_book = None
                self.state.characters = []
                self.char_list.clear()
                self.current_index = -1
                
                # 입력 필드 비우기
                if hasattr(self, 'name_input'):
                    self.name_input.clear()
                if hasattr(self, 'tag_input'):
                    self.tag_input.clear()
                if hasattr(self, 'desc_input'):
                    self.desc_input.clear()
                if hasattr(self, 'prompt_input'):
                    self.prompt_input.clear()
                if hasattr(self, 'lock_checkbox'):
                    self.lock_checkbox.setChecked(False)
                    self.lock_checkbox.setText("🔓 페이지 잠금")
                    self.lock_checkbox.setEnabled(False)
                self.image_scene.clear()
                self.image_view.update_drop_hint_visibility()
        
        self.book_list.blockSignals(False)

    def save_current_character(self):
        if self.current_book and 0 <= self.current_index < len(self.state.characters):
            data = self.state.characters[self.current_index]
            data["name"] = self.name_input.text()
            data["tags"] = self.tag_input.text()
            data["desc"] = self.desc_input.toPlainText()
            data["prompt"] = self.prompt_input.toPlainText()
            if self.current_book and self.current_book in self.state.books:
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
        self.update_image_buttons_state()
    
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
                
            # 리스트 갱신
            current_name = self.state.characters[self.current_index].get('name')
            self.refresh_character_list(selected_name=current_name)
            self.save_to_file()

    def save_ui_settings(self):
        settings = {
            "width": self.width(),
            "height": self.height(),
            "splitter_sizes": self.main_splitter.sizes() if hasattr(self, "main_splitter") else [200, 400, 372],
            "sort_mode": self.sort_selector.currentText() if hasattr(self, "sort_selector") else "오름차순 정렬",
            "sort_mode_custom": self.sort_mode_custom,
            "book_sort_mode": self.book_sort_selector.currentText() if hasattr(self, "book_sort_selector") else "오름차순 정렬",
            "book_sort_custom": getattr(self, "book_sort_custom", False),
            "current_theme": getattr(self, "current_theme", "어두운 모드")
        }
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"[ERROR] UI 설정 저장 실패: {e}")

    def load_ui_settings_early(self):
        """UI 구성 전에 로드할 설정들 (테마 등)"""
        if not os.path.exists(self.SETTINGS_FILE):
            return
            
        try:
            with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
                # 테마 설정만 먼저 복원
                saved_theme = settings.get("current_theme", "어두운 모드")
                if saved_theme in self.THEMES:
                    self.current_theme = saved_theme
                    print(f"[DEBUG] 저장된 테마 로드: {saved_theme}")
                        
        except Exception as e:
            print(f"[ERROR] 초기 UI 설정 불러오기 실패: {e}")
    
    def load_ui_settings_late(self):
        """UI 구성 후에 로드할 설정들 (크기, 정렬 등)"""
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
        """캐릭터 리스트를 갱신합니다."""
        if not self.current_book:
            self.state.characters = []
            self.char_list.clear()
            self.update_all_buttons_state()
            return

        # 검색어 가져오기
        query = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        
        # 리스트 갱신 준비
        self.char_list.blockSignals(True)
        self.char_list.clear()
        
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
                is_locked = char.get("locked", False)  # 잠금 상태 가져오기
                
                # 커스텀 위젯 생성
                widget = PageItemWidget(text, is_favorite, emoji, is_locked)  # is_locked 전달
                item.setData(Qt.UserRole, text)
                
                self.char_list.addItem(item)
                self.char_list.setItemWidget(item, widget)
                item.setSizeHint(widget.sizeHint())
                
                if text == selected_name:
                    selected_index = self.char_list.count() - 1

        self.char_list.blockSignals(False)

        # 선택 상태 복원
        if selected_index >= 0:
            self.char_list.setCurrentRow(selected_index)
            self.current_index = selected_index
        else:
            # selected_name이 None이거나 찾을 수 없으면 아무것도 선택하지 않음
            self.char_list.clearSelection()
            self.current_index = -1

        self.update_all_buttons_state()
        
        # 상태가 변경되었으면 저장
        if should_save and self.current_book and self.current_book in self.state.books:
            self.state.books[self.current_book]["pages"] = self.state.characters
            self.save_to_file()

    def on_book_selected(self, index):
        # 즐겨찾기 토글 중일 때는 북 선택 처리를 하지 않음
        if getattr(self, '_toggling_favorite', False):
            return
        
        self.sort_mode_custom = False
        
        # 다중 선택 여부 확인
        selected_books = self.book_list.selectedItems()
        
        if len(selected_books) > 1:
            # 다중 선택된 경우 - 페이지 리스트 숨기기
            self.current_book = None
            self.state.characters = []
            self.char_list.clear()
            if hasattr(self, 'add_button'):
                self.add_button.setEnabled(False)
            
            # 입력 필드 초기화
            self.current_index = -1
            if hasattr(self, 'name_input'):
                self.name_input.clear()
            if hasattr(self, 'tag_input'):
                self.tag_input.clear()
            if hasattr(self, 'desc_input'):
                self.desc_input.clear()
            if hasattr(self, 'prompt_input'):
                self.prompt_input.clear()
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            
            self.update_all_buttons_state()
            return
        
        # 단일 선택인 경우 기존 로직
        if 0 <= index < self.book_list.count():
            item = self.book_list.item(index)
            book_name = item.data(Qt.UserRole) if item else None
            self.current_book = book_name
            book_data = self.state.books.get(book_name, {})
            self.state.characters = book_data.get("pages", [])
            
            # 현재 정렬 모드 적용 (커스텀 정렬이 아닌 경우)
            if hasattr(self, 'sort_selector') and not self.sort_mode_custom and self.state.characters and self.current_book in self.state.books:
                current_sort_mode = self.sort_selector.currentText()
                from promptbook_features import sort_characters
                self.state.characters = sort_characters(self.state.characters, current_sort_mode)
                if self.current_book and self.current_book in self.state.books:
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
        """파일 저장 시 자동으로 이미지 정리 실행"""
        if getattr(self, '_initial_loading', False):
            return
        
        # 즐겨찾기 토글 중일 때는 저장하지 않음 (이벤트 충돌 방지)
        if getattr(self, '_toggling_favorite', False):
            return
        
        try:
            with open(self.SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state.books, f, ensure_ascii=False, indent=2)
            
            # 즐겨찾기 토글 중에는 이미지 정리를 하지 않음 (UI 이벤트 충돌 방지)
            # self.cleanup_unused_images_silent()
            
        except Exception as e:
            print(f"[ERROR] 저장 실패: {e}")

    def load_from_file(self):
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
        # 다중 선택이 있는지 확인
        selected_items = self.char_list.selectedItems()
        if len(selected_items) > 1:
            self.duplicate_multiple_characters(selected_items)
        else:
            self.duplicate_selected_character()
            QToolTip.showText(self.duplicate_button.mapToGlobal(self.duplicate_button.rect().center()), "페이지가 복제되었습니다.")

    def delete_selected_character_with_tooltip(self):
        # 다중 선택이 있는지 확인
        selected_items = self.char_list.selectedItems()
        if len(selected_items) > 1:
            self.delete_multiple_characters(selected_items)
        else:
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
        
        # 이미지 뷰 업데이트
        self.update_image_view(file_path)
        
        # 버튼 상태 업데이트
        self.update_image_buttons_state()
        
        # 상태 저장
        if self.current_book and self.current_book in self.state.books:
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
        selected_pages = self.char_list.selectedItems()
        clicked_name = item.data(Qt.UserRole)
        print(f"[DEBUG] 클릭된 아이템: {clicked_name}")
        print(f"[DEBUG] 클릭 후 선택된 페이지 수: {len(selected_pages)}")
        
        # 클릭된 아이템이 실제로 선택되어 있는지 확인
        is_clicked_item_selected = item in selected_pages
        print(f"[DEBUG] 클릭된 아이템이 선택되어 있나? {is_clicked_item_selected}")
        
        # itemSelectionChanged가 모든 선택 처리를 담당하므로 여기서는 아무것도 하지 않음
        print("[DEBUG] itemSelectionChanged 신호에서 처리하므로 여기서는 아무것도 안함")
    
    def on_book_selection_changed(self):
        """북 선택 변경 시 호출 (다중 선택 감지용)"""
        selected_books = self.book_list.selectedItems()
        
        if len(selected_books) > 1:
            # 다중 선택된 경우 - 페이지 리스트 숨기기
            self.current_book = None
            self.state.characters = []
            self.char_list.clear()
            if hasattr(self, 'add_button'):
                self.add_button.setEnabled(False)
            
            # 입력 필드 초기화
            self.current_index = -1
            if hasattr(self, 'name_input'):
                self.name_input.clear()
            if hasattr(self, 'tag_input'):
                self.tag_input.clear()
            if hasattr(self, 'desc_input'):
                self.desc_input.clear()
            if hasattr(self, 'prompt_input'):
                self.prompt_input.clear()
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            
            self.update_all_buttons_state()
        elif len(selected_books) == 1:
            # 단일 선택으로 돌아온 경우
            current_item = selected_books[0]
            index = self.book_list.row(current_item)
            self.on_book_selected(index)
    
    def on_character_selection_changed(self):
        """페이지 선택 변경 시 호출 (다중 선택 감지용)"""
        # 약간의 지연을 두어 모든 선택 변경이 완료된 후 처리
        QTimer.singleShot(10, self._handle_selection_change)
    
    def _handle_selection_change(self):
        """실제 선택 변경 처리"""
        selected_pages = self.char_list.selectedItems()
        print(f"[DEBUG] _handle_selection_change: 선택된 페이지 수={len(selected_pages)}")
        
        if len(selected_pages) > 1:
            # 다중 선택된 경우 - 내용 포커싱 안하기
            self.current_index = -1
            if hasattr(self, 'name_input'):
                self.name_input.clear()
            if hasattr(self, 'tag_input'):
                self.tag_input.clear()
            if hasattr(self, 'desc_input'):
                self.desc_input.clear()
            if hasattr(self, 'prompt_input'):
                self.prompt_input.clear()
            if hasattr(self, 'lock_checkbox'):
                self.lock_checkbox.setChecked(False)
                self.lock_checkbox.setText("🔓 페이지 잠금")
                self.lock_checkbox.setEnabled(False)
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            
            self.update_all_buttons_state()
            self.update_image_buttons_state()
        elif len(selected_pages) == 1:
            # 단일 선택으로 돌아온 경우
            print("[DEBUG] 단일 선택으로 내용 로드")
            # 선택된 아이템만 사용 (currentItem 완전히 무시)
            selected_item = selected_pages[0]
            name = selected_item.data(Qt.UserRole)
            print(f"[DEBUG] 선택된 아이템 이름: {name}")
            
            # characters 리스트에서 해당 페이지 찾기
            for i, char in enumerate(self.state.characters):
                if char.get("name") == name:
                    print(f"[DEBUG] 페이지 데이터 찾음 - 인덱스: {i}")
                    self.current_index = i
                    
                    # 입력 필드 업데이트
                    if hasattr(self, 'name_input'):
                        self.name_input.setText(char.get("name", ""))
                    if hasattr(self, 'tag_input'):
                        self.tag_input.setText(char.get("tags", ""))
                    if hasattr(self, 'desc_input'):
                        self.desc_input.setPlainText(char.get("desc", ""))
                    if hasattr(self, 'prompt_input'):
                        self.prompt_input.setPlainText(char.get("prompt", ""))
                    
                    # 잠금 상태 표시
                    if hasattr(self, 'lock_checkbox'):
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
                    
                    self.update_all_buttons_state()
                    self.update_image_buttons_state()
                    break
        elif len(selected_pages) == 0:
            # 모든 선택 해제된 경우 - 내용 비우기
            self.current_index = -1
            if hasattr(self, 'name_input'):
                self.name_input.clear()
            if hasattr(self, 'tag_input'):
                self.tag_input.clear()
            if hasattr(self, 'desc_input'):
                self.desc_input.clear()
            if hasattr(self, 'prompt_input'):
                self.prompt_input.clear()
            if hasattr(self, 'lock_checkbox'):
                self.lock_checkbox.setChecked(False)
                self.lock_checkbox.setText("🔓 페이지 잠금")
                self.lock_checkbox.setEnabled(False)
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            
            self.update_all_buttons_state()
            self.update_image_buttons_state()

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
            if self.current_book and self.current_book in self.state.books:
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
        """선택된 북(들)을 zip 파일로 저장합니다."""
        # 다중 선택된 북들 확인
        selected_books = self.book_list.selectedItems()
        book_names = []
        
        for item in selected_books:
            book_name = item.data(Qt.UserRole)
            if book_name:
                book_names.append(book_name)
        
        # 선택된 북이 없으면 현재 북 사용
        if not book_names:
            if not self.current_book:
                QMessageBox.warning(self, "저장 실패", "선택된 북이 없습니다.")
                return
            book_names = [self.current_book]
        
        # 파일 저장 대화상자
        if len(book_names) == 1:
            default_name = f"{book_names[0]}.zip"
        else:
            default_name = f"북_모음_{len(book_names)}개.zip"
            
        path, _ = QFileDialog.getSaveFileName(self, "북 저장", default_name, "Zip Files (*.zip)")
        if not path:
            return
            
        try:
            from zipfile import ZipFile
            
            with ZipFile(path, 'w') as zipf:
                if len(book_names) == 1:
                    # 단일 북 저장 (기존 형식)
                    book_name = book_names[0]
                    book_data = self.state.books[book_name]
                    pages = book_data.get("pages", [])
                    
                    # 내보낼 데이터 준비
                    export_data = {
                        "book_name": book_name,
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
                    
                else:
                    # 다중 북 저장 (새 형식)
                    export_data = {
                        "format": "multiple_books",
                        "books": []
                    }
                    
                    # 각 북 처리
                    for book_name in book_names:
                        book_data = self.state.books[book_name]
                        pages = book_data.get("pages", [])
                        
                        book_export = {
                            "book_name": book_name,
                            "emoji": book_data.get("emoji", "📕"),
                            "pages": []
                        }
                        
                        # 각 페이지 처리
                        for i, page in enumerate(pages):
                            page_copy = dict(page)
                            
                            # 이미지가 있으면 zip에 포함
                            img_path = page.get("image_path")
                            if img_path and os.path.exists(img_path):
                                # zip 내부 경로 생성 (북 이름을 포함하여 중복 방지)
                                filename = f"images/{book_name}_{i}_{os.path.basename(img_path)}"
                                zipf.write(img_path, filename)
                                page_copy["image_path"] = filename
                            else:
                                page_copy["image_path"] = ""
                                
                            book_export["pages"].append(page_copy)
                        
                        export_data["books"].append(book_export)
                    
                    # 다중 북 데이터를 JSON으로 저장
                    zipf.writestr("books_data.json", json.dumps(export_data, ensure_ascii=False, indent=2))
                
            if len(book_names) == 1:
                QMessageBox.information(self, "저장 완료", f"'{book_names[0]}' 북이 성공적으로 저장되었습니다.")
                print(f"[DEBUG] 선택된 북 저장 완료: {book_names[0]} -> {path}")
            else:
                QMessageBox.information(self, "저장 완료", f"{len(book_names)}개의 북이 성공적으로 저장되었습니다.\n{', '.join(book_names[:3])}{' 외' if len(book_names) > 3 else ''}")
                print(f"[DEBUG] 다중 북 저장 완료: {book_names} -> {path}")
            
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
                
                # 다중 북 형식 확인: books_data.json 파일
                books_json_path = os.path.join(temp_dir, "books_data.json")
                if os.path.exists(books_json_path):
                    # 다중 북 형식 처리
                    self._load_multiple_books_format(temp_dir, books_json_path)
                else:
                    # 단일 북 형식 확인: book_data.json 파일
                    json_path = os.path.join(temp_dir, "book_data.json")
                    if os.path.exists(json_path):
                        # 단일 북 형식 처리
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
                if self.current_book and self.current_book in self.state.books:
                    self.state.books[self.current_book]["pages"] = self.state.characters
                self.refresh_character_list()
        
        # 데이터 저장
        self.save_to_file()

    def _load_multiple_books_format(self, temp_dir, books_json_path):
        """다중 북 형식 파일 불러오기 (books_data.json)"""
        with open(books_json_path, 'r', encoding='utf-8') as f:
            books_data = json.load(f)
        
        books_list = books_data.get("books", [])
        if not books_list:
            QMessageBox.warning(self, "불러오기 실패", "불러올 북이 없습니다.")
            return
        
        existing_names = set(self.state.books.keys())
        loaded_books = []
        name_conflicts = []
        
        # 각 북에 대해 이름 중복 체크
        for book_data in books_list:
            original_name = book_data.get("book_name", "불러온 북")
            if original_name in existing_names:
                name_conflicts.append(original_name)
        
        # 이름 중복이 있는 경우 처리 방법 묻기
        if name_conflicts:
            msgBox = QMessageBox()
            msgBox.setWindowTitle("북 이름 중복")
            msgBox.setText(f"{len(name_conflicts)}개의 북 이름이 중복됩니다:")
            msgBox.setInformativeText(f"{', '.join(name_conflicts[:3])}{' 외' if len(name_conflicts) > 3 else ''}\n\n어떻게 하시겠습니까?")
            
            overwrite_btn = msgBox.addButton("모두 덮어쓰기", QMessageBox.AcceptRole)
            add_new_btn = msgBox.addButton("새 이름으로 추가", QMessageBox.ActionRole)
            cancel_btn = msgBox.addButton("취소", QMessageBox.RejectRole)
            
            msgBox.setDefaultButton(cancel_btn)
            msgBox.exec()
            
            if msgBox.clickedButton() == cancel_btn:
                print("[DEBUG] 다중 북 불러오기 취소")
                return
            
            overwrite_mode = msgBox.clickedButton() == overwrite_btn
        else:
            overwrite_mode = False
        
        # 각 북 처리
        for book_data in books_list:
            original_name = book_data.get("book_name", "불러온 북")
            book_name = original_name
            
            # 이름 중복 처리
            if original_name in existing_names:
                if not overwrite_mode:
                    # 새 이름으로 추가
                    for i in range(1, 1000):
                        candidate = f"{original_name} ({i})"
                        if candidate not in existing_names:
                            book_name = candidate
                            break
                    existing_names.add(book_name)
            else:
                existing_names.add(book_name)
            
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
            loaded_books.append(book_name)
            print(f"[DEBUG] 북 불러오기 완료: {book_name}")
        
        # 첫 번째 불러온 북 선택
        if loaded_books:
            first_book = loaded_books[0]
            for i in range(self.book_list.count()):
                item = self.book_list.item(i)
                if item.data(Qt.UserRole) == first_book:
                    self.book_list.setCurrentItem(item)
                    self.on_book_selected(i)
                    break
        
        QMessageBox.information(self, "불러오기 완료", f"{len(loaded_books)}개의 북이 성공적으로 불러와졌습니다.\n{', '.join(loaded_books[:3])}{' 외' if len(loaded_books) > 3 else ''}")
        print(f"[DEBUG] 다중 북 형식 불러오기 완료: {loaded_books}")

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

        if self.current_book and self.current_book in self.state.books:
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
        
        # 메뉴 스타일 적용
        menu_style = self.get_menu_style()
        menu.setStyleSheet(menu_style)
        
        # 선택된 아이템들 확인
        selected_items = self.char_list.selectedItems()
        selected_count = len(selected_items)
        
        if selected_count > 1:
            # 다중 선택된 경우
            menu.addAction(f"🔢 선택된 항목: {selected_count}개").setEnabled(False)
            menu.addSeparator()
            
            duplicate_action = menu.addAction("📋 모두 복제")
            delete_action = menu.addAction("🗑️ 모두 삭제")
            
            # 메뉴 실행 및 액션 처리
            action = menu.exec_(self.char_list.mapToGlobal(position))
            if action == duplicate_action:
                self.duplicate_multiple_characters(selected_items)
            elif action == delete_action:
                self.delete_multiple_characters(selected_items)
            return
        
        # 단일 선택인 경우 기존 메뉴
        name = item.data(Qt.UserRole)
        is_favorite = False
        
        # 현재 즐겨찾기 상태 확인
        for char in self.state.characters:
            if char.get("name") == name:
                is_favorite = char.get("favorite", False)
                break
        
        # 즐겨찾기 액션 추가
        if is_favorite:
            favorite_action = menu.addAction("🖤 즐겨찾기 해제")
        else:
            favorite_action = menu.addAction("❤️ 즐겨찾기")
        
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
            group_menu.setStyleSheet(menu_style)
            emoji_menu.addMenu(group_menu)
            for emoji in emojis:
                action = group_menu.addAction(emoji)
                action.triggered.connect(lambda checked, e=emoji, i=item: self.set_page_emoji(i, e))
        
        # 구분선 추가
        menu.addSeparator()
        
        # 기타 액션들 추가
        duplicate_action = menu.addAction("📋 복제")
        delete_action = menu.addAction("🗑️ 삭제")
        
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
                if self.current_book and self.current_book in self.state.books:
                    self.state.books[self.current_book]["pages"] = self.state.characters
                    self.save_to_file()
                break

    def show_book_context_menu(self, position):
        item = self.book_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        # 메뉴 스타일 적용
        menu_style = self.get_menu_style()
        menu.setStyleSheet(menu_style)
        
        # 선택된 아이템들 확인
        selected_items = self.book_list.selectedItems()
        selected_count = len(selected_items)
        
        if selected_count > 1:
            # 다중 선택된 경우
            menu.addAction(f"🔢 선택된 항목: {selected_count}개").setEnabled(False)
            menu.addSeparator()
            
            delete_action = menu.addAction("🗑️ 모두 삭제")
            
            # 메뉴 실행 및 액션 처리
            action = menu.exec_(self.book_list.mapToGlobal(position))
            if action == delete_action:
                self.delete_multiple_books(selected_items)
            return
        
        # 단일 선택인 경우 기존 메뉴
        name = item.data(Qt.UserRole)
        is_favorite = False
        
        # 현재 즐겨찾기 상태 확인
        if name in self.state.books:
            is_favorite = self.state.books[name].get("favorite", False)
        
        # 즐겨찾기 액션 추가
        if is_favorite:
            favorite_action = menu.addAction("🖤 즐겨찾기 해제")
        else:
            favorite_action = menu.addAction("❤️ 즐겨찾기")
        
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
        """북 즐겨찾기 토글 - 사용하지 않음 (BookItemWidget.toggle_favorite 사용)"""
        # 이 메서드는 더 이상 사용하지 않습니다.
        # BookItemWidget.toggle_favorite()에서 모든 처리를 담당합니다.
        pass

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
        """북 삭제"""
        # 북 이름 가져오기
        if isinstance(item, BookItemWidget):
            book_name = item.book_name
        else:
            widget = self.book_list.itemWidget(item)
            if isinstance(widget, BookItemWidget):
                book_name = widget.book_name
            else:
                return
        
        if not book_name or book_name not in self.state.books:
            return
        
        # 잠긴 페이지가 있는지 확인
        pages = self.state.books[book_name]["pages"]
        for page in pages:
            if page.get('locked', False):
                QMessageBox.warning(
                    self,
                    '북 삭제 불가',
                    f'잠긴 페이지가 있어 삭제할 수 없습니다.',
                    QMessageBox.Ok
                )
                return
        
        # 삭제 전 확인
        reply = QMessageBox.question(
            self,
            '북 삭제',
            f'"{book_name}" 북을 삭제하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 현재 선택된 북이 삭제하려는 북인지 확인
                current_book = None
                if self.book_list.currentItem():
                    widget = self.book_list.itemWidget(self.book_list.currentItem())
                    if isinstance(widget, BookItemWidget):
                        current_book = widget.book_name
                
                # 북 삭제
                del self.state.books[book_name]
                row = self.book_list.row(item)
                self.book_list.takeItem(row)
                
                # 삭제된 북이 현재 선택된 북이었다면 UI 초기화
                if current_book == book_name:
                    self.character_list.clear()
                    self.clear_page_list()
                    self.current_book = None
                    self.state.characters = []
                
                # 변경사항 저장
                self.save_to_file()
                self.refresh_book_list()
                
            except Exception as e:
                print(f"[ERROR] 북 삭제 중 오류 발생: {str(e)}")
                QMessageBox.warning(self, '오류', f'북 삭제 중 오류가 발생했습니다.', QMessageBox.Ok)

    def update_image_buttons_state(self):
        # 이미지 불러오기 버튼: 북과 페이지가 선택되어 있을 때 활성화
        page_selected = (self.current_book is not None and 
                        self.current_index >= 0 and 
                        self.current_index < len(self.state.characters))
        self.image_load_btn.setEnabled(page_selected)
        
        # 이미지 제거 버튼: 페이지가 선택되어 있고 이미지가 있을 때만 활성화
        has_image = False
        if page_selected:
            image_path = self.state.characters[self.current_index].get("image_path", "")
            has_image = bool(image_path and os.path.exists(image_path))
        
        self.image_remove_btn.setEnabled(has_image)

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
            if self.current_book and self.current_book in self.state.books:
                self.state.books[self.current_book]["pages"] = self.state.characters
            self.image_scene.clear()
            self.image_view.update_drop_hint_visibility()
            
            # 버튼 상태 업데이트
            self.update_image_buttons_state()
            
            self.save_to_file()
    
    def delete_focused_item(self):
        """현재 포커스된 리스트에 따라 북 또는 페이지 삭제 (다중 선택 지원)"""
        # 현재 포커스된 위젯 확인
        focused_widget = QApplication.focusWidget()
        
        # 북 리스트에 포커스가 있는 경우
        if focused_widget == self.book_list or self.book_list.isAncestorOf(focused_widget):
            selected_items = self.book_list.selectedItems()
            if selected_items:
                self.delete_multiple_books(selected_items)
        
        # 페이지 리스트에 포커스가 있는 경우
        elif focused_widget == self.char_list or self.char_list.isAncestorOf(focused_widget):
            selected_items = self.char_list.selectedItems()
            if selected_items:
                self.delete_multiple_characters(selected_items)
        
        # 다른 위젯에 포커스가 있어도 페이지가 선택되어 있으면 페이지 삭제
        elif self.current_index >= 0:
            self.delete_selected_character()
    
    def delete_multiple_books(self, selected_items):
        """선택된 여러 북을 삭제합니다."""
        if not selected_items:
            return
            
        book_names = []
        for item in selected_items:
            name = item.data(Qt.UserRole)
            if name:
                book_names.append(name)
        
        if not book_names:
            return
            
        # 삭제 확인 대화상자
        count = len(book_names)
        if count == 1:
            message = f"'{book_names[0]}' 북을 삭제하시겠습니까?"
        else:
            message = f"선택된 {count}개의 북을 삭제하시겠습니까?"
            
        reply = QMessageBox.question(
            self, 
            "북 삭제 확인",
            f"{message}\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes  # Enter 키로 삭제 확인 가능
        )
        
        if reply == QMessageBox.Yes:
            # 현재 선택된 북이 삭제 목록에 있는지 확인
            current_book_deleted = self.current_book in book_names
            
            # 북들 삭제
            for name in book_names:
                if name in self.state.books:
                    del self.state.books[name]
            
            # 리스트에서 아이템들 제거
            for item in selected_items:
                row = self.book_list.row(item)
                self.book_list.takeItem(row)
            
            # 현재 선택된 북이 삭제된 경우 상태 초기화
            if current_book_deleted:
                self.current_book = None
                self.state.characters = []
                self.char_list.clear()
                if hasattr(self, 'name_input'):
                    self.name_input.clear()
                if hasattr(self, 'tag_input'):
                    self.tag_input.clear()
                if hasattr(self, 'desc_input'):
                    self.desc_input.clear()
                if hasattr(self, 'prompt_input'):
                    self.prompt_input.clear()
                self.image_scene.clear()
            
            # UI 상태 업데이트
            self.update_all_buttons_state()
            self.save_to_file()
            
            # 다른 북이 있고 현재 북이 삭제되었다면 첫 번째 북 선택
            if current_book_deleted and self.book_list.count() > 0:
                self.book_list.setCurrentRow(0)
                self.on_book_selected(0)
    
    def delete_multiple_characters(self, selected_items):
        """선택된 여러 페이지를 삭제합니다."""
        if not selected_items:
            return
            
        page_names = []
        locked_pages = []
        
        for item in selected_items:
            name = item.data(Qt.UserRole)
            if name:
                # 해당 페이지 찾기
                for char in self.state.characters:
                    if char.get("name") == name:
                        if char.get('locked', False):
                            locked_pages.append(name)
                        else:
                            page_names.append(name)
                        break
        
        # 잠금된 페이지가 있으면 경고
        if locked_pages:
            locked_names = ", ".join(locked_pages)
            if page_names:
                reply = QMessageBox.question(
                    self,
                    "일부 삭제 불가",
                    f"다음 페이지들은 잠금되어 있어 삭제할 수 없습니다:\n{locked_names}\n\n나머지 페이지들만 삭제하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            else:
                QMessageBox.warning(
                    self,
                    "삭제 불가",
                    f"선택된 모든 페이지가 잠금되어 있습니다:\n{locked_names}\n\n잠금을 해제한 후 다시 시도해주세요."
                )
                return
        
        if not page_names:
            return
            
        # 삭제 확인 대화상자
        count = len(page_names)
        if count == 1:
            message = f"'{page_names[0]}' 페이지를 삭제하시겠습니까?"
        else:
            message = f"선택된 {count}개의 페이지를 삭제하시겠습니까?"
            
        reply = QMessageBox.question(
            self, 
            "페이지 삭제 확인",
            f"{message}\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes  # Enter 키로 삭제 확인 가능
        )
        
        if reply == QMessageBox.Yes:
            # 페이지들 삭제 (역순으로 삭제하여 인덱스 문제 방지)
            pages_to_delete = []
            for i, char in enumerate(self.state.characters):
                if char.get("name") in page_names:
                    pages_to_delete.append(i)
                    
                    # 이미지 파일 삭제
                    image_path = char.get("image_path")
                    if image_path and os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                        except Exception as e:
                            print(f"이미지 파일 삭제 실패: {e}")
            
            # 역순으로 삭제
            for i in reversed(pages_to_delete):
                del self.state.characters[i]
            
            # 상태 업데이트
            if self.current_book and self.current_book in self.state.books:
                self.state.books[self.current_book]["pages"] = self.state.characters
            
            # UI 업데이트
            self.refresh_character_list()
            
            # 현재 선택된 페이지가 삭제되었는지 확인
            if self.current_index in pages_to_delete or not self.state.characters:
                self.current_index = -1
                if hasattr(self, 'name_input'):
                    self.name_input.clear()
                if hasattr(self, 'tag_input'):
                    self.tag_input.clear()
                if hasattr(self, 'desc_input'):
                    self.desc_input.clear()
                if hasattr(self, 'prompt_input'):
                    self.prompt_input.clear()
                self.image_scene.clear()
                if hasattr(self.image_view, 'drop_hint'):
                    self.image_view.drop_hint.setVisible(True)
            
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
        if self.current_book and self.current_book in self.state.books:
            self.state.books[self.current_book]["pages"] = self.state.characters
        self.refresh_character_list(selected_name=base_name)
        self.save_to_file()
    
    def duplicate_focused_characters(self):
        """포커스된 리스트의 선택된 페이지들을 복제합니다."""
        # 현재 포커스된 위젯 확인
        focused_widget = QApplication.focusWidget()
        
        # 페이지 리스트에 포커스가 있는 경우만 복제
        if focused_widget == self.char_list or self.char_list.isAncestorOf(focused_widget):
            selected_items = self.char_list.selectedItems()
            if selected_items:
                self.duplicate_multiple_characters(selected_items)
        else:
            # 다른 위젯에 포커스가 있으면 기존 단일 복제 방식 사용
            self.duplicate_selected_character()
    
    def duplicate_multiple_characters(self, selected_items):
        """선택된 여러 페이지를 복제합니다."""
        if not selected_items or not self.current_book:
            return
            
        page_names = []
        for item in selected_items:
            name = item.data(Qt.UserRole)
            if name:
                page_names.append(name)
        
        if not page_names:
            return
            
        # 복제할 페이지 데이터들 수집
        pages_to_duplicate = []
        for char in self.state.characters:
            if char.get("name") in page_names:
                pages_to_duplicate.append(char.copy())
        
        if not pages_to_duplicate:
            return
            
        # 기존 페이지 이름들 수집 (중복 방지용)
        existing_names = {char["name"] for char in self.state.characters}
        
        # 새로 생성될 페이지들
        new_pages = []
        
        for original_data in pages_to_duplicate:
            # 이름 중복 방지
            base_name = original_data["name"]
            
            # 새 이름 생성
            for i in range(1, 1000):
                candidate = f"{base_name} ({i})"
                if candidate not in existing_names:
                    base_name = candidate
                    existing_names.add(candidate)  # 중복 방지용 세트에 추가
                    break
                    
            # 새 데이터 생성
            new_data = original_data.copy()
            new_data["name"] = base_name
            
            # 이미지가 있는 경우 복사
            if "image_path" in original_data and os.path.exists(original_data["image_path"]):
                original_path = original_data["image_path"]
                file_name, ext = os.path.splitext(os.path.basename(original_path))
                new_file_name = f"{file_name}_copy{ext}"
                new_path = os.path.join(os.path.dirname(original_path), new_file_name)
                
                # 파일명 중복 방지
                counter = 1
                while os.path.exists(new_path):
                    new_file_name = f"{file_name}_copy{counter}{ext}"
                    new_path = os.path.join(os.path.dirname(original_path), new_file_name)
                    counter += 1
                
                try:
                    shutil.copy2(original_path, new_path)
                    new_data["image_path"] = new_path
                except Exception as e:
                    print(f"이미지 복사 실패: {e}")
                    new_data["image_path"] = ""
            
            new_pages.append(new_data)
        
        # 새 페이지들 추가
        self.state.characters.extend(new_pages)
        
        # 정렬 모드가 커스텀이 아닌 경우 정렬 적용
        if not self.sort_mode_custom:
            from promptbook_features import sort_characters
            self.state.characters = sort_characters(self.state.characters, self.sort_selector.currentText())
        
        # 상태 업데이트 및 저장
        if self.current_book and self.current_book in self.state.books:
            self.state.books[self.current_book]["pages"] = self.state.characters
        
        # 복제된 페이지가 하나인 경우 해당 페이지 선택, 여러 개인 경우 마지막 페이지 선택
        if new_pages:
            selected_name = new_pages[-1]["name"]  # 마지막으로 복제된 페이지 선택
            self.refresh_character_list(selected_name=selected_name)
        else:
            self.refresh_character_list()
            
        self.save_to_file()
        
        # 복제 완료 메시지
        count = len(new_pages)
        if count == 1:
            message = "1개 페이지가 복제되었습니다."
        else:
            message = f"{count}개 페이지가 복제되었습니다."
        
        if hasattr(self, 'duplicate_button'):
            QToolTip.showText(
                self.duplicate_button.mapToGlobal(self.duplicate_button.rect().center()), 
                message
            )

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
            if self.current_book and self.current_book in self.state.books:
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
    
    def rename_focused_item(self):
        """현재 포커스된 리스트에 따라 북 또는 페이지 이름 변경"""
        # 현재 포커스된 위젯 확인
        focused_widget = QApplication.focusWidget()
        
        # 북 리스트에 포커스가 있는 경우
        if focused_widget == self.book_list or self.book_list.isAncestorOf(focused_widget):
            current_item = self.book_list.currentItem()
            if current_item:
                self.rename_book_dialog(current_item)
        
        # 페이지 리스트에 포커스가 있는 경우
        elif focused_widget == self.char_list or self.char_list.isAncestorOf(focused_widget):
            current_item = self.char_list.currentItem()
            if current_item:
                self.rename_character_dialog(current_item)
    
    def rename_character_dialog(self, item):
        """페이지 이름 변경 대화상자"""
        old_name = item.data(Qt.UserRole)
        if not old_name:
            return
            
        new_name, ok = QInputDialog.getText(
            self, 
            "페이지 이름 변경", 
            "새 이름을 입력하세요:", 
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            # 중복 이름 확인
            existing_names = {char["name"] for char in self.state.characters if char["name"] != old_name}
            if new_name in existing_names:
                QMessageBox.warning(self, "이름 중복", "이미 존재하는 페이지 이름입니다.")
                return
            
            # 페이지 데이터 업데이트
            for char in self.state.characters:
                if char["name"] == old_name:
                    char["name"] = new_name
                    break
            
            # UI 업데이트
            self.refresh_character_list(selected_name=new_name)
            self.save_to_file()
    
    def handle_book_reorder(self):
        """북 순서 변경 처리"""
        print("[DEBUG] handle_book_reorder 호출됨")
        self.book_sort_custom = True
        
        # 새로운 북 순서 생성
        new_book_order = {}
        for i in range(self.book_list.count()):
            item = self.book_list.item(i)
            book_name = item.data(Qt.UserRole)
            if book_name in self.state.books:
                new_book_order[book_name] = self.state.books[book_name]
        
        # 순서 업데이트
        self.state.books = new_book_order
        print("[DEBUG] 새로운 북 순서로 저장됨")
        self.save_to_file()

    def apply_theme(self, theme_name):
        """테마를 적용합니다."""
        if theme_name not in self.THEMES:
            return
            
        self.current_theme = theme_name
        theme = self.THEMES[theme_name]
        
        # 전체 애플리케이션 스타일시트 적용
        style = f"""
        QMainWindow {{
            background-color: {theme['background']};
            color: {theme['text']};
            border: 2px solid {theme['border']};
            border-radius: 12px;
        }}
        
        QWidget {{
            background-color: {theme['background']};
            color: {theme['text']};
        }}
        
        QLabel {{
            color: {theme['text']};
            background-color: transparent;
        }}
        
        QLineEdit, CustomLineEdit {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            padding: 4px;
            border-radius: 3px;
        }}
        
        QLineEdit:focus, CustomLineEdit:focus {{
            border: 2px solid {theme['primary']};
        }}
        
        QTextEdit {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            padding: 4px;
            border-radius: 3px;
        }}
        
        QTextEdit:focus {{
            border: 2px solid {theme['primary']};
        }}
        
        QPushButton {{
            background-color: {theme['button']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            padding: 6px 12px;
            border-radius: 3px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {theme['button_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {theme['primary']};
        }}
        
        QPushButton:disabled {{
            background-color: {theme['surface']};
            color: {theme['text_secondary']};
        }}
        
        QListWidget {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            outline: none;
            border-radius: 3px;
        }}
        
        QListWidget::item {{
            background-color: transparent;
            border: none;
            padding: 2px;
        }}
        
        QListWidget::item:selected {{
            background-color: {theme['selected']};
            color: white;
        }}"""
        
        # 네온 테마용 특별 효과
        if theme_name in ["블루 네온", "핑크 네온"]:
            # 네온 윈도우 테두리
            style = style.replace(
                f"border: 2px solid {theme['border']};",
                f"border: 3px solid {theme['primary']};"
            )
            
            # 네온 타이틀 바 스타일
            title_bar_style = f"""
            QWidget#titleBar {{
                background-color: {theme['background']};
                border-bottom: 3px solid {theme['primary']};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            
            QLabel#titleLabel {{
                color: {theme['primary']};
                background-color: transparent;
                font-weight: bold;
                font-size: 14px;
            }}
            """
            
            style += title_bar_style
            style += f"""
        QPushButton {{
            background-color: {theme['button']};
            border: 3px solid {theme['primary']};
            color: {theme['text']};
            padding: 6px 12px;
            border-radius: 5px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {theme['button_hover']};
            border: 3px solid {theme['primary']};
            color: {theme['primary']};
        }}
        
        QPushButton:pressed {{
            background-color: {theme['primary']};
            color: black;
            border: 3px solid {theme['primary']};
        }}
        
        QListWidget::item:selected {{
            background-color: {theme['selected']};
            color: black;
            border: 2px solid {theme['primary']};
            font-weight: bold;
        }}
        
        QLineEdit, QTextEdit, CustomLineEdit {{
            background-color: {theme['button']};
            border: 2px solid {theme['border']};
            color: {theme['text']};
            padding: 4px;
            border-radius: 3px;
        }}
        
        QLineEdit:focus, QTextEdit:focus, CustomLineEdit:focus {{
            border: 3px solid {theme['primary']};
            background-color: {theme['button']};
        }}
        
        QPushButton:disabled {{
            background-color: {theme['background']};
            border: 1px solid #333333;
            color: #555555;
            font-weight: normal;
        }}
        
        QSplitter::handle:horizontal {{
            width: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {theme['background']}, 
                stop:0.5 {theme['primary']}, 
                stop:1 {theme['background']});
            border: 2px solid {theme['primary']};
        }}
        
        QSplitter::handle:horizontal:hover {{
            background: {theme['primary']};
            border: 2px solid {theme['primary']};
        }}
        
        QSplitter::handle:vertical {{
            height: 10px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {theme['background']}, 
                stop:0.5 {theme['primary']}, 
                stop:1 {theme['background']});
            border: 2px solid {theme['primary']};
        }}
        
        QSplitter::handle:vertical:hover {{
            background: {theme['primary']};
            border: 2px solid {theme['primary']};
        }}"""
        
        style += """
        
        QListWidget::item:hover {{
            background-color: {theme['hover']};
        }}
        
        QComboBox {{
            background-color: {theme['button']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            padding: 4px 8px;
            border-radius: 3px;
        }}
        
        QComboBox:hover {{
            background-color: {theme['button_hover']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {theme['text']};
            margin-right: 6px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            selection-background-color: {theme['selected']};
        }}
        
        QCheckBox {{
            color: {theme['text']};
            spacing: 5px;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {theme['border']};
            border-radius: 2px;
            background-color: {theme['surface']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {theme['primary']};
            image: none;
        }}
        
        QCheckBox::indicator:checked:after {{
            content: "✓";
            color: white;
            font-weight: bold;
        }}
        
        QScrollBar:vertical {{
            background-color: {theme['surface']};
            width: 12px;
            border: none;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {theme['border']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {theme['text_secondary']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background-color: {theme['surface']};
            height: 12px;
            border: none;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {theme['border']};
            border-radius: 6px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {theme['text_secondary']};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        QMenuBar {{
            background-color: {theme['surface']};
            color: {theme['text']};
            border-bottom: 1px solid {theme['border']};
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 3px;
            margin: 2px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QMenuBar::item:hover {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QMenuBar::item:pressed {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QMenu {{
            background-color: {theme['surface']};
            color: {theme['text']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
        }}
        
        QMenu::item {{
            background-color: transparent;
            padding: 6px 20px;
            border: none;
            margin: 1px;
            border-radius: 2px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QMenu::item:hover {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {theme['border']};
            margin: 2px 0px;
        }}
        
        QMenu QMenu {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
        }}
        
        QMenu QMenu::item {{
            background-color: transparent;
            padding: 6px 20px;
            border: none;
            margin: 1px;
            border-radius: 2px;
        }}
        
        QMenu QMenu::item:selected {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QMenu QMenu::item:hover {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QSplitter::handle {{
            background-color: {theme['border']};
            border: 1px solid {theme['border']};
        }}
        
        QSplitter::handle:horizontal {{
            width: 8px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {theme['surface']}, 
                stop:0.5 {theme['border']}, 
                stop:1 {theme['surface']});
            border-left: 1px solid {theme['border']};
            border-right: 1px solid {theme['border']};
        }}
        
        QSplitter::handle:horizontal:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {theme['hover']}, 
                stop:0.5 {theme['primary']}, 
                stop:1 {theme['hover']});
        }}
        
        QSplitter::handle:vertical {{
            height: 8px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {theme['surface']}, 
                stop:0.5 {theme['border']}, 
                stop:1 {theme['surface']});
            border-top: 1px solid {theme['border']};
            border-bottom: 1px solid {theme['border']};
        }}
        
        QSplitter::handle:vertical:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {theme['hover']}, 
                stop:0.5 {theme['primary']}, 
                stop:1 {theme['hover']});
        }}
        
        QGraphicsView {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            border-radius: 3px;
        }}
        """
        
        # 커스텀 타이틀 바 스타일 추가
        title_bar_style = f"""
        QWidget#titleBar {{
            background-color: {theme['surface']};
            border-bottom: 1px solid {theme['border']};
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
        }}
        
        QLabel#titleLabel {{
            color: {theme['text']};
            background-color: transparent;
            font-weight: bold;
            font-size: 14px;
        }}
        """
        
        style += title_bar_style
        
        self.setStyleSheet(style)
        
        # 타이틀 바 버튼 스타일 업데이트 (테마별 색상 적용)
        if hasattr(self, 'minimize_btn'):
            if theme_name in ["블루 네온", "핑크 네온"]:
                # 네온 테마용 타이틀 바 버튼
                button_style = f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px solid {theme['primary']};
                        color: {theme['primary']};
                        font-size: 12px;
                        font-weight: bold;
                        padding: 5px 8px;
                        border-radius: 3px;
                        margin: 2px;
                    }}
                    QPushButton:hover {{
                        background-color: {theme['primary']};
                        color: black;
                    }}
                """
                
                close_button_style = f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px solid #ff0040;
                        color: #ff0040;
                        font-size: 12px;
                        font-weight: bold;
                        padding: 5px 8px;
                        border-radius: 3px;
                        margin: 2px;
                    }}
                    QPushButton:hover {{
                        background-color: #ff0040;
                        color: white;
                    }}
                """
            else:
                # 일반 테마용 타이틀 바 버튼
                button_style = f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        color: {theme['text']};
                        font-size: 14px;
                        font-weight: bold;
                        padding: 5px 10px;
                        border-radius: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {theme['hover']};
                    }}
                """
                
                close_button_style = button_style + """
                    QPushButton:hover {
                        background-color: #e81123;
                        color: white;
                    }
                """
            
            self.minimize_btn.setStyleSheet(button_style)
            self.maximize_btn.setStyleSheet(button_style)
            self.close_btn.setStyleSheet(close_button_style)
            
            # 메뉴 버튼도 동일한 스타일 적용
            if hasattr(self, 'menu_btn'):
                if theme_name in ["블루 네온", "핑크 네온"]:
                    menu_button_style = f"""
                        QPushButton {{
                            background-color: transparent;
                            border: 1px solid {theme['primary']};
                            color: {theme['primary']};
                            font-size: 14px;
                            font-weight: bold;
                            padding: 3px;
                            border-radius: 3px;
                            margin: 2px;
                        }}
                        QPushButton:hover {{
                            background-color: {theme['primary']};
                            color: black;
                        }}
                    """
                else:
                    menu_button_style = f"""
                        QPushButton {{
                            background-color: transparent;
                            border: none;
                            color: {theme['text']};
                            font-size: 16px;
                            font-weight: bold;
                            padding: 3px;
                            border-radius: 0px;
                        }}
                        QPushButton:hover {{
                            background-color: {theme['hover']};
                        }}
                    """
                self.menu_btn.setStyleSheet(menu_button_style)
        
        # 이미지 뷰포트 배경색 직접 설정
        if hasattr(self, 'image_view'):
            # QGraphicsView 배경 브러시 설정
            background_color = QColor(theme['surface'])
            self.image_view.setBackgroundBrush(QBrush(background_color))
            
            # 씬 배경색도 설정
            if hasattr(self, 'image_scene'):
                self.image_scene.setBackgroundBrush(QBrush(background_color))
            
            # 드롭 힌트 스타일 업데이트
            self.image_view.update_drop_hint_style(theme)
        
        # 테마 액션 상태 업데이트 (theme_group이 있는 경우에만)
        if hasattr(self, 'theme_group') and self.theme_group:
            for action in self.theme_group.actions():
                action.setChecked(action.text() == theme_name)
        
        # UI 설정에 테마 저장
        self.save_ui_settings()
        
        print(f"[DEBUG] 테마 적용됨: {theme_name}")

    def get_menu_style(self):
        """현재 테마에 맞는 메뉴 스타일 반환"""
        current_theme = getattr(self, 'current_theme', '어두운 모드')
        theme = self.THEMES.get(current_theme, self.THEMES['어두운 모드'])
        
        return f"""
            QMenu {{
                background-color: {theme['surface']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: 8px 20px;
                border: none;
                margin: 1px;
                border-radius: 3px;
            }}
            QMenu::item:hover {{
                background-color: {theme['primary']};
                color: white;
            }}
            QMenu::item:selected {{
                background-color: {theme['primary']};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {theme['border']};
                margin: 4px 0px;
            }}
        """

    def setup_shortcuts(self):
        """단축키를 설정합니다."""
        # Ctrl+S: 현재 페이지 저장
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(lambda: (
            self.save_current_character(), 
            QToolTip.showText(
                self.save_button.mapToGlobal(self.save_button.rect().center()), 
                "페이지가 저장되었습니다."
            ) if hasattr(self, 'save_button') else None
        ))
        
        # Ctrl+N: 새 페이지 추가
        self.new_page_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.new_page_shortcut.activated.connect(self.add_character)
        
        # Ctrl+D: 페이지 복제 (다중 선택 지원)
        self.duplicate_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.duplicate_shortcut.activated.connect(self.duplicate_focused_characters)
        
        # Delete: 포커스된 리스트에 따라 북 또는 페이지 삭제 (다중 선택 지원)
        self.delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        self.delete_shortcut.activated.connect(self.delete_focused_item)
        
        # F2: 포커스된 리스트에 따라 북 또는 페이지 이름 변경
        self.rename_shortcut = QShortcut(QKeySequence("F2"), self)
        self.rename_shortcut.activated.connect(self.rename_focused_item)
        
        print("[DEBUG] 단축키 설정 완료")
    
    def setup_resize_handles(self):
        """투명한 리사이즈 핸들들 설정"""
        handle_size = 8  # 핸들 두께
        corner_size = 15  # 모서리 핸들 크기
        
        # 8개 방향의 핸들 생성
        directions = [
            ('top', 0, 0, 0, handle_size),
            ('bottom', 0, 0, 0, handle_size),
            ('left', 0, 0, handle_size, 0),
            ('right', 0, 0, handle_size, 0),
            ('top-left', 0, 0, corner_size, corner_size),
            ('top-right', 0, 0, corner_size, corner_size),
            ('bottom-left', 0, 0, corner_size, corner_size),
            ('bottom-right', 0, 0, corner_size, corner_size)
        ]
        
        for direction, _, _, width, height in directions:
            handle = ResizeHandle(direction, self)
            if width > 0:
                handle.setFixedWidth(width)
            if height > 0:
                handle.setFixedHeight(height)
            self.resize_handles[direction] = handle
            handle.show()
        
        # 초기 위치 설정
        self.update_resize_handles()
    
    def update_resize_handles(self):
        """리사이즈 핸들들의 위치 업데이트"""
        if not hasattr(self, 'resize_handles'):
            return
            
        rect = self.rect()
        handle_size = 8
        corner_size = 15
        
        # 최대화된 상태에서는 핸들 숨기기
        visible = not self.isMaximized()
        
        for direction, handle in self.resize_handles.items():
            handle.setVisible(visible)
            if not visible:
                continue
                
            if direction == 'top':
                handle.setGeometry(corner_size, 0, rect.width() - 2 * corner_size, handle_size)
            elif direction == 'bottom':
                handle.setGeometry(corner_size, rect.height() - handle_size, 
                                 rect.width() - 2 * corner_size, handle_size)
            elif direction == 'left':
                handle.setGeometry(0, corner_size, handle_size, rect.height() - 2 * corner_size)
            elif direction == 'right':
                handle.setGeometry(rect.width() - handle_size, corner_size, 
                                 handle_size, rect.height() - 2 * corner_size)
            elif direction == 'top-left':
                handle.setGeometry(0, 0, corner_size, corner_size)
            elif direction == 'top-right':
                handle.setGeometry(rect.width() - corner_size, 0, corner_size, corner_size)
            elif direction == 'bottom-left':
                handle.setGeometry(0, rect.height() - corner_size, corner_size, corner_size)
            elif direction == 'bottom-right':
                handle.setGeometry(rect.width() - corner_size, rect.height() - corner_size, 
                                 corner_size, corner_size)

    def setup_theme_actions(self):
        """테마 액션들을 미리 설정"""
        # 테마별 이모지 매핑
        theme_emojis = {
            "어두운 모드": "🌙",
            "밝은 모드": "☀️",
            "파란 바다": "🌊",
            "숲속": "🌲",
            "보라 우주": "🌌",
            "황혼": "🌅",
            "벚꽃": "🌸",
            "민트": "🍃",
            "블루 네온": "⚡",
            "핑크 네온": "💖"
        }
        
        for theme_name in self.THEMES.keys():
            emoji = theme_emojis.get(theme_name, "🎨")
            display_name = f"{emoji} {theme_name}"
            
            theme_action = QAction(display_name, self)
            theme_action.setCheckable(True)
            theme_action.triggered.connect(lambda checked, name=theme_name: self.apply_theme(name))
            self.theme_group.addAction(theme_action)
            
            # 현재 테마 설정
            if theme_name == self.current_theme:
                theme_action.setChecked(True)

    def setup_custom_title_bar(self, main_layout):
        """커스텀 타이틀 바를 설정합니다."""
        # 타이틀 바 위젯
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(35)
        self.title_bar.setObjectName("titleBar")
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(0, 0, 5, 0)  # 왼쪽 여백을 0으로 설정
        title_layout.setSpacing(5)
        
        # 메뉴 버튼 (햄버거 메뉴)
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(35, 35)  # 버튼 크기를 타이틀바 높이에 맞춤
        self.menu_btn.setObjectName("menuButton")
        self.menu_btn.setToolTip("메뉴")
        self.menu_btn.clicked.connect(self.show_main_menu)
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        # 타이틀 라벨
        title_text = f"프롬프트 북 {self.VERSION}"  # 버전 정보 추가
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)  # 중앙 정렬 설정
        self.title_label.setMinimumWidth(200)  # 최소 너비 설정
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 0 10px;
            }
        """)

        # Donate 버튼
        self.donate_btn = QPushButton("💖 Donate")
        self.donate_btn.setToolTip("카카오페이로 후원해주세요!")
        self.donate_btn.clicked.connect(self.show_kakao_info)
        
        # 윈도우 컨트롤 버튼들
        self.minimize_btn = QPushButton("－")
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.minimize_btn.setToolTip("최소화")
        
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.maximize_btn.setToolTip("최대화")
        
        self.close_btn = QPushButton("✕")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setToolTip("닫기")
        
        # 버튼 스타일 설정
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 14px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """
        
        close_button_style = button_style + """
            QPushButton:hover {
                background-color: #e81123;
                color: white;
            }
        """
        
        self.donate_btn.setStyleSheet(button_style)
        self.minimize_btn.setStyleSheet(button_style)
        self.maximize_btn.setStyleSheet(button_style)
        self.close_btn.setStyleSheet(close_button_style)
        
        # 레이아웃에 위젯 추가
        title_layout.addWidget(self.menu_btn)
        title_layout.addStretch()  # 왼쪽 여백
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()  # 오른쪽 여백
        title_layout.addWidget(self.donate_btn)
        title_layout.addWidget(self.minimize_btn)
        title_layout.addWidget(self.maximize_btn)
        title_layout.addWidget(self.close_btn)
        
        main_layout.addWidget(self.title_bar)
    
    def toggle_maximize(self):
        """윈도우 최대화/복원 토글"""
        if self.isMaximized():
            self.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.showMaximized()
            self.maximize_btn.setText("❐")
        
        # 핸들 상태 업데이트
        self.update_resize_handles()
    
    def mousePressEvent(self, event):
        """마우스 프레스 이벤트 - 타이틀바에서만 드래그 허용"""
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            
            # 타이틀바 영역에서만 드래그 시작 허용
            if hasattr(self, 'title_bar') and self.title_bar:
                title_bar_global_pos = self.title_bar.mapFromGlobal(event.globalPosition().toPoint())
                if self.title_bar.rect().contains(title_bar_global_pos):
                    self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    event.accept()
                    return
            
            # 리사이즈는 투명 핸들에서만 처리하도록 함
            # 기존 마우스 이벤트 기반 리사이즈는 비활성화
            event.ignore()
    
    def mouseMoveEvent(self, event):
        """마우스 무브 이벤트 - 타이틀바 드래그만 처리"""
        # 타이틀바 드래그 중인 경우만 처리
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            return
        
        # 리사이즈와 커서 변경은 투명 핸들에서 처리하므로 여기서는 제거
    
    def mouseReleaseEvent(self, event):
        """마우스 릴리즈 이벤트 - 드래그 종료"""
        self.drag_position = None
    
    def leaveEvent(self, event):
        """마우스가 윈도우를 벗어날 때"""
        super().leaveEvent(event)
    

    

    
    def mouseDoubleClickEvent(self, event):
        """더블클릭으로 최대화/복원"""
        if event.button() == Qt.LeftButton and self.title_bar.rect().contains(
            self.title_bar.mapFromGlobal(event.globalPosition().toPoint())
        ):
            self.toggle_maximize()
            event.accept()
    
    def resizeEvent(self, event):
        """리사이즈 이벤트 - 둥근 모서리 마스크 적용 및 핸들 위치 업데이트"""
        super().resizeEvent(event)
        self.apply_rounded_corners()
        self.update_resize_handles()
    
    def showEvent(self, event):
        """쇼 이벤트 - 초기 둥근 모서리 적용"""
        super().showEvent(event)
        self.apply_rounded_corners()
    
    def changeEvent(self, event):
        """윈도우 상태 변경 이벤트 - 핸들 상태 업데이트"""
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            # 핸들 상태 업데이트
            self.update_resize_handles()
    
    def apply_rounded_corners(self):
        """윈도우에 둥근 모서리 마스크 적용"""
        # 윈도우 크기 가져오기
        rect = self.rect()
        
        # 둥근 사각형 경로 생성
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.border_radius, self.border_radius)
        
        # 경로를 QRegion으로 변환
        region = QRegion(path.toFillPolygon().toPolygon())
        
        # 윈도우 마스크 설정
        self.setMask(region)
    
    def show_main_menu(self):
        """메인 메뉴 표시"""
        menu = QMenu(self)
        
        # 메뉴 스타일 적용
        menu_style = self.get_menu_style()
        menu.setStyleSheet(menu_style)
        
        # 파일 메뉴
        file_menu = menu.addMenu("📁 파일")
        file_menu.setStyleSheet(menu_style)  # 서브메뉴에도 적용
        
        # 선택된 북 저장하기
        save_book_action = QAction("💾 선택된 북 저장하기", self)
        save_book_action.triggered.connect(self.save_selected_book)
        file_menu.addAction(save_book_action)
        
        # 저장된 북 불러오기
        load_book_action = QAction("📂 저장된 북 불러오기", self)
        load_book_action.triggered.connect(self.load_saved_book)
        file_menu.addAction(load_book_action)
        
        # 테마 메뉴
        theme_menu = menu.addMenu("🎨 테마")
        theme_menu.setStyleSheet(menu_style)  # 서브메뉴에도 적용
        
        # 미리 생성된 테마 액션들을 메뉴에 추가
        for action in self.theme_group.actions():
            theme_menu.addAction(action)
            # 현재 테마 체크 상태 업데이트
            if action.text() == self.current_theme:
                action.setChecked(True)
            else:
                action.setChecked(False)
        
        # 도움말 메뉴
        menu.addSeparator()
        
        # 단축키 안내
        shortcuts_action = QAction("⌨️ 단축키 안내", self)
        shortcuts_action.triggered.connect(self.show_shortcuts_help)
        menu.addAction(shortcuts_action)
        
        # 메뉴 표시 위치 계산 (메뉴 버튼 아래쪽)
        button_pos = self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft())
        menu.exec_(button_pos)

    def show_donate_options(self):
        """후원 옵션 메뉴 표시"""
        menu = QMenu(self)
        
        # 메뉴 스타일 적용
        menu_style = self.get_menu_style()
        menu.setStyleSheet(menu_style)
        
        # 후원 옵션들
        paypal_action = QAction("💳 PayPal", self)
        paypal_action.triggered.connect(lambda: self.open_url("https://paypal.me/qohqohqoh"))
        menu.addAction(paypal_action)
        
        menu.addSeparator()
        
        # 국내 후원 옵션
        kakao_action = QAction("💛 카카오페이", self)
        kakao_action.triggered.connect(self.show_kakao_info)
        menu.addAction(kakao_action)
        
        # 메뉴 표시 위치 계산
        button_pos = self.donate_btn.mapToGlobal(self.donate_btn.rect().bottomLeft())
        menu.exec_(button_pos)
    
    def open_url(self, url):
        """URL을 기본 브라우저에서 열기"""
        import webbrowser
        webbrowser.open(url)
    
    def show_kakao_info(self):
        """카카오페이 QR코드 팝업창 표시"""
        import os
        
        image_path = "KakaoPay.png"
        
        if not os.path.exists(image_path):
            QMessageBox.warning(
                self, 
                "카카오페이 QR코드", 
                f"QR코드 이미지 파일을 찾을 수 없습니다.\n경로: {image_path}\n\n파일을 확인해주세요! 💛"
            )
            return
        
        # 커스텀 팝업 다이얼로그 생성
        dialog = QDialog(self)
        dialog.setWindowTitle("💛 카카오페이 후원")
        dialog.setModal(True)
        dialog.setFixedSize(400, 550)
        
        # 윈도우 플래그 설정으로 떨림 방지
        dialog.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        
        # 렌더링 최적화 속성 설정
        dialog.setAttribute(Qt.WA_OpaquePaintEvent, True)
        dialog.setAttribute(Qt.WA_NoSystemBackground, False)
        dialog.setAttribute(Qt.WA_StaticContents, True)
        
        # 현재 테마 적용
        current_theme = getattr(self, 'current_theme', '어두운 모드')
        theme = self.THEMES.get(current_theme, self.THEMES['어두운 모드'])
        
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['background']};
                color: {theme['text']};
                border: 2px solid {theme['border']};
                border-radius: 10px;
            }}
            QLabel {{
                color: {theme['text']};
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {theme['button']};
                border: 1px solid {theme['border']};
                color: {theme['text']};
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 메시지 라벨
        message_label = QLabel()
        message_label.setText(
            
            "주기적인 카페인 주입이 필요합니다.☕"
        )
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(message_label)
        
        # QR코드 이미지 표시
        try:
            # 고품질 이미지 리더 사용
            reader = QImageReader(image_path)
            reader.setAutoTransform(True)
            reader.setQuality(100)
            
            # 고품질 이미지 로드
            image = reader.read()
            if not image.isNull():
                # 고품질 픽스맵 생성
                pixmap = QPixmap.fromImage(image, Qt.PreferDither | Qt.AutoColor)
                
                # 이미지 크기 조정 (최대 300x300, 고품질 스케일링)
                scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                image_label = QLabel()
                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setMinimumSize(310, 310)  # 고정 크기로 레이아웃 안정화
                image_label.setMaximumSize(310, 310)
                image_label.setScaledContents(False)  # 자동 스케일링 비활성화
                
                # 이미지 캐싱 및 렌더링 최적화
                image_label.setAttribute(Qt.WA_OpaquePaintEvent, True)
                image_label.setAttribute(Qt.WA_NoSystemBackground, False)
                
                image_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #cccccc; 
                        border-radius: 5px; 
                        padding: 5px; 
                        background-color: white;
                        qproperty-alignment: AlignCenter;
                    }
                """)
                
                # 이미지를 중앙정렬하여 레이아웃에 추가
                image_layout = QHBoxLayout()
                image_layout.addStretch()
                image_layout.addWidget(image_label)
                image_layout.addStretch()
                layout.addLayout(image_layout)
            else:
                error_label = QLabel("QR코드 이미지를 불러올 수 없습니다.")
                error_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(error_label)
        except Exception as e:
            error_label = QLabel(f"이미지 로드 오류: {str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
        
        # 감사 메시지
        thanks_label = QLabel("💖 후원해주셔서 정말 감사합니다! 💖")
        thanks_label.setAlignment(Qt.AlignCenter)
        thanks_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #ff6b9d;")
        layout.addWidget(thanks_label)
        
        # 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        # 다이얼로그 표시
        dialog.exec()
    
    def cleanup_unused_images(self):
        """사용되지 않는 이미지를 휴지통으로 이동합니다."""
        if send2trash is None:
            QMessageBox.warning(self, "오류", "send2trash 모듈이 설치되지 않았습니다.\npip install send2trash로 설치해 주세요.")
            return
            
        # images 폴더가 존재하지 않으면 아무것도 안 함
        images_dir = "images"
        if not os.path.exists(images_dir):
            return
        
        # 현재 사용 중인 이미지 경로들 수집
        used_images = set()
        for book_name, book_data in self.state.books.items():
            pages = book_data.get("pages", [])
            for page in pages:
                image_path = page.get("image_path", "")
                if image_path and os.path.exists(image_path):
                    # 절대 경로로 변환하여 비교
                    used_images.add(os.path.abspath(image_path))
        
        # images 폴더의 모든 이미지 파일 찾기
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp'}
        all_images = []
        
        for root, dirs, files in os.walk(images_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.splitext(file)[1].lower() in image_extensions:
                    all_images.append(os.path.abspath(file_path))
        
        # 사용되지 않는 이미지 찾기
        unused_images = []
        for image_path in all_images:
            if image_path not in used_images:
                unused_images.append(image_path)
        
        if not unused_images:
            QMessageBox.information(self, "정리 완료", "사용되지 않는 이미지가 없습니다.")
            return
        
        # 사용자에게 확인
        count = len(unused_images)
        file_list = "\n".join([os.path.basename(path) for path in unused_images[:10]])
        if count > 10:
            file_list += f"\n... 및 {count - 10}개 더"
            
        reply = QMessageBox.question(
            self,
            "이미지 정리 확인",
            f"사용되지 않는 이미지 {count}개를 휴지통으로 이동하시겠습니까?\n\n"
            f"이동될 파일들:\n{file_list}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            failed_files = []
            
            for image_path in unused_images:
                try:
                    send2trash(image_path)
                    success_count += 1
                    print(f"[DEBUG] 휴지통으로 이동: {image_path}")
                except Exception as e:
                    failed_files.append(os.path.basename(image_path))
                    print(f"[ERROR] 휴지통 이동 실패: {image_path} - {e}")
            
            # 결과 보고
            if failed_files:
                QMessageBox.warning(
                    self,
                    "정리 부분 완료",
                    f"{success_count}개의 이미지가 휴지통으로 이동되었습니다.\n"
                    f"실패한 파일 {len(failed_files)}개:\n" + 
                    "\n".join(failed_files[:5]) + 
                    (f"\n... 및 {len(failed_files) - 5}개 더" if len(failed_files) > 5 else "")
                )
            else:
                QMessageBox.information(
                    self,
                    "정리 완료",
                    f"{success_count}개의 사용되지 않는 이미지가 휴지통으로 이동되었습니다."
                )

    def cleanup_unused_images_silent(self):
        """조용히 사용되지 않는 이미지를 휴지통으로 이동 (확인 대화상자 없음)"""
        if send2trash is None:
            return
            
        try:
            # images 폴더가 존재하지 않으면 아무것도 안 함
            images_dir = "images"
            if not os.path.exists(images_dir):
                return
            
            # 현재 사용 중인 이미지 경로들 수집
            used_images = set()
            for book_name, book_data in self.state.books.items():
                pages = book_data.get("pages", [])
                for page in pages:
                    image_path = page.get("image_path", "")
                    if image_path and os.path.exists(image_path):
                        # 절대 경로로 변환하여 비교
                        used_images.add(os.path.abspath(image_path))
            
            # images 폴더의 모든 이미지 파일 찾기
            image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp'}
            unused_images = []
            
            for root, dirs, files in os.walk(images_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.splitext(file)[1].lower() in image_extensions:
                        abs_path = os.path.abspath(file_path)
                        if abs_path not in used_images:
                            unused_images.append(abs_path)
            
            # 사용되지 않는 이미지를 휴지통으로 이동
            for image_path in unused_images:
                try:
                    send2trash(image_path)
                    print(f"[DEBUG] 자동 정리: 휴지통으로 이동 - {os.path.basename(image_path)}")
                except Exception as e:
                    print(f"[ERROR] 자동 정리 실패: {image_path} - {e}")
                    
        except Exception as e:
            print(f"[ERROR] 자동 이미지 정리 중 오류: {e}")
    
    def show_shortcuts_help(self):
        """단축키 안내 다이얼로그 표시"""
        dialog = QDialog(self)
        dialog.setWindowTitle("⌨️ 단축키 안내")
        dialog.setModal(True)
        dialog.setFixedSize(600, 500)
        
        # 윈도우 플래그 설정
        dialog.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        
        # 현재 테마 적용
        current_theme = getattr(self, 'current_theme', '어두운 모드')
        theme = self.THEMES.get(current_theme, self.THEMES['어두운 모드'])
        
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['background']};
                color: {theme['text']};
                border: 2px solid {theme['border']};
                border-radius: 10px;
            }}
            QLabel {{
                color: {theme['text']};
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {theme['button']};
                border: 1px solid {theme['border']};
                color: {theme['text']};
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            QScrollArea {{
                background-color: {theme['surface']};
                border: 1px solid {theme['border']};
                border-radius: 5px;
            }}
            QWidget#scrollContent {{
                background-color: {theme['surface']};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title_label = QLabel("⌨️ 프롬프트북 단축키 안내")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 단축키 데이터
        shortcuts_data = [
            {
                "category": "📝 페이지 관리",
                "shortcuts": [
                    ("Ctrl + N", "새 페이지 추가"),
                    ("Ctrl + S", "현재 페이지 저장"),
                    ("Ctrl + D", "페이지 복제 (다중 선택 지원)"),
                    ("Delete", "페이지/북 삭제 (다중 선택 지원)"),
                    ("F2", "페이지/북 이름 변경"),
                ]
            },
            {
                "category": "🔢 다중 선택",
                "shortcuts": [
                    ("Ctrl + 클릭", "개별 항목을 하나씩 선택/해제"),
                    ("Shift + 클릭", "첫 선택부터 클릭 위치까지 범위 선택"),
                    ("Ctrl + A", "모든 항목 선택 (리스트 포커스 시)"),
                ]
            },
            {
                "category": "🖱️ 마우스 조작",
                "shortcuts": [
                    ("더블클릭", "페이지/북 이름 변경"),
                    ("우클릭", "컨텍스트 메뉴 열기"),
                    ("드래그", "정렬 순서 변경 (커스텀 모드)"),
                    ("다중 드래그", "선택된 여러 항목 동시 이동"),
                ]
            },
            {
                "category": "📁 파일 관리",
                "shortcuts": [
                    ("이미지 드래그", "페이지에 이미지 추가"),
                    ("Zip 불러오기", "저장된 북 불러오기"),
                    ("Zip 저장", "현재 북 저장하기"),
                ]
            }
        ]
        
        # 각 카테고리별로 단축키 표시
        for category_data in shortcuts_data:
            # 카테고리 제목
            category_label = QLabel(category_data["category"])
            category_label.setStyleSheet(f"""
                font-size: 16px; 
                font-weight: bold; 
                color: {theme['primary']}; 
                padding: 10px 0px 5px 0px;
            """)
            scroll_layout.addWidget(category_label)
            
            # 단축키 목록
            for shortcut, description in category_data["shortcuts"]:
                shortcut_layout = QHBoxLayout()
                
                # 단축키 라벨
                shortcut_label = QLabel(shortcut)
                shortcut_label.setStyleSheet(f"""
                    background-color: {theme['button']};
                    border: 1px solid {theme['border']};
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-weight: bold;
                    min-width: 120px;
                """)
                shortcut_label.setAlignment(Qt.AlignCenter)
                shortcut_label.setFixedWidth(140)
                
                # 설명 라벨
                desc_label = QLabel(description)
                desc_label.setStyleSheet("padding: 4px 8px;")
                
                shortcut_layout.addWidget(shortcut_label)
                shortcut_layout.addWidget(desc_label)
                shortcut_layout.addStretch()
                
                scroll_layout.addLayout(shortcut_layout)
            
            # 카테고리 간 간격
            scroll_layout.addSpacing(10)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        # 다이얼로그 표시
        dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PromptBook()
    window.show()
    sys.exit(app.exec())
