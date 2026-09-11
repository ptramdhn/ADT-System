@echo off
title PT Anugrah Djaya Tunggal - Sistem Operasional
cd /d "%~dp0"
echo ========================================================
echo   MENJALANKAN SISTEM OPERASIONAL PT ADT
echo   Buka browser di: http://localhost:8000
echo   PIN Admin : 010126
echo   PIN Viewer: 161616
echo ========================================================
echo.
.venv\Scripts\python.exe run.py
pause
