@echo off
REM run.bat - Windows startup script

echo Starting DB AutoOrgChart with Waitress (Windows-compatible)...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Start Waitress server (Windows-compatible production server)
echo Starting Waitress server...
python run_waitress.py