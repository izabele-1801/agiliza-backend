"""Constantes da aplicação."""

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'xlsx', 'xls', 'jpg', 'jpeg', 'png', 'bmp'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Colunas padrão do Excel - com PEDIDO incluído
EXCEL_COLUMNS = [
    'PEDIDO',
    'CODCLI',
    'CNPJ',
    'EAN',
    'DESCRICAO',
    'PREÇO',
    'QTDE',
    'TOTAL'
]
