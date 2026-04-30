# Activate virtual environment and run Flask app
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
& ".\\.venv\Scripts\Activate.ps1"
cd backend-python
python app.py
