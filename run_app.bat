@echo off
cd /d "D:\AI RECOMMENDER SYSTEM"
powershell -ExecutionPolicy Bypass -NoExit -Command ".\.venv\Scripts\Activate.ps1; streamlit run app.py"
