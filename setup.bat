@echo off
REM Script de setup para Windows com FastAPI
REM Cria virtual environment, instala dependências e inicia a aplicação

echo.
echo ====================================
echo  Gerador de Planilhas - Setup
echo ====================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado. Instale Python 3.8+ e tente novamente.
    pause
    exit /b 1
)

echo [1/4] Criando virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERRO] Falha ao criar virtual environment
    pause
    exit /b 1
)

echo [2/4] Ativando virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERRO] Falha ao ativar virtual environment
    pause
    exit /b 1
)

echo [3/4] Instalando dependências FastAPI...
pip install --upgrade pip

REM Instala apenas wheels pré-compiladas para evitar erros de compilação no Windows
pip install --only-binary :all: -r requirements.txt
if errorlevel 1 (
    echo [AVISO] Tentando instalação alternativa...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependências
        echo.
        echo Para resolver este problema, instale o Microsoft C++ Build Tools:
        echo https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo.
        pause
        exit /b 1
    )
)

echo [4/4] Iniciando aplicação FastAPI...
echo.
echo ====================================
echo  Setup completo!
echo.
echo  API: http://localhost:5000
echo  Docs: http://localhost:5000/docs
echo  Frontend: abra ..\frontend\index.html
echo.
echo  Pressione Ctrl+C para parar o servidor
echo ====================================
echo.

python app.py

pause
