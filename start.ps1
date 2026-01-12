# Script para iniciar a aplicação automaticamente
# Execute: .\start.ps1

# Ativa o venv
.\venv\Scripts\Activate.ps1

# Inicia o servidor
Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host " Servidor iniciando..." -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "API: http://localhost:5000" -ForegroundColor Cyan
Write-Host "Frontend: c:\projetos\gerador_planilhas\frontend\index.html" -ForegroundColor Yellow
Write-Host ""
Write-Host "Pressione Ctrl+C para parar" -ForegroundColor Yellow
Write-Host ""

# Inicia a aplicação
python app.py
