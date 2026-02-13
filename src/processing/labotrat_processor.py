"""Processador especializado para Labotrat."""

import pandas as pd
from io import BytesIO
from .base import FileProcessor
from src.utils.validators import extract_cnpj, extract_ean13, normalizar_preco


class LabotratProcessor(FileProcessor):
    """Processa pedidos Labotrat."""
    
    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame:
        """Processa arquivo Labotrat e extrai dados estruturados."""
        print(f"\n[LABOTRAT] Processando: {filename or 'arquivo'}")
        
        try:
            ext = filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else 'xlsx'
            
            if ext in ['xlsx', 'xls']:
                return self._processar_excel(file_content, ext)
            else:
                print(f"[LABOTRAT] Formato não suportado: {ext}")
                return None
                
        except Exception as e:
            print(f"[LABOTRAT] ERRO: {type(e).__name__}: {str(e)}")
            return None
    
    def _processar_excel(self, file_content: bytes, ext: str) -> pd.DataFrame | None:
        """Processa arquivo Excel Labotrat."""
        try:
            engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
            # Ler sem headers para processar a estrutura custom
            df = pd.read_excel(BytesIO(file_content), engine=engine, header=None)
            return self._extrair_dados(df)
        except Exception as e:
            print(f"[LABOTRAT] ERRO ao processar Excel: {e}")
            return None
    
    def _extrair_dados(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """Extrai dados do DataFrame Labotrat - detecta formato automaticamente."""
        try:
            if df.empty:
                print("[LABOTRAT] DataFrame vazio")
                return None
            
            # Detectar formato baseado no número de colunas
            num_cols = len(df.columns)
            
            if num_cols == 2:
                # Formato SIMPLES: Código do Produto | Quantidade
                print(f"[LABOTRAT] Detectado formato SIMPLES (2 colunas)")
                return self._processar_formato_simples(df)
            elif num_cols >= 10:
                # Formato COMPLETO: estrutura complexa com CNPJ, descrição, preço, etc
                print(f"[LABOTRAT] Detectado formato COMPLETO ({num_cols} colunas)")
                return self._processar_formato_completo(df)
            else:
                print(f"[LABOTRAT] Formato desconhecido: {num_cols} colunas")
                return None
        
        except Exception as e:
            print(f"[LABOTRAT] ERRO ao extrair dados: {e}")
            return None
    
    def _processar_formato_simples(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """
        Processa formato SIMPLES: Código do Produto | Quantidade
        Retorna dados com apenas código e quantidade (sem descrição/preço).
        """
        try:
            dados = []
            
            # Header geralmente está na linha 0
            header_idx = 0
            data_start_idx = 1
            
            # Processar todas as linhas de dados
            for idx in range(data_start_idx, len(df)):
                try:
                    row = df.iloc[idx]
                    
                    # Coluna 0: Código do Produto
                    codigo_raw = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                    if not codigo_raw or codigo_raw.lower() == 'nan':
                        continue
                    
                    # Coluna 1: Quantidade
                    qtde_raw = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ''
                    if not qtde_raw or qtde_raw.lower() in ['nan', '']:
                        continue
                    
                    # Validar QTDE
                    try:
                        qtde_float = float(qtde_raw.replace(',', '.'))
                        qtde = int(qtde_float)
                    except (ValueError, AttributeError):
                        print(f"[LABOTRAT] AVISO: Quantidade inválida '{qtde_raw}' na linha {idx+1}")
                        continue
                    
                    if qtde <= 0:
                        continue
                    
                    # Para formato simples, usamos código como EAN e nome genérico
                    dados.append({
                        'CNPJ': 'N/A',  # Não disponível neste formato
                        'EAN': codigo_raw,
                        'DESCRICAO': f'Produto {codigo_raw}',  # Descrição genérica
                        'QTDE': qtde,
                        'PREÇO': None  # Não disponível neste formato
                    })
                    
                except Exception as e:
                    print(f"[LABOTRAT] ERRO ao processar linha {idx+1}: {e}")
                    continue
            
            if dados:
                result_df = pd.DataFrame(dados)
                print(f"[LABOTRAT] Formato simples: {len(result_df)} itens extraídos (códigos de produto)")
                return result_df
            else:
                print("[LABOTRAT] Nenhum dado extraído do formato simples")
                return None
        
        except Exception as e:
            print(f"[LABOTRAT] ERRO ao processar formato simples: {e}")
            return None
    
    def _processar_formato_completo(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """
        Processa formato COMPLETO: estrutura com CNPJ, EAN, descrição, QtD, preço, etc.
        """
        try:
            if len(df) < 20:
                print("[LABOTRAT] DataFrame muito pequeno para formato completo (<20 linhas)")
                return None
            
            # Extrair CNPJ da linha 5 (índice 4), coluna 13
            cnpj = self._extrair_cnpj(df)
            if not cnpj:
                print("[LABOTRAT] ⚠️  CNPJ não encontrado, continuando sem CNPJ...")
                cnpj = "N/A"
            else:
                print(f"[LABOTRAT] CNPJ extraído: {cnpj}")
            
            # Indices das colunas (0-based):
            # EAN 13: coluna 2
            # Descrição: coluna 5
            # Qtde.: coluna 6
            # Pço. Tabela: coluna 7
            # Cabeçalho está na linha 19 (índice 18)
            # Dados começam na linha 20 (índice 19)
            
            col_ean = 2
            col_desc = 5
            col_qtde = 6
            col_preco = 7
            data_start_idx = 19
            
            dados = []
            
            # Processar linhas a partir de data_start_idx
            for idx in range(data_start_idx, len(df)):
                try:
                    row = df.iloc[idx]
                    
                    # Extrair EAN
                    ean_raw = str(row.iloc[col_ean]).strip() if col_ean < len(row) and pd.notna(row.iloc[col_ean]) else ''
                    ean = extract_ean13(ean_raw) or ean_raw
                    
                    # Extrair DESCRIÇÃO
                    desc = str(row.iloc[col_desc]).strip() if col_desc < len(row) and pd.notna(row.iloc[col_desc]) else ''
                    
                    # Ignorar linhas vazias e títulos que começam com "Linha"
                    if not desc or desc.lower().startswith('linha'):
                        continue
                    
                    # Extrair e validar QTDE
                    qtde_raw = str(row.iloc[col_qtde]).strip() if col_qtde < len(row) and pd.notna(row.iloc[col_qtde]) else ''
                    if not qtde_raw or qtde_raw.lower() in ['nan', '', 'qtde', 'qtde.']:
                        continue
                    
                    # Validar que QTDE é inteiro positivo
                    if not qtde_raw.isdigit():
                        # Pode ser float, tenta converter
                        try:
                            qtde_float = float(qtde_raw.replace(',', '.'))
                            if qtde_float != int(qtde_float):
                                print(f"[LABOTRAT] AVISO: QTDE decimal convertida de '{qtde_raw}' para {int(qtde_float)}")
                            qtde = int(qtde_float)
                        except ValueError:
                            # Se não conseguir converter, pula esta linha (provavelmente é header)
                            continue
                    else:
                        qtde = int(qtde_raw)
                    
                    if qtde <= 0:
                        continue
                    
                    # Extrair PREÇO
                    preco_raw = row.iloc[col_preco] if col_preco < len(row) and pd.notna(row.iloc[col_preco]) else 0.0
                    preco = normalizar_preco(preco_raw) if preco_raw else 0.0
                    
                    # Validar dados mínimos
                    if not ean or not desc:
                        continue
                    
                    dados.append({
                        'CNPJ': cnpj,
                        'EAN': ean,
                        'DESCRICAO': desc,
                        'QTDE': qtde,
                        'PREÇO': preco if preco > 0 else None
                    })
                    
                except Exception as e:
                    print(f"[LABOTRAT] ERRO ao processar linha {idx+1}: {e}")
                    continue
            
            result_df = pd.DataFrame(dados) if dados else None
            if result_df is not None:
                print(f"[LABOTRAT] Formato completo: {len(result_df)} produtos extraídos")
            return result_df
        
        except Exception as e:
            print(f"[LABOTRAT] ERRO ao processar formato completo: {e}")
            return None
    
    def _extrair_cnpj(self, df: pd.DataFrame) -> str | None:
        """Extrai CNPJ da linha 5, coluna 13 (0-based)."""
        try:
            # Linha 5 é índice 4
            if len(df) < 5:
                return None
            
            row = df.iloc[4]
            
            # Coluna 13 (índice 13)
            if 13 < len(row):
                valor = str(row.iloc[13]).strip() if pd.notna(row.iloc[13]) else ''
                cnpj = extract_cnpj(valor)
                if cnpj:
                    return cnpj
            
            return None
        except Exception as e:
            print(f"[LABOTRAT] ERRO ao extrair CNPJ: {e}")
            return None
