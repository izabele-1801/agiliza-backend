#!/usr/bin/env python3
"""
Verificar dados andradas linha por linha - corrigido
"""

import sys
sys.path.insert(0, '/home/agiliza/Documentos/gerador_planilhas/backend')

import pandas as pd
from pathlib import Path

filepath = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos/Pedido labotrat  andradas.xlsx')

# Ler a aba completa (TABELA VENDA 2025.2)
df = pd.read_excel(filepath, header=None, sheet_name='TABELA VENDA 2025.2')

print("ARQUIVO: Pedido labotrat andradas.xlsx\n")

# Primeiros 10 produtos com dados reais (não cabeçalho)
print("PRIMEIROS 10 PRODUTOS COM DADOS REAIS:")
print("─" * 110)

count = 0
for data_idx in range(19, len(df)):
    row = df.iloc[data_idx]
    
    # Pular cabeçalhos internos
    if pd.notna(row.iloc[1]):
        try:
            codigo = int(row.iloc[1])  # Se for número, é dado real
            
            ean = row.iloc[2] if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            qtcx = row.iloc[4] if len(row) > 4 and pd.notna(row.iloc[4]) else None
            desc = str(row.iloc[5]).strip() if len(row) > 5 and pd.notna(row.iloc[5]) else ""
            qtde = row.iloc[6] if len(row) > 6 and pd.notna(row.iloc[6]) else None
            preco = row.iloc[7] if len(row) > 7 and pd.notna(row.iloc[7]) else ""
            
            if desc and not desc.lower().startswith('linha') and not desc.startswith('Rotina'):
                print(f"\nLinha {data_idx+1}:")
                print(f"  EAN: {ean}")
                print(f"  Descrição: {desc[:70]}")
                print(f"  Qt. Cx. (Col 4): {qtcx}")
                print(f"  QTDE (Col 6): {qtde} (tipo: {type(qtde).__name__})")
                print(f"  Preço: {preco}")
                
                # Mostrar se está sendo multiplicado
                if qtde and qtcx:
                    try:
                        qtde_val = float(qtde) if qtde else 1
                        qtcx_val = float(qtcx) if qtcx else 1
                        mult = qtde_val * qtcx_val
                        print(f"  → Se multiplicar: {qtde_val} × {qtcx_val} = {mult}")
                    except:
                        pass
                
                count += 1
                if count >= 10:
                    break
        except:
            # Não é um número válido, pula
            pass
