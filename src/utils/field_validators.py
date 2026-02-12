"""Validadores e normalizadores de campos obrigatórios."""

import re
from typing import Optional, Tuple


class FieldValidators:
    """Validação e normalização de campos obrigatórios."""
    
    @staticmethod
    def validate_cnpj(cnpj: str) -> Optional[str]:
        """
        Valida e normaliza CNPJ.
        
        Aceita formatos:
        - xxxxxxxxxxxxxx (14 dígitos)
        - xx.xxx.xxx/xxxx-xx
        - xxxxxxxx/xxxx-xx
        - xxxxxxxx/xxxxxx
        
        Returns: CNPJ normalizado (14 dígitos) ou None se inválido
        """
        if not cnpj:
            return None
        
        # Extrai apenas números
        cnpj_clean = re.sub(r'[^\d]', '', str(cnpj))
        
        # Deve ter exatamente 14 dígitos
        if len(cnpj_clean) != 14:
            return None
        
        # Rejeita sequências repetidas (ex: 00000000000000)
        if cnpj_clean == cnpj_clean[0] * 14:
            return None
        
        return cnpj_clean
    
    @staticmethod
    def validate_ean(ean: str) -> Optional[str]:
        """
        Valida e normaliza EAN.
        
        Deve conter apenas números, sem vírgulas, pontos ou espaços.
        Aceita EAN-13 (13 dígitos) ou EAN-14 (14 dígitos).
        
        Returns: EAN normalizado ou None se inválido
        """
        if not ean:
            return None
        
        # Remove espaços e caracteres especiais (MAS apenas de formatação)
        ean_clean = re.sub(r'[^\d]', '', str(ean).strip())
        
        # Deve ter 13 ou 14 dígitos
        if len(ean_clean) not in [13, 14]:
            return None
        
        # Rejeita sequências repetidas
        if ean_clean == ean_clean[0] * len(ean_clean):
            return None
        
        return ean_clean
    
    @staticmethod
    def validate_descricao(descricao: str) -> Optional[str]:
        """
        Valida e normaliza descrição do produto.
        
        Deve ser texto não-vazio após limpeza.
        Remove espaços extras.
        
        Returns: Descrição normalizada ou None se vazia
        """
        if not descricao:
            return None
        
        # Limpa espaços extras
        desc_clean = ' '.join(str(descricao).split())
        
        # Rejeita se ficar vazio após limpeza
        if not desc_clean or len(desc_clean) < 2:
            return None
        
        # Limita a 255 caracteres
        return desc_clean[:255]
    
    @staticmethod
    def validate_quantidade(quantidade) -> Optional[int]:
        """
        Valida e normaliza quantidade.
        
        Deve ser número inteiro positivo (não decimal).
        Não pode ser negativo ou zero.
        
        Returns: Quantidade como inteiro ou None se inválido
        """
        if quantidade is None or quantidade == '':
            return None
        
        try:
            # Converte para float primeiro (para aceitar "10.0")
            qtd_float = float(str(quantidade).replace(',', '.'))
            qtd_int = int(qtd_float)
            
            # Rejeita decimais (se não for inteiro exato)
            if qtd_float != qtd_int:
                return None
            
            # Deve ser positivo
            if qtd_int <= 0:
                return None
            
            # Limite razoável (99999 unidades)
            if qtd_int > 99999:
                return None
            
            return qtd_int
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def validate_preco(preco) -> Optional[float]:
        """
        Valida e normaliza preço.
        
        Aceita formatos:
        - 10,50 (vírgula como decimal)
        - 10.50 (ponto como decimal)
        - R$ 10,50
        - 1.234,56 (formato brasileiro com milhares)
        
        Não pode ser negativo.
        
        Returns: Preço como float ou None se inválido
        """
        if preco is None or preco == '':
            return 0.0
        
        try:
            preco_str = str(preco).strip()
            
            # Remove símbolo de moeda
            preco_str = preco_str.replace('R$', '').replace('r$', '').strip()
            
            # Se tem vírgula e ponto, assumir formato brasileiro (1.234,56)
            if ',' in preco_str and '.' in preco_str:
                preco_str = preco_str.replace('.', '').replace(',', '.')
            elif ',' in preco_str:
                # Apenas vírgula: converter para ponto
                preco_str = preco_str.replace(',', '.')
            
            preco_float = float(preco_str)
            
            # Não pode ser negativo
            if preco_float < 0:
                return None
            
            return round(preco_float, 2)
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def validate_row(row: dict, required_fields: list = None, optional_fields: list = None) -> Tuple[bool, dict]:
        """
        Valida uma linha completa de dados.
        
        Args:
            row: Dicionário com dados da linha
            required_fields: Lista de campos obrigatórios
            optional_fields: Lista de campos opcionais
            
        Returns:
            (é_válido, dados_normalizados)
        """
        if required_fields is None:
            required_fields = ['CNPJ', 'EAN', 'DESCRICAO', 'QUANT']
        
        if optional_fields is None:
            optional_fields = ['PRECO']
        
        normalized = {}
        
        # Validar campos obrigatórios
        if cnpj := FieldValidators.validate_cnpj(row.get('CNPJ', '')):
            normalized['CNPJ'] = cnpj
        else:
            return False, {}
        
        if ean := FieldValidators.validate_ean(row.get('EAN', '')):
            normalized['EAN'] = ean
        else:
            return False, {}
        
        if desc := FieldValidators.validate_descricao(row.get('DESCRICAO', '')):
            normalized['DESCRICAO'] = desc
        else:
            return False, {}
        
        if quant := FieldValidators.validate_quantidade(row.get('QUANT', '')):
            normalized['QUANT'] = quant
        else:
            return False, {}
        
        # Validar campos opcionais
        if 'PRECO' in optional_fields:
            if preco := FieldValidators.validate_preco(row.get('PRECO', 0.0)):
                normalized['PRECO'] = preco
        
        return True, normalized


# Aliases para uso direto
validate_cnpj = FieldValidators.validate_cnpj
validate_ean = FieldValidators.validate_ean
validate_descricao = FieldValidators.validate_descricao
validate_quantidade = FieldValidators.validate_quantidade
validate_preco = FieldValidators.validate_preco
validate_row = FieldValidators.validate_row
