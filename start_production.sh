#!/bin/bash

# AGILIZA - Production Startup Script
# Este script inicia o servidor em modo produção na porta 80

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo ""
echo "════════════════════════════════════════════════════════════"
echo " 🚀 AGILIZA - Iniciando em Produção"
echo "════════════════════════════════════════════════════════════"
echo ""

# Verificar se venv existe
if [ ! -d "venv" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "Execute: python3 -m venv venv"
    exit 1
fi

# Ativar venv
echo "📦 Ativando ambiente virtual..."
source venv/bin/activate

# Verificar porta 80
if [ "$(id -u)" != "0" ]; then
    echo "⚠️  WARNING: Porta 80 requer permissões root (sudo)"
    echo ""
    echo "Opções:"
    echo "  1. Use sudo: sudo bash start_production.sh"
    echo "  2. Use porta 5000: python3 app.py"
    echo "  3. Configure Nginx para reverter proxy porta 80 → 5000"
    echo ""
    exit 1
fi

# Iniciar servidor
echo "✅ Iniciando servidor em http://192.168.1.25"
echo "   (Pressione Ctrl+C para parar)"
echo ""

python3 app.py --prod "$@"
