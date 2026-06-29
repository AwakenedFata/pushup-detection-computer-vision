@echo off
echo ============================================================
echo  PUSHUP POSTURE DETECTION - Backend Setup
echo ============================================================
echo.

cd /d "%~dp0"

echo [Step 1/3] Extracting landmarks from dataset videos...
python data_pipeline.py
if errorlevel 1 (
    echo ERROR: data_pipeline.py failed.
    pause
    exit /b 1
)

echo.
echo [Step 2/3] Training classifier...
python train.py
if errorlevel 1 (
    echo ERROR: train.py failed.
    pause
    exit /b 1
)

echo.
echo [Step 3/3] Starting FastAPI server...
echo   API docs: http://localhost:8000/docs
echo   Health  : http://localhost:8000/health
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
