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

    def process(self, file_content: bytes) -> pd.DataFrame | None:
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
                'PEDIDO': numero_pedido_global,
                'CODCLI': '',
                'CNPJ': cnpj_value,
                'EAN': ean_value,
                'DESCRICAO': desc_limpa.strip(),
                'PREÇO': preco,
                'QTDE': qtde,
                'TOTAL': qtde * preco if preco > 0 else 0
            })
        
        df = pd.DataFrame(dados) if dados else None
        
        # Reordenar colunas conforme Regra 06: PEDIDO, CODCLI, CNPJ, EAN, DESCRICAO, PRECO, QTDE, TOTAL
        if df is not None:
            col_order = [col for col in ['PEDIDO', 'CODCLI', 'CNPJ', 'EAN', 'DESCRICAO', 'PREÇO', 'QTDE', 'TOTAL'] if col in df.columns]
            df = df[col_order]
        
        return df

    def _extrair_de_tabela(self, table: list, cnpj_pagina: str = '') -> list:
        """Extrai produtos de uma tabela estruturada, incluindo descrição e quantidade."""
        produtos = []

        def _is_int_cell(s: str) -> int | None:
            if s is None:
                return None
            txt = str(s).strip()
            if not txt:
                return None
            # rejeita se tem letras (para evitar '500ML')
            if re.search(r'[A-Za-z]', txt):
                return None
            # normaliza milhar/decimal
            cand = txt.replace('.', '').replace(',', '')
            try:
                val = int(float(cand))
                if 0 < val <= 9999:
                    return val
            except Exception:
                return None
            return None

        def _is_money_cell(s: str) -> float | None:
            if s is None:
                return None
            txt = str(s).strip()
            if not txt:
                return None
            # aceita formatos 1.234,56 ou 12,34 ou 12.34
            m = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2}", txt)
            if not m:
                return None
            return normalizar_preco(m.group(0))

        for row in table:
            if not row or len(row) < 2:
                continue

            ean = None
            desc = ''
            qtde = None
            preco_unit = None

            # localizar EAN
            ean_col = None
            for col_idx, cell in enumerate(row):
                cell_str = '' if cell is None else str(cell).strip()
                ean_temp = extract_ean13(cell_str)
                if ean_temp:
                    ean = ean_temp
                    ean_col = col_idx
                    break

            if ean is None:
                continue

            # primeiro, localizar a primeira coluna de preço (monetária) à direita do EAN
            price_col = None
            for j in range(ean_col + 1, len(row)):
                price = _is_money_cell(row[j])
                if price is not None and price > 0:
                    preco_unit = price
                    price_col = j
                    break

            # selecionar quantidade: o penúltimo inteiro antes da primeira coluna de preço
            # (pula "1 X 1" ou "1 X") e pega o próximo inteiro isolado
            q_col = None
            if price_col is not None:
                candidates = []
                for j in range(ean_col + 1, price_col):
                    cell_str = '' if row[j] is None else str(row[j]).strip()
                    val = _is_int_cell(cell_str)
                    if val is not None:
                        # rejeita se a célula seguinte for 'X' (padrão embalagem "1 X")
                        next_cell = '' if (j + 1 >= len(row) or row[j+1] is None) else str(row[j+1]).strip()
                        if next_cell.upper() == 'X':
                            continue
                        candidates.append((j, val))
                
                # Escolhe o último candidato válido (mais próximo do preço)
                if candidates:
                    q_col, qtde = candidates[-1]

            # fallback: primeiro inteiro à direita do EAN
            if qtde is None:
                for j in range(ean_col + 1, len(row)):
                    cell_str = '' if row[j] is None else str(row[j]).strip()
                    val = _is_int_cell(cell_str)
                    if val is not None:
                        qtde = val
                        q_col = j
                        break

            # construir descrição com base no intervalo entre EAN e coluna de quantidade escolhida
            desc_parts = []
            limit = q_col if q_col is not None else len(row)
            for j in range(ean_col + 1, limit):
                cell = row[j]
                cell_str = '' if cell is None else str(cell).strip()
                if cell_str:
                    desc_parts.append(cell_str)
            desc = ' '.join(desc_parts).strip()

            if ean and qtde and qtde > 0:
                produtos.append({
                    'ean': ean,
                    'descricao': desc,
                    'quantidade': qtde,
                    'preco_unitario': preco_unit or 0,
                    'cnpj': cnpj_pagina  # Adicionar CNPJ da página
                })

        return produtos

    def _extrair_produtos(self, texto: str, cnpj_pagina: str = '') -> list:
        """Extrai produtos de uma página de texto (fallback), com descrição e preços."""
        produtos = []
        linhas = texto.split('\n')

        for linha in linhas:
            if not linha.strip():
                continue

            ean = extract_ean13(linha)
            if not ean:
                continue

            # Padrão observado: EAN CODIGO DESCRICAO ... UN 1 X QTD PRECO
            # Exemplo: 7891350041408 60064 DES BOZZANO ... UN 1 X 1 2 9,17
            # Busca padrão: UN seguido de "1 X", depois qtd (int), depois preço (decimal)
            m = re.search(r'\bUN\s+1\s+X\s+\d+\s+(\d+)\s+([\d,\.]+)', linha, re.IGNORECASE)
            if m:
                try:
                    qtd = int(m.group(1))
                    preco_unit = normalizar_preco(m.group(2))
                except:
                    qtd = 1
                    preco_unit = 0.0
            else:
                # Fallback original para outros formatos
                m = re.search(rf"0?{ean}\s+(.+?)\s+(\d{{1,4}})\s+([\d.,]+).*?([\d.,]+)\s*$", linha)
                if m:
                    try:
                        qtd = int(m.group(2))
                        preco_unit = normalizar_preco(m.group(3))
                    except:
                        qtd = self._extrair_quantidade(linha)
                        preco_unit = 0.0
                else:
                    qtd = self._extrair_quantidade(linha)
                    preco_unit = 0.0

            # Extrai descrição: localiza EAN, depois captura texto até "UN"
            desc = ''
            # Encontra posição do EAN na linha (com ou sem 0 inicial)
            ean_match = re.search(rf'\b0?{ean}\b', linha)
            if ean_match:
                # Pega tudo após o EAN
                pos_fim_ean = ean_match.end()
                resto = linha[pos_fim_ean:].strip()
                
                # Remove possível código numérico logo após o EAN
                resto = re.sub(r'^\d+\s+', '', resto)
                
                # Captura tudo até "UN" (unidade)
                md = re.match(r'(.+?)\s+UN\b', resto, re.IGNORECASE)
                if md:
                    desc = md.group(1).strip()
                else:
                    # Fallback: captura até "1 X" (padrão de embalagem)
                    md2 = re.match(r'(.+?)\s+1\s+X\b', resto, re.IGNORECASE)
                    if md2:
                        desc = md2.group(1).strip()
                    else:
                        # Terceira tentativa: até padrão de números decimais (preços)
                        md3 = re.match(r'(.+?)\s+[\d,\.]+\s+[\d,\.]+', resto)
                        if md3:
                            desc = md3.group(1).strip()
                        else:
                            # Último fallback: até múltiplos espaços + dígito
                            md4 = re.match(r'(.+?)\s{2,}\d', resto)
                            if md4:
                                desc = md4.group(1).strip()

            if qtd and qtd > 0:
                produtos.append({
                    'ean': ean,
                    'descricao': desc,
                    'quantidade': qtd,
                    'preco_unitario': preco_unit,
                    'cnpj': cnpj_pagina  # Adicionar CNPJ da página
                })

        return produtos

    def _extrair_quantidade(self, linha: str) -> int:
        """Extrai quantidade de uma linha."""
        # Remove múltiplos espaços
        linha_limpa = ' '.join(linha.split())
        partes = linha_limpa.split()
        
        # Se houver EAN, procura número APÓS o EAN (primeira coluna numérica com valor > 0)
        ean = extract_ean13(linha)
        if ean:
            # Encontra posição do EAN
            ean_idx = None
            for i, parte in enumerate(partes):
                if ean in parte or parte in ean:
                    ean_idx = i
                    break
            
            # Se encontrou EAN, procura primeiro número válido depois dele
            if ean_idx is not None:
                for i in range(ean_idx + 1, len(partes)):
                    parte = partes[i].replace(',', '.').replace('(', '').replace(')', '').strip()
                    try:
                        qtd = int(float(parte))
                        if 0 < qtd <= 9999:  # Quantidade razoável (não acima de 9999)
                            return qtd
                    except (ValueError, TypeError):
                        pass
        
        # Se não encontrou após EAN, procura número em geral
        # Preferência: primeiro número inteiro válido na linha
        for parte in partes:
            parte_limpa = parte.replace(',', '.').replace('(', '').replace(')', '').replace('-', '')
            try:
                num = float(parte_limpa)
                qtd = int(num)
                if 0 < qtd <= 9999:  # Quantidade razoável
                    return qtd
            except (ValueError, TypeError):
                pass
        
        return 1  # Padrão: 1 unidade

