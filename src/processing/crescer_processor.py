"""Processador especializado para Crescer."""

import pandas as pd
import re
from io import BytesIO
from .base import FileProcessor
from src.utils.validators import extract_cnpj, extract_ean13, normalizar_preco


class CrescerProcessor(FileProcessor):
    """Processa pedidos Crescer."""
    
    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame:
        """Processa arquivo Crescer e extrai dados estruturados."""
        print(f"\n[CRESCER] Processando: {filename or 'arquivo'}")
        
        try:
            ext = filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else 'xlsx'
            
            if ext in ['xlsx', 'xls']:
                return self._processar_excel(file_content, ext)
            elif ext == 'pdf':
                return self._processar_pdf(file_content)
            elif ext == 'txt':
                return self._processar_txt(file_content)
            else:
                return None
                
        except Exception as e:
            print(f"[CRESCER] ERRO: {type(e).__name__}: {str(e)}")
            return None
    
    def _processar_excel(self, file_content: bytes, ext: str) -> pd.DataFrame | None:
        """Processa arquivo Excel Crescer (Cód. Barra, Descrição, Qtd)."""
        try:
            engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
            
            # Extrair CNPJ da linha 6, coluna D (índice 3)
            df_cnpj = pd.read_excel(BytesIO(file_content), engine=engine, header=None, nrows=7)
            cnpj = ''
            if len(df_cnpj) > 6 and len(df_cnpj.columns) > 3:
                cnpj_raw = df_cnpj.iloc[6, 3]
                if pd.notna(cnpj_raw):
                    cnpj_str = str(cnpj_raw).strip()
                    # Remover formatação xxx/xxx-xx -> xxxxxxxxxx
                    cnpj = cnpj_str.replace('/', '').replace('-', '')
                    print(f"[CRESCER] CNPJ extraído: {cnpj_str} -> {cnpj}")
            
            # Ler dados com header na linha 11
            df = pd.read_excel(BytesIO(file_content), engine=engine, header=11)
            df.columns = [str(col).strip() for col in df.columns]
            return self._extrair_dados(df, cnpj)
        except Exception as e:
            print(f"[CRESCER] ERRO ao processar Excel: {e}")
            return None
    
    def _processar_pdf(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo PDF Crescer."""
        try:
            import pdfplumber
            
            dados = []
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if not texto:
                        continue
                    
                    # Extrair CNPJ: linha "Filial", após três números no formato xxxxxxxx/xxxx-xx
                    cnpj = self._extrair_cnpj_crescer(texto)
                    
                    tables = pagina.extract_tables()
                    for table in tables or []:
                        produtos = self._extrair_de_tabela(table, cnpj)
                        dados.extend(produtos)
            
            return pd.DataFrame(dados) if dados else None
        except Exception as e:
            print(f"[CRESCER] ERRO ao processar PDF: {e}")
            return None
    
    def _processar_txt(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo TXT Crescer."""
        try:
            texto = file_content.decode('utf-8', errors='ignore')
            linhas = texto.split('\n')
            
            cnpj = self._extrair_cnpj_crescer(texto)
            dados = []
            
            for linha in linhas:
                if cnpj and (produto := self._extrair_linha_produto(linha, cnpj)):
                    dados.append(produto)
            
            return pd.DataFrame(dados) if dados else None
        except Exception as e:
            print(f"[CRESCER] ERRO ao processar TXT: {e}")
            return None
    
    def _extrair_dados(self, df: pd.DataFrame, cnpj: str = "") -> pd.DataFrame | None:
        """Extrai dados do DataFrame Crescer."""
        try:
            if df.empty:
                return None
            
            print(f"[CRESCER] CNPJ recebido: {cnpj}")
            
            # Identificar colunas pelo nome
            col_ean = self._buscar_coluna(df.columns, ['Cód. Barra', 'Código','Código Barra', 'EAN'])
            col_desc = self._buscar_coluna(df.columns, ['Unnamed: 4', 'Descrição', 'Produto'])  # Unnamed: 4 é coluna E
            col_qtde = self._buscar_coluna(df.columns, ['Qtd.', 'Quantidade', 'Qtde'])
            col_preco = self._buscar_coluna(df.columns, ['Emb', 'Unitário', 'Preço'])  # Emb é onde está o preço unitário
            
            print(f"[CRESCER] Colunas found: EAN={col_ean}, DESC={col_desc}, QTDE={col_qtde}, PRECO={col_preco}")
            
            if not all([col_ean, col_desc, col_qtde]):
                print("[CRESCER] AVISO: Colunas obrigatórias não encontradas")
                return None
            
            dados = []
            for _, row in df.iterrows():
                ean = extract_ean13(str(row[col_ean]).strip()) or str(row[col_ean]).strip()
                desc = str(row[col_desc]).strip() if col_desc else ''
                
                try:
                    qtde = int(float(str(row[col_qtde]).replace(',', '.')))
                except:
                    continue
                
                if not ean or not desc or qtde <= 0:
                    continue
                
                preco = normalizar_preco(row[col_preco]) if col_preco and qtde > 0 else 0.0
                
                dados.append({
                    'CNPJ': cnpj,
                    'EAN': ean,
                    'DESCRICAO': desc,
                    'QTDE': qtde,
                    'PREÇO': preco if preco > 0 else None
                })
            
            print(f"[CRESCER] Total de produtos extraídos: {len(dados)}")
            return pd.DataFrame(dados) if dados else None
        except Exception as e:
            print(f"[CRESCER] ERRO ao extrair dados: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extrair_cnpj_crescer(self, texto: str) -> str:
        """Extrai CNPJ no formato específico Crescer."""
        match = re.search(r'Filial.*?(\d{8}/\d{4}-\d{2})', texto)
        if match:
            return match.group(1).replace('/', '').replace('-', '')
        return ''
    
    def _extrair_de_tabela(self, table: list, cnpj: str) -> list:
        """Extrai dados de tabelas PDF."""
        dados = []
        for row in table:
            if not row or len(row) < 3:
                continue
            try:
                ean = extract_ean13(str(row[0]).strip()) or str(row[0]).strip()
                desc = str(row[1]).strip() if row[1] else ''
                qtde = int(float(str(row[2]).replace(',', '.')))
                
                if not ean or not desc or qtde <= 0:
                    continue
                
                preco = normalizar_preco(row[3]) if len(row) > 3 else 0.0
                
                dados.append({
                    'CNPJ': cnpj,
                    'EAN': ean,
                    'DESCRICAO': desc,
                    'QTDE': qtde,
                    'PREÇO': preco if preco > 0 else None
                })
            except:
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
            
            desc = ' '.join(partes[1:-1])
            qtde = int(partes[-1])
            
            if qtde <= 0 or not desc:
                return None
            
            return {
                'CNPJ': cnpj,
                'EAN': ean,
                'DESCRICAO': desc,
                'QTDE': qtde,
                'PREÇO': None
            }
        except:
            return None
    
    def _buscar_coluna(self, colunas, nomes_possiveis: list) -> str | None:
        """Busca coluna por nomes possíveis."""
        colunas_lower = {col.lower().strip(): col for col in colunas}
        for nome in nomes_possiveis:
            nome_lower = nome.lower().strip()
            if nome_lower in colunas_lower:
                return colunas_lower[nome_lower]
            for col_lower, col_real in colunas_lower.items():
                if nome_lower in col_lower:
                    return col_real
        return None
