@echo off
:: TelegramAccess - Script de Administracion y Ejecucion
:: Totalmente accesible y en espanol.

cd /d "%~dp0"

chcp 65001 > nul
setlocal enabledelayedexpansion

:: Detectar ejecutable de python (preferir entorno virtual .venv si existe)
set PYTHON=python
if exist .venv\Scripts\python.exe (
    set PYTHON=.venv\Scripts\python.exe
)

:MENU
cls
echo =================================================================
echo                TelegramAccess - Menu de Control
echo =================================================================
echo 1. Crear entorno virtual (.venv)
echo 2. Instalar dependencias (requirements.txt y basskit)
echo 3. Ejecutar aplicacion (main.py)
echo 4. Compilar ejecutable .exe (PyInstaller)
echo 5. Abrir carpeta de distribucion (dist)
echo 6. Abrir carpeta de datos de usuario (data)
echo 7. Abrir carpeta de registros (logs)
echo 8. Salir
echo =================================================================
echo.
set /p OPCION="Seleccione una opcion [1-8] y presione Enter: "

if "%OPCION%"=="1" goto ENTORNO
if "%OPCION%"=="2" goto DEPENDENCIAS
if "%OPCION%"=="3" goto EJECUTAR
if "%OPCION%"=="4" goto COMPILAR
if "%OPCION%"=="5" goto CARPETA_DIST
if "%OPCION%"=="6" goto CARPETA_DATA
if "%OPCION%"=="7" goto CARPETA_LOGS
if "%OPCION%"=="8" goto SALIR
goto MENU

:ENTORNO
echo Creando entorno virtual .venv...
python -m venv .venv
if exist .venv\Scripts\python.exe (
    set PYTHON=.venv\Scripts\python.exe
    echo Entorno virtual creado y seleccionado.
) else (
    echo Error al crear el entorno virtual.
)
pause
goto MENU

:DEPENDENCIAS
echo Instalando dependencias...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt
if exist __pip__\basskit*.whl (
    %PYTHON% -m pip install __pip__\basskit*.whl
)
echo Dependencias instaladas.
pause
goto MENU

:EJECUTAR
echo Iniciando TelegramAccess...
%PYTHON% main.py
goto MENU

:COMPILAR
echo =================================================================
echo                Compilacion de TelegramAccess (.exe)
echo =================================================================
%PYTHON% build_exe.py
echo.
pause
goto MENU

:CARPETA_DIST
if exist dist\TelegramAccess (
    explorer dist\TelegramAccess
) else (
    echo La carpeta dist todavia no existe. Compila primero el ejecutable (opcion 4).
    pause
)
goto MENU

:CARPETA_DATA
if exist data (
    explorer data
) else (
    echo La carpeta data todavia no existe. Se crea al primer inicio.
    pause
)
goto MENU

:CARPETA_LOGS
if exist data\logs (
    explorer data\logs
) else (
    echo La carpeta de logs todavia no existe.
    pause
)
goto MENU

:SALIR
exit /b 0
