"""Rotas e endpoints da API - FastAPI."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime
import pandas as pd

from src.processing.pdf_processor import PDFProcessor
from src.processing.txt_processor import TXTProcessor
from src.processing.excel_processor import ExcelProcessor
from src.processing.labotrat_processor import LabotratProcessor
from src.processing.excel_generator import ExcelGenerator
from src.processing.factory import get_processor, PROCESSOR_CLASSES
from src.utils.validators import validate_file
from src.config.model_processor_mapping import (
    detect_model_from_filename,
    get_processor_for_model,
    MODEL_PROCESSOR_MAPPING
)

router = APIRouter(prefix="/api", tags=["files"])

# Processadores genéricos iniciados uma vez
pdf_processor = PDFProcessor()
txt_processor = TXTProcessor()
image_processor = None  # Será carregado sob demanda
excel_processor = ExcelProcessor()
labotrat_processor = LabotratProcessor()

# Cache de processadores especializados
specialized_processors = {}

def get_image_processor():
    """Carrega ImageProcessor apenas quando necessário"""
    global image_processor
    if image_processor is None:
        from src.processing.image_processor import ImageProcessor
        image_processor = ImageProcessor()
    return image_processor


def get_available_processor(detected_model: str, file_ext: str):
    """
    Obtém o processador apropriado: especializado se disponível, senão genérico.
    
    Args:
        detected_model: Modelo detectado (ex: 'BIOMAXFARMA')
        file_ext: Extensão do arquivo (ex: 'xlsx')
    
    Returns:
        Tuple (processor, processor_type, is_specialized)
    """
    model_upper = detected_model.upper()
    processor_config = get_processor_for_model(model_upper, file_ext)
    processor_type = processor_config['processor']
    
    print(f"[GET_PROCESSOR] Modelo: {model_upper}, Extensão: {file_ext}")
    print(f"[GET_PROCESSOR] Tipo configurado: {processor_type}")
    
    # Tenta usar processador especializado
    if processor_type in PROCESSOR_CLASSES:
        # Verifica se é um processador especializado (não genérico)
        if processor_type not in ['pdf', 'txt', 'excel', 'image']:
            if processor_type not in specialized_processors:
                specialized_processors[processor_type] = get_processor(processor_type)
            processor_instance = specialized_processors[processor_type]
            if processor_instance:
                print(f"[GET_PROCESSOR] ✓ Usando processador ESPECIALIZADO: {processor_type}")
                return processor_instance, processor_type, True
    
    # Fallback para processadores genéricos
    if processor_type == 'pdf':
        print(f"[GET_PROCESSOR] ✓ Usando processador genérico: pdf")
        return pdf_processor, processor_type, False
    elif processor_type == 'txt':
        print(f"[GET_PROCESSOR] ✓ Usando processador genérico: txt")
        return txt_processor, processor_type, False
    elif processor_type == 'excel':
        print(f"[GET_PROCESSOR] ✓ Usando processador genérico: excel")
        return excel_processor, processor_type, False
    elif processor_type == 'image':
        print(f"[GET_PROCESSOR] ✓ Usando processador genérico: image")
        return get_image_processor(), processor_type, False
    elif processor_type == 'labotrat':
        print(f"[GET_PROCESSOR] ✓ Usando processador genérico: labotrat")
        return labotrat_processor, processor_type, False
    
    # Fallback final
    print(f"[GET_PROCESSOR] ⚠ Fallback to excel")
    return excel_processor, 'excel', False


@router.get("/health")
async def health_check():
    """Endpoint para verificar se a API está respondendo."""
    return {"status": "ok"}


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...), model: str = Form(default="winthor")):
    """Endpoint para upload de arquivos PDF/TXT/Imagem com roteamento por modelo."""
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
    
    if model not in ['winthor', 'planilha']:
        model = 'winthor'  # Padrão se inválido

    all_dataframes = []
    first_filename = None
    errors = []
    model_processor_info = []  # Rastreia qual processador foi usado para cada arquivo

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

            # ===== DETECÇÃO DE MODELO E ROTEAMENTO =====
            detected_model = detect_model_from_filename(file.filename)
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
            processor_config = get_processor_for_model(detected_model, file_ext)
            processor_type = processor_config['processor']
            processor_desc = processor_config['description']
            
            print(f"\n[ROTEAMENTO] Arquivo: {file.filename}")
            print(f"[ROTEAMENTO] Modelo detectado: {detected_model}")
            print(f"[ROTEAMENTO] Processador: {processor_type} - {processor_desc}")
            
            # Obtém o processador apropriado
            processor_instance, actual_processor_type, is_specialized = get_available_processor(detected_model, file_ext)
            
            if is_specialized:
                print(f"[ROTEAMENTO] ✓ Usando processador ESPECIALIZADO para {detected_model}")
            
            # Processamento com processador obtido
            dataframe = processor_instance.process(file_content, file.filename)
            
            if dataframe is None or dataframe.empty:
                # Tenta processador genérico se especializado falhou
                if is_specialized:
                    print(f"[ROTEAMENTO] ⚠ Processador especializado falhou, tentando genérico...")
                    processor_instance, actual_processor_type, _ = get_available_processor('GENERIC', file_ext)
                    dataframe = processor_instance.process(file_content, file.filename)
            
            if dataframe is None or dataframe.empty:
                errors.append(f'{file.filename}: Nenhum dado extraído')
                continue

            # DEBUG: Mostrar dados logo após processador
            print(f"\n[UPLOAD] Após processador:")
            print(f"[UPLOAD] Colunas: {list(dataframe.columns)}")
            if 'QTDE' in dataframe.columns:
                print(f"[UPLOAD] QTDE (primeiras 3): {dataframe['QTDE'].head(3).tolist()}")
            if 'PREÇO' in dataframe.columns:
                print(f"[UPLOAD] PREÇO (primeiras 3): {dataframe['PREÇO'].head(3).tolist()}")
            print(f"[UPLOAD] Shape: {dataframe.shape}")
            print(f"[UPLOAD] Dtypes:\n{dataframe.dtypes}")

            # Adiciona coluna com informação do modelo e processador
            dataframe['MODELO'] = detected_model
            dataframe['PROCESSADOR'] = processor_type
            
            # Colunas padrão não precisam mais de PEDIDO/CODCLI
            
            # Processa preços conforme modelo de negócio (winthor ou planilha)
            dataframe = processar_modelo(dataframe, model)
            all_dataframes.append(dataframe)
            
            # Rastreia qual processador foi usado
            model_processor_info.append({
                'arquivo': file.filename,
                'modelo': detected_model,
                'processador': processor_type,
                'descricao': processor_desc
            })

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
    colunas_base = ['MODELO', 'PROCESSADOR', 'CNPJ', 'EAN', 'DESCRICAO', 'QTDE']
    colunas_finais = [col for col in colunas_base if col in combined_df.columns]
    
    # Adiciona colunas de preço (pode ser PREÇO, PREÇO UNITÁRIO, PREÇO TOTAL, etc)
    for col in combined_df.columns:
        if 'PREÇO' in col and col not in colunas_finais:
            colunas_finais.append(col)
    
    combined_df = combined_df[colunas_finais]
    
    # Log de rastreabilidade
    print(f"\n[PROCESSAMENTO CONCLUÍDO]")
    print(f"Total de arquivos processados com sucesso: {len(model_processor_info)}")
    for info in model_processor_info:
        print(f"  - {info['arquivo']}: {info['modelo']} -> {info['processador']}")
    
    excel_bytes = ExcelGenerator.generate(combined_df)
    
    # Define nome do arquivo com padrão "AgilizaConverter{dd.mm.yyyy}"
    data_atual = datetime.now().strftime("%d.%m.%Y")
    filename = f"AgilizaConverter{data_atual}.xlsx"
    
    # Armazena informações de processamento na sessão/memória para o cliente recuperar
    # (O frontend pode fazer um GET /api/last-processing-info para obter)
    # Por enquanto, vamos retornar as informações como headers
    
    # Retorna Excel direto (não ZIP)
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Processing-Info": str(model_processor_info)  # Informação dos processadores usados
        }
    )


def processar_modelo(df: pd.DataFrame, model: str) -> pd.DataFrame:
    """Processa o DataFrame conforme o modelo escolhido."""
    try:
        df = df.copy()
        
        print(f"\n[PROCESSA_MODELO] Model: {model}")
        print(f"[PROCESSA_MODELO] Colunas antes: {list(df.columns)}")
        print(f"[PROCESSA_MODELO] QTDE antes: {df['QTDE'].head(3).tolist() if 'QTDE' in df.columns else 'N/A'}")
        print(f"[PROCESSA_MODELO] PREÇO antes: {df['PREÇO'].head(3).tolist() if 'PREÇO' in df.columns else 'N/A'}")
        
        # Remove PEDIDO e CODCLI se existirem
        df = df.drop(columns=['PEDIDO', 'CODCLI'], errors='ignore')
        
        if model == 'winthor':
            # Preço sempre em branco
            if 'PREÇO' in df.columns:
                df['PREÇO'] = ''
            if 'VALOR_TOTAL' in df.columns:
                df['VALOR_TOTAL'] = ''
            # Reordena colunas
            colunas = ['CNPJ', 'EAN', 'DESCRICAO', 'QTDE']
            df = df[[col for col in colunas if col in df.columns]]
        elif model == 'planilha':
            # Usa PREÇO como PREÇO UNITÁRIO
            if 'PREÇO' in df.columns and 'QTDE' in df.columns:
                # Renomeia PREÇO para PREÇO UNITÁRIO
                df.rename(columns={'PREÇO': 'PREÇO UNITÁRIO'}, inplace=True)
                
                print(f"[PROCESSA_MODELO] Após rename:")
                print(f"[PROCESSA_MODELO] PREÇO UNITÁRIO: {df['PREÇO UNITÁRIO'].head(3).tolist()}")
                
                # Reordena as colunas
                colunas = ['CNPJ', 'EAN', 'DESCRICAO', 'QTDE', 'PREÇO UNITÁRIO']
                colunas_existentes = [col for col in colunas if col in df.columns]
                print(f"[PROCESSA_MODELO] Colunas a selecionar: {colunas_existentes}")
                df = df[colunas_existentes]
                
                # Ajusta nome para atender ao solicitado: PREÇO UNIT.
                df.rename(columns={'PREÇO UNITÁRIO': 'PREÇO UNIT.'}, inplace=True)
            else:
                # Se não tem PREÇO/QTDE, reordena mesmo assim
                colunas = ['CNPJ', 'EAN', 'DESCRICAO', 'QTDE', 'PREÇO']
                df = df[[col for col in colunas if col in df.columns]]
        
        print(f"[PROCESSA_MODELO] Colunas após: {list(df.columns)}")
        print(f"[PROCESSA_MODELO] QTDE após: {df['QTDE'].head(3).tolist() if 'QTDE' in df.columns else 'N/A'}")
        
        return df
    except Exception as e:
        print(f"[PROCESSA_MODELO] ERRO: {e}")
        raise
