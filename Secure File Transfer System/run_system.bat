@echo off
REM run_system.bat - Start the complete Secure File Transfer System (Windows)

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting API Server (Flask)...
echo The GUI will be available at: http://localhost:5000
echo.
python api_server.py
pause
