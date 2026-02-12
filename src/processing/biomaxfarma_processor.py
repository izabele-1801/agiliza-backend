"""Processador especializado para BioMax Farma."""

import pandas as pd
import re
from io import BytesIO
from .base import FileProcessor
from src.utils.validators import extract_cnpj, extract_ean13, normalizar_preco, extract_multiplicador_fardos


class BioMaxFarmaProcessor(FileProcessor):
    """Processa pedidos BioMax Farma."""
    
    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame:
        """Processa arquivo BioMax Farma e extrai dados estruturados."""
        
        print(f"\n[BIOMAXFARMA] Processando: {filename or 'arquivo'}")
        
        try:
            ext = filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else 'xlsx'
            
            if ext in ['xlsx', 'xls']:
                return self._processar_excel(file_content, ext)
            elif ext == 'pdf':
                return self._processar_pdf(file_content)
            elif ext == 'txt':
                return self._processar_txt(file_content)
            else:
                print(f"[BIOMAXFARMA] ERRO: Extensão não suportada: .{ext}")
                return None
                
        except Exception as e:
            print(f"[BIOMAXFARMA] ERRO: {type(e).__name__}: {str(e)}")
            return None
    
    def _processar_excel(self, file_content: bytes, ext: str) -> pd.DataFrame | None:
        """Processa arquivo Excel BioMax Farma."""
        try:
            engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
            
            # Extrair CNPJ da primeira linha (metadados)
            df_meta = pd.read_excel(BytesIO(file_content), engine=engine, header=None, nrows=1)
            cnpj_doc = ''
            for col in df_meta.columns:
                valor_meta = str(df_meta.iloc[0, col]).strip()
                if cnpj_temp := extract_cnpj(valor_meta):
                    cnpj_doc = cnpj_temp
                    break
            
            # BioMax tem metadados na linha 0, headers na linha 1
            df = pd.read_excel(BytesIO(file_content), engine=engine, header=1)
            
            # Normalizar nomes de colunas
            df.columns = [str(col).strip() for col in df.columns]
            
            # Se conseguiu CNPJ dos metadados, usar esse
            if cnpj_doc:
                # Pré-preencher com CNPJ extraído dos metadados
                df['CNPJ_METADATA'] = cnpj_doc
            
            return self._extrair_dados(df)
            
        except Exception as e:
            print(f"[BIOMAXFARMA] ERRO ao processar Excel: {e}")
            return None
    
    def _processar_pdf(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo PDF BioMax Farma."""
        try:
            import pdfplumber
            
            dados = []
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if not texto:
                        continue
                    
                    # Extrair CNPJ da primeira linha
                    linhas = texto.split('\n')
                    cnpj = ''
                    for linha in linhas[:5]:
                        cnpj_temp = extract_cnpj(linha)
                        if cnpj_temp:
                            cnpj = cnpj_temp
                            break
                    
                    # Extrair tabela
                    tables = pagina.extract_tables()
                    for table in tables or []:
                        produtos = self._extrair_de_tabela(table, cnpj)
                        dados.extend(produtos)
            
            return pd.DataFrame(dados) if dados else None
            
        except Exception as e:
            print(f"[BIOMAXFARMA] ERRO ao processar PDF: {e}")
            return None
    
    def _processar_txt(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo TXT BioMax Farma."""
        try:
            texto = file_content.decode('utf-8', errors='ignore')
            linhas = texto.split('\n')
            
            cnpj = ''
            dados = []
            
            for linha in linhas:
                if not cnpj:
                    cnpj_temp = extract_cnpj(linha)
                    if cnpj_temp:
                        cnpj = cnpj_temp
                        continue
                
                # Processar linhas de produto
                if cnpj:
                    produto = self._extrair_linha_produto(linha, cnpj)
                    if produto:
                        dados.append(produto)
            
            return pd.DataFrame(dados) if dados else None
            
        except Exception as e:
            print(f"[BIOMAXFARMA] ERRO ao processar TXT: {e}")
            return None
    
    def _extrair_dados(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """Extrai dados estruturados do DataFrame."""
        try:
            if df.empty:
                return None
            
            # Extrair CNPJ (preferir dos metadados se disponível)
            cnpj = ''
            if 'CNPJ_METADATA' in df.columns:
                cnpj = df['CNPJ_METADATA'].iloc[0]
            else:
                for col in df.columns:
                    valor = str(df.iloc[0, list(df.columns).index(col)]).strip()
                    if cnpj_temp := extract_cnpj(valor):
                        cnpj = cnpj_temp
                        break
            
            # Identificar colunas
            col_ean = self._buscar_coluna(df.columns, ['Código de Barras', 'EAN', 'Código', 'Barras'])
            col_desc = self._buscar_coluna(df.columns, ['Descrição', 'Produto', 'Mercadoria'])
            col_qtde = self._buscar_coluna(df.columns, ['Quantidade UN', 'Quantidade', 'Qtde'])
            col_preco = self._buscar_coluna(df.columns, ['Custo UN', 'Custo', 'Preço'])
            
            if not all([col_ean, col_desc, col_qtde]):
                print("[BIOMAXFARMA] AVISO: Colunas obrigatórias não encontradas")
                return None
            
            dados = []
            for _, row in df.iterrows():
                ean = str(row[col_ean]).strip() if col_ean else ''
                desc = str(row[col_desc]).strip() if col_desc else ''
                qtde_str = str(row[col_qtde]).strip() if col_qtde else '0'
                preco_str = str(row[col_preco]).strip() if col_preco else '0'
                
                # Validar campos obrigatórios
                if not ean or not desc or not qtde_str:
                    continue
                
                ean = extract_ean13(ean) or ean
                if not ean.isdigit() or len(ean) < 13:
                    continue
                
                try:
                    qtde = int(float(qtde_str.replace(',', '.')))
                except:
                    continue
                
                if qtde <= 0:
                    continue
                
                desc_limpa, multiplicador = extract_multiplicador_fardos(desc)
                qtde = qtde * multiplicador
                
                preco = normalizar_preco(preco_str) if col_preco else 0.0
                
                dados.append({
                    'CNPJ': cnpj,
                    'EAN': ean,
                    'DESCRICAO': desc_limpa.strip(),
                    'QTDE': qtde,
                    'PREÇO': preco if preco > 0 else None
                })
            
            return pd.DataFrame(dados) if dados else None
            
        except Exception as e:
            print(f"[BIOMAXFARMA] ERRO ao extrair dados: {e}")
            return None
    
    def _extrair_de_tabela(self, table: list, cnpj: str) -> list:
        """Extrai dados de tabelas PDF."""
        dados = []
        
        for row in table:
            if not row or len(row) < 3:
                continue
            
            try:
                ean_str = str(row[0]).strip() if row[0] else ''
                desc_str = str(row[1]).strip() if row[1] else ''
                qtde_str = str(row[2]).strip() if row[2] else ''
                preco_str = str(row[3]).strip() if len(row) > 3 else '0'
                
                ean = extract_ean13(ean_str) or ean_str
                if not ean or not ean.isdigit() or len(ean) < 13:
                    continue
                
                if not desc_str:
                    continue
                
                qtde = int(float(qtde_str.replace(',', '.')))
                if qtde <= 0:
                    continue
                
                desc_limpa, multiplicador = extract_multiplicador_fardos(desc_str)
                qtde = qtde * multiplicador
                
                preco = normalizar_preco(preco_str)
                
                dados.append({
                    'CNPJ': cnpj,
                    'EAN': ean,
                    'DESCRICAO': desc_limpa.strip(),
                    'QTDE': qtde,
                    'PREÇO': preco if preco > 0 else None
                })
            except Exception as e:
                print(f"[BIOMAXFARMA] AVISO ao processar linha: {e}")
                continue
        
        return dados
    
    def _extrair_linha_produto(self, linha: str, cnpj: str) -> dict | None:
        """Extrai produto de uma linha TXT."""
        try:
            ean = extract_ean13(linha)
            if not ean:
                return None
            
            partes = linha.split()
            if len(partes) < 3:
                return None
            
            desc = ' '.join(partes[1:-2]) if len(partes) > 2 else ''
            
            try:
                qtde = int(partes[-1])
            except:
                return None
            
            if qtde <= 0 or not desc:
                return None
            
            desc_limpa, multiplicador = extract_multiplicador_fardos(desc)
            qtde = qtde * multiplicador
            
            return {
                'CNPJ': cnpj,
                'EAN': ean,
                'DESCRICAO': desc_limpa.strip(),
                'QTDE': qtde,
                'PREÇO': None
            }
            
        except Exception:
            return None
    
    def _buscar_coluna(self, colunas, nomes_possiveis: list) -> str | None:
        """Busca coluna por nomes possíveis (fuzzy matching)."""
        colunas_lower = {col.lower().strip(): col for col in colunas}
        
        for nome in nomes_possiveis:
            nome_lower = nome.lower().strip()
            if nome_lower in colunas_lower:
                return colunas_lower[nome_lower]
            
            # Fuzzy matching
            for col_lower, col_real in colunas_lower.items():
                if nome_lower in col_lower or col_lower in nome_lower:
                    return col_real
        
        return None
