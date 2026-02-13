#!/usr/bin/env python3
"""
Debug: Encontrar CNPJ em linha 5 do andradas
"""

import pandas as pd
from pathlib import Path
import re

filepath = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos/Pedido labotrat  andradas.xlsx')

print(f"Analisando: {filepath.name}\n")

# Ler com várias estratégias
print("="*80)
print("ESTRATÉGIA 1: header=None (sem interpretação)")
print("="*80)
df = pd.read_excel(filepath, header=None, sheet_name=0)
print(f"Dimensões: {len(df)} linhas x {len(df.columns)} colunas\n")

print("Linha 5 (índice 4) - TODAS as colunas:")
row = df.iloc[4]
for col_idx, val in enumerate(row):
    if pd.notna(val):
        val_str = str(val).strip()
        print(f"  Col {col_idx:2d}: {val_str}")

print("\n" + "="*80)
print("ESTRATÉGIA 2: Procurar CNPJ em TODAS as linhas")
print("="*80)

cnpj_pattern = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'

for row_idx, row in df.iterrows():
    for col_idx, val in enumerate(row):
        if pd.notna(val):
            val_str = str(val).strip()
            if re.search(cnpj_pattern, val_str):
                match = re.search(cnpj_pattern, val_str)
                cnpj_encontrado = match.group(0)
                print(f"\n✅ ENCONTRADO: Linha {row_idx+1} (idx {row_idx}), Col {col_idx}")
                print(f"   Celula inteira: {val_str}")
                print(f"   CNPJ extraído: {cnpj_encontrado}")
                
                # Se for linha 5, destacar
                if row_idx == 4:
                    print(f"   *** ESTA É A LINHA 5! ***")

print("\n" + "="*80)
print("ESTRATÉGIA 3: Carregar sem skiprows para ver tudo")
print("="*80)

df2 = pd.read_excel(filepath, header=None, sheet_name=0)
print(f"\nPrimeiras 10 linhas (completas):")
for idx in range(min(10, len(df2))):
    valores = [str(v)[:40] if pd.notna(v) else "NaN" for v in df2.iloc[idx]]
    print(f"[{idx}] {' | '.join(valores)}")
