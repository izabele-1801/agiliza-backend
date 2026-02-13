#!/usr/bin/env python3
"""
Script para debugar estrutura dos arquivos Labotrat
Ajuda a entender as diferenças entre modelos que funcionam e os que retornam vazio
"""

import pandas as pd
import sys
from pathlib import Path

def inspect_excel(filepath):
    """Inspeciona estrutura de um arquivo Excel"""
    print(f"\n{'='*70}")
    print(f"Inspecionando: {filepath}")
    print(f"{'='*70}\n")
    
    try:
        # Ler sem headers para ver estrutura bruta
        df = pd.read_excel(filepath, header=None, sheet_name=0)
        
        print(f"Total de linhas: {len(df)}")
        print(f"Total de colunas: {len(df.columns)}")
        
        print("\n--- PRIMEIRAS 25 LINHAS (com índices) ---\n")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 40)
        
        for idx, row in df.iterrows():
            print(f"Linha {idx}: {row.to_list()}")
            if idx >= 24:
                break
        
        # Procurar por CNPJ na linha 5 (índice 4)
        print(f"\n--- ANÁLISE ESPECÍFICA ---\n")
        if len(df) > 4:
            linha_cnpj = df.iloc[4]
            print(f"Linha 5 (índice 4): {linha_cnpj.to_list()}")
            print(f"  Col 13 (índice 12): {linha_cnpj.iloc[12] if len(linha_cnpj) > 12 else 'N/A'}")
            print(f"  Col 14 (índice 13): {linha_cnpj.iloc[13] if len(linha_cnpj) > 13 else 'N/A'}")
        
        # Procurar cabeçalho na linha 19
        if len(df) > 18:
            print(f"\nLinha 19 (índice 18 - esperado cabeçalho):")
            linha_header = df.iloc[18]
            for col_idx, val in enumerate(linha_header):
                if pd.notna(val):
                    print(f"  Col {col_idx}: {val}")
        
        # Procurar por "Linha" para ignorar títulos de seção
        print(f"\nLinhas que começam com 'Linha':")
        for idx, row in df.iterrows():
            if idx > 18 and pd.notna(row.iloc[0]):
                val = str(row.iloc[0]).strip()
                if val.startswith('Linha'):
                    print(f"  Linha {idx}: {val}")
        
        # Contar linhas com dados após cabeçalho
        if len(df) > 19:
            data_lines = 0
            for idx in range(19, len(df)):
                row = df.iloc[idx]
                # Se primeira coluna tem valor, considerar como linha de dados
                if pd.notna(row.iloc[0]):
                    val = str(row.iloc[0]).strip()
                    if not val.startswith('Linha'):
                        data_lines += 1
            print(f"\nLinhas de dados (após linha 19): {data_lines}")
        
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    modelos_dir = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos')
    
    labotrat_files = [
        'LABOTRAT.xlsx',
        'Pedido promocional labotrat  andradas.xlsx',
        'Pedido promocional labotrat  caxias - colorido.xlsx'
    ]
    
    print("ANÁLISE DE ESTRUTURA DE ARQUIVOS LABOTRAT")
    
    for filename in labotrat_files:
        filepath = modelos_dir / filename
        if filepath.exists():
            inspect_excel(filepath)
        else:
            print(f"⚠️  Arquivo não encontrado: {filename}")
    
    # Se usuário passou arquivo como argumento
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if Path(test_file).exists():
            print("\n\n" + "="*70)
            print("ANÁLISE DE ARQUIVO DO USUÁRIO")
            print("="*70)
            inspect_excel(test_file)
        else:
            print(f"❌ Arquivo não encontrado: {test_file}")
