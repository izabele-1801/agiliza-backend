#!/usr/bin/env python3
"""
Debug específico para os arquivos que o usuário testou e retornaram vazio
"""

import pandas as pd
from pathlib import Path

def analyze_labotrat_file(filepath):
    """Análise detalhada de um arquivo Labotrat"""
    print(f"\n{'='*80}")
    print(f"Arquivo: {Path(filepath).name}")
    print(f"{'='*80}\n")
    
    try:
        df = pd.read_excel(filepath, header=None, sheet_name=0)
        
        print(f"Dimensões: {len(df)} linhas x {len(df.columns)} colunas\n")
        
        # Mostrar primeiras 30 linhas
        print("PRIMEIRAS 30 LINHAS:")
        print("-" * 80)
        for idx, row in df.iterrows():
            valores = [str(v)[:30] if pd.notna(v) else "NaN" for v in row]
            print(f"[{idx:3d}] {' | '.join(valores)}")
            if idx >= 29:
                break
        
        # Procurar cabeçalho (linhas com múltiplos headers)
        print(f"\n\nPROCURANDO CABEÇALHO E DADOS:")
        print("-" * 80)
        
        for idx, row in df.iterrows():
            # Procurar linhas que pareçam cabeçalho
            valores_str = [str(v).strip() for v in row if pd.notna(v)]
            
            # Potencial cabeçalho se tiver palavras como "Código", "Descrição", "Qtde", etc
            if any(kw in str(row).lower() for kw in ['código', 'descrição', 'qtde', 'quantidade', 'preço', 'ean']):
                print(f"\n✓ CABEÇALHO POTENCIAL na linha {idx}:")
                for col_idx, val in enumerate(row):
                    if pd.notna(val):
                        print(f"    Col {col_idx}: {val}")
            
            # Contar linhas de dados após putativo cabeçalho
            if idx > 10:
                col0 = row.iloc[0]
                col1 = row.iloc[1] if len(row) > 1 else None
                
                # Se primeira coluna é número e segunda também, pode ser dado
                try:
                    if pd.notna(col0) and isinstance(col0, (int, float)):
                        val0 = float(col0)
                        val1 = float(col1) if pd.notna(col1) else None
                        if val1 is not None and idx <= 35:
                            print(f"  Linha {idx}: {col0} | {col1}")
                except:
                    pass
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    modelos_dir = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos')
    
    files_to_test = [
        'Pedido labotrat  andradas.xlsx',
        'Pedido promocional labotrat  buenos aires.xlsx',
    ]
    
    print("="*80)
    print("ANÁLISE DETALHADA DOS ARQUIVOS QUE RETORNARAM VAZIO")
    print("="*80)
    
    for filename in files_to_test:
        filepath = modelos_dir / filename
        if filepath.exists():
            analyze_labotrat_file(filepath)
        else:
            print(f"❌ NÃO ENCONTRADO: {filename}")
