DARK_STYLE = """
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
}

QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
}

QListWidget {
    background-color: #1e1e1e;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    color: #ffffff;
    padding: 4px;
}

QListWidget::item {
    padding: 4px;
    border-radius: 2px;
}

QListWidget::item:selected {
    background-color: #3c3c3c;
}

QListWidget::item:hover {
    background-color: #323232;
}

QLineEdit, QTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    color: #ffffff;
    padding: 4px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #5c5c5c;
}

QPushButton {
    background-color: #3c3c3c;
    border: none;
    border-radius: 4px;
    color: #ffffff;
    padding: 6px 12px;
}

QPushButton:hover {
    background-color: #4c4c4c;
}

QPushButton:pressed {
    background-color: #2c2c2c;
}

QComboBox {
    background-color: #3c3c3c;
    border: none;
    border-radius: 4px;
    color: #ffffff;
    padding: 4px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox::down-arrow {
    image: url(down_arrow.png);
    width: 12px;
    height: 12px;
}

QComboBox:hover {
    background-color: #4c4c4c;
}

QLabel {
    color: #ffffff;
}

QScrollBar:vertical {
    border: none;
    background: #2b2b2b;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3c3c3c;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #2b2b2b;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #3c3c3c;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QSplitter::handle {
    background-color: #3c3c3c;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #4c4c4c;
}
""" 