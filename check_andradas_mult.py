#!/usr/bin/env python3
"""
Verificar dados andradas linha por linha
"""

import sys
sys.path.insert(0, '/home/agiliza/Documentos/gerador_planilhas/backend')

import pandas as pd
from pathlib import Path

filepath = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos/Pedido labotrat  andradas.xlsx')

# Ler a aba completa (TABELA VENDA 2025.2)
df = pd.read_excel(filepath, header=None, sheet_name='TABELA VENDA 2025.2')

print("ARQUIVO: Pedido labotrat andradas.xlsx")
print("ABA: TABELA VENDA 2025.2\n")

# Cabeçalho (linha 19, índice 18)
print("CABEÇALHO (Linha 19):")
for col_idx, val in enumerate(df.iloc[18]):
    if pd.notna(val):
        print(f"  Col {col_idx:2d}: {val}")

# Primeiros 10 produtos
print("\n\nPRIMEIROS 10 PRODUTOS:")
print("─" * 100)
for data_idx in range(19, min(29, len(df))):
    row = df.iloc[data_idx]
    
    codigo = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else ""
    ean = row.iloc[2] if len(row) > 2 and pd.notna(row.iloc[2]) else ""
    qtcx = row.iloc[4] if len(row) > 4 and pd.notna(row.iloc[4]) else ""
    desc = row.iloc[5] if len(row) > 5 and pd.notna(row.iloc[5]) else ""
    qtde = row.iloc[6] if len(row) > 6 and pd.notna(row.iloc[6]) else ""
    preco = row.iloc[7] if len(row) > 7 and pd.notna(row.iloc[7]) else ""
    
    if desc and str(desc).strip() and not str(desc).lower().startswith('linha'):
        print(f"\nLinha {data_idx+1}:")
        print(f"  EAN: {ean}")
        print(f"  Descrição: {desc}")
        print(f"  Qt. Cx. (Col 4): {qtcx}")
        print(f"  QTDE (Col 6): {qtde}")
        print(f"  Preço: {preco}")
        print(f"  ⚠️  QTDE × Qt.Cx = {qtde if qtde else 0} × {qtcx if qtcx else 1} = {float(qtde if qtde else 0) * float(qtcx if qtcx else 1)}")
