import pandas as pd
import unicodedata
import openpyxl
import xlrd
from io import BytesIO
from pathlib import Path
from .base import FileProcessor
from src.utils.validators import normalizar_preco, extract_multiplicador_fardos, map_columns


class ExcelProcessor(FileProcessor):
    """Processa arquivos Excel (.xlsx e .xls) e padroniza para formato Agiliza"""
    
    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame:
        """
        Processa arquivo Excel e retorna DataFrame padronizado
        Estrutura esperada em colunas como: CodFilial, CnpjFilial, CodBarra, QtPedido
        Retorna: CODCLI, CNPJ, EAN, QTDE, PREÇO, TOTAL
        
        Suporta múltiplos modelos:
        - VILA NOVA: Estrutura limpa com headers definidos
        - VAREJINHO: Estrutura complexa com muitas colunas
        """
        
        print(f"\n[EXCEL PROCESSOR] Iniciando processamento de: {filename or 'arquivo sem nome'}")
        print(f"[EXCEL PROCESSOR] Tamanho do arquivo: {len(file_content)} bytes")
        
        # ===== MÉTODO LEGADO (fallback) =====
        print(f"[EXCEL PROCESSOR] Tentando método legado (pandas)...")
        df = None
        
        # Detectar extensão a partir do filename ou do content
        if not filename:
            # Tentar com xlsx primeiro, depois xls
            try:
                print(f"[EXCEL PROCESSOR] Tentando ler com openpyxl...")
                df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
                print(f"[EXCEL PROCESSOR] OK Leitura com openpyxl: {df.shape}")
            except Exception as e:
                print(f"[EXCEL PROCESSOR] WARN openpyxl falhou: {type(e).__name__}")
                try:
                    print(f"[EXCEL PROCESSOR] Tentando ler com xlrd...")
                    df = pd.read_excel(BytesIO(file_content), engine='xlrd')
                    print(f"[EXCEL PROCESSOR] OK Leitura com xlrd: {df.shape}")
                except Exception as e2:
                    print(f"[EXCEL PROCESSOR] WARN xlrd falhou: {type(e2).__name__}")
                    df = None
        else:
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'xlsx'
            print(f"[EXCEL PROCESSOR] Extensão detectada: .{ext}")
            
            if ext == 'xlsx':
                try:
                    print(f"[EXCEL PROCESSOR] Tentando ler XLSX com openpyxl...")
                    df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
                    print(f"[EXCEL PROCESSOR] OK Leitura XLSX sucesso: {df.shape}")
                except Exception as e:
                    print(f"[EXCEL PROCESSOR] WARN openpyxl falhou: {type(e).__name__}: {e}")
                    df = None
            elif ext == 'xls':
                # Para .xls, tentar ler TODAS as linhas para detectar múltiplas seções com CNPJ
                try:
                    print(f"[EXCEL PROCESSOR] Tentando _processar_xls_com_secoes...")
                    df = self._processar_xls_com_secoes(BytesIO(file_content))
                    print(f"[EXCEL PROCESSOR] OK Leitura XLS sucesso: {df.shape if df is not None else None}")
                except Exception as e:
                    # Se falhar, tenta ler como arquivo simples com múltiplos headers
                    print(f"[EXCEL PROCESSOR] WARN _processar_xls_com_secoes falhou: {type(e).__name__}: {e}")
                    print(f"[EXCEL PROCESSOR] Tentando _processar_xls_alternativo...")
                    try:
                        df = self._processar_xls_alternativo(BytesIO(file_content))
                        print(f"[EXCEL PROCESSOR] OK Leitura XLS (alternativo) sucesso: {df.shape if df is not None else None}")
                    except Exception as e2:
                        print(f"[EXCEL PROCESSOR] WARN _processar_xls_alternativo falhou: {type(e2).__name__}: {e2}")
                        df = None
            else:
                print(f"[EXCEL PROCESSOR] ERR Formato não suportado: {ext}")
                raise ValueError(f"Formato não suportado: {ext}")
        
        # Se não houver colunas relevantes, tentar detectar cabeçalho automaticamente
        if df is None or df.empty or (hasattr(self, '_has_relevant_columns') and not self._has_relevant_columns(df)):
            print(f"[EXCEL PROCESSOR] Tentando detecção automática de cabeçalho...")
            try:
                df = self._reler_com_cabecalho_detectado(file_content, filename)
                if df is not None and not df.empty:
                    print(f"[EXCEL PROCESSOR] OK Detecção automática sucesso: {df.shape}")
                else:
                    print(f"[EXCEL PROCESSOR] WARN Detecção automática retornou DataFrame vazio")
            except Exception as e:
                print(f"[EXCEL PROCESSOR] WARN Detecção automática falhou: {type(e).__name__}: {e}")
        
        # Se ainda assim nenhum dataframe válido, retorna None
        if df is None or df.empty:
            print(f"[EXCEL PROCESSOR] ERR ERRO: Não foi possível extrair dados do arquivo")
            return None
        
        print(f"[EXCEL PROCESSOR] OK DataFrame extraído: {df.shape[0]} linhas, {df.shape[1]} colunas")

        # Mapear colunas para padrão Agiliza
        df = self._normalize_columns(df)
        
        # Renomear QUANTIDADE para QTDE
        rename_mapping = {
            'QUANTIDADE': 'QTDE',
        }
        for old_name, new_name in rename_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Remover colunas duplicadas (manter a primeira)
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        
        # Extrair apenas as colunas necessárias (sem duplicatas)
        required_cols = ['CNPJ', 'EAN', 'DESCRICAO', 'QTDE', 'PREÇO']
        
        # Manter primeira ocorrência de cada coluna necessária
        available_cols = []
        for col in required_cols:
            if col in df.columns and col not in available_cols:
                available_cols.append(col)
        
        if available_cols:
            df = df[available_cols]
        else:
            df = df[[]]  # DataFrame vazio com as colunas corretas
        
        # Adicionar colunas faltantes (em branco)
        for col in required_cols:
            if col not in df.columns:
                # Colunas vazias
                df[col] = ''
        
        # Reordenar para ordem padrão (sem duplicatas)
        order = ['CNPJ', 'EAN', 'DESCRICAO', 'QTDE', 'PREÇO']
        
        # Manter apenas as colunas que existem e sem duplicatas
        order = [col for col in order if col in df.columns]
        df = df[order]
        
        # Preenchimento de valores vazios
        # CODCLI fica em branco se não houver valor na coluna "Código"
        if 'CNPJ' in df.columns:
            df['CNPJ'] = df['CNPJ'].fillna('').astype(str)
        if 'EAN' in df.columns:
            # Converter EAN para string, removendo .0 de floats
            df['EAN'] = df['EAN'].fillna('')
            df['EAN'] = df['EAN'].apply(lambda x: str(int(x)) if isinstance(x, float) and x != '' else str(x))
        if 'QTDE' in df.columns:
            # Converter para número, usando 0 para valores inválidos
            try:
                df['QTDE'] = pd.to_numeric(df['QTDE'], errors='coerce').fillna(0).astype(int)
            except Exception as e:
                print(f"[WARN] Erro ao converter QTDE para int: {e}. Tentando conversão linha-a-linha...")
                df['QTDE'] = df['QTDE'].apply(lambda x: int(float(str(x).replace(',', '.'))) if pd.notna(x) and str(x).strip() != '' else 0)
        
        # Procurar por coluna PREÇO (com ou sem acento)
        preco_col = None
        for col in df.columns:
            if col.upper() == 'PREÇO' or col.upper() == 'PREÇO':
                preco_col = col
                break
        
        if preco_col:
            # Converter PREÇO para float usando função normalizar_preco
            if preco_col != 'PREÇO':
                df = df.rename(columns={preco_col: 'PREÇO'})
            try:
                df['PREÇO'] = df['PREÇO'].apply(normalizar_preco)
            except Exception as e:
                print(f"[WARN] Erro ao normalizar PREÇO: {e}. Tentando pd.to_numeric...")
                df['PREÇO'] = pd.to_numeric(df['PREÇO'], errors='coerce').fillna(0.0)
        
        # Aplicar multiplicador de fardos ANTES de limpar descrição
        # Passo 1: Extrair multiplicadores e aplicar na quantidade
        if 'DESCRICAO' in df.columns and 'QTDE' in df.columns:
            def aplicar_fardos(row):
                desc = row['DESCRICAO'] if 'DESCRICAO' in row.index else ''
                qtde = row['QTDE'] if 'QTDE' in row.index else 0
                
                if pd.isna(desc) or desc == '':
                    return int(qtde) if qtde else 0
                
                try:
                    qtde = int(float(str(qtde).replace(',', '.'))) if qtde else 0
                    _, multiplicador = extract_multiplicador_fardos(str(desc))
                    return int(qtde * multiplicador)
                except:
                    return int(qtde) if qtde else 0
            
            df['QTDE'] = df.apply(aplicar_fardos, axis=1)
        
        # Passo 2: Limpar descrição removendo os multiplicadores
        if 'DESCRICAO' in df.columns:
            def limpar_descricao(desc):
                if pd.isna(desc) or desc == '':
                    return desc
                desc_limpa, _ = extract_multiplicador_fardos(str(desc))
                return desc_limpa.strip()
            
            df['DESCRICAO'] = df['DESCRICAO'].fillna('').apply(limpar_descricao)

        # Filtrar linhas inválidas (cabeçalhos, linhas vazias, etc) após normalização
        df_antes_filtro = df.copy()
        df = self._filtrar_linhas_validas(df)
        
        # Se a filtragem deixou o DF vazio, e temos dados antes, tenta estratégia menos rigorosa
        if df.empty and not df_antes_filtro.empty:
            print(f"[WARN] Filtragem eliminou todos os dados! Tentando sem filtro...")
            df = df_antes_filtro
        
        # Colunas TOTAL removidas conforme requisição
        can_compute_total = 'QTDE' in df.columns and 'PREÇO' in df.columns

        if can_compute_total:
            # Garantir que QTDE e PREÇO são numéricos
            try:
                df['QTDE'] = pd.to_numeric(df['QTDE'], errors='coerce').fillna(0).astype(int)
                df['PREÇO'] = pd.to_numeric(df['PREÇO'], errors='coerce').fillna(0.0)
            except Exception as e:
                print(f"[WARN] Erro ao garantir tipos numéricos para QTDE/PREÇO: {e}")
        else:
            # Sem preço, zera total se não existir
            if not has_total:
                df['TOTAL'] = 0.0
        
        # Reordenar colunas com TOTAL ao final
        col_order = ['CNPJ', 'EAN', 'DESCRICAO', 'PRECO_UNITARIO', 'QUANTIDADE', 'TOTAL']
        # Usar nomes reais das colunas (após normalização)
        col_order_real = [col for col in ['CNPJ', 'EAN', 'DESCRICAO', 'PREÇO', 'QTDE', 'TOTAL'] if col in df.columns]
        df = df[col_order_real]
        
        return df

    def _process_universal_parsed(self, df: pd.DataFrame, metadados: dict, filename: str = None) -> pd.DataFrame:
        """
        Processa DataFrame já parseado pelo UniversalExcelParser
        Normaliza colunas e garante QTDE, PREÇO e TOTAL corretos
        """
        
        # Mapear colunas para padrão Agiliza
        df = self._normalize_columns(df)
        
        # Remover colunas duplicadas
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        
        # Colunas já estão como esperado
        
        # Garantir CNPJ da metadata
        if 'CNPJ' not in df.columns and 'cnpj' in metadados:
            df['CNPJ'] = metadados['cnpj']
        
        # Normalizar QTDE (quantidade)
        if 'QTDE' in df.columns:
            try:
                df['QTDE'] = pd.to_numeric(df['QTDE'], errors='coerce').fillna(0).astype(int)
            except Exception as e:
                print(f"[WARN] Erro ao converter QTDE: {e}. Tentando aplicação linha-a-linha...")
                df['QTDE'] = df['QTDE'].apply(lambda x: int(float(str(x).replace(',', '.'))) if pd.notna(x) and str(x).strip() != '' else 0)
        else:
            df['QTDE'] = 0
        
        # Normalizar PREÇO (custo unitário / valor unitário)
        # Pode estar em várias colunas: PREÇO, CUSTO_UNITARIO, VALOR, etc.
        if 'PREÇO' in df.columns:
            try:
                df['PREÇO'] = df['PREÇO'].apply(normalizar_preco)
            except Exception as e:
                print(f"[WARN] Erro ao converter PREÇO: {e}. Tentando conversão numérica...")
                df['PREÇO'] = pd.to_numeric(df['PREÇO'], errors='coerce').fillna(0.0)
        elif 'CUSTO_UNITARIO' in df.columns:
            try:
                df['PREÇO'] = df['CUSTO_UNITARIO'].apply(normalizar_preco)
            except:
                df['PREÇO'] = pd.to_numeric(df['CUSTO_UNITARIO'], errors='coerce').fillna(0.0)
            df.drop('CUSTO_UNITARIO', axis=1, inplace=True)
        elif 'VALOR' in df.columns:
            try:
                df['PREÇO'] = df['VALOR'].apply(normalizar_preco)
            except:
                df['PREÇO'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0.0)
            df.drop('VALOR', axis=1, inplace=True)
        else:
            df['PREÇO'] = 0.0
        
        # Garantir tipos corretos ANTES de calcular TOTAL
        df['QTDE'] = pd.to_numeric(df['QTDE'], errors='coerce').fillna(0).astype(int)
        df['PREÇO'] = pd.to_numeric(df['PREÇO'], errors='coerce').fillna(0.0)
        
        # Se TOTAL existe como coluna, garantir que é numérico
        if 'TOTAL' in df.columns:
            try:
                df['TOTAL'] = pd.to_numeric(df['TOTAL'], errors='coerce').fillna(0.0)
            except:
                pass
        
        # Calcular TOTAL = QTDE × PREÇO (custo total)
        # Sempre recalcular para garantir precisão
        if 'QTDE' in df.columns and 'PREÇO' in df.columns:
            try:
                df['TOTAL'] = (df['QTDE'] * df['PREÇO']).round(2)
            except Exception as e:
                print(f"[WARN] Erro ao calcular TOTAL em _process_universal_parsed: {e}")
                df['TOTAL'] = 0.0
        else:
            df['TOTAL'] = 0.0
        
        # Normalizar EAN (pode estar vazio em VAREJINHO)
        if 'EAN' not in df.columns:
            df['EAN'] = ''
        else:
            df['EAN'] = df['EAN'].fillna('')
            # Converter para string, se for float
            df['EAN'] = df['EAN'].apply(
                lambda x: str(int(x)) if isinstance(x, float) and x != '' else str(x)
            )
        
        # EAN já é usado para identificação
        
        # Filtrar linhas válidas (remover vazias) - modo lenient porque UniversalExcelParser já filtra
        df = self._filtrar_linhas_validas(df, strict=False)
        
        # Reordenar colunas padrão (TOTAL SEMPRE NO FINAL)
        col_order = ['CNPJ', 'EAN', 'DESCRICAO', 'PREÇO', 'QTDE', 'TOTAL']
        col_order_real = [col for col in col_order if col in df.columns]
        
        # Garantir que TOTAL está lá
        if 'TOTAL' not in col_order_real:
            col_order_real.append('TOTAL')
        
        df = df[col_order_real]
        
        return df

    def _reler_com_cabecalho_detectado(self, file_content: bytes | BytesIO, filename: str | None) -> pd.DataFrame:
        """Tenta reler a planilha detectando automaticamente a linha de cabeçalho.
        Procura uma linha que contenha palavras-chave como 'ean', 'barras', 'produto', 'qtde', 'quantidade'.
        """
        # Escolher engine por extensão
        ext = None
        if filename and '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()

        engine = 'openpyxl' if ext == 'xlsx' or ext is None else 'xlrd'
        buffer = file_content if isinstance(file_content, BytesIO) else BytesIO(file_content)

        df_raw = pd.read_excel(buffer, engine=engine, header=None)
        if df_raw is None or df_raw.empty:
            return df_raw

        # Palavras-chave para identificar cabeçalho
        keywords = ['ean', 'barras', 'código', 'codigo', 'produto', 'descr', 'qtde', 'quantidade', 'preço', 'preco', 'valor']
        header_row = None
        for i in range(min(len(df_raw), 50)):
            row_vals = [str(v).lower().strip() for v in list(df_raw.iloc[i].values)]
            row_str = ' '.join(row_vals)
            if any(kw in row_str for kw in keywords):
                header_row = i
                break

        if header_row is None:
            # fallback: usa primeira linha
            header_row = 0

        # Construir DataFrame com essa linha como cabeçalho
        headers = [str(v).strip() for v in list(df_raw.iloc[header_row].values)]
        data = df_raw.iloc[header_row + 1:].copy()
        data.columns = headers
        # Remover linhas totalmente vazias
        data = data.dropna(how='all')
        return data
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Mapeia colunas do Excel para o padrão Agiliza usando fuzzy matching.
        Suporta múltiplos formatos de nomes de colunas.
        """
        print(f"[EXCEL PROCESSOR] Colunas originais: {list(df.columns)}")
        
        # Usar o novo mapeamento fuzzy
        mapping = map_columns(df)
        
        print(f"[EXCEL PROCESSOR] Mapeamento fuzzy detectado: {mapping}")
        
        # Renomear colunas de acordo com mapeamento
        if mapping:
            df = df.rename(columns=mapping)
        
        print(f"[EXCEL PROCESSOR] Colunas após mapeamento: {list(df.columns)}")
        return df
    
    def _has_relevant_columns(self, df: pd.DataFrame) -> bool:
        """Verifica se o DataFrame tem colunas relevantes (EAN ou código de barras)"""
        if df is None or df.empty:
            return False
        
        cols_lower = [str(col).lower() for col in df.columns]
        relevant_keywords = ['ean', 'código', 'codigo', 'barras', 'quantidade', 'compra', 'qtde']
        
        for col in cols_lower:
            for keyword in relevant_keywords:
                if keyword in col:
                    return True
        
        return False
    
    def _extrair_cnpj_cabecalho(self, file_content: BytesIO, header_row: int) -> str:
        """Extrai CNPJ do cabeçalho do arquivo (linhas anteriores ao header)"""
        try:
            # Ler linhas antes do header
            df_raw = pd.read_excel(file_content, engine='xlrd', header=None)
            
            # Procurar por CNPJ válido nas primeiras linhas (antes do header_row)
            # Verificar linha por linha
            for i in range(min(header_row, len(df_raw))):
                for j in range(len(df_raw.columns)):
                    val = df_raw.iloc[i, j]
                    if val is not None and not pd.isna(val):
                        val_str = str(val).strip()
                        # Remover formatação
                        val_limpo = val_str.replace('.', '').replace('/', '').replace('-', '')
                        # Verificar se é um CNPJ válido (14 dígitos) ou parcialmente válido (10+ dígitos)
                        if len(val_limpo) >= 14 and val_limpo[:14].isdigit():
                            return val_limpo[:14]
            
            return None
        except:
            return None
        """Detecta se arquivo tem múltiplos CNPJs em seções e preenche automaticamente"""
        try:
            # Ler arquivo bruto para detectar padrão de seções
            df_raw = pd.read_excel(file_content, engine='xlrd', header=None)
            
            # Procurar por CNPJs válidos no arquivo
            cnpjs_encontrados = {}  # {row_index: cnpj}
            
            for i in range(len(df_raw)):
                for j in range(min(3, len(df_raw.columns))):  # Verificar primeiras 3 colunas
                    val = df_raw.iloc[i, j]
                    if val is not None and not pd.isna(val):
                        val_str = str(val).strip()
                        val_limpo = val_str.replace('.', '').replace('/', '').replace('-', '')
                        # Se é CNPJ válido
                        if len(val_limpo) >= 14 and val_limpo[:14].isdigit():
                            cnpjs_encontrados[i] = val_limpo[:14]
            
            # Se encontrou múltiplos CNPJs, adicionar coluna com valores específicos
            if len(cnpjs_encontrados) > 1:
                self._cnpj_multiplo = cnpjs_encontrados
                self._aplicar_cnpj_por_secao(df, df_raw, cnpjs_encontrados)
        except:
            pass
            pass
    
    def _aplicar_cnpj_por_secao(self, df: pd.DataFrame, df_raw: pd.DataFrame, cnpjs_map: dict):
        """Aplica CNPJ específico para cada seção do DataFrame"""
        # Determinar qual CNPJ cada linha do DataFrame deveria ter
        # baseado na linha original do arquivo bruto
        # Isso é complexo pois o DataFrame processado pode ter menos linhas
        # Por enquanto, marca que há múltiplos CNPJs
        self._tem_cnpj_multiplo = True
    
    def _extrair_cnpj_primeira_linha(self, df: pd.DataFrame) -> str:
        """Extrai CNPJ da primeira linha válida do DataFrame"""
        try:
            if df is None or df.empty:
                return None
            
            # Procurar CNPJ válido na primeira linha
            primeira_linha = df.iloc[0]
            for val in primeira_linha:
                if val is not None and not pd.isna(val):
                    val_str = str(val).strip()
                    val_limpo = val_str.replace('.', '').replace('/', '').replace('-', '')
                    if len(val_limpo) >= 14 and val_limpo[:14].isdigit():
                        return val_limpo[:14]
            
            return None
        except:
            return None
    
    def _processar_xls_com_secoes(self, file_content: BytesIO) -> pd.DataFrame:
        """
        Processa arquivo .xls que contém múltiplas seções com CNPJs diferentes
        Estrutura esperada:
          Linha X: [CNPJ, Descrição, ...]
          Linha X+1: [vazio]
          Linha X+2: [Cabeçalho: Código, EAN, Produto, Qtde, ...]
          Linhas X+3+: [dados...]
        """
        dfs_por_cnpj = []
        
        try:
            # Ler todas as linhas do arquivo
            import xlrd
            file_content.seek(0)
            book = xlrd.open_workbook(file_contents=file_content.getvalue())
            sheet = book.sheet_by_index(0)
            
            # Identificar linhas de CNPJ (começam com número de 11-15 dígitos)
            cnpj_sections = []
            for i in range(sheet.nrows):
                row = sheet.row_values(i)
                first_cell = str(row[0]).strip() if row else ''
                
                if (first_cell and first_cell[0].isdigit() and 11 <= len(first_cell) <= 15):
                    # Validar se é realmente CNPJ (14 dígitos)
                    if len(first_cell.replace('.', '').replace('/', '').replace('-', '')) >= 14:
                        cnpj_sections.append((i, first_cell))
            
            # Processar cada seção
            for idx, (cnpj_row, cnpj_raw) in enumerate(cnpj_sections):
                # Limpar CNPJ
                cnpj = cnpj_raw.replace('.', '').replace('/', '').replace('-', '')[:14]
                
                # Encontrar próxima linha de CNPJ (ou fim do arquivo)
                proxima_secao_row = cnpj_sections[idx + 1][0] if idx + 1 < len(cnpj_sections) else sheet.nrows
                
                # A seção começa 2-3 linhas após o CNPJ (linha de cabeçalho)
                # Procurar linha de cabeçalho
                header_row = None
                for r in range(cnpj_row + 1, min(cnpj_row + 4, proxima_secao_row)):
                    row_vals = sheet.row_values(r)
                    # Procurar por colunas relevantes
                    row_str = ' '.join([str(v).lower() for v in row_vals if v])
                    if any(kw in row_str for kw in ['ean', 'código', 'qtde', 'quantidade', 'produto']):
                        header_row = r
                        break
                
                if header_row is None:
                    # Se não achar, assume que está 2 linhas após CNPJ
                    header_row = cnpj_row + 2
                
                # Extrair dados da seção (da linha de cabeçalho até próxima seção)
                # Ler com pandas a partir dessa seção
                section_start = cnpj_row
                section_end = proxima_secao_row
                
                # Converter linhas do xlrd para uma lista e depois para DataFrame
                rows_data = []
                headers = None
                
                for r in range(section_start, section_end):
                    row_vals = sheet.row_values(r)
                    if r == header_row:
                        headers = row_vals
                    elif r > header_row:
                        rows_data.append(row_vals)
                
                # Criar DataFrame para essa seção
                if headers and rows_data:
                    df_secao = pd.DataFrame(rows_data, columns=headers)
                    
                    # Adicionar coluna CNPJ (se não existir)
                    if 'CNPJ' not in df_secao.columns:
                        df_secao['CNPJ'] = cnpj
                    else:
                        # Preencher com CNPJ da seção
                        df_secao['CNPJ'] = cnpj
                    
                    dfs_por_cnpj.append(df_secao)
            
            # Concatenar todos os DataFrames
            if dfs_por_cnpj:
                df_result = pd.concat(dfs_por_cnpj, ignore_index=True)
                return df_result
            else:
                # Fallback: ler como arquivo normal
                return pd.read_excel(file_content, engine='xlrd', header=2)
        
        except Exception as e:
            # Se algo deu errado, tentar ler como arquivo normal
            try:
                return pd.read_excel(file_content, engine='xlrd', header=2)
            except:
                raise ValueError(f"Erro ao processar arquivo .xls: {str(e)}")
    
    def _processar_xls_alternativo(self, file_content: BytesIO) -> pd.DataFrame:
        """
        Alternativa robusta para processar .xls com múltiplas seções ou estruturas diferentes.
        Tenta múltiplas estratégias de leitura.
        """
        try:
            file_content.seek(0)
            
            # Estratégia 1: Tentar com openpyxl (mais robusto para alguns arquivos)
            try:
                df = pd.read_excel(file_content, engine='openpyxl', header=None)
                if df is not None and not df.empty:
                    return self._reler_com_cabecalho_detectado(file_content.getvalue(), None)
            except:
                pass
            
            # Estratégia 2: Ler com xlrd sem tratamento especial de seções
            file_content.seek(0)
            df = pd.read_excel(file_content, engine='xlrd', header=None)
            
            if df is None or df.empty:
                return None
            
            # Detectar cabeçalho automaticamente
            return self._reler_com_cabecalho_detectado(file_content.getvalue(), None)
            
        except Exception as e:
            return None
    
    def _filtrar_linhas_validas(self, df: pd.DataFrame, strict: bool = True) -> pd.DataFrame:
        """Remove linhas que são cabeçalhos ou não têm dados válidos"""
        if df is None or df.empty:
            return df
        
        # Se não há colunas de dados úteis mapeadas, usar filtro bem menos restritivo
        relevant_cols = [col for col in ['EAN', 'DESCRICAO', 'QTDE', 'PREÇO'] if col in df.columns]
        if not relevant_cols or not strict:
            # Filtro minimalista: remover linhas onde todos os valores são NaN/vazio
            df_filtrado = df.dropna(how='all').reset_index(drop=True)
            return df_filtrado
        
        # Função para verificar se EAN é válido
        def ean_valido(ean):
            if pd.isna(ean) or ean == '' or ean == 0:
                return False
            ean_str = str(ean).strip().replace('.', '').replace('-', '')
            # EAN deve ter 13 ou 14 dígitos
            return len(ean_str) in [13, 14] and ean_str.isdigit()
        
        # Função para verificar se a linha tem dados válidos
        def linha_tem_dados(row):
            # CRITÉRIO PRINCIPAL: Se tem EAN válido, sempre manter
            if 'EAN' in df.columns:
                try:
                    if ean_valido(row['EAN']):
                        return True
                except:
                    pass
            
            # CRITÉRIO SECUNDÁRIO: Se tem DESCRICAO com conteúdo válido e não é cabeçalho
            if 'DESCRICAO' in df.columns:
                try:
                    desc = str(row['DESCRICAO']).strip().lower()
                    # Rejeitar se for claramente um cabeçalho
                    header_keywords = [
                        'produto', 'descrição', 'descricao', 'desc',
                        'qtde', 'quantidade', 'código', 'codigos', 'codigo',
                        'barras', 'código de barras',
                        'preço', 'preco', 'valor', 'valor unitário',
                        'total', 'subtotal', 'desconto', 'frete',
                        'ean', 'ean13', 'cód', 'cod', 'ref',
                        'unidade', 'embalagem', 'fabricante'
                    ]
                    
                    # Se contém MAIS de 2 palavras-chave de cabeçalho, é cabeçalho
                    matches = sum(1 for kw in header_keywords if kw in desc)
                    if matches >= 2 or desc in ['', 'nan', 'none']:
                        return False
                    
                    # Se tem descrição não-vazia de tamanho razoável, pode ser válido
                    if desc and len(desc) > 2:
                        return True
                except:
                    pass
            
            # CRITÉRIO TERCIÁRIO: Qualquer linha com QTDE válida ou PREÇO válido é mantida
            has_valid_qtde = False
            has_valid_preco = False
            
            if 'QTDE' in df.columns:
                try:
                    qtde = row['QTDE']
                    if pd.notna(qtde) and isinstance(qtde, (int, float)) and qtde > 0:
                        has_valid_qtde = True
                except:
                    pass
            
            if 'PREÇO' in df.columns:
                try:
                    preco = row['PREÇO']
                    if pd.notna(preco) and isinstance(preco, (int, float)) and preco > 0:
                        has_valid_preco = True
                except:
                    pass
            
            return has_valid_qtde or has_valid_preco
        
        # Filtrar linhas que têm dados válidos
        df_filtrado = df[df.apply(linha_tem_dados, axis=1)].reset_index(drop=True)
        
        return df_filtrado
