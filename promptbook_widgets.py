from PySide6.QtWidgets import QPlainTextEdit, QGraphicsView, QCompleter, QApplication, QWidget, QHBoxLayout, QLabel
from PySide6.QtGui import QKeyEvent, QPainter, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtCore import Signal

class CustomLineEdit(QPlainTextEdit):
    def __init__(self, completer=None):
        super().__init__()
        self._completer = None
        self.prompt_display_map = {}
        self.set_custom_completer(completer)
        self.textChanged.connect(lambda: self.update_completion(self.toPlainText()))

    def set_custom_completer(self, completer):
        self._completer = completer
        if self._completer:
            self._completer.setWidget(self)
            self._completer.setCompletionMode(QCompleter.PopupCompletion)
            self._completer.setCaseSensitivity(Qt.CaseInsensitive)
            self._completer.activated.connect(lambda display_text: self.insert_completion(self.prompt_display_map.get(display_text, display_text)))

    def update_completion(self, text=''):
        if not self._completer:
            return
        if QApplication.focusWidget() != self:
            self._completer.popup().hide()
            return
        if not self._completer or QApplication.focusWidget() != self:
            self._completer.popup().hide()
            return

        cursor_pos = self.textCursor().position()
        current_text = self.toPlainText()[:cursor_pos]
        last_comma = current_text.rfind(',')
        prefix = current_text[last_comma + 1:].strip() if last_comma != -1 else current_text.strip()

        if prefix:
            self._completer.setCompletionPrefix(prefix)
            popup = self._completer.popup()
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
            
            prefix_start_pos = last_comma + 1 if last_comma != -1 else 0
            cursor = self.textCursor()
            cursor.setPosition(prefix_start_pos)
            rect = self.cursorRect(cursor)
            
            # 팝업 크기 계산
            popup_width = popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width()
            popup_height = min(popup.sizeHint().height(), 200)  # 최대 높이 제한
            
            # 현재 위젯의 전역 좌표
            widget_global_rect = self.mapToGlobal(self.rect().topLeft())
            widget_bottom = widget_global_rect.y() + self.height()
            
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
            
            QTimer.singleShot(0, lambda: (
                popup.move(popup_pos),
                popup.show(),
                popup.raise_()
            ))
        else:
            self._completer.popup().hide()

    def insert_completion(self, completion):
        cursor_pos = self.textCursor().position()
        text_before = self.toPlainText()[:cursor_pos]
        text_after = self.toPlainText()[cursor_pos:]

        last_comma = text_before.rfind(',')
        if last_comma != -1:
            new_text = text_before[:last_comma + 1] + ' ' + completion + ', ' + text_after
        else:
            new_text = completion + ', ' + text_after

        self.setPlainText(new_text)
        new_cursor = self.textCursor()
        new_pos = len(text_before[:last_comma + 1] + ' ' + completion + ', ') if last_comma != -1 else len(completion + ', ')
        new_cursor.setPosition(new_pos)
        self.setTextCursor(new_cursor)

    def keyPressEvent(self, event):
        if self._completer and self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                index = self._completer.popup().currentIndex()
                completion = index.data(Qt.DisplayRole)
                self._completer.activated.emit(completion)
                return
        super().keyPressEvent(event)

class ImageView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        parent = self.parentWidget()
        if hasattr(parent, 'current_index') and 0 <= parent.current_index < len(parent.characters):
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                    parent.characters[parent.current_index]["image_path"] = file_path
                    parent.edited = True
                    parent.update_image_buttons_state()
                    parent.update_image_view(file_path)
                    break

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
        self.star_label.setText("❤️" if is_favorite else "🖤")
    
    def set_name(self, name):
        self.name_label.setText(name)
        self.page_name = name
    
    def set_emoji(self, emoji):
        self.page_label.setText(emoji)
        
    def set_locked(self, is_locked):
        """잠금 상태 설정"""
        self.lock_label.setText("🔒" if is_locked else "")

class ClickableLabel(QLabel):
    """클릭 가능한 라벨 위젯"""
    clicked = Signal()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
