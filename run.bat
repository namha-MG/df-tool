@echo off
title LagoFast Event Tool
cd /d "%~dp0"
echo Dang khoi dong LagoFast Event Tool...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong the chay tool. Kiem tra xem Python da duoc cai dat chua.
    pause
)
