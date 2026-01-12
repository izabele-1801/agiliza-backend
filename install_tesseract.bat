@echo off
REM Instala Tesseract OCR no Windows usando Chocolatey ou download direto

echo Instalando Tesseract OCR...

REM Tenta usar scoop (mais moderno)
scoop install tesseract 2>nul
if %errorlevel% equ 0 (
    echo Tesseract instalado com sucesso via scoop!
    goto end
)

REM Se scoop não funcionar, tenta chocolatey
choco install tesseract -y 2>nul
if %errorlevel% equ 0 (
    echo Tesseract instalado com sucesso via chocolatey!
    goto end
)

REM Se nada funcionar, fornece instruções
echo.
echo Nenhum gerenciador de pacotes encontrado. Instale manualmente:
echo.
echo Opção 1 - Instalar Scoop (recomendado):
echo   1. Abra PowerShell como Admin
echo   2. Cole: iex (New-Object Net.WebClient).DownloadString('https://get.scoop.sh')
echo   3. Depois execute: scoop install tesseract
echo.
echo Opção 2 - Instalar Chocolatey:
echo   1. Abra PowerShell como Admin
echo   2. Cole: Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
echo   3. Depois execute: choco install tesseract -y
echo.
echo Opção 3 - Download direto:
echo   Visite: https://github.com/UB-Mannheim/tesseract/wiki
echo   Baixe e instale o executável
echo.

:end
pause
