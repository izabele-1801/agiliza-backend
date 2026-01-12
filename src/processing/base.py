"""Processador base - Interface comum para todos os processadores."""

from abc import ABC, abstractmethod
import pandas as pd


class FileProcessor(ABC):
    """Interface para processadores de arquivo."""

    @abstractmethod
    def process(self, file_content: bytes) -> pd.DataFrame | None:
        """
        Processa o arquivo e retorna um DataFrame.
        
        Args:
            file_content: Conteúdo do arquivo em bytes
            
        Returns:
            DataFrame com dados processados ou None se erro
        """
        pass
