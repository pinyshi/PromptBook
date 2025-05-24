from PySide6.QtWidgets import QGraphicsView, QFrame, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter

class ImageView(QGraphicsView):
    """이미지 뷰어 위젯"""
    
    image_dropped = Signal(str)  # 이미지가 드롭되었을 때의 시그널
    
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
        
        # 드래그 앤 드롭 설정
        self.setAcceptDrops(True)
        
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
        self.update_drop_hint_position()
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
        
    def update_drop_hint_position(self):
        """드래그 앤 드롭 안내 라벨의 위치를 업데이트합니다."""
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
        
    def dragEnterEvent(self, event):
        """드래그 진입 이벤트 처리"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """드롭 이벤트 처리"""
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            file_path = url.toLocalFile()
            self.image_dropped.emit(file_path)
            event.accept()
        else:
            event.ignore() 