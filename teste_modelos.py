#!/usr/bin/env python3
"""Script para testar processadores com arquivos reais da pasta modelos_pedidos"""

import os
import sys
from pathlib import Path
import pandas as pd

# Adicionar o diretório backend ao path
sys.path.insert(0, '/home/agiliza/Documentos/gerador_planilhas/backend')

try:
    from src.processing.factory import get_processor
except ImportError as e:
    print(f"❌ Erro ao importar factory: {e}")
    print("Certifique-se que as dependências estão instaladas")
    sys.exit(1)

# Mapeamento de arquivos para processadores
ARQUIVOS_TESTE = {
    'BIOMAXFARMA.xlsx': 'biomaxfarma',
    'COTE_FACIL.xls': 'cotefacil',
    'CRESCER.xls': 'crescer',
    'DSG FARMA MATRIZ PASSOS LTDA.txt': 'dsgfarma',
    'FARMACIA OCEANICA DE ITAIPUACU LTDA.TXT': 'oceanica',
    'KIMBERLY.xlsx': 'kimberly',
    'LOREAL.pdf': 'loreal',
    'NatusFarma.PDF': 'natusfarma',
    'POUPA_MINAS.pdf': 'poupaminas',
    'PRUDENCE.pdf': 'prudence',
    'SIAGE.pdf': 'siage',
    'UNILEVER.PDF': 'unilever',
}

MODELOS_DIR = Path('/home/agiliza/Documentos/gerador_planilhas/modelos_pedidos')

def teste_processador(arquivo_nome, processador_nome):
    """Testa um processador com um arquivo específico"""
    
    arquivo_path = MODELOS_DIR / arquivo_nome
    
    if not arquivo_path.exists():
        return None, f"Arquivo não encontrado: {arquivo_nome}"
    
    try:
        # Ler arquivo
        with open(arquivo_path, 'rb') as f:
            file_content = f.read()
        
        # Obter processador
        processor = get_processor(processador_nome)
        if not processor:
            return None, f"Processador '{processador_nome}' não encontrado"
        
        # Processar
        df = processor.process(file_content, arquivo_nome)
        
        if df is None:
            return None, "Processador retornou None"
        
        if df.empty:
            return None, "DataFrame vazio"
        
        # Remover colunas totalmente vazias
        df_clean = df.dropna(axis=1, how='all')
        
        # Calcular percentual de campos preenchidos
        total_campos = df_clean.size
        campos_vazios = df_clean.isna().sum().sum()
        campos_preenchidos = total_campos - campos_vazios
        percentual = (campos_preenchidos / total_campos * 100) if total_campos > 0 else 0
        
        return {
            'arquivo': arquivo_nome,
            'processador': processador_nome,
            'linhas': len(df_clean),
            'colunas': len(df_clean.columns),
            'colunas_usadas': list(df_clean.columns),
            'campos_preenchidos': campos_preenchidos,
            'campos_vazios': campos_vazios,
            'total_campos': total_campos,
            'percentual_preenchido': round(percentual, 1),
            'df': df_clean
        }, None
        
    except Exception as e:
        return None, f"Erro: {type(e).__name__}: {str(e)[:100]}"

def main():
    print("=" * 80)
    print("🧪 TESTE DOS PROCESSADORES COM ARQUIVOS REAIS")
    print("=" * 80)
    
    resultados_sucesso = []
    resultados_erro = []
    
    for arquivo_nome, processador_nome in ARQUIVOS_TESTE.items():
        print(f"\n🔍 Testando: {arquivo_nome}")
        print(f"   Processador: {processador_nome}")
        
        resultado, erro = teste_processador(arquivo_nome, processador_nome)
        
        if erro:
            print(f"   ❌ {erro}")
            resultados_erro.append({
                'arquivo': arquivo_nome,
                'processador': processador_nome,
                'erro': erro
            })
        else:
            print(f"   ✅ Sucesso!")
            print(f"   📊 Linhas: {resultado['linhas']}")
            print(f"   📋 Colunas: {resultado['colunas']} ({', '.join(resultado['colunas_usadas'][:3])}...)")
            print(f"   📈 Campos preenchidos: {resultado['percentual_preenchido']}% ({resultado['campos_preenchidos']}/{resultado['total_campos']})")
            
            resultados_sucesso.append(resultado)
    
    # Resumo final
    print("\n" + "=" * 80)
    print("📈 RESUMO DOS TESTES")
    print("=" * 80)
    print(f"\n✅ Sucesso: {len(resultados_sucesso)}/{len(ARQUIVOS_TESTE)}")
    print(f"❌ Falha: {len(resultados_erro)}/{len(ARQUIVOS_TESTE)}")
    
    if resultados_sucesso:
        print("\n✅ PROCESSADORES QUE FUNCIONARAM:")
        print("-" * 80)
        for r in resultados_sucesso:
            print(f"  • {r['arquivo']:40s} → {r['processador']:15s} | "
                  f"{r['linhas']} linhas | {r['percentual_preenchido']}% preenchido")
    
    if resultados_erro:
        print("\n❌ PROCESSADORES COM ERRO:")
        print("-" * 80)
        for r in resultados_erro:
            print(f"  • {r['arquivo']:40s} → {r['processador']:15s}")
            print(f"    Erro: {r['erro']}")
    
    # Estatísticas gerais
    if resultados_sucesso:
        percentuais = [r['percentual_preenchido'] for r in resultados_sucesso]
        media_preenchimento = sum(percentuais) / len(percentuais)
        
        print(f"\n📊 ESTATÍSTICAS:")
        print(f"  Preenchimento médio: {round(media_preenchimento, 1)}%")
        print(f"  Melhor preenchimento: {max(percentuais)}%")
        print(f"  Pior preenchimento: {min(percentuais)}%")
    
    # Mostrar amostra de dados de cada processador bem-sucedido
    print("\n" + "=" * 80)
    print("📋 AMOSTRA DOS DADOS EXTRAÍDOS")
    print("=" * 80)
    
    for r in resultados_sucesso[:3]:  # Mostrar apenas os 3 primeiros
        print(f"\n{r['arquivo']} ({r['processador']}):")
        print("-" * 80)
        # Mostrar primeiras 3 linhas
        print(r['df'].head(3).to_string())
        print(f"... ({r['linhas']} linhas no total)")

if __name__ == '__main__':
    main()
