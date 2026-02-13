#!/usr/bin/env python3
"""
Debug: Procurar CNPJ formatado na linha 5 de arquivos Labotrat
"""

import pandas as pd
from pathlib import Path
import re

def find_cnpj_in_row(df, row_idx=4):
    """Procura CNPJ formatado na linha especificada"""
    print(f"\n{'='*80}")
    print(f"Procurando CNPJ na linha {row_idx+1} (índice {row_idx})")
    print(f"{'='*80}\n")
    
    if len(df) <= row_idx:
        print(f"❌ Arquivo não tem linha {row_idx+1}")
        return None
    
    row = df.iloc[row_idx]
    
    print(f"Conteúdo completo da linha:")
    for col_idx, val in enumerate(row):
        if pd.notna(val):
            val_str = str(val).strip()
            print(f"  Col {col_idx:2d}: {val_str}")
    
    # Procurar padrão de CNPJ formatado
    cnpj_pattern = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'
    
    print(f"\nProcurando padrão: {cnpj_pattern}")
    
    for col_idx, val in enumerate(row):
        if pd.notna(val):
            val_str = str(val).strip()
            if re.search(cnpj_pattern, val_str):
                print(f"\n✅ ENCONTRADO na coluna {col_idx}: {val_str}")
                return col_idx, val_str
    
    # Se não encontrar formatado, procurar apenas números
    cnpj_digits_pattern = r'\d{14}'
    print(f"\nProcurando padrão de dígitos: {cnpj_digits_pattern}")
    
    for col_idx, val in enumerate(row):
        if pd.notna(val):
            val_str = str(val).strip()
            if re.search(cnpj_digits_pattern, val_str):
                print(f"  Col {col_idx}: {val_str}")
    
    return None

# Testar todos os arquivos Labotrat
modelos_dir = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos')

files = [
    'LABOTRAT.xlsx',
    'Pedido labotrat  andradas.xlsx',
    'Pedido promocional labotrat  buenos aires.xlsx',
]

for filename in files:
    filepath = modelos_dir / filename
    if filepath.exists():
        print(f"\n\n{'#'*80}")
        print(f"# {filename}")
        print(f"{'#'*80}")
        
        try:
            df = pd.read_excel(filepath, header=None, sheet_name=0)
            find_cnpj_in_row(df)
        except Exception as e:
            print(f"❌ ERRO: {e}")
    else:
        print(f"\n❌ NÃO ENCONTRADO: {filename}")
