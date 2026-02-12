"""Processador de arquivos PDF."""

import re
from io import BytesIO
import pandas as pd
import pdfplumber
from src.processing.base import FileProcessor
from src.utils.constants import EXCEL_COLUMNS
from src.utils.validators import extract_cnpj, extract_all_cnpjs, extract_ean13, normalizar_preco, extract_multiplicador_fardos, extract_numero_pedido


class PDFProcessor(FileProcessor):
    """Processa arquivos PDF."""

    def process(self, file_content: bytes, filename: str = None) -> pd.DataFrame | None:
        """Processa PDF e extrai dados de pedidos."""
        try:
            return self._extract_data(file_content)
        except Exception as e:
            print(f"Erro ao processar PDF: {e}")
            return None

    def _extract_data(self, file_content: bytes) -> pd.DataFrame | None:
        """Extrai dados do PDF, detectando CNPJ por seção/página quando possível."""
        produtos = []
        numero_pedido_global = ''
        
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            # Tenta extrair número do pedido do documento inteiro (primeira vez)
            if not numero_pedido_global and len(pdf.pages) > 0:
                primeira_pagina = pdf.pages[0]
                texto_primeira = primeira_pagina.extract_text()
                if texto_primeira:
                    numero_pedido_global = extract_numero_pedido(texto_primeira) or ''
                    if numero_pedido_global:
                        print(f"[PDF PROCESSOR] Número do Pedido detectado: {numero_pedido_global}")
            
            # Processa cada página, detectando CNPJ no contexto da página
            for num_pagina, pagina in enumerate(pdf.pages):
                print(f"\n[PDF PROCESSOR] Processando página {num_pagina + 1} de {len(pdf.pages)}")
                
                # Extrair CNPJ da página atual
                texto_pagina = pagina.extract_text()
                cnpj_pagina = ''
                if texto_pagina:
                    cnpj_pagina = extract_cnpj(texto_pagina)
                    if cnpj_pagina:
                        print(f"[PDF PROCESSOR] CNPJ detectado na página: {cnpj_pagina}")
                
                # Tenta extrair de tabelas estruturadas
                tables = pagina.extract_tables()
                if tables:
                    print(f"[PDF PROCESSOR] {len(tables)} tabela(s) encontrada(s) na página")
                    for idx_tabela, table in enumerate(tables):
                        produtos_tabela = self._extrair_de_tabela(table, cnpj_pagina)
                        print(f"[PDF PROCESSOR] Tabela {idx_tabela + 1}: {len(produtos_tabela)} produtos extraídos")
                        produtos.extend(produtos_tabela)
                else:
                    # Se não houver tabelas, tenta texto
                    if texto_pagina:
                        produtos_texto = self._extrair_produtos(texto_pagina, cnpj_pagina)
                        print(f"[PDF PROCESSOR] Texto: {len(produtos_texto)} produtos extraídos")
                        produtos.extend(produtos_texto)
        
        if not produtos:
            print("[PDF PROCESSOR] Nenhum produto encontrado!")
            return None
        
        print(f"\n[PDF PROCESSOR] Total de {len(produtos)} produtos extraídos")
        
        # Cria DataFrame com os produtos
        dados = []
        for produto in produtos:
            # Extrair multiplicador de fardos e normalizar descrição
            desc = produto.get('descricao', '')
            desc_limpa, multiplicador = extract_multiplicador_fardos(desc)
            
            # Aplicar multiplicador na quantidade
            qtde = int(produto['quantidade'] * multiplicador)
            preco = normalizar_preco(produto.get('preco_unitario', 0))
            
            ean_value = produto['ean']
            cnpj_value = produto.get('cnpj', '')  # Usar CNPJ do produto se tiver
            
            dados.append({
                'CNPJ': cnpj_value,
                'EAN': ean_value,
                'DESCRICAO': desc_limpa.strip(),
                'PREÇO': preco,
                'QTDE': qtde
            })
        
        df = pd.DataFrame(dados) if dados else None
        
        # Reordenar colunas: CNPJ, EAN, DESCRICAO, PREÇO, QTDE
        if df is not None:
            col_order = [col for col in ['CNPJ', 'EAN', 'DESCRICAO', 'PREÇO', 'QTDE'] if col in df.columns]
            df = df[col_order]
        
        return df

    def _extrair_de_tabela(self, table: list, cnpj_pagina: str = '') -> list:
        """Extrai produtos de uma tabela estruturada."""
        produtos = []

        def _is_int_cell(s: str) -> int | None:
            if not s:
                return None
            txt = str(s).strip()
            if re.search(r'[A-Za-z]', txt):
                return None
            try:
                val = int(float(txt.replace('.', '').replace(',', '')))
                return val if 0 < val <= 9999 else None
            except:
                return None

        def _is_money_cell(s: str) -> float | None:
            if not s:
                return None
            txt = str(s).strip()
            m = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2}", txt)
            return normalizar_preco(m.group(0)) if m else None

        for row in table:
            if not row or len(row) < 2:
                continue

            ean = None
            ean_col = None
            for col_idx, cell in enumerate(row):
                if ean := extract_ean13(str(cell) if cell else ''):
                    ean_col = col_idx
                    break

            if not ean:
                continue

            preco_unit = None
            price_col = None
            for j in range(ean_col + 1, len(row)):
                if price := _is_money_cell(row[j]):
                    preco_unit = price
                    price_col = j
                    break

            qtde = None
            if price_col:
                candidates = []
                for j in range(ean_col + 1, price_col):
                    if val := _is_int_cell(row[j]):
                        next_cell = str(row[j+1]).strip().upper() if j + 1 < len(row) else ''
                        if next_cell != 'X':
                            candidates.append((j, val))
                if candidates:
                    _, qtde = candidates[-1]

            if not qtde:
                for j in range(ean_col + 1, len(row)):
                    if val := _is_int_cell(row[j]):
                        qtde = val
                        break

            desc_parts = [str(row[j]).strip() for j in range(ean_col + 1, (price_col or len(row))) if row[j]]
            desc = ' '.join(desc_parts).strip()

            if ean and qtde and qtde > 0:
                produtos.append({
                    'ean': ean,
                    'descricao': desc,
                    'quantidade': qtde,
                    'preco_unitario': preco_unit or 0,
                    'cnpj': cnpj_pagina
                })

        return produtos

    def _extrair_produtos(self, texto: str, cnpj_pagina: str = '') -> list:
        """Extrai produtos de uma página de texto."""
        produtos = []
        
        for linha in texto.split('\n'):
            linha = linha.strip()
            if not linha or not (ean := extract_ean13(linha)):
                continue

            qtd = 1
            preco_unit = 0.0
            
            m = re.search(r'\bUN\s+1\s+X\s+\d+\s+(\d+)\s+([\d,\.]+)', linha, re.IGNORECASE)
            if m:
                try:
                    qtd = int(m.group(1))
                    preco_unit = normalizar_preco(m.group(2))
                except:
                    pass
            else:
                m = re.search(rf"0?{ean}\s+(.+?)\s+(\d{{1,4}})\s+([\d.,]+)", linha)
                if m:
                    try:
                        qtd = int(m.group(2))
                        preco_unit = normalizar_preco(m.group(3))
                    except:
                        qtd = self._extrair_quantidade(linha)

            desc = ''
            ean_match = re.search(rf'\b0?{ean}\b', linha)
            if ean_match:
                resto = linha[ean_match.end():].strip()
                resto = re.sub(r'^\d+\s+', '', resto)
                
                for pattern in [r'(.+?)\s+UN\b', r'(.+?)\s+1\s+X\b', r'(.+?)\s+[\d,\.]+\s+[\d,\.]+']:
                    md = re.match(pattern, resto, re.IGNORECASE)
                    if md:
                        desc = md.group(1).strip()
                        break

            if qtd > 0:
                produtos.append({
                    'ean': ean,
                    'descricao': desc,
                    'quantidade': qtd,
                    'preco_unitario': preco_unit,
                    'cnpj': cnpj_pagina
                })

        return produtos

    def _extrair_quantidade(self, linha: str) -> int:
        """Extrai quantidade de uma linha."""
        partes = ' '.join(linha.split()).split()
        
        if ean := extract_ean13(linha):
            ean_idx = next((i for i, p in enumerate(partes) if ean in p), None)
            if ean_idx:
                for i in range(ean_idx + 1, len(partes)):
                    try:
                        qtd = int(float(partes[i].replace(',', '.')))
                        if 0 < qtd <= 9999:
                            return qtd
                    except:
                        pass
        
        for parte in partes:
            try:
                qtd = int(float(parte.replace(',', '.')))
                if 0 < qtd <= 9999:
                    return qtd
            except:
                pass
        
        return 1

