"""Mapeamento de modelos/fornecedores para processadores específicos."""

# Mapeia modelos para processadores e suas extensões de arquivo esperadas
MODEL_PROCESSOR_MAPPING = {
    # === FORNECEDORES ESPECÍFICOS ===
    'BIOMAXFARMA': {
        'processor': 'biomaxfarma',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para BioMax Farma'
    },
    'COTEFACIL': {
        'processor': 'cotefacil',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para CotefácilProcessor'
    },
    'CRESCER': {
        'processor': 'crescer',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para Crescer'
    },
    'DSGFARMA': {
        'processor': 'dsgfarma',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para DSG Farma'
    },
    'OCEANICA': {
        'processor': 'oceanica',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para Farmácia Oceânica'
    },
    'FARMACIAOCEANICA': {
        'processor': 'oceanica',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para Farmácia Oceânica'
    },
    'KIMBERLY': {
        'processor': 'kimberly',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para Kimberly'
    },
    'LOREAL': {
        'processor': 'loreal',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para L Oréal'
    },
    'NATUSFARMA': {
        'processor': 'natusfarma',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para NatusFarma'
    },
    'POUPAMINAS': {
        'processor': 'poupaminas',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para Poupaminas'
    },
    'PRUDENCE': {
        'processor': 'prudence',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para Prudence'
    },
    'UNILEVER': {
        'processor': 'unilever',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para Unilever'
    },
    'SIAGE': {
        'processor': 'siage',
        'extensions': ['xlsx', 'xls', 'txt', 'pdf'],
        'description': 'Processador especializado para Siage'
    },
    
    # === MODELOS GENÉRICOS ===
    'LABOTRAT': {
        'processor': 'labotrat',
        'extensions': ['xlsx', 'xls'],
        'description': 'Processador especializado para Labotrat'
    },
    'VILA_NOVA': {
        'processor': 'excel',
        'extensions': ['xlsx', 'xls'],
        'description': 'Processador Excel para Vila Nova'
    },
    'VAREJINHO': {
        'processor': 'excel',
        'extensions': ['xlsx', 'xls'],
        'description': 'Processador Excel para Varejinho'
    },
    'WINTHOR': {
        'processor': 'pdf',
        'extensions': ['pdf'],
        'description': 'Processador PDF para Winthor'
    },
    'GENERIC_TXT': {
        'processor': 'txt',
        'extensions': ['txt'],
        'description': 'Processador TXT genérico'
    },
    'GENERIC_EXCEL': {
        'processor': 'excel',
        'extensions': ['xlsx', 'xls'],
        'description': 'Processador Excel genérico'
    },
    'GENERIC_PDF': {
        'processor': 'pdf',
        'extensions': ['pdf'],
        'description': 'Processador PDF genérico'
    },
    'GENERIC_IMAGE': {
        'processor': 'image',
        'extensions': ['jpg', 'jpeg', 'png', 'bmp'],
        'description': 'Processador OCR para imagens'
    }
}

# Mapeamento reverso: extensão → modelo padrão quando não identificado
EXTENSION_DEFAULT_MODEL = {
    'xlsx': 'GENERIC_EXCEL',
    'xls': 'GENERIC_EXCEL',
    'pdf': 'GENERIC_PDF',
    'txt': 'GENERIC_TXT',
    'jpg': 'GENERIC_IMAGE',
    'jpeg': 'GENERIC_IMAGE',
    'png': 'GENERIC_IMAGE',
    'bmp': 'GENERIC_IMAGE'
}

# Processadores disponíveis e seus tipos de arquivo suportados
SUPPORTED_PROCESSORS = {
    'excel': ['xlsx', 'xls'],
    'pdf': ['pdf'],
    'txt': ['txt'],
    'image': ['jpg', 'jpeg', 'png', 'bmp']
}


def detect_model_from_filename(filename: str) -> str:
    """
    Detecta o modelo a partir do nome do arquivo.
    
    Args:
        filename: Nome do arquivo (ex: "pedido_labotrat_123.xlsx")
    
    Returns:
        Model ID em maiúsculas (ex: "LABOTRAT")
    """
    if not filename:
        return 'GENERIC'
    
    filename_upper = filename.upper()
    filename_normalized = filename_upper.replace('_', '').replace('-', '').replace(' ', '')
    
    # Procura por modelo exato nos nomes mapeados
    for model in MODEL_PROCESSOR_MAPPING.keys():
        model_normalized = model.replace('_', '').replace('-', '').replace(' ', '')
        
        # Tenta correspondência direta
        if model in filename_upper:
            return model
        
        # Tenta correspondência normalizada (sem underscores/hífens)
        if model_normalized == filename_normalized or model_normalized in filename_normalized:
            return model
        
        # Tenta correspondência com substituição de _ por espaço
        if model.replace('_', ' ') in filename_upper:
            return model
    
    # Se não encontrar, retorna GENERIC
    return 'GENERIC'


def get_processor_for_model(model: str, file_extension: str = None) -> dict:
    """
    Retorna a configuração do processador para um modelo.
    
    Args:
        model: Model ID (ex: "LABOTRAT")
        file_extension: Extensão do arquivo (ex: "xlsx")
    
    Returns:
        Dict com 'processor' e 'description'
    """
    model_upper = model.upper()
    
    # Se modelo existe na mapping, retorna
    if model_upper in MODEL_PROCESSOR_MAPPING:
        return MODEL_PROCESSOR_MAPPING[model_upper]
    
    # Caso contrário, usa extensão para determinar
    if file_extension:
        ext_lower = file_extension.lower() if isinstance(file_extension, str) else ''
        for model_key, config in MODEL_PROCESSOR_MAPPING.items():
            if ext_lower in config['extensions'] and 'GENERIC' in model_key:
                return config
    
    # Fallback final
    return {
        'processor': 'excel',
        'extensions': ['xlsx', 'xls'],
        'description': 'Processador genérico (fallback)'
    }
