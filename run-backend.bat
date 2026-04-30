@echo off
REM Activate virtual environment and run Flask app
call .venv\Scripts\activate.bat
cd backend-python
python app.py
pause
