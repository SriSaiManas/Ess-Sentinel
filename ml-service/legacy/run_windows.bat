@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Run setup_windows.bat first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe -c "import streamlit,numpy,pandas,sklearn,plotly,reportlab,openpyxl,pyarrow"
if errorlevel 1 (
 echo Required packages are missing. Run setup_windows.bat and inspect its errors.
 pause
 exit /b 1
)
echo ESS Sentinel 2.0 will be available at http://localhost:8501
.venv\Scripts\python.exe -m streamlit run app.py
set ESS_EXIT=%ERRORLEVEL%
pause
exit /b %ESS_EXIT%
