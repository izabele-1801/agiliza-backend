#!/usr/bin/env python3
"""
Teste do processador Labotrat com AUTO-DETECÇÃO de formato
"""

import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, '/home/agiliza/Documentos/gerador_planilhas/backend')

from src.processing.labotrat_processor import LabotratProcessor

modelos_dir = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos')

test_files = [
    'LABOTRAT.xlsx',                                   # Formato COMPLETO
    'Pedido labotrat  andradas.xlsx',                 # Formato SIMPLES
    'Pedido promocional labotrat  buenos aires.xlsx', # Formato SIMPLES
]

processor = LabotratProcessor()

print("="*80)
print("TESTE DO PROCESSADOR LABOTRAT COM AUTO-DETECÇÃO")
print("="*80)

for filename in test_files:
    filepath = modelos_dir / filename
    
    if not filepath.exists():
        print(f"\n❌ NÃO ENCONTRADO: {filename}")
        continue
    
    print(f"\n{'─'*80}")
    print(f"Testando: {filename}")
    print(f"{'─'*80}")
    
    try:
        with open(filepath, 'rb') as f:
            file_content = f.read()
        
        result_df = processor.process(file_content, filename)
        
        if result_df is not None and len(result_df) > 0:
            print(f"✅ SUCESSO: {len(result_df)} registros extraídos\n")
            print("Primeiras 5 linhas:")
            print(result_df.head(5).to_string())
        else:
            print(f"❌ FALHA: Nenhum dado extraído")
    
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
