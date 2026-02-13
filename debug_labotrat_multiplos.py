#!/usr/bin/env python3
"""
Debug: Verificar se há multiplicadores em Labotrat
"""

import pandas as pd
from pathlib import Path

filepath = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos/LABOTRAT.xlsx')

print(f"Analisando: {filepath.name}\n")

# Ler aba completa
df = pd.read_excel(filepath, header=None, sheet_name='TABELA VENDA 2025.2')

print("Linha 18 (cabeçalho - índice 18):")
header_row = df.iloc[18]
for col_idx, val in enumerate(header_row):
    if pd.notna(val):
        print(f"  Col {col_idx:2d}: {val}")

print("\n\nPrimeiros 5 produtos (linhas 19-23):")
print("─" * 120)
for data_idx in range(19, 24):
    row = df.iloc[data_idx]
    print(f"\nLinha {data_idx+1} (idx {data_idx}):")
    for col_idx in range(len(row)):
        if pd.notna(row.iloc[col_idx]):
            val_str = str(row.iloc[col_idx]).strip()
            if len(val_str) > 0:
                print(f"  Col {col_idx:2d}: {val_str[:60]}")
