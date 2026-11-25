@echo off
echo ========================================
echo  Compilando Calculadora 3D
echo ========================================
echo.

REM Eliminar archivos antiguos
echo Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist Calculadora3D.spec del Calculadora3D.spec
if exist Calculadora3D.exe del Calculadora3D.exe

echo.
echo Compilando aplicacion...
python -m PyInstaller --onefile --windowed --name Calculadora3D --distpath . main.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo  Compilacion EXITOSA!
    echo ========================================
    echo.
    echo El ejecutable se encuentra en: Calculadora3D.exe
    echo (en la misma carpeta del proyecto)
    echo.
    pause
) else (
    echo.
    echo ========================================
    echo  ERROR en la compilacion
    echo ========================================
    echo.
    pause
)
