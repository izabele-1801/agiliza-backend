"""Rotas e endpoints da API - FastAPI."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime
import pandas as pd

from src.processing.pdf_processor import PDFProcessor
from src.processing.txt_processor import TXTProcessor
# Importação lazy do ImageProcessor para evitar carregar torch/easyocr no startup
from src.processing.excel_processor import ExcelProcessor
from src.processing.excel_generator import ExcelGenerator
from src.utils.validators import validate_file

router = APIRouter(prefix="/api", tags=["files"])

pdf_processor = PDFProcessor()
txt_processor = TXTProcessor()
image_processor = None  # Será carregado sob demanda
excel_processor = ExcelProcessor()

def get_image_processor():
    """Carrega ImageProcessor apenas quando necessário"""
    global image_processor
    if image_processor is None:
        from src.processing.image_processor import ImageProcessor
        image_processor = ImageProcessor()
    return image_processor


@router.get("/health")
async def health_check():
    """Endpoint para verificar se a API está respondendo."""
    return {"status": "ok"}


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...), model: str = Form(default="winthor")):
    """Endpoint para upload de arquivos PDF/TXT/Imagem."""
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
    
    if model not in ['winthor', 'planilha']:
        model = 'winthor'  # Padrão se inválido

    all_dataframes = []
    first_filename = None
    errors = []

    for file in files:
        if not file.filename:
            continue

        # Guarda o primeiro nome de arquivo
        if first_filename is None:
            first_filename = file.filename.rsplit('.', 1)[0]

        try:
            # Lê conteúdo
            file_content = await file.read()
            
            # Validação
            is_valid, error_msg = validate_file(file.filename, len(file_content))
            if not is_valid:
                errors.append(error_msg)
                continue

            # Processamento
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            
            if file_ext == 'pdf':
                dataframe = pdf_processor.process(file_content)
            elif file_ext == 'txt':
                dataframe = txt_processor.process(file_content)
            elif file_ext in ['xlsx', 'xls']:
                dataframe = excel_processor.process(file_content, file.filename)
            elif file_ext in ['jpg', 'jpeg', 'png', 'bmp']:
                dataframe = get_image_processor().process(file_content)
            else:
                errors.append(f'{file.filename}: Formato não suportado')
                continue

            if dataframe is None or dataframe.empty:
                errors.append(f'{file.filename}: Nenhum dado extraído')
                continue

            # Processa preços conforme modelo
            dataframe = processar_modelo(dataframe, model)
            all_dataframes.append(dataframe)

        except Exception as e:
            errors.append(f'{file.filename}: {str(e)}')

    # Resposta
    if not all_dataframes:
        error_msg = 'Nenhum arquivo foi processado com sucesso'
        if errors:
            error_msg += ': ' + '; '.join(errors)
        raise HTTPException(status_code=400, detail=error_msg)

    # Se há arquivos processados, avisa dos que falharam mas continua
    warning_msg = None
    if errors:
        warning_msg = 'Arquivos não processados: ' + '; '.join(errors)

    # Combina todos os DataFrames
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Garante que DESCRICAO existe (cria se não existir)
    if 'DESCRICAO' not in combined_df.columns:
        combined_df['DESCRICAO'] = ''
    
    # Remove colunas que possam estar vazias ou não essenciais
    # Mantém todas as colunas que foram adicionadas (PREÇO UNITÁRIO, PREÇO TOTAL, etc)
    colunas_base = ['PEDIDO', 'CODCLI', 'CNPJ', 'EAN', 'DESCRICAO', 'QTDE']
    colunas_finais = [col for col in colunas_base if col in combined_df.columns]
    
    # Adiciona colunas de preço (pode ser PREÇO, PREÇO UNITÁRIO, PREÇO TOTAL, etc)
    for col in combined_df.columns:
        if 'PREÇO' in col and col not in colunas_finais:
            colunas_finais.append(col)
    
    combined_df = combined_df[colunas_finais]
    
    excel_bytes = ExcelGenerator.generate(combined_df)
    
    # Define nome do arquivo com padrão "AgilizaConverter{dd.mm.yyyy}"
    data_atual = datetime.now().strftime("%d.%m.%Y")
    filename = f"AgilizaConverter{data_atual}.xlsx"
    
    # Retorna Excel direto (não ZIP)
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def processar_modelo(df: pd.DataFrame, model: str) -> pd.DataFrame:
    """Processa o DataFrame conforme o modelo escolhido."""
    try:
        df = df.copy()
        
        # Garante que CODCLI está sempre vazio
        if 'CODCLI' in df.columns:
            df['CODCLI'] = ''
        
        # Normaliza colunas de preço
        if 'VALOR_TOTAL' in df.columns and 'PREÇO' not in df.columns:
            # Se tem VALOR_TOTAL, usa como PREÇO
            df['PREÇO'] = df['VALOR_TOTAL']
        
        if model == 'winthor':
            # Preço sempre em branco
            if 'PREÇO' in df.columns:
                df['PREÇO'] = ''
            if 'VALOR_TOTAL' in df.columns:
                df['VALOR_TOTAL'] = ''
            # Reordena colunas para garantir PEDIDO na primeira posição
            colunas = ['PEDIDO', 'CODCLI', 'CNPJ', 'EAN', 'DESCRICAO', 'QTDE', 'TOTAL']
            df = df[[col for col in colunas if col in df.columns]]
        elif model == 'planilha':
            # Usa PREÇO como PREÇO UNITÁRIO e calcula PREÇO TOTAL
            if 'PREÇO' in df.columns and 'QTDE' in df.columns:
                # Renomeia PREÇO para PREÇO UNITÁRIO
                df.rename(columns={'PREÇO': 'PREÇO UNITÁRIO'}, inplace=True)
                # Se não temos VALOR_TOTAL, calcula
                if 'VALOR_TOTAL' not in df.columns:
                    df['PREÇO TOTAL'] = (df['PREÇO UNITÁRIO'] * df['QTDE']).round(2)
                else:
                    df['PREÇO TOTAL'] = df['VALOR_TOTAL']
                # Reordena as colunas (PEDIDO como primeira coluna)
                colunas = ['PEDIDO', 'CODCLI', 'CNPJ', 'EAN', 'DESCRICAO', 'QTDE', 'PREÇO UNITÁRIO', 'PREÇO TOTAL']
                df = df[[col for col in colunas if col in df.columns]]
                
                # Ajusta nomes para atender ao solicitado: PREÇO UNIT. e TOTAL LIQ
                df.rename(columns={'PREÇO UNITÁRIO': 'PREÇO UNIT.', 'PREÇO TOTAL': 'TOTAL LIQ'}, inplace=True)
            else:
                # Se não tem PREÇO/QTDE, reordena mesmo assim para manter PEDIDO na primeira coluna
                colunas = ['PEDIDO', 'CODCLI', 'CNPJ', 'EAN', 'DESCRICAO', 'QTDE', 'PREÇO', 'TOTAL']
                df = df[[col for col in colunas if col in df.columns]]
        
        return df
    except Exception as e:
        raise
