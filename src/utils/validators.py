"""Validadores de entrada."""

import re
from difflib import SequenceMatcher
from src.utils.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE


def is_allowed_file(filename: str) -> bool:
    """Verifica se o arquivo tem extensão permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_file_size(file_size: int) -> bool:
    """Verifica se o tamanho do arquivo está dentro do limite."""
    return file_size <= MAX_FILE_SIZE


def sanitize_filename(filename: str) -> str:
    """Sanitiza o nome do arquivo para segurança."""
    # Remove caracteres perigosos
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'[\s]+', '_', filename)
    return filename[:255]  # Limita tamanho


def extract_cnpj(text: str) -> str | None:
    """
    Extrai CNPJ do texto procurando especificamente após "Filial:".
    
    Formatos aceitos:
    - Filial: 001 XX.XXX.XXX/XXXX-XX
    - Filial: XXXXXXXX/XXXX-XX
    - XX.XXX.XXX/XXXX-XX
    - XXXXXXXX/XXXX-XX
    - 19526317000437 (apenas dígitos)
    
    Args:
        text: Texto contendo CNPJ
        
    Returns:
        CNPJ em formato limpo (apenas dígitos) ou None se não encontrado
    """
    if not text:
        return None
    
    # Padrão 1: Busca após "Filial:" - padrão mais específico
    # "Filial: 001 28386809/0001-12" ou "Filial: 28386809/0001-12"
    pattern_filial = r'Filial:\s+\d*\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{8}/\d{4}-\d{2})'
    match = re.search(pattern_filial, text, re.IGNORECASE)
    if match:
        cnpj_formatted = match.group(1)
        return re.sub(r'[^\d]', '', cnpj_formatted)
    
    # Padrão 2: XX.XXX.XXX/XXXX-XX (formato padrão com pontuação)
    pattern2 = r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})'
    match = re.search(pattern2, text)
    if match:
        cnpj_formatted = match.group(1)
        return re.sub(r'[^\d]', '', cnpj_formatted)
    
    # Padrão 3: XXXXXXXX/XXXX-XX ou XXXXXXXX XXXX-XX
    pattern3 = r'(\d{8})[/\s]?(\d{4})-?(\d{2})'
    match = re.search(pattern3, text)
    if match:
        return match.group(1) + match.group(2) + match.group(3)
    
    # Padrão 4: Apenas 14 dígitos isolados no início (CNPJ sem formatação)
    pattern4 = r'(?:^|\s)(\d{14})(?:\s|$)'
    match = re.search(pattern4, text, re.MULTILINE)
    if match:
        cnpj = match.group(1)
        # Valida se parece um CNPJ real (não sequência repetida)
        if cnpj != cnpj[0] * 14:
            return cnpj
    
    return None


def extract_all_cnpjs(text: str) -> dict[str, str] | None:
    """
    Extrai MÚLTIPLOS CNPJs do texto com seus códigos de filial.
    
    Padrão procurado:
    - Filial: 001 XX.XXX.XXX/XXXX-XX
    - Filial: 002 XX.XXX.XXX/XXXX-XX
    - etc.
    
    Args:
        text: Texto contendo múltiplos CNPJs com filiais
        
    Returns:
        Dicionário {filial: cnpj_limpo} ou None se não encontrado
    """
    if not text:
        return None
    
    cnpjs_dict = {}
    
    # Padrão para extrair filial + CNPJ
    # "Filial: 001 XX.XXX.XXX/XXXX-XX" ou "Filial: 001 XXXXXXXX/XXXX-XX"
    pattern = r'Filial:\s+(\d{3})\s+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{8}/\d{4}-\d{2})'
    
    matches = re.finditer(pattern, text, re.IGNORECASE)
    for match in matches:
        filial = match.group(1)
        cnpj_formatted = match.group(2)
        cnpj_limpo = re.sub(r'[^\d]', '', cnpj_formatted)
        
        if cnpj_limpo and len(cnpj_limpo) == 14:
            cnpjs_dict[filial] = cnpj_limpo
    
    return cnpjs_dict if cnpjs_dict else None


def extract_ean13(text: str) -> str | None:
    """
    Extrai EAN-13 do texto buscando por diversos padrões de nome.
    
    Procura por:
    - Código de Barras: XXXXXXXXXXXXX
    - Ref.: XXXXXXXXXXXXX
    - CodBarra: XXXXXXXXXXXXX
    - EAN: XXXXXXXXXXXXX
    - Barras: XXXXXXXXXXXXX
    - etc.
    
    Args:
        text: Texto contendo o EAN-13
        
    Returns:
        EAN-13 (13 dígitos) ou None se não encontrado
    """
    if not text:
        return None
    
    # Lista de variações de nomes para EAN
    variacoes = [
        r'Código\s+de\s+Barras\s*:?\s*(\d{13})',
        r'Codigo\s+de\s+Barras\s*:?\s*(\d{13})',
        r'Código\s+Barras\s*:?\s*(\d{13})',
        r'Codigo\s+Barras\s*:?\s*(\d{13})',
        r'CodBarra\s*:?\s*(\d{13})',
        r'Cod\s+Barra\s*:?\s*(\d{13})',
        r'Ref\.?\s*:?\s*(\d{13})',
        r'Referência\s*:?\s*(\d{13})',
        r'Referencia\s*:?\s*(\d{13})',
        r'EAN\s*:?\s*(\d{13})',
        r'Barras\s*:?\s*(\d{13})',
        r':(\d{13})\s',  # EAN entre dois-pontos com espaço após (formato tabular)
        r'(?:^|\s)(\d{13})(?:\s|$)',  # Apenas 13 dígitos isolados
    ]
    
    for pattern in variacoes:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            ean = match.group(1)
            if is_valid_ean13(ean):
                return ean
    
    return None


def is_valid_ean13(ean: str) -> bool:
    """
    Valida um EAN-13.
    
    Args:
        ean: String com 13 dígitos
        
    Returns:
        True se é um EAN-13 válido, False caso contrário
    """
    if not ean or len(ean) != 13 or not ean.isdigit():
        return False
    
    # Rejeita sequências repetidas
    if ean == ean[0] * 13:
        return False
    
    # Calcula check digit (último dígito)
    soma = 0
    for i in range(12):
        multiplicador = 1 if i % 2 == 0 else 3
        soma += int(ean[i]) * multiplicador
    
    check_digit = (10 - (soma % 10)) % 10
    return int(ean[12]) == check_digit


def extract_numero_pedido(text: str) -> str | None:
    """
    Extrai o número do pedido do texto.
    
    Procura por padrões como:
    - Número Pedido: 085786
    - NÚMERO PEDIDO: 085786
    - Pedido: 085786
    - PEDIDO: 085786
    - NR PEDIDO: 085786
    - etc.
    
    Args:
        text: Texto contendo o número do pedido
        
    Returns:
        Número do pedido (string) ou None se não encontrado
    """
    if not text:
        return None
    
    # Padrões para procurar número do pedido
    patterns = [
        r'(?:Número\s+Pedido|NÚMERO\s+PEDIDO|Numero\s+Pedido|NUMERO\s+PEDIDO)[:\s.]+(\d+)',
        r'(?:NR\.?\s+PEDIDO|NR\s+PEDIDO)[:\s.]+(\d+)',
        r'(?:N[º°]?\s+PEDIDO|N°\s+PEDIDO)[:\s.]+(\d+)',
        r'(?:^|\s)(?:Pedido|PEDIDO)[:\s.]+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            numero = match.group(1).strip()
            if numero:  # Valida que não é vazio
                return numero
    
    return None


def is_valid_cnpj(cnpj: str) -> bool:
    """
    Valida um CNPJ usando o algoritmo de check digits.
    
    Args:
        cnpj: CNPJ em formato limpo (apenas dígitos)
        
    Returns:
        True se é um CNPJ válido, False caso contrário
    """
    if not cnpj or len(cnpj) != 14 or not cnpj.isdigit():
        return False
    
    # Rejeita sequências repetidas (ex: 00000000000000)
    if cnpj == cnpj[0] * 14:
        return False
    
    # Calcula primeiro check digit
    sequencia = '5432109876543'
    soma = sum(int(d) * int(s) for d, s in zip(cnpj[:12], sequencia))
    primeiro_digito = 11 - (soma % 11)
    primeiro_digito = 0 if primeiro_digito > 9 else primeiro_digito
    
    if int(cnpj[12]) != primeiro_digito:
        return False
    
    # Calcula segundo check digit
    sequencia = '6543210987654'
    soma = sum(int(d) * int(s) for d, s in zip(cnpj[:13], sequencia))
    segundo_digito = 11 - (soma % 11)
    segundo_digito = 0 if segundo_digito > 9 else segundo_digito
    
    return int(cnpj[13]) == segundo_digito


def validate_file(filename: str, file_size: int) -> tuple[bool, str]:
    """
    Valida um arquivo completamente.
    
    Returns:
        (is_valid, error_message)
    """
    if not is_allowed_file(filename):
        return False, f"Tipo de arquivo não permitido: {filename}"
    
    if not is_valid_file_size(file_size):
        return False, f"Arquivo muito grande: {filename} (máximo 50MB)"
    
    return True, ""


def extract_multiplicador_fardos(descricao: str) -> tuple[str, int]:
    """
    Extrai multiplicador de fardos da descrição do produto.
    
    Padrões suportados:
    - PRODUTO (12)
    - PRODUTO [12]
    - PRODUTO x12
    - PRODUTO 12un
    - PRODUTO 12 unidades
    
    Args:
        descricao: Descrição do produto
        
    Returns:
        (descricao_limpa, multiplicador)
        Retorna multiplicador=1 se não encontrar padrão
    """
    if not descricao:
        return descricao, 1
    
    # Padrão 1: Número entre parênteses ao final
    match = re.search(r'\(\s*(\d+)\s*\)\s*$', descricao)
    if match:
        mult = int(match.group(1))
        descricao_limpa = re.sub(r'\(\s*\d+\s*\)\s*$', '', descricao).strip()
        return descricao_limpa, mult if mult > 1 else 1
    
    # Padrão 2: Número entre colchetes ao final
    match = re.search(r'\[\s*(\d+)\s*\]\s*$', descricao)
    if match:
        mult = int(match.group(1))
        descricao_limpa = re.sub(r'\[\s*\d+\s*\]\s*$', '', descricao).strip()
        return descricao_limpa, mult if mult > 1 else 1
    
    # Padrão 3: x ou X seguido de número ao final
    match = re.search(r'[xX]\s*(\d+)\s*$', descricao)
    if match:
        mult = int(match.group(1))
        descricao_limpa = re.sub(r'[xX]\s*\d+\s*$', '', descricao).strip()
        return descricao_limpa, mult if mult > 1 else 1
    
    # Padrão 4: Número seguido de 'un' ou 'unidades' ao final
    match = re.search(r'(\d+)\s*(?:un(?:idades)?)\s*$', descricao, re.IGNORECASE)
    if match:
        mult = int(match.group(1))
        descricao_limpa = re.sub(r'\d+\s*(?:un(?:idades)?)\s*$', '', descricao, flags=re.IGNORECASE).strip()
        return descricao_limpa, mult if mult > 1 else 1
    
    return descricao, 1


def normalizar_preco(preco: any) -> float:
    """
    Normaliza preço para float, tratando múltiplos formatos.
    
    Formatos aceitos:
    - 3,99 (vírgula como decimal)
    - 3.99 (ponto como decimal)
    - R$ 3,99
    - R$3,99
    - "3,99" (string)
    
    Args:
        preco: Preço em qualquer formato
        
    Returns:
        Float com o preço normalizado, ou 0.0 se inválido
    """
    try:
        if preco is None or preco == '' or (isinstance(preco, float) and preco == 0):
            return 0.0
        
        # Se já é número, converter
        if isinstance(preco, (int, float)):
            return float(preco)
        
        # Converter para string e limpar
        preco_str = str(preco).strip()
        # Remover espaços (inclui non-breaking space) que às vezes vêm em planilhas
        preco_str = preco_str.replace('\xa0', '').replace(' ', '')
        
        # Remover R$ e espaços
        preco_str = preco_str.replace('R$', '').replace('r$', '').strip()
        
        # Se tem vírgula e ponto, assumir formato brasileiro (3.000,99)
        if ',' in preco_str and '.' in preco_str:
            # Remover ponto (separador de milha) e converter vírgula
            preco_str = preco_str.replace('.', '').replace(',', '.')
        elif ',' in preco_str:
            # Apenas vírgula, converter para ponto
            preco_str = preco_str.replace(',', '.')
        
        return float(preco_str)
    except:
        return 0.0


def similarity_ratio(a: str, b: str) -> float:
    """Calcula a similaridade entre duas strings (0-1)."""
    a_clean = a.lower().strip()
    b_clean = b.lower().strip()
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def find_column_fuzzy(dataframe_columns, target_names: list[str], min_similarity: float = 0.5) -> str | None:
    """
    Encontra uma coluna do DataFrame que melhor corresponde aos nomes de destino.
    Usa fuzzy matching para lidar com variações de nomes.
    
    Args:
        dataframe_columns: Lista de colunas do DataFrame
        target_names: Lista de nomes de coluna esperados (em ordem de preferência)
        min_similarity: Mínima similaridade (0-1) para considerar uma correspondência
        
    Returns:
        Nome da coluna encontrada ou None
    """
    best_match = None
    best_score = min_similarity
    
    for col in dataframe_columns:
        col_clean = col.lower().strip()
        
        for target in target_names:
            target_clean = target.lower().strip()
            score = similarity_ratio(col_clean, target_clean)
            
            # Correspondência exata tem prioridade
            if col_clean == target_clean:
                return col
            
            # Guardar melhor aproximação
            if score > best_score:
                best_score = score
                best_match = col
    
    return best_match


def map_columns(dataframe) -> dict:
    """
    Mapeia as colunas do DataFrame para os nomes padrão esperados.
    Usa fuzzy matching para lidar com variações de nomenclatura.
    
    Mapeamento de possíveis nomes:
    - CODCLI: CODCLI, CODE, CÓD
    - CNPJ: CNPJ
    - EAN: EAN, CÓDIGO, COD_BARRA, CÓDIGO_BARRA
    - DESCRIÇÃO: DESCRIÇÃO, DESCRICAO, MERCADORIA, PRODUTO, NOME
    - QUANTIDADE: QUANTIDADE, QTDE, QT, COMPRA, QUANT
    - VALOR: VALOR, PREÇO, CUSTO, PREÇO_UNITÁRIO, PREÇO_UNIT
    - TOTAL: TOTAL, CUSTO_TOTAL, PREÇO_TOTAL, VALOR_TOTAL
    
    Returns:
        Dicionário mapeando colunas reais para colunas padrão
        Exemplo: {'Mercadoria': 'DESCRICAO', 'Compra': 'QUANTIDADE'}
    """
    cols = list(dataframe.columns)
    mapping = {}  # Mapeamento: coluna_original -> coluna_padrão
    used_cols = set()  # Rastrear colunas já mapeadas
    
    # Definir mapeamentos com ordem de preferência
    standard_columns = {
        'CNPJ': ['CNPJ', 'CNPJ_FILIAL', 'CNPJ_LOJA'],  # CNPJ é único
        'EAN': ['EAN', 'CÓDIGO', 'COD_BARRA', 'CÓDIGO_BARRA', 'BARCODE', 'SKU'],
        'DESCRICAO': ['DESCRIÇÃO', 'DESCRICAO', 'MERCADORIA', 'PRODUTO', 'NOME', 'DESC'],
        'QUANTIDADE': ['QUANTIDADE', 'QTDE', 'QT', 'COMPRA', 'QUANT', 'QTD', 'QUANTIDADE_PEDIDO'],
        'PREÇO': ['PREÇO', 'VALOR', 'CUSTO', 'PREÇO_UNITÁRIO', 'PREÇO_UNIT', 'VALOR_UNITÁRIO', 'VLR_UNIT'],
        'TOTAL': ['TOTAL', 'CUSTO_TOTAL', 'PREÇO_TOTAL', 'VALOR_TOTAL', 'TOTAL_ITEM'],
        'CODCLI': ['CODCLI', 'CODE', 'CÓD', 'CODIGO_CLI', 'CÓDIGO_CLIENTE'],  # CODCLI por último
    }
    
    for standard_name, possible_names in standard_columns.items():
        best_col = None
        best_score = 0.6  # Limiar de similaridade
        
        for col in cols:
            if col in used_cols:  # Pular colunas já mapeadas
                continue
                
            for target in possible_names:
                score = similarity_ratio(col, target)
                if score > best_score:
                    best_score = score
                    best_col = col
        
        if best_col:
            mapping[best_col] = standard_name  # INVERSO: original -> padrão
            used_cols.add(best_col)
    
    return mapping
