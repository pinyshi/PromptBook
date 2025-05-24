# PromptBook

프롬프트북은 AI 프롬프트를 관리하고 구성하기 위한 데스크톱 애플리케이션입니다.

## 주요 기능

- 북 관리: 프롬프트를 북 단위로 구성
- 페이지 관리: 각 북 안에 여러 페이지를 생성하여 프롬프트 관리
- 이미지 지원: 각 페이지에 이미지 첨부 가능
- 태그 시스템: 태그를 사용하여 프롬프트 분류
- 즐겨찾기: 자주 사용하는 프롬프트를 즐겨찾기로 등록
- 자동 저장: 모든 변경사항 자동 저장
- 백업 기능: 데이터 백업 및 복원 지원

## 설치 방법

1. Python 3.8 이상 설치
2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

## 실행 방법

```bash
python promptbook_main.py
```

## 개발 환경 설정

1. 저장소 클론:
```bash
git clone https://github.com/your-username/promptbook.git
cd promptbook
```

2. 가상 환경 생성 및 활성화:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 개발 의존성 설치:
```bash
pip install -r requirements-dev.txt
```

## 테스트 실행

```bash
python -m unittest discover tests
```

## 프로젝트 구조

```
promptbook/
├── promptbook/
│   ├── __init__.py
│   ├── main_window.py
│   ├── state.py
│   ├── features.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── book_handlers.py
│   │   ├── character_handlers.py
│   │   └── event_handlers.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_utils.py
│   │   └── image_utils.py
│   └── widgets/
│       ├── __init__.py
│       ├── book_list_widget.py
│       ├── character_list_widget.py
│       └── character_editor_widget.py
├── tests/
│   ├── __init__.py
│   ├── test_state.py
│   └── test_utils.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## 의존성

- PySide6: Qt 기반 GUI 프레임워크
- Pillow: 이미지 처리 라이브러리

## 라이선스

MIT License

## 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request 