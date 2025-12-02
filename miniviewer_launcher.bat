@echo off
REM MiniViewer launcher — drag an image file or folder onto this batch file
REM It opens the path directly in miniviewer.py

setlocal
set "PYTHON_EXE=python"
set "SCRIPT=%~dp0miniviewer.py"

if "%~1"=="" (
    echo Drag an image file or folder onto this batch file to open it in MiniViewer.
    pause
    exit /b
)

"%PYTHON_EXE%" "%SCRIPT%" "%~1"
