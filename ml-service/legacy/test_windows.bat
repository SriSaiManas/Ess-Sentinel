@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Run setup_windows.bat first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m pytest -q --cov=ess --cov=services --cov=ui --cov=app --cov-report=term-missing --junitxml=evidence/tests_windows.xml
set ESS_TEST_EXIT=%ERRORLEVEL%
pause
exit /b %ESS_TEST_EXIT%
