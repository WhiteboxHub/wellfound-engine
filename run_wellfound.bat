@echo off
REM Activate virtual environment and run Wellfound discovery
if not exist venv (
    echo [ERROR] Virtual environment not found. Please run setup_venv.ps1 first.
    pause
    exit /b
)
call .\venv\Scripts\activate.bat
python scripts/main.py
pause
