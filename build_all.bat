@echo off
echo 🚀 프롬프트북 & 프롬프트 입력기 빌드 시작...

echo.
echo 📋 버전 정보 추출 중...
powershell -ExecutionPolicy Bypass -File get_version.ps1 > temp_version.txt
set /p VERSION=<temp_version.txt
del temp_version.txt
echo   현재 버전: %VERSION%

echo.
echo 📦 프롬프트북 빌드 중...
pyinstaller PromptBook_Build.spec --clean

echo.
echo 📄 프롬프트 입력기 빌드 중...
pyinstaller PromptInput_Build.spec --clean

echo.
echo 📋 파일 정리 중...
echo   - autocomplete.txt 복사...
copy autocomplete.txt dist\PromptBook\

echo   - PromptInput.exe 이동...
echo     실행 중인 프로세스 확인 중...
taskkill /f /im PromptInput.exe >nul 2>&1
timeout /t 2 /nobreak >nul

if exist dist\PromptInput.exe (
    move dist\PromptInput.exe dist\PromptBook\
    if errorlevel 1 (
        echo     ⚠️ 이동 실패 - 복사로 대체...
        copy dist\PromptInput.exe dist\PromptBook\
        del dist\PromptInput.exe
    ) else (
        echo     ✅ 이동 완료
    )
) else (
    echo     ⚠️ PromptInput.exe 파일을 찾을 수 없습니다.
)

echo.
echo 📦 ZIP 압축 중...
cd dist
powershell -command "Compress-Archive -Path 'PromptBook' -DestinationPath 'PromptBook_%VERSION%.zip' -Force"
cd ..

echo.
echo ✅ 빌드 완료!
echo 📁 결과 위치:
echo   - dist\PromptBook\ (폴더)
echo     ├── PromptBook.exe (메인 프로그램)
echo     ├── PromptInput.exe (프롬프트 입력기)
echo     ├── autocomplete.txt (자동완성 데이터)
echo     └── _internal\ (라이브러리 폴더)
echo.
echo   - dist\PromptBook_%VERSION%.zip (배포용 압축 파일)

pause 