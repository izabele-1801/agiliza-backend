#!/usr/bin/env python3
"""
Teste: Ver se QTDE está sendo multiplicada por Qt. Cx.
"""

import sys
sys.path.insert(0, '/home/agiliza/Documentos/gerador_planilhas/backend')

import pandas as pd
from pathlib import Path
from src.processing.labotrat_processor import LabotratProcessor

filepath = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos/LABOTRAT.xlsx')

print("Testando extração de dados do LABOTRAT.xlsx\n")

with open(filepath, 'rb') as f:
    file_content = f.read()

processor = LabotratProcessor()
result_df = processor.process(file_content, 'LABOTRAT.xlsx')

if result_df is not None:
    print(f"\n✅ {len(result_df)} registros extraídos\n")
    print("Primeiros 5 registros:")
    print(result_df.head(5).to_string())
    
    print("\n\nDados brutos para análise:")
    for idx, row in result_df.head(5).iterrows():
        print(f"\nRegistro {idx+1}:")
        print(f"  CNPJ: {row['CNPJ']}")
        print(f"  EAN: {row['EAN']}")
        print(f"  DESCRICAO: {row['DESCRICAO']}")
        print(f"  QTDE: {row['QTDE']} (tipo: {type(row['QTDE']).__name__})")
        print(f"  PREÇO: {row['PREÇO']}")
else:
    print("❌ Falha ao processar arquivo")
