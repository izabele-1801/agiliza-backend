"""Processador especializado para Prudence."""

import pandas as pd
from io import BytesIO
from .base import FileProcessor
from .pdf_text_parser import PDFTextParser
from src.utils.validators import extract_cnpj, extract_ean13, normalizar_preco, extract_multiplicador_fardos


class PrudenceProcessor(FileProcessor):
    """Processa pedidos Prudence."""
    
    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame:
        """Processa arquivo Prudence e extrai dados estruturados."""
        print(f"\n{'='*60}")
        print(f" [PRUDENCE] INICIANDO PROCESSAMENTO")
        print(f" Arquivo: {filename or 'desconhecido'}")
        print(f" Tamanho: {len(file_content)} bytes")
        print(f"{'='*60}")
        
        try:
            ext = filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else 'xlsx'
            print(f" [PRUDENCE] Extensão detectada: .{ext}")
            
            if ext in ['xlsx', 'xls']:
                print(f" [PRUDENCE] → Roteando para processador EXCEL")
                return self._processar_excel(file_content, ext)
            elif ext == 'pdf':
                print(f" [PRUDENCE] → Roteando para processador PDF")
                return self._processar_pdf(file_content)
            elif ext == 'txt':
                print(f" [PRUDENCE] → Roteando para processador TXT")
                return self._processar_txt(file_content)
            else:
                print(f" [PRUDENCE] ✗ Extensão não suportada: .{ext}")
                return None
                
        except Exception as e:
            print(f" [PRUDENCE] ✗ ERRO geral: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _processar_excel(self, file_content: bytes, ext: str) -> pd.DataFrame | None:
        """Processa arquivo Excel Prudence."""
        print(f" [PRUDENCE] Lendo Excel com engine: {ext}")
        try:
            engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
            df = pd.read_excel(BytesIO(file_content), engine=engine)
            print(f" [PRUDENCE] ✓ Excel lido: {df.shape[0]} linhas × {df.shape[1]} colunas")
            print(f" [PRUDENCE] Colunas brutos: {list(df.columns)}")
            
            df.columns = [str(col).strip() for col in df.columns]
            print(f" [PRUDENCE] Colunas após limpeza: {list(df.columns)}")
            
            print(f"\n [PRUDENCE] Primeiras 3 linhas do Excel:")
            print(df.head(3).to_string() if not df.empty else "Vazio")
            
            result = self._extrair_dados(df)
            print(f"\n [PRUDENCE] Resultado: {result.shape if result is not None else 'None'}")
            return result
        except Exception as e:
            print(f" [PRUDENCE] ✗ ERRO ao processar Excel: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _processar_pdf(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa PDF Prudence com extração de COMPRA e CUSTO por posição."""
        print(f" [PRUDENCE] Processando PDF - Extração por posição de colunas")
        try:
            import pdfplumber
            import re
            
            produtos = []
            
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                for num_pagina, pagina in enumerate(pdf.pages):
                    print(f" [PRUDENCE] Página {num_pagina + 1}/{len(pdf.pages)}")
                    
                    texto_pagina = pagina.extract_text()
                    
                    # Extrair CNPJ da página
                    cnpj_pagina = ''
                    loja_match = re.search(r'LOJA\d+\s*-\s*([\d.]+)', texto_pagina)
                    if loja_match:
                        cnpj_pagina = loja_match.group(1)
                    
                    # Procurar o header da tabela
                    linhas = texto_pagina.split('\n')
                    header_idx = None
                    
                    for i, linha in enumerate(linhas):
                        if 'Código' in linha and 'Compra' in linha and 'Custo' in linha:
                            header_idx = i
                            break
                    
                    if header_idx is None:
                        continue
                    
                    # Processar linhas após header
                    for linha_raw in linhas[header_idx + 1:]:
                        linha = linha_raw.strip()
                        if not linha or len(linha) < 30:
                            continue
                        
                        # Procurar EAN
                        ean_match = re.search(r'\b([3678]\d{12})\b', linha)
                        if not ean_match:
                            continue
                        
                        ean = ean_match.group(1)
                        
                        # Estratégia: a QTDE está na coluna Compra, que tem padrão P[DIGIT]E
                        # Exemplo: "P3E,0S0SOAL" contém "3" que é a quantidade
                        # CUSTO está nos números decimais X,XX que aparecem depois
                        
                        qtde = 0
                        custo = 0.0
                        
                        # Buscar padrão P[DIGIT]E para COMPRA (QTDE)
                        # Exemplo: "P3E", "P2E", "P1E"
                        compra_match = re.search(r'P(\d)E', linha)
                        if compra_match:
                            try:
                                qtde = int(compra_match.group(1))
                            except:
                                pass
                        
                        # Buscar números decimais: primeiro será CUSTO
                        numeros = re.findall(r'(\d+[,\.]\d{2})', linha)
                        if numeros:
                            try:
                                custo = normalizar_preco(numeros[0])
                            except:
                                pass
                        
                        # Validação: QTDE deve estar entre 1-9 (do padrão P[DIGIT]E), CUSTO > 0
                        if not (1 <= qtde <= 9 and custo > 0):
                            print(f"  [DESCARTADA] QTDE={qtde}, CUSTO={custo}")
                            continue
                        
                        # Extrair descrição: retirar as partes conhecidas
                        desc = linha
                        desc = desc.replace(ean, '', 1)  # Remove EAN
                        # Remove tudo depois do LTDA ou do primeiro número decimal
                        if 'LTDA' in desc:
                            desc = desc[:desc.find('LTDA')]
                        elif numeros:
                            # Remove tudo depois do primeiro número decimal
                            desc = desc[:desc.find(numeros[0])]
                        
                        desc = desc.strip()
                        desc = re.sub(r'\s+', ' ', desc)
                        if len(desc) > 100:
                            desc = desc[:100]
                        
                        desc_limpa, mult = extract_multiplicador_fardos(desc)
                        qtde_final = max(1, qtde * mult)
                        
                        if desc_limpa and qtde_final > 0 and custo > 0:
                            produtos.append({
                                'CNPJ': cnpj_pagina,
                                'EAN': ean,
                                'DESCRICAO': desc_limpa.strip(),
                                'QTDE': qtde_final,
                                'PREÇO': custo
                            })
            
            if produtos:
                print(f" [PRUDENCE] ✓ Total extraído: {len(produtos)} produtos")
                return pd.DataFrame(produtos)
            else:
                print(f" [PRUDENCE] ⚠ Nenhum produto extraído")
                return None
                
        except Exception as e:
            print(f" [PRUDENCE] ✗ ERRO: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _processar_txt(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa arquivo TXT Prudence."""
        print(f" [PRUDENCE] Processando TXT")
        try:
            texto = file_content.decode('utf-8', errors='ignore')
            linhas = texto.split('\n')
            
            cnpj = extract_cnpj(texto) or ''
            dados = []
            
            for linha in linhas:
                if cnpj and (produto := self._extrair_linha_produto(linha, cnpj)):
                    dados.append(produto)
            
            if dados:
                result = pd.DataFrame(dados)
                print(f" [PRUDENCE] ✓ TXT processado: {len(dados)} produtos")
                return result
            else:
                print(f" [PRUDENCE] ⚠ Nenhum dado extraído do TXT")
                return None
        except Exception as e:
            print(f" [PRUDENCE] ✗ ERRO ao processar TXT: {type(e).__name__}: {e}")
            return None
    
    def _extrair_dados(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """Extrai dados do DataFrame Prudence."""
        print(f"\n [PRUDENCE] === INICIANDO EXTRAÇÃO DE DADOS ===")
        try:
            if df.empty:
                print(f" [PRUDENCE] ⚠ DataFrame vazio!")
                return None
            
            cnpj = ''
            try:
                cnpj = extract_cnpj(str(df.iloc[1, 0])) or ''
            except:
                pass
            
            col_ean = self._buscar_coluna(df.columns, ['Código barras', 'Código', 'EAN'])
            col_desc = self._buscar_coluna(df.columns, ['Mercadoria', 'Descrição', 'Produto'])
            col_qtde = self._buscar_coluna(df.columns, ['Compra', 'Compra.', 'Quantidade'])
            col_preco = self._buscar_coluna(df.columns, ['Custo', 'Preço', 'Valor'])
            
            print(f"\n [PRUDENCE] Colunas encontradas:")
            print(f"   EAN: {col_ean}")
            print(f"   DESC: {col_desc}")
            print(f"   QTDE: {col_qtde}")
            print(f"   PRECO: {col_preco}")
            print(f" [PRUDENCE] Colunas disponíveis: {list(df.columns)}")
            
            # Debug: mostrar valores brutos
            if col_qtde and not df.empty:
                print(f"\n [PRUDENCE] Primeiros valores de '{col_qtde}':")
                for i, val in enumerate(df[col_qtde].head(3)):
                    print(f"   [{i}]: {repr(val)} (tipo: {type(val).__name__})")
            
            if col_preco and not df.empty:
                print(f"\n [PRUDENCE] Primeiros valores de '{col_preco}':")
                for i, val in enumerate(df[col_preco].head(3)):
                    print(f"   [{i}]: {repr(val)} (tipo: {type(val).__name__})")
            
            if not all([col_ean, col_desc, col_qtde]):
                print(f"\n [PRUDENCE] ✗ Colunas obrigatórias não encontradas!")
                return None
            
            dados = []
            for idx, (_, row) in enumerate(df.iterrows()):
                ean = extract_ean13(str(row[col_ean]).strip()) or str(row[col_ean]).strip()
                desc = str(row[col_desc]).strip() if col_desc else ''
                
                # DEBUG: Mostrar valor bruto da quantidade
                valor_qtde_bruto = row[col_qtde]
                print(f"\n [PRUDENCE] Linha {idx}: EAN={ean}")
                print(f"   QTDE_BRUTO={repr(valor_qtde_bruto)} (tipo: {type(valor_qtde_bruto).__name__})")
                
                try:
                    # Converter para string, remover espaços, converter vírgula em ponto
                    qtde_str = str(valor_qtde_bruto).strip()
                    if qtde_str.lower() in ['nan', 'none', '']:
                        print(f"   ⚠ QTDE vazia, pulando linha")
                        continue
                    
                    qtde = int(float(qtde_str.replace(',', '.')))
                    print(f"   → QTDE convertida: {qtde}")
                except Exception as e:
                    print(f"   ✗ ERRO ao converter QTDE: {e}")
                    continue
                
                if not ean or not desc or qtde <= 0:
                    print(f"   ⚠ Dados inválidos: ean={bool(ean)}, desc={bool(desc)}, qtde={qtde}")
                    continue
                
                desc_limpa, mult = extract_multiplicador_fardos(desc)
                qtde = qtde * mult
                
                # Extrair preço
                valor_preco_bruto = row[col_preco] if col_preco else 0
                preco = normalizar_preco(valor_preco_bruto) if col_preco else 0.0
                print(f"   PRECO_BRUTO={repr(valor_preco_bruto)}, PRECO_NORMALIZADO={preco}")
                
                print(f"   ✓ Produto adicionado: {ean} | {desc_limpa} | Qtde={qtde} | Preço={preco}")
                
                dados.append({
                    'CNPJ': cnpj,
                    'EAN': ean,
                    'DESCRICAO': desc_limpa.strip(),
                    'QTDE': qtde,
                    'PREÇO': preco if preco > 0 else None
                })
            
            print(f"\n [PRUDENCE] === FIM DA EXTRAÇÃO: {len(dados)} produtos encontrados ===\n")
            return pd.DataFrame(dados) if dados else None
        except Exception as e:
            print(f" [PRUDENCE] ✗ ERRO ao extrair dados: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extrair_de_tabela(self, table: list, cnpj: str) -> list:
        """Extrai dados de tabelas PDF - PROCURA PELAS COLUNAS CORRETAS."""
        dados = []
        
        if not table or len(table) < 2:
            return dados
        
        # PASSO 1: Identificar colunas pelo header (primeira linha da tabela)
        header = [str(cell).lower().strip() if cell else '' for cell in table[0]]
        print(f"   [PDF] Header encontrado: {table[0]}")
        print(f"   [PDF] Header normalizado: {header}")
        
        # Procurar índices das colunas
        col_idx_ean = None
        col_idx_desc = None
        col_idx_qtde = None
        col_idx_preco = None
        
        for idx, col_name in enumerate(header):
            col_lower = col_name.lower()
            if any(x in col_lower for x in ['código', 'ean', 'código barras']):
                col_idx_ean = idx
                print(f"   [PDF] ✓ Coluna EAN encontrada no índice {idx}")
            elif any(x in col_lower for x in ['mercadoria', 'descrição', 'produto']):
                col_idx_desc = idx
                print(f"   [PDF] ✓ Coluna DESC encontrada no índice {idx}")
            elif any(x in col_lower for x in ['compra', 'quantidade', 'qtd']):
                col_idx_qtde = idx
                print(f"   [PDF] ✓ Coluna QTDE encontrada no índice {idx}")
            elif any(x in col_lower for x in ['custo', 'preço', 'valor']):
                col_idx_preco = idx
                print(f"   [PDF] ✓ Coluna PREÇO encontrada no índice {idx}")
        
        # Se não encontrou pelo header, usa as posições padrão (fallback)
        if col_idx_ean is None:
            col_idx_ean = 0
        if col_idx_desc is None:
            col_idx_desc = 1
        if col_idx_qtde is None:
            col_idx_qtde = 2
        if col_idx_preco is None:
            col_idx_preco = 3
        
        print(f"   [PDF] Colunas finais: EAN={col_idx_ean}, DESC={col_idx_desc}, QTDE={col_idx_qtde}, PRECO={col_idx_preco}")
        
        # PASSO 2: Processar dados (ignorar header)
        for row_idx, row in enumerate(table[1:], start=1):
            if not row or len(row) < max(col_idx_ean, col_idx_desc, col_idx_qtde) + 1:
                continue
            
            try:
                # Extrair valores pelas colunas identificadas
                ean = extract_ean13(str(row[col_idx_ean]).strip()) or str(row[col_idx_ean]).strip()
                desc = str(row[col_idx_desc]).strip() if col_idx_desc < len(row) else ''
                
                # Extrair quantidade com debug
                valor_qtde = row[col_idx_qtde] if col_idx_qtde < len(row) else 1
                qtde_str = str(valor_qtde).strip()
                print(f"   [PDF] Linha {row_idx}: EAN={ean}, QTDE_BRUTO={repr(valor_qtde)}")
                
                if qtde_str.lower() in ['nan', 'none', '']:
                    qtde = 1
                else:
                    qtde = int(float(qtde_str.replace(',', '.')))
                
                print(f"   [PDF] → QTDE convertida: {qtde}")
                
                if not ean or not desc or qtde <= 0:
                    continue
                
                desc_limpa, mult = extract_multiplicador_fardos(desc)
                qtde = qtde * mult
                
                # Extrair preço
                preco = 0.0
                if col_idx_preco < len(row):
                    preco = normalizar_preco(row[col_idx_preco])
                
                dados.append({
                    'CNPJ': cnpj,
                    'EAN': ean,
                    'DESCRICAO': desc_limpa.strip(),
                    'QTDE': qtde,
                    'PREÇO': preco if preco > 0 else None
                })
                print(f"   [PDF] ✓ Produto: {ean} | {desc_limpa} | Qtde={qtde} | Preço={preco}")
            except Exception as e:
                print(f"   [PDF] ✗ Erro linha {row_idx}: {type(e).__name__}: {e}")
                continue
        
        return dados
    
    def _extrair_linha_produto(self, linha: str, cnpj: str) -> dict | None:
        """Extrai produto de uma linha TXT."""
        try:
            ean = extract_ean13(linha)
            if not ean:
                return None
            
            partes = linha.split()
            if len(partes) < 3:
                return None
            
            desc = ' '.join(partes[1:-1])
            qtde = int(partes[-1])
            
            if qtde <= 0 or not desc:
                return None
            
            desc_limpa, mult = extract_multiplicador_fardos(desc)
            qtde = qtde * mult
            
            return {
                'CNPJ': cnpj,
                'EAN': ean,
                'DESCRICAO': desc_limpa.strip(),
                'QTDE': qtde,
                'PREÇO': None
            }
        except:
            return None
    
    def _buscar_coluna(self, colunas, nomes_possiveis: list) -> str | None:
        """Busca coluna por nomes possíveis - correspondência exata PRIMEIRO."""
        colunas_lower = {col.lower().strip(): col for col in colunas}
        
        # PASSO 1: Correspondência exata
        for nome in nomes_possiveis:
            nome_lower = nome.lower().strip()
            if nome_lower in colunas_lower:
                resultado = colunas_lower[nome_lower]
                print(f"   ✓ Coluna '{nome}' → ENCONTRADA como '{resultado}' (EXATA)")
                return resultado
        
        # PASSO 2: Correspondência parcial
        for nome in nomes_possiveis:
            nome_lower = nome.lower().strip()
            for col_lower, col_real in colunas_lower.items():
                if nome_lower in col_lower and nome_lower != '':
                    print(f"   ✓ Coluna '{nome}' → ENCONTRADA como '{col_real}' (PARCIAL)")
                    return col_real
        
        print(f"   ✗ Coluna não encontrada entre: {nomes_possiveis}")
        return None
