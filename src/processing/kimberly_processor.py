"""Processador especializado para Kimberly."""

import pandas as pd
from io import BytesIO
from .base import FileProcessor
from src.utils.validators import extract_cnpj, extract_ean13, normalizar_preco, extract_multiplicador_fardos


class KimberlyProcessor(FileProcessor):
    """Processa pedidos Kimberly."""
    
    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame:
        """Processa arquivo Kimberly e extrai dados estruturados."""
        print(f"\n[KIMBERLY] Processando: {filename or 'arquivo'}")
        
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
            print(f"[KIMBERLY] ERRO: {type(e).__name__}: {str(e)}")
            return None
    
    def _processar_excel(self, file_content: bytes, ext: str) -> pd.DataFrame | None:
        """Processa arquivo Excel Kimberly."""
        try:
            engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
            df = pd.read_excel(BytesIO(file_content), engine=engine)
            df.columns = [str(col).strip() for col in df.columns]
            return self._extrair_dados(df)
        except Exception as e:
            print(f"[KIMBERLY] ERRO ao processar Excel: {e}")
            return None
    
    def _processar_pdf(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo PDF Kimberly."""
        try:
            import pdfplumber
            dados = []
            
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if not texto:
                        continue
                    
                    # Extrair CNPJ em coluna "CnpjFilial"
                    cnpj = extract_cnpj(texto) or ''
                    tables = pagina.extract_tables()
                    for table in tables or []:
                        produtos = self._extrair_de_tabela(table, cnpj)
                        dados.extend(produtos)
            
            return pd.DataFrame(dados) if dados else None
        except Exception as e:
            print(f"[KIMBERLY] ERRO ao processar PDF: {e}")
            return None
    
    def _processar_txt(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo TXT Kimberly."""
        try:
            texto = file_content.decode('utf-8', errors='ignore')
            linhas = texto.split('\n')
            
            cnpj = extract_cnpj(texto) or ''
            dados = []
            
            for linha in linhas:
                if cnpj and (produto := self._extrair_linha_produto(linha, cnpj)):
                    dados.append(produto)
            
            return pd.DataFrame(dados) if dados else None
        except Exception as e:
            print(f"[KIMBERLY] ERRO ao processar TXT: {e}")
            return None
    
    def _extrair_dados(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """Extrai dados do DataFrame Kimberly."""
        try:
            if df.empty:
                return None
            
            cnpj = ''
            # Procurar coluna CnpjFilial
            col_temp = self._buscar_coluna(df.columns, ['CnpjFilial', 'CNPJ'])
            if col_temp:
                for val in df[col_temp].head(10):
                    if cnpj_temp := extract_cnpj(str(val)):
                        cnpj = cnpj_temp
                        break
            
            col_ean = self._buscar_coluna(df.columns, ['CodBarra', 'Código', 'EAN'])
            col_desc = self._buscar_coluna(df.columns, ['DescricaoProduto', 'Descrição', 'Produto'])
            col_qtde = self._buscar_coluna(df.columns, ['QtPedido', 'Quantidade', 'Qtde'])
            col_preco = self._buscar_coluna(df.columns, ['PRECO', 'Preço', 'Custo'])
            
            if not all([col_ean, col_desc, col_qtde]):
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
                
                desc_limpa, mult = extract_multiplicador_fardos(desc)
                qtde = qtde * mult
                preco = normalizar_preco(row[col_preco]) if col_preco else 0.0
                
                dados.append({
                    'CNPJ': cnpj,
                    'EAN': ean,
                    'DESCRICAO': desc_limpa.strip(),
                    'QTDE': qtde,
                    'PREÇO': preco if preco > 0 else None
                })
            
            return pd.DataFrame(dados) if dados else None
        except Exception as e:
            print(f"[KIMBERLY] ERRO ao extrair dados: {e}")
            return None
    
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
                
                desc_limpa, mult = extract_multiplicador_fardos(desc)
                qtde = qtde * mult
                preco = normalizar_preco(row[3]) if len(row) > 3 else 0.0
                
                dados.append({
                    'CNPJ': cnpj,
                    'EAN': ean,
                    'DESCRICAO': desc_limpa.strip(),
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
            
            desc_limpa, mult = extract_multiplicador_fardos(desc)
            qtde = qtde * mult
            
            return {
                'CNPJ': cnpj,
                'EAN': ean,
                'DESCRICAO': desc_limpa.strip(),
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
