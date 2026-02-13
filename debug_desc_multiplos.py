#!/usr/bin/env python3
"""
Debug: Verificar se há multiplicadores nas DESCRIÇÕES
Procurar por padrões tipo "x5", "Kit 3", "1/2", etc.
"""

import sys
sys.path.insert(0, '/home/agiliza/Documentos/gerador_planilhas/backend')

import pandas as pd
from pathlib import Path
import re

filepath = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos/LABOTRAT.xlsx')

df = pd.read_excel(filepath, header=None, sheet_name='TABELA VENDA 2025.2')

print("Analisando DESCRIÇÕES para procurar multiplicadores\n")
print("─" * 100)

# Coluna de descrição está no índice 5
col_desc = 5

found_multipliers = False

for idx in range(19, min(50, len(df))):  # Primeiras 30 linhas de dados
    row = df.iloc[idx]
    
    if pd.notna(row.iloc[col_desc]):
        desc = str(row.iloc[col_desc]).strip()
        
        # Procurar padrões de multiplicadores
        patterns = [
            (r'x\d+', 'quantidade x (ex: x5, x10)'),
            (r'\d+x\d+', 'medida x medida (ex: 2x4, 5x10)'),
            (r'Kit\s+\d+', 'Kit com número'),
            (r'\d+un\.?', 'Número de unidades (ex: 3un)'),
            (r'garrafa', 'múltiplas garrafas'),
            (r'caixa', 'referência a caixa na descrição'),
            (r'pack', 'pack'),
            (r'blister', 'blister'),
        ]
        
        for pattern, desc_pattern in patterns:
            if re.search(pattern, desc, re.IGNORECASE):
                match = re.search(pattern, desc, re.IGNORECASE)
                found_match = match.group(0) if match else ""
                
                qtde = row.iloc[6] if len(row) > 6 and pd.notna(row.iloc[6]) else "?"
                print(f"\nLinha {idx+1}:")
                print(f"  Descrição: {desc[:80]}")
                print(f"  QTDE original: {qtde}")
                print(f"  ⚠️  Possível multiplicador encontrado: '{found_match}' ({desc_pattern})")
                found_multipliers = True

if not found_multipliers:
    print("✅ Nenhum padrão de multiplicador encontrado nas descrições")
    print("\nPrimeiras 10 descrições:")
    for idx in range(19, min(29, len(df))):
        row = df.iloc[idx]
        if pd.notna(row.iloc[col_desc]):
            desc = str(row.iloc[col_desc]).strip()
            if desc and not desc.lower().startswith('linha'):
                qtde = row.iloc[6] if len(row) > 6 and pd.notna(row.iloc[6]) else "?"
                print(f"  • {desc[:70]:<70} → QTDE: {qtde}")
