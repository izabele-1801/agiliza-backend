"""Processador especializado para arquivos Labotrat."""

import pandas as pd
import openpyxl
import xlrd
from io import BytesIO
from .base import FileProcessor


class LabotratProcessor(FileProcessor):
    """Processa arquivos Labotrat extraindo apenas: Nº PEDIDO, CNPJ, Descrição, Qtde."""
    
    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame:
        """Processa arquivo Labotrat Excel. Extrai: Nº PEDIDO, CNPJ, Descrição, Qtde."""
        
        print(f"\n[LABOTRAT] Processando: {filename or 'arquivo'}")
        
        try:
            ext = filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else 'xlsx'
            engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
            df_raw = pd.read_excel(BytesIO(file_content), engine=engine, header=None)
            
            print(f"[LABOTRAT] Arquivo lido: {df_raw.shape[0]} linhas, {df_raw.shape[1]} colunas")
            
            nro_pedido = self._extrair_nro_pedido(df_raw)
            cnpj = self._extrair_cnpj(df_raw)
            
            print(f"[LABOTRAT] Nº PEDIDO: {nro_pedido}, CNPJ: {cnpj}")
            
            header_row_idx = self._encontrar_header_row(df_raw)
            if header_row_idx is None:
                print(f"[LABOTRAT] AVISO: Header não encontrado")
                return None
            
            print(f"[LABOTRAT] Header na linha {header_row_idx + 1}")
            
            df = pd.read_excel(BytesIO(file_content), skiprows=header_row_idx, header=0, engine=engine)
            df.columns = [str(col).strip() for col in df.columns]
            
            print(f"[LABOTRAT] Colunas: {list(df.columns)}")
            
            colunas_necessarias = self._buscar_colunas(df)
            if not colunas_necessarias:
                print(f"[LABOTRAT] AVISO: Colunas necessárias não encontradas")
                return None
            
            df_result = df[colunas_necessarias].copy()
            df_result.insert(0, 'CNPJ', cnpj)
            df_result.insert(0, 'NROPEDIDO', nro_pedido)
            df_result = self._filtrar_linhas_validas(df_result, colunas_necessarias)
            
            df_result.rename(columns={'NROPEDIDO': 'NRO_PEDIDO', 'Descrição': 'DESCRICAO', 'Qtde': 'QTDE'}, inplace=True)
            
            print(f"[LABOTRAT] OK: {len(df_result)} linhas extraídas")
            return df_result if not df_result.empty else None
            
        except Exception as e:
            print(f"[LABOTRAT] ERRO: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _buscar_colunas(self, df: pd.DataFrame) -> list:
        """Busca colunas necessárias (Descrição/DESCRICAO e Qtde/QTDE)."""
        colunas = []
        
        for col in df.columns:
            col_upper = col.upper()
            if col_upper in ['DESCRIÇÃO', 'DESCRICAO']:
                colunas.append(col)
            elif col_upper in ['QTDE', 'QUANTIDADE']:
                colunas.append(col)
        
        return colunas
    
    def _extrair_nro_pedido(self, df: pd.DataFrame) -> str:
        """Extrai Nº PEDIDO da linha 15, colunas D-E (índices 3-4)."""
        try:
            if len(df) < 15:
                return ""
            linha_15 = df.iloc[14]
            valor_d = str(linha_15.iloc[3]).strip() if len(linha_15) > 3 else ""
            valor_e = str(linha_15.iloc[4]).strip() if len(linha_15) > 4 else ""
            nro_pedido = (valor_d + valor_e).strip()
            return nro_pedido if nro_pedido and nro_pedido.lower() != 'nan' else ""
        except Exception as e:
            print(f"[LABOTRAT] AVISO ao extrair Nº PEDIDO: {e}")
            return ""
    
    
    def _extrair_cnpj(self, df: pd.DataFrame) -> str:
        """Extrai CNPJ da linha 5, colunas N-O (índices 13-14)."""
        try:
            if len(df) < 5:
                return ""
            linha_5 = df.iloc[4]
            valor_n = str(linha_5.iloc[13]).strip() if len(linha_5) > 13 else ""
            valor_o = str(linha_5.iloc[14]).strip() if len(linha_5) > 14 else ""
            cnpj = (valor_n + valor_o).strip()
            return cnpj if cnpj and cnpj.lower() != 'nan' else ""
        except Exception as e:
            print(f"[LABOTRAT] AVISO ao extrair CNPJ: {e}")
            return ""
    
    
    def _encontrar_header_row(self, df: pd.DataFrame) -> int | None:
        """Encontra a linha que contém os headers 'Descrição' e 'Qtde'."""
        for idx, row in df.iterrows():
            row_str = ' '.join([str(val).upper() for val in row if pd.notna(val)])
            if 'DESCRIÇÃO' in row_str and 'QTDE' in row_str:
                return idx
        return None
    
    
    def _filtrar_linhas_validas(self, df: pd.DataFrame, colunas_necessarias: list) -> pd.DataFrame:
        """Remove linhas inválidas: vazias ou com títulos de seção."""
        if len(df) == 0:
            return df
        
        keywords_ignorar = ['LINHA', 'ROTINA', 'SEÇÃO', 'CATEGORIA', 'GRUPO']
        col_descricao = next((col for col in df.columns if 'DESC' in col.upper()), None)
        
        df_filtrado = df.copy()
        if col_descricao:
            mask = ~df_filtrado[col_descricao].astype(str).str.upper().isin(keywords_ignorar)
            df_filtrado = df_filtrado[mask]
        
        return df_filtrado.dropna(how='all').reset_index(drop=True)
