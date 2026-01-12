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

# Servir arquivos estáticos do frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def read_root():
    """Serve o arquivo index.html do frontend."""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Gerador de Planilhas API v1.0"}

@app.get("/api/info")
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

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*50)
    print(" Servidor iniciando...")
    print("="*50)
    print("\nAPI: http://localhost:5000")
    print("Frontend: http://localhost:5000")
    print("\nPressione Ctrl+C para parar")
    print("="*50 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
