@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo  Video Scene Finder - Build Script (Gerador de EXE)
echo ============================================================
echo.

set PYTHON_CMD=python
set PIP_CMD=pip
if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD="venv\Scripts\python.exe"
    set PIP_CMD="venv\Scripts\pip.exe"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERRO] Python nao encontrado no PATH nem no venv.
        pause & exit /b 1
    )
)

!PYTHON_CMD! -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller nao encontrado. Instalando...
    !PIP_CMD! install pyinstaller
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar PyInstaller.
        pause & exit /b 1
    )
)

echo [INFO] Verificando dependencias...
!PIP_CMD! install python-dotenv google-generativeai yt-dlp youtube-transcript-api certifi customtkinter static-ffmpeg opencv-python --quiet
echo [OK] Dependencias verificadas.

echo.
echo [INFO] Limpando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist\VideoSceneFinder.exe" del /f /q "dist\VideoSceneFinder.exe"
if exist "dist\download_clip.exe" del /f /q "dist\download_clip.exe"
echo [OK] Pastas de build limpas.

echo.
echo [INFO] Iniciando build do VideoSceneFinder GUI...
!PYTHON_CMD! -m PyInstaller --noconfirm --onefile --noconsole --name "VideoSceneFinder_GUI" "gui_app.py"
if errorlevel 1 (
    echo [ERRO] Build do VideoSceneFinder GUI falhou.
    pause & exit /b 1
)

echo.
echo [INFO] Iniciando build do download_clip (download_clip.py)...
!PYTHON_CMD! -m PyInstaller --noconfirm --onefile --console --name "download_clip" "download_clip.py"
if errorlevel 1 (
    echo [ERRO] Build do download_clip falhou.
    pause & exit /b 1
)

echo.
echo ============================================================
echo  BUILD CONCLUIDO COM SUCESSO!
echo  Executaveis gerados na pasta: dist\
echo  - VideoSceneFinder_GUI.exe
echo  - download_clip.exe
echo ============================================================
echo.

:: Limpa os lixos do PyInstaller que ficam na raiz
if exist "VideoSceneFinder_GUI.spec" del "VideoSceneFinder_GUI.spec"
if exist "download_clip.spec" del "download_clip.spec"
if exist "build" rmdir /s /q "build"

pause
endlocal
