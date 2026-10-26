@echo off
setlocal
cd /d "%~dp0"
if exist .venv\Scripts\python.exe goto checkvenv
if defined ESS_PYTHON goto custompython
py -3.14 -c "import sys;sys.exit(0 if sys.version_info[:2]==(3,14) else 1)" >nul 2>&1
if not errorlevel 1 (
 py -3.14 -m venv .venv
 if errorlevel 1 goto failed
 goto checkvenv
)
python -c "import sys;sys.exit(0 if sys.version_info[:2]==(3,14) else 1)" >nul 2>&1
if errorlevel 1 goto nopython
python -m venv .venv
if errorlevel 1 goto failed
goto checkvenv
:custompython
"%ESS_PYTHON%" -c "import sys;sys.exit(0 if sys.version_info[:2]==(3,14) else 1)"
if errorlevel 1 goto nopython
"%ESS_PYTHON%" -m venv .venv
if errorlevel 1 goto failed
:checkvenv
.venv\Scripts\python.exe -c "import sys; print(sys.version); sys.exit(0 if sys.version_info[:2]==(3,14) else 1)"
if errorlevel 1 (
 echo Existing .venv uses another Python. Move it aside and rerun setup. Your system Python is unchanged.
 goto failed
)
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip check
if errorlevel 1 goto failed
echo Setup complete. Run run_windows.bat.
pause
exit /b 0
:nopython
echo Python 3.14 was not found. Do not install another Python.
echo Set ESS_PYTHON to the full path of your existing Python 3.14.6 executable and retry.
:failed
echo Setup failed. Read the error above; verify the interpreter and network access.
pause
exit /b 1
