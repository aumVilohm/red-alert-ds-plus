@echo off
setlocal DisableDelayedExpansion
where py >nul 2>nul
if errorlevel 1 goto try_python
py -3 -c "import sys, ctypes, zlib; sys.exit(sys.version_info < (3, 9))" >nul 2>nul
if errorlevel 1 goto try_python
py -3 "%~dp0prepare.py" %*
goto finished
:try_python
where python >nul 2>nul
if errorlevel 1 goto missing_python
python -c "import sys, ctypes, zlib; sys.exit(sys.version_info < (3, 9))" >nul 2>nul
if errorlevel 1 goto missing_python
python "%~dp0prepare.py" %*
goto finished
:missing_python
echo Install Python 3.9 or newer, then run this script again.
if "%~1"=="" pause
exit /b 1
:finished
set "result=%errorlevel%"
if "%~1"=="" pause
exit /b %result%
