"""Gerador de arquivos Excel."""

from io import BytesIO
import pandas as pd


class ExcelGenerator:
    """Gera arquivos Excel a partir de DataFrames."""

    @staticmethod
    def generate(dataframe: pd.DataFrame) -> bytes:
        """
        Gera arquivo Excel em memória.
        
        Args:
            dataframe: DataFrame com os dados
            
        Returns:
            Bytes do arquivo Excel
        """
        if dataframe is None or dataframe.empty:
            return None
        
        buffer = BytesIO()
        dataframe.to_excel(buffer, sheet_name='Pedido', index=False)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def get_filename(dataframe: pd.DataFrame, original_filename: str) -> str:
        """
        Gera nome do arquivo Excel.
        
        Args:
            dataframe: DataFrame com os dados
            original_filename: Nome original do arquivo
            
        Returns:
            Nome do arquivo Excel
        """
        if not dataframe.empty and 'Pedido de compra' in dataframe.columns:
            pedido = dataframe['Pedido de compra'].iloc[0]
            return f"{pedido}.xlsx"
        
        return f"{original_filename.split('.')[0]}.xlsx"
