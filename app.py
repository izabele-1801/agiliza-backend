"""
Aplicação FastAPI para processamento de PDFs, TXTs e Imagens.
Gera planilhas Excel a partir dos dados extraídos.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from src.api.routes import router

# Criar aplicação FastAPI
app = FastAPI(
    title="Gerador de Planilhas",
    description="API para processar PDFs, TXTs e Imagens e gerar planilhas Excel",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas da API
app.include_router(router)

# Definir endpoints fixos ANTES de montar static files (que captura tudo)
@app.get("/api/info", include_in_schema=False)
async def get_info():
    """Retorna informações sobre a API."""
    return {
        "app": "Gerador de Planilhas",
        "version": "1.0.0",
        "features": [
            "Processamento de PDFs",
            "Processamento de TXTs",
            "Processamento de Imagens (OCR)",
            "Geração de planilhas Excel"
        ]
    }

# Caminho do frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

# Montar pasta frontend como arquivos estáticos na raiz (DEPOIS das rotas da API)
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Detectar ambiente
    is_production = "--prod" in sys.argv
    port = 80 if is_production else 5000
    host = "0.0.0.0"
    
    print("\n" + "="*60)
    print(" 🚀 AGILIZA - Gerador de Planilhas")
    print("="*60)
    print(f" Modo: {'📦 PRODUÇÃO' if is_production else '🔧 DESENVOLVIMENTO'}")
    print(f" Host: {host}")
    print(f" Porta: {port}")
    if is_production:
        print(f" URL: http://192.168.1.25")
    else:
        print(f" URL: http://localhost:{port}")
    print("\n Pressione Ctrl+C para parar")
    print("="*60 + "\n")
    
    # Rodar sem reload quando em produção ou quando há workers múltiplos
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        log_level="info",
        reload=not is_production,
        reload_dirs=["."] if not is_production else None,
        workers=4 if is_production else 1
    )
