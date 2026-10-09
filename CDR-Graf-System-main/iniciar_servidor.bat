@echo off
setlocal EnableDelayedExpansion
title CDR Graf System - Servidor
chcp 65001 >nul

:: ==============================================================================
:: 1. LOCALIZAR DIRECTORIO DEL BACKEND
:: ==============================================================================
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "BACKEND_DIR="

if exist "%SCRIPT_DIR%\backend\app\main.py" (
    set "BACKEND_DIR=%SCRIPT_DIR%\backend"
) else if exist "%SCRIPT_DIR%\CDR-Graf-System-main\backend\app\main.py" (
    set "BACKEND_DIR=%SCRIPT_DIR%\CDR-Graf-System-main\backend"
) else if exist "%SCRIPT_DIR%\app\main.py" (
    set "BACKEND_DIR=%SCRIPT_DIR%"
) else if exist "%SCRIPT_DIR%\..\backend\app\main.py" (
    set "BACKEND_DIR=%SCRIPT_DIR%\..\backend"
)

if not defined BACKEND_DIR (
    echo [ERROR] No se encontro la carpeta del backend - app\main.py.
    echo Asegurese de ejecutar este archivo dentro de la carpeta del proyecto.
    echo:
    pause
    exit /b 1
)

:: ==============================================================================
:: 2. DETECTAR ENTORNO PYTHON
:: ==============================================================================
set "PYTHON_EXE="

if exist "%SCRIPT_DIR%\env\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\env\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%\..\env\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\..\env\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\venv\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%\..\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\..\venv\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%\.venv\Scripts\python.exe"
) else if exist "%BACKEND_DIR%\..\env\Scripts\python.exe" (
    set "PYTHON_EXE=%BACKEND_DIR%\..\env\Scripts\python.exe"
)

if not defined PYTHON_EXE (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        where py >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=py"
        )
    )
)

if not defined PYTHON_EXE (
    echo ==============================================================================
    echo [ERROR] No se encontro Python ni un entorno virtual 'env'.
    echo Por favor instale Python e incluyalo en el PATH de Windows.
    echo ==============================================================================
    pause
    exit /b 1
)

:: Verificar si uvicorn y fastapi estan disponibles, si no, instalar requirements
"%PYTHON_EXE%" -c "import uvicorn, fastapi" >nul 2>&1
if !errorlevel! neq 0 (
    echo ==============================================================================
    echo [AVISO] Se detectaron dependencias faltantes en el entorno.
    echo Instalando paquetes requeridos desde requirements.txt...
    echo ==============================================================================
    "%PYTHON_EXE%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
    if !errorlevel! neq 0 (
        echo:
        echo [ERROR] Fallo la instalacion de dependencias. Revise su conexion a Internet.
        pause
        exit /b 1
    )
)

:: ==============================================================================
:: 3. DETECTAR IP LOCAL EN EL WI-FI / RED
:: ==============================================================================
set "DETECTED_IP="
"%PYTHON_EXE%" -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.255.255.255', 1)); print(s.getsockname()[0]); s.close()" > "%TEMP%\cdr_ip.txt" 2>nul
if exist "%TEMP%\cdr_ip.txt" (
    set /p DETECTED_IP=<"%TEMP%\cdr_ip.txt"
    del "%TEMP%\cdr_ip.txt" >nul 2>&1
)

if not defined DETECTED_IP (
    set "DETECTED_IP=127.0.0.1"
)

:: ==============================================================================
:: 4. PREGUNTAS Y CONFIGURACION INTERACTIVA
:: ==============================================================================
cls
echo ==============================================================================
echo                 SISTEMA DE GRAFICAS CDR - INICIO DE SERVIDOR
echo ==============================================================================
echo  Equipo actual:         %COMPUTERNAME%
echo  IP detectada en Wi-Fi: !DETECTED_IP!
echo ==============================================================================
echo:
echo  Seleccione como desea iniciar el servidor:
echo:
echo    [1] Red Local / Wi-Fi [RECOMENDADO]
echo        - Permite ingresar desde ESTA PC y desde OTRAS PCs o telefonos en el Wi-Fi.
echo        - Escuchara en todas las tarjetas de red [0.0.0.0].
echo:
echo    [2] Solo esta PC [Localhost]
echo        - Solo accesible desde esta misma computadora [127.0.0.1].
echo:
echo    [3] Personalizado
echo        - Ingresar manualmente la direccion IP de enlace.
echo:
set "OPT="
set /p "OPT=Elija una opcion [1/2/3] (Presione Enter para 1): "
if "!OPT!"=="" set "OPT=1"

set "HOST=0.0.0.0"
set "PORT=8000"

if "!OPT!"=="1" (
    set "HOST=0.0.0.0"
) else if "!OPT!"=="2" (
    set "HOST=127.0.0.1"
) else if "!OPT!"=="3" (
    echo:
    set /p "CUSTOM_HOST=Ingrese la IP para enlazar [Por defecto: 0.0.0.0]: "
    if not "!CUSTOM_HOST!"=="" set "HOST=!CUSTOM_HOST!"
) else (
    echo Opcion no reconocida, usando modo Red Local [0.0.0.0].
    set "HOST=0.0.0.0"
)

echo:
set /p "CUSTOM_PORT=Ingrese el puerto del servidor [Presione Enter para 8000]: "
if not "!CUSTOM_PORT!"=="" set "PORT=!CUSTOM_PORT!"

echo:
set "OPEN_BROWSER="
set /p "OPEN_BROWSER=Desea abrir el navegador automaticamente? (S/N) [Presione Enter para S]: "
if "!OPEN_BROWSER!"=="" set "OPEN_BROWSER=S"

:: ==============================================================================
:: 5. MOSTRAR INFORMACION DE ACCESO
:: ==============================================================================
cls
echo ==============================================================================
echo                         SERVIDOR CDR EN EJECUCION
echo ==============================================================================
echo  Host:   !HOST!
echo  Puerto: !PORT!
echo ------------------------------------------------------------------------------
echo  ENLACES DE ACCESO:
echo:
echo    Desde ESTA COMPUTADORA:
echo      - http://localhost:!PORT!
echo      - http://127.0.0.1:!PORT!
echo:
if not "!DETECTED_IP!"=="127.0.0.1" (
    echo    Desde OTRAS COMPUTADORAS o CELULARES en este mismo Wi-Fi:
    echo      - http://!DETECTED_IP!:!PORT!
    echo:
)
echo ------------------------------------------------------------------------------
echo  RECORDATORIO PARA OTRAS PCS:
echo  * Ambas PCs deben estar conectadas a la misma red Wi-Fi o red local.
echo  * Si otra PC no puede cargar la pagina, verifique que el Firewall de Windows
echo    en esta maquina permita conexiones de entrada al puerto !PORT! TCP.
echo  * Para detener el servidor, presione Ctrl + C en esta ventana.
echo ==============================================================================
echo:

if /i "!OPEN_BROWSER!"=="S" (
    timeout /t 2 /nobreak >nul
    start http://localhost:!PORT!
)

:: ==============================================================================
:: 6. EJECUTAR EL SERVIDOR
:: ==============================================================================
cd /d "%BACKEND_DIR%"
"%PYTHON_EXE%" -m uvicorn app.main:app --host !HOST! --port !PORT! --reload

if !errorlevel! neq 0 (
    echo:
    echo ==============================================================================
    echo [ERROR] El servidor se ha detenido de forma inesperada.
    echo ==============================================================================
    pause
)
