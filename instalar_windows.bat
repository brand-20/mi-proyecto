@echo off
REM Instalador para Windows: doble clic sobre este archivo.
REM Instala los paquetes de Python y verifica la skill codigo-ingeniero-civil.
setlocal
cd /d "%~dp0"

echo.
echo === Instalacion: skill codigo-ingeniero-civil ===
echo.

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3"
    goto hay_python
)
python --version >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
    goto hay_python
)

echo [X] No se encontro Python en esta computadora.
echo     1. Descargalo de https://www.python.org/downloads/  (version 3.10 o mas nueva)
echo     2. En el instalador marca la casilla "Add python.exe to PATH"
echo     3. Cierra esta ventana y vuelve a hacer doble clic en este archivo
echo.
pause
exit /b 1

:hay_python
echo Python encontrado:
%PY% --version
echo.
echo Instalando paquetes (pytest, pandas, openpyxl, matplotlib)...
%PY% -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [X] Fallo la instalacion de paquetes. Revisa tu conexion a internet y vuelve a intentar.
    pause
    exit /b 1
)

echo.
%PY% verificar_instalacion.py
echo.
pause
