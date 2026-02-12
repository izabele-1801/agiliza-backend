"""Processador especializado para Cotefácil."""

import pandas as pd
from io import BytesIO
from .base import FileProcessor
from src.utils.validators import extract_cnpj, extract_ean13, normalizar_preco, extract_multiplicador_fardos


class CotefacilProcessor(FileProcessor):
    """Processa pedidos Cotefácil."""
    
    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame:
        """Processa arquivo Cotefácil e extrai dados estruturados."""
        
        print(f"\n[COTEFACIL] Processando: {filename or 'arquivo'}")
        
        try:
            ext = filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else 'xlsx'
            
            if ext in ['xlsx', 'xls']:
                return self._processar_excel(file_content, ext)
            elif ext == 'pdf':
                return self._processar_pdf(file_content)
            elif ext == 'txt':
                return self._processar_txt(file_content)
            else:
                print(f"[COTEFACIL] ERRO: Extensão não suportada: .{ext}")
                return None
                
        except Exception as e:
            print(f"[COTEFACIL] ERRO: {type(e).__name__}: {str(e)}")
            return None
    
    def _processar_excel(self, file_content: bytes, ext: str) -> pd.DataFrame | None:
        """Processa arquivo Excel Cotefácil."""
        try:
            engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
            
            # Ler primeira linha para extrair CNPJ
            df_cnpj = pd.read_excel(BytesIO(file_content), engine=engine, header=None, nrows=1)
            cnpj = ''
            if not df_cnpj.empty:
                for val in df_cnpj.iloc[0]:
                    if cnpj_temp := extract_cnpj(str(val)):
                        cnpj = cnpj_temp
                        break
            
            print(f"[COTEFACIL] CNPJ extraído: {cnpj}")
            
            # Ler dados com header na linha 2
            df = pd.read_excel(BytesIO(file_content), engine=engine, header=2)
            df.columns = [str(col).strip() for col in df.columns]
            
            return self._extrair_dados(df, cnpj)
            
        except Exception as e:
            print(f"[COTEFACIL] ERRO ao processar Excel: {e}")
            return None
    
    def _processar_pdf(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo PDF Cotefácil."""
        try:
            import pdfplumber
            
            dados = []
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if not texto:
                        continue
                    
                    # Extrair CNPJ da primeira linha com cor diferente (verde)
                    cnpj = ''
                    for linha in texto.split('\n')[:5]:
                        if cnpj_temp := extract_cnpj(linha):
                            cnpj = cnpj_temp
                            break
                    
                    tables = pagina.extract_tables()
                    for table in tables or []:
                        produtos = self._extrair_de_tabela(table, cnpj)
                        dados.extend(produtos)
            
            return pd.DataFrame(dados) if dados else None
            
        except Exception as e:
            print(f"[COTEFACIL] ERRO ao processar PDF: {e}")
            return None
    
    def _processar_txt(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo TXT Cotefácil."""
        try:
            texto = file_content.decode('utf-8', errors='ignore')
            linhas = texto.split('\n')
            
            cnpj = ''
            dados = []
            
            for linha in linhas:
                if not cnpj:
                    if cnpj_temp := extract_cnpj(linha):
                        cnpj = cnpj_temp
                        continue
                
                if cnpj:
                    if produto := self._extrair_linha_produto(linha, cnpj):
                        dados.append(produto)
            
            return pd.DataFrame(dados) if dados else None
            
        except Exception as e:
            print(f"[COTEFACIL] ERRO ao processar TXT: {e}")
            return None
    
    def _extrair_dados(self, df: pd.DataFrame, cnpj: str = '') -> pd.DataFrame | None:
        """Extrai dados estruturados do DataFrame."""
        try:
            if df.empty:
                return None
            
            # Se CNPJ não foi passado, tenta extrair da primeira linha do DataFrame
            if not cnpj:
                for col in df.columns:
                    try:
                        valor = str(df.iloc[0, list(df.columns).index(col)]).strip()
                        if cnpj_temp := extract_cnpj(valor):
                            cnpj = cnpj_temp
                            break
                    except:
                        continue
            
            print(f"[COTEFACIL] CNPJ para dados: {cnpj}")
            
            # Identificar colunas
            col_ean = self._buscar_coluna(df.columns, ['EAN', 'Código', 'Cod'])
            col_desc = self._buscar_coluna(df.columns, ['Produto', 'Descrição', 'Mercadoria'])
            col_qtde = self._buscar_coluna(df.columns, ['Qtde. Ped.', 'Quantidade', 'Qtde'])
            col_preco = self._buscar_coluna(df.columns, ['Valor Un. (R$)', 'Valor', 'Preço'])
            
            if not all([col_ean, col_desc, col_qtde]):
                print("[COTEFACIL] AVISO: Colunas obrigatórias não encontradas")
                return None
            
            dados = []
            for _, row in df.iterrows():
                ean = str(row[col_ean]).strip() if col_ean else ''
                desc = str(row[col_desc]).strip() if col_desc else ''
                qtde_str = str(row[col_qtde]).strip() if col_qtde else '0'
                preco_str = str(row[col_preco]).strip() if col_preco else '0'
                
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
            print(f"[COTEFACIL] ERRO ao extrair dados: {e}")
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
                print(f"[COTEFACIL] AVISO ao processar linha: {e}")
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
            
            for col_lower, col_real in colunas_lower.items():
                if nome_lower in col_lower or col_lower in nome_lower:
                    return col_real
        
        return None
