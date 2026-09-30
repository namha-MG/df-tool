@echo off
title Build LagoFast Event Tool EXE
cd /d "%~dp0"
echo ====================================================
echo   DANG DONG GOI UNG DUNG THANG FILE .EXE
echo ====================================================
echo.
pyinstaller --noconfirm --onedir --windowed --collect-all customtkinter --name "LagoFast_Event_Tool" main.py

if %errorlevel% equ 0 (
    echo.
    echo ====================================================
    echo   DONG GOI THANH CONG!
    echo   File EXE nam tai: dist\LagoFast_Event_Tool\LagoFast_Event_Tool.exe
    echo ====================================================
) else (
    echo.
    echo [LOI] Dong goi that bai. Kiem tra log o tren.
)
pause
