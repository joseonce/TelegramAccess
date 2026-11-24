@echo off
:: TelegramAccess - Lanzador de Ejecucion Directa
:: Totalmente accesible y con retencion de consola en caso de error.

cd /d "%~dp0"

chcp 65001 > nul
setlocal enabledelayedexpansion
title TelegramAccess

:: Detectar ejecutable de python (preferir entorno virtual .venv si existe)
set PYTHON=python
if exist .venv\Scripts\python.exe (
    set PYTHON=.venv\Scripts\python.exe
)

echo =================================================================
echo                   Iniciando TelegramAccess...
echo =================================================================
echo Utilizando interprete: %PYTHON%
echo.

%PYTHON% main.py
set CODIGO_SALIDA=%ERRORLEVEL%

if not "%CODIGO_SALIDA%"=="0" (
    echo.
    echo =================================================================
    echo [ERROR] La aplicacion se cerro con codigo de error: %CODIGO_SALIDA%
    echo Revisa el mensaje de error anterior o los registros en data\logs\
    echo =================================================================
    echo.
    pause
)

exit /b %CODIGO_SALIDA%
