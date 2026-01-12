"""Processador de arquivos de Imagem (JPG, PNG, BMP)."""

import re
from io import BytesIO
import pandas as pd
from PIL import Image
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

from src.processing.base import FileProcessor
from src.utils.validators import extract_cnpj, is_valid_cnpj, extract_ean13, normalizar_preco, extract_multiplicador_fardos, extract_numero_pedido


class ImageProcessor(FileProcessor):
    """Processa arquivos de imagem e extrai dados via OCR."""
    
    _reader = None
    
    @classmethod
    def _get_reader(cls):
        """Obter ou inicializar o reader EasyOCR (lazy loading)."""
        if not EASYOCR_AVAILABLE:
            return None
        
        if cls._reader is None:
            try:
                print("Inicializando EasyOCR (primeira vez)...")
                import easyocr
                cls._reader = easyocr.Reader(['pt', 'en'], gpu=False)
                print("EasyOCR inicializado com sucesso!")
            except Exception as e:
                print(f"Erro ao inicializar EasyOCR: {e}")
                return None
        
        return cls._reader

    def process(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa imagem e extrai dados de pedidos via OCR."""
        try:
            return self._extract_data(file_content)
        except Exception as e:
            print(f"Erro ao processar imagem: {e}")
            return None

    def _extract_data(self, file_content: bytes) -> pd.DataFrame | None:
        """Extrai dados da imagem usando OCR."""
        try:
            # Abre imagem
            image = Image.open(BytesIO(file_content))
            print(f"Imagem aberta: {image.size} pixels, modo {image.mode}")
            
            # Tenta extrair com análise de posição (novo método)
            df = self._extrair_com_posicoes(image)
            if df is not None and not df.empty:
                print(f"✓ Sucesso! Extraído com análise de posição: {len(df)} produtos")
                return df
            
            print("ℹ️ Método com posições retornou vazio, tentando método fallback...")
            
            # Fallback: extrai texto simples
            texto = self._extrair_texto_ocr(image)
            
            print(f"Texto extraído ({len(texto)} caracteres):")
            if len(texto) > 500:
                print(f"'{texto[:500]}...'")
            else:
                print(f"'{texto}'")
            
            if not texto or texto.strip() == '':
                print("\n❌ ERRO: Nenhum texto foi extraído da imagem!")
                print("\nPossíveis causas:")
                print("  1. A imagem não contém texto legível")
                print("  2. A imagem está muito pequena (< 200x200 pixels)")
                print("  3. A imagem tem muito pouco contraste")
                print("  4. OCR não conseguiu processar (EasyOCR ou Tesseract indisponível)")
                return None
            
            # Processa o texto extraído similar ao TXT
            resultado = self._processar_texto(texto)
            
            if resultado is None or resultado.empty:
                print("\n❌ ERRO: Texto extraído mas nenhum produto foi identificado!")
                print("Nenhum EAN válido foi encontrado na imagem.")
            
            return resultado
            
        except Exception as e:
            print(f"\n❌ ERRO ao extrair OCR: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extrair_com_posicoes(self, image: Image.Image) -> pd.DataFrame | None:
        """Extrai dados analisando posições X,Y do OCR (método novo).
        
        LAYOUT ESPERADO:
        - Coluna esquerda (X ≈ 3-500): Descrição
        - Coluna preço (X ≈ 700-750): Preço (X,YY)
        - Coluna marca (X ≈ 790-950): Gama/Televendas/Marca
        - Coluna quantidade (X ≈ 980-1020): Quantidade (OPCIONAL)
        - Coluna EAN (X ≈ 1080-1206): EAN (13 dígitos)
        """
        try:
            reader = self._get_reader()
            if not reader:
                return None
            
            import numpy as np
            img_array = np.array(image)
            results = reader.readtext(img_array, detail=2)
            
            if not results:
                return None
            
            print("\n[METODO COM POSICOES] Analisando layout da imagem...")
            
            # Agrupar por linhas visuais (Y)
            y_grupos = {}
            
            for result in results:
                bbox = result[0]
                texto = result[1].strip()
                conf = result[2]
                
                if not texto:
                    continue
                
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)
                y_meio = (y_min + y_max) / 2
                
                # Agrupar por linha visual (arredondar Y)
                y_chave = round(y_meio / 25) * 25
                
                if y_chave not in y_grupos:
                    y_grupos[y_chave] = []
                
                # Detectar tipo
                eh_numero = texto.isdigit() and 1 <= int(texto) <= 9999
                eh_preco = bool(re.match(r'^\d+[.,]\d{2}$', texto))
                eh_ean = bool(extract_ean13(texto))
                eh_marca = 'Gama' in texto or 'Televendas' in texto or 'televendas' in texto.lower()
                
                y_grupos[y_chave].append({
                    'x_min': x_min,
                    'x_max': x_max,
                    'y_meio': y_meio,
                    'texto': texto,
                    'conf': conf,
                    'eh_numero': eh_numero,
                    'eh_preco': eh_preco,
                    'eh_ean': eh_ean,
                    'eh_marca': eh_marca,
                    'eh_descricao': not (eh_numero or eh_preco or eh_ean or eh_marca)
                })
            
            # Extrair CNPJ
            cnpj_extraido = ''
            for y_chave in y_grupos:
                for item in y_grupos[y_chave]:
                    cnpj = extract_cnpj(item['texto'])
                    if cnpj:
                        cnpj_extraido = cnpj
                        break
            
            if cnpj_extraido:
                print(f"   CNPJ encontrado: {cnpj_extraido}")
            
            # Processa cada linha visual - procura por EAN
            dados = []
            y_linhas = sorted(y_grupos.keys())
            
            for idx_linha, y_linha in enumerate(y_linhas):
                items = sorted(y_grupos[y_linha], key=lambda t: t['x_min'])
                
                # Procura por EAN nesta linha
                ean_item = None
                for item in items:
                    if item['eh_ean']:
                        ean_item = item
                        break
                
                if not ean_item:
                    continue  # Linha sem EAN, pula
                
                print(f"\n  [OK] Linha Y={y_linha}: EAN {ean_item['texto']} encontrado")
                
                # Procura pelos campos nesta MESMA linha
                desc_item = None
                preco_item = None
                qtd_item = None
                
                for item in items:
                    if item['eh_descricao'] and item['x_min'] < 500:
                        desc_item = item
                    elif item['eh_preco']:
                        preco_item = item
                    elif item['eh_numero'] and item['x_min'] > 980 and item['x_min'] < 1020:
                        qtd_item = item
                
                # Se não achou descrição nesta linha, procura na LINHA ANTERIOR
                if not desc_item and idx_linha > 0:
                    y_anterior = y_linhas[idx_linha - 1]
                    items_anterior = sorted(y_grupos[y_anterior], key=lambda t: t['x_min'])
                    for item in items_anterior:
                        if item['eh_descricao'] and item['x_min'] < 500:
                            desc_item = item
                            break
                
                # Se não achou preço nesta linha, procura na LINHA ANTERIOR
                if not preco_item and idx_linha > 0:
                    y_anterior = y_linhas[idx_linha - 1]
                    items_anterior = sorted(y_grupos[y_anterior], key=lambda t: t['x_min'])
                    for item in items_anterior:
                        if item['eh_preco']:
                            preco_item = item
                            break
                
                # Se não achou quantidade nesta linha, procura na LINHA ANTERIOR
                if not qtd_item and idx_linha > 0:
                    y_anterior = y_linhas[idx_linha - 1]
                    items_anterior = sorted(y_grupos[y_anterior], key=lambda t: t['x_min'])
                    for item in items_anterior:
                        if item['eh_numero'] and item['x_min'] > 980 and item['x_min'] < 1020:
                            qtd_item = item
                            break
                
                # Extrai valores
                descricao = desc_item['texto'] if desc_item else ''
                preco_unit = 0.0
                qtd = 1
                
                if preco_item:
                    preco_str = preco_item['texto'].replace(',', '.')
                    try:
                        preco_unit = float(preco_str)
                        print(f"     Preco: R$ {preco_unit:.2f}")
                    except ValueError:
                        pass
                
                if qtd_item:
                    try:
                        qtd = int(qtd_item['texto'])
                        print(f"     Quantidade: {qtd}")
                    except ValueError:
                        pass
                
                if descricao:
                    print(f"     Descricao: {descricao}")
                
                # Valida: precisa ter descrição e preço
                if descricao and preco_unit > 0:
                    valor_total = preco_unit * qtd
                    print(f"     [VALIDO] QTD={qtd}, PRECO=R${preco_unit:.2f}, TOTAL=R${valor_total:.2f}")
                    
                    dados.append({
                        'CODCLI': ean_item['texto'],
                        'CNPJ': cnpj_extraido,
                        'EAN': ean_item['texto'],
                        'DESCRICAO': descricao,
                        'QTDE': qtd,
                        'PREÇO': preco_unit,
                        'VALOR_TOTAL': valor_total
                    })
                else:
                    print(f"     [SKIP] DESC='{descricao}', PRECO={preco_unit}")
            
            if dados:
                print(f"\n[OK] Extração com posições: {len(dados)} produtos!")
                return pd.DataFrame(dados)
            
            return None
            
        except Exception as e:
            print(f"Erro na extração com posições: {e}")
            return None

    def _extrair_texto_ocr(self, image: Image.Image) -> str:
        """Extrai texto da imagem via OCR."""
        # Tenta EasyOCR primeiro (mais fácil de instalar)
        reader = self._get_reader()
        if reader:
            try:
                # Converte PIL Image para array numpy
                import numpy as np
                img_array = np.array(image)
                
                # EasyOCR
                results = reader.readtext(img_array, detail=0)
                texto = '\n'.join(results)
                
                if texto and texto.strip():
                    print(f"Texto extraído via EasyOCR ({len(texto)} caracteres)")
                    return texto
            except Exception as e:
                print(f"EasyOCR falhou: {e}")
        
        # Se EasyOCR não funcionar, tenta Pytesseract
        if TESSERACT_AVAILABLE:
            try:
                texto = pytesseract.image_to_string(image, lang='por')
                if texto and texto.strip():
                    print(f"Texto extraído via Pytesseract ({len(texto)} caracteres)")
                    return texto
            except Exception as e:
                print(f"Pytesseract falhou: {e}")
        
        # Se nada funcionar, retorna vazio
        print("Aviso: Nenhum OCR disponível. Instale: pip install easyocr")
        return ""

    def _processar_texto(self, texto: str) -> pd.DataFrame | None:
        """Processa o texto extraído e cria DataFrame."""
        linhas = texto.split('\n')
        
        # Tenta extrair número do pedido de todo o texto
        numero_pedido_global = extract_numero_pedido(texto)
        if numero_pedido_global:
            print(f"[IMAGE PROCESSOR] Número do Pedido detectado: {numero_pedido_global}")
        
        # Detecta e tenta processar como TABELA estruturada (novo formato)
        df = self._extrair_tabela_nota_fiscal(linhas)
        if df is not None and not df.empty:
            print(f"OK! Extraido como tabela de nota fiscal: {len(df)} produtos")
            return df
        
        # Tenta extrair como tabela estruturada primeiro (NOVO: combina múltiplas linhas)
        df = self._extrair_tabela_combinada(linhas)
        if df is not None and not df.empty:
            return df
        
        # Tenta abordagem anterior (tabela estruturada simples)
        df = self._extrair_tabela_estruturada(linhas)
        if df is not None and not df.empty:
            return df
        
        # Fallback: extrai como formato de pedido tradicional
        produtos_por_pedido = {}
        pedido_atual = numero_pedido_global or None
        
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            
            # Extrai número do pedido (se ainda não foi extraído globalmente)
            if not pedido_atual:
                if "Numero Pedido:" in linha or "Numero pedido:" in linha or "NUMERO PEDIDO:" in linha:
                    match = re.search(r'(?:Numero Pedido:|Numero pedido:|NUMERO PEDIDO:)\s+(\d+)', linha, re.IGNORECASE)
                    if match:
                        pedido_atual = match.group(1)
                        numero_pedido_global = pedido_atual
                        if pedido_atual not in produtos_por_pedido:
                            produtos_por_pedido[pedido_atual] = {
                                'cnpj': '', 'produtos': [], 'numero_pedido': pedido_atual
                            }
            
            # Garante que há pedido_atual
            if not pedido_atual:
                pedido_atual = numero_pedido_global or 'SEM_NUMERO'
                if pedido_atual not in produtos_por_pedido:
                    produtos_por_pedido[pedido_atual] = {
                        'cnpj': '', 'produtos': [], 'numero_pedido': numero_pedido_global or ''
                    }
            
            # Extrai CNPJ e Filial
            if "Filial:" in linha:
                cnpj = extract_cnpj(linha)
                if cnpj and pedido_atual:
                    produtos_por_pedido[pedido_atual]['cnpj'] = cnpj
            
            # Processa produtos
            if pedido_atual and linha:
                self._processar_linha_produto(linha, pedido_atual, produtos_por_pedido)
        
        if not produtos_por_pedido:
            return None
        
        return self._criar_dataframe(produtos_por_pedido)

    def _extrair_tabela_nota_fiscal(self, linhas: list) -> pd.DataFrame | None:
        """Extrai dados de tabela de nota fiscal/recibo estruturada.
        
        LAYOUT:
        RAZAO SOCIAL.: ...
        CNPJ..........: ...
        
        COD. BARRAS      DESCRICAO                    QUANTIDADE  PRECO UNIT.
        XXXXXXXXXX XXXXX DESCRICAO... QTD PRECO
        ...
        
        TOTAL.....: VALOR
        """
        
        # Procura pela linha de cabeçalho da tabela
        tabela_inicio = -1
        for idx, linha in enumerate(linhas):
            if 'COD. BARRAS' in linha and 'DESCRICAO' in linha:
                tabela_inicio = idx
                break
        
        if tabela_inicio < 0:
            return None  # Não é tabela de nota fiscal
        
        print(f"\n[TABELA NOTA FISCAL] Cabeçalho encontrado na linha {tabela_inicio}")
        
        # Extrair CNPJ do cabeçalho
        cnpj_extraido = ''
        for idx in range(max(0, tabela_inicio - 10), tabela_inicio):
            cnpj_match = extract_cnpj(linhas[idx])
            if cnpj_match:
                cnpj_extraido = cnpj_match
                print(f"   CNPJ: {cnpj_extraido}")
                break
        
        # Processar linhas de produtos
        dados = []
        
        for idx in range(tabela_inicio + 1, len(linhas)):
            linha = linhas[idx].strip()
            
            # Pula linhas vazias
            if not linha:
                continue
            
            # Para quando encontra TOTAL
            if 'TOTAL' in linha:
                break
            
            # Processa linha de produto
            partes = linha.split()
            if len(partes) < 4:  # Mínimo: EAN DIGITO DESC QTD PRECO
                continue
            
            # Extrai EAN - tenta validado primeiro, depois tenta formato puro
            ean = None
            ean_idx = -1
            
            for i in range(min(3, len(partes))):
                # Tenta com validação
                ean_extraido = extract_ean13(partes[i])
                if ean_extraido:
                    ean = ean_extraido
                    ean_idx = i
                    break
                
                # Se não achou, tenta formato puro (13 dígitos, mesmo que inválido)
                if re.match(r'^\d{13}$', partes[i]):
                    ean = partes[i]
                    ean_idx = i
                    break
            
            if not ean:
                continue
            
            # Processa a linha: EAN [digito] DESC... QTD PRECO
            # Estratégia: últimos 2 números são QTD e PRECO
            
            numeros_no_final = []
            for i in range(len(partes) - 1, -1, -1):
                if re.match(r'^\d+[.,]?\d*$', partes[i]):
                    numeros_no_final.insert(0, (i, partes[i]))
                else:
                    if len(numeros_no_final) >= 2:
                        break
            
            if len(numeros_no_final) < 2:
                continue  # Sem quantidade e preço válidos
            
            # Extrair valores
            qtde_str = numeros_no_final[-2][1]
            preco_str = numeros_no_final[-1][1]
            
            try:
                qtde = int(qtde_str) if qtde_str.isdigit() else 1
            except ValueError:
                qtde = 1
            
            try:
                preco = float(preco_str.replace(',', '.'))
            except ValueError:
                preco = 0.0
            
            # Descrição: tudo entre EAN e quantidade
            desc_fim = numeros_no_final[-2][0]
            desc_partes = partes[ean_idx + 1:desc_fim]
            
            # Remove dígitos de controle (números únicos após EAN)
            if desc_partes and desc_partes[0].isdigit() and len(desc_partes[0]) <= 2:
                desc_partes = desc_partes[1:]
            
            descricao = ' '.join(desc_partes).strip()
            
            if not descricao or preco <= 0:
                continue
            
            print(f"  EAN {ean}: '{descricao[:50]}' QTD={qtde} P=R${preco:.2f}")
            
            valor_total = preco * qtde
            
            dados.append({
                'CODCLI': ean,
                'CNPJ': cnpj_extraido,
                'EAN': ean,
                'DESCRICAO': descricao,
                'QTDE': qtde,
                'PREÇO': preco,
                'VALOR_TOTAL': valor_total
            })
        
        if dados:
            print(f"[OK] {len(dados)} produtos extraídos da tabela!")
            return pd.DataFrame(dados)
        
        return None
        """Extrai tabelas onde EAN e descrição podem estar em linhas diferentes.
        
        ESTRUTURA ESPERADA (Imagem com tabela de pedidos):
        - Descrição (linha N)
        - Preço unitário (linha N+1) - formato X,YY ou X.YY
        - Marca/Fabricante (linha N+2) - "Gama", "Televendas", etc
        - [QUANTIDADE] (linha N+3 - OPCIONAL) - apenas se presente
        - EAN (linha N+3 ou N+4) - 13 dígitos
        
        ESTRATÉGIA REVISADA:
        - Procura por EANs (13 dígitos)
        - Para cada EAN, procura PARA TRÁS:
          1. Descrição: primeira linha não-vazia que não é número puro
          2. Preço: primeira linha com decimal (X,YY ou X.YY)
          3. Quantidade: número inteiro (1-9999) entre preço e EAN
        """
        dados = []
        cnpj_extraido = extract_cnpj('\n'.join(linhas))
        
        print(f"[METODO COMBINADO] Procurando EANs em {len(linhas)} linhas...")
        print(f"   CNPJ encontrado: {cnpj_extraido}")
        
        i = 0
        while i < len(linhas):
            linha = linhas[i].strip()
            
            # Procura por EAN nesta linha
            ean = extract_ean13(linha)
            
            if ean:
                print(f"  [OK] Linha {i}: EAN {ean} encontrado")
                
                descricao = ''
                qtd = 1
                preco_unit = 0.0
                
                # Procura PARA TRÁS a partir do EAN
                qtd_encontrada = False
                preco_encontrado = False
                desc_encontrada = False
                
                # Busca para trás: procura por preço, quantidade e descrição
                for j in range(i - 1, max(-1, i - 15), -1):  # Procura até 15 linhas atrás
                    prev_line = linhas[j].strip()
                    if not prev_line:
                        continue
                    
                    # QUANTIDADE: número inteiro entre 1 e 9999, linha "pura"
                    if not qtd_encontrada:
                        numeros_puros = re.findall(r'^\d+$', prev_line)
                        if numeros_puros:
                            qtd_temp = int(numeros_puros[0])
                            # Filtra: quantidade deve estar entre 1 e 9999, NÃO ser EAN (13 dígitos)
                            if 1 <= qtd_temp <= 9999 and len(numeros_puros[0]) != 13:
                                qtd = qtd_temp
                                qtd_encontrada = True
                                print(f"     Quantidade (linha {j}): {qtd}")
                                continue
                    
                    # PRECO: número com decimal (X,YY ou X.YY), EXATAMENTE com 2 casas decimais
                    if not preco_encontrado:
                        precos = re.findall(r'(\d+[.,]\d{2})(?:\s|$)', prev_line)
                        if precos:
                            preco_str = precos[0].replace(',', '.')
                            try:
                                preco_temp = float(preco_str)
                                # Preço válido: entre 0.1 e 999999
                                if 0.1 <= preco_temp <= 999999:
                                    preco_unit = preco_temp
                                    preco_encontrado = True
                                    print(f"     Preco (linha {j}): R$ {preco_unit:.2f}")
                            except ValueError:
                                pass
                    
                    # DESCRIÇÃO: primeira linha "normal" que NÃO é:
                    # - número puro, - preço com decimal, - EAN, - marca (Gama, Televendas, etc)
                    if not desc_encontrada:
                        if (prev_line and 
                            not extract_ean13(prev_line) and
                            not re.match(r'^\d+$', prev_line) and  # não é número puro
                            not re.match(r'^\d+[.,]\d{2}$', prev_line) and  # não é preço
                            'Gama' not in prev_line and
                            'Televendas' not in prev_line and
                            'CNPJ' not in prev_line):
                            
                            descricao = prev_line
                            desc_encontrada = True
                            print(f"     Descricao (linha {j}): {descricao}")
                
                # Calcula valor total
                valor_total = preco_unit * qtd if preco_unit > 0 else 0
                
                # Valida: se temos descrição e EAN, adiciona (quantidade e preço são opcionais)
                # Mas PRECO é mandatório para marcar como válido
                if descricao and preco_unit > 0:
                    print(f"     [VALIDO] DESC='{descricao}', QTD={qtd}, PRECO=R${preco_unit:.2f}, TOTAL=R${valor_total:.2f}")
                    print()
                    
                    dados.append({
                        'CODCLI': ean,
                        'CNPJ': cnpj_extraido or '',
                        'EAN': ean,
                        'DESCRICAO': descricao,
                        'QTDE': qtd,
                        'PREÇO': preco_unit,
                        'VALOR_TOTAL': valor_total
                    })
                elif descricao:
                    # Tem descrição mas sem preço - pode ser caso especial
                    print(f"     [PARCIAL] Tem descricao mas sem preco: DESC='{descricao}'")
                    print()
                else:
                    print(f"     [INVALIDO] Faltam dados: DESC='{descricao}', PRECO={preco_unit}")
                    print()
            
            i += 1
        
        if dados:
            print(f"[OK] METODO COMBINADO: {len(dados)} produtos encontrados!")
            return pd.DataFrame(dados)
        
        return None

    def _extrair_tabela_estruturada(self, linhas: list) -> pd.DataFrame | None:
        """Extrai dados de tabelas estruturadas (como memos de distribuição BAHM)."""
        dados = []
        cnpj_extraido = ''
        print(f"🔍 Procurando tabelas estruturadas em {len(linhas)} linhas...")
        
        # Primeiro, tenta extrair CNPJ da imagem inteira
        texto_completo = '\n'.join(linhas)
        cnpj_extraido = extract_cnpj(texto_completo)
        if cnpj_extraido:
            print(f"  ✅ CNPJ encontrado: {cnpj_extraido}")
        
        for i, linha in enumerate(linhas):
            linha_original = linha
            linha = linha.strip()
            if not linha:
                continue
            
            # Procura por linhas que contêm EAN (13 dígitos)
            ean = extract_ean13(linha)
            
            if ean:
                print(f"  ✅ Linha {i}: Encontrado EAN {ean}")
                print(f"     Linha original: '{linha_original}'")
                
                # Extrai quantidade e descrição para essa estrutura
                descricao, qtd = self._extrair_desc_qtd_bahm(linha, ean)
                
                print(f"     Descrição: '{descricao}'")
                print(f"     Quantidade: {qtd}")
                
                dados.append({
                    'CODCLI': ean,
                    'CNPJ': cnpj_extraido,
                    'EAN': ean,
                    'DESCRICAO': descricao,
                    'QTDE': qtd,
                    'PREÇO': 0
                })
        
        if dados:
            print(f"✅ Tabela estruturada: {len(dados)} produtos encontrados!")
        else:
            print(f"❌ Nenhuma tabela estruturada encontrada")
        
        return pd.DataFrame(dados) if dados else None
    
    def _extrair_desc_qtd_preco_bahm(self, linha: str, ean: str) -> tuple:
        """Extrai descrição, quantidade e preço unitário seguindo REGRAS OBRIGATÓRIAS.
        
        REGRAS:
        1. PRODUTO: Identificado pela coluna de descrição (Produto, Mercadoria, Descrição, etc.)
        2. FABRICANTE: Desconsiderado - NÃO é usado na análise
        3. QUANTIDADE: Identificada por "Qtde. Ped." ou variações similares (número inteiro)
        4. VALOR UNITÁRIO: Preço de um único item
        5. VALOR TOTAL: Calculado como Quantidade × Valor Unitário
        
        ESTRATÉGIA: Se EAN é fornecido, extrai dados da linha com EAN.
                    Se EAN é vazio, trata a linha como DESCRIÇÃO pura.
        """
        descricao = ''
        qtd = 1
        preco = 0.0
        
        linha = ' '.join(linha.split())
        
        # MODO 1: Linha com EAN (dados estruturados)
        if ean:
            ean_pos = linha.find(ean)
            if ean_pos < 0:
                return '', 1, 0.0
            
            depois_ean = linha[ean_pos + len(ean):].strip()
            partes = depois_ean.split()
            
            if not partes:
                return '', 1, 0.0
            
            # Encontra a QUANTIDADE (primeiro número inteiro > 0)
            idx_quantidade = -1
            qtd_temp = 1
            
            for idx, p in enumerate(partes):
                if p.isdigit() and idx > 1:
                    num = int(p)
                    if 0 < num < 1000:
                        idx_quantidade = idx
                        qtd_temp = num
                        break
            
            # Encontra o FABRICANTE (procurando para trás)
            idx_fabricante = -1
            
            if idx_quantidade > 0:
                ultimo_maiuscula_idx = -1
                
                for idx in range(idx_quantidade - 1, -1, -1):
                    p = partes[idx]
                    
                    eh_maiuscula = (len(p) >= 2 and 
                                   p.isupper() and 
                                   not p.isdigit() and 
                                   not self._eh_numero(p) and
                                   ',' not in p and '.' not in p)
                    
                    if eh_maiuscula:
                        if ultimo_maiuscula_idx < 0:
                            ultimo_maiuscula_idx = idx
                        idx_fabricante = idx
                    else:
                        if ultimo_maiuscula_idx >= 0:
                            break
                
                if idx_fabricante >= 0:
                    fabricante_palavras = partes[idx_fabricante:ultimo_maiuscula_idx + 1]
                    print(f"     [DESCARTADO] Fabricante: {' '.join(fabricante_palavras)}")
            
            # Coleta DESCRIÇÃO
            if idx_fabricante > 0:
                palavras_desc = partes[:idx_fabricante]
            elif idx_quantidade > 0:
                palavras_desc = partes[:idx_quantidade]
            else:
                palavras_desc = partes
            
            palavras_desc_filtradas = []
            for p in palavras_desc:
                if not p.isdigit() and not self._eh_numero(p) and p not in ['-', '|', '(un)', 'un']:
                    p_limpo = p.rstrip(',.')
                    if p_limpo:
                        palavras_desc_filtradas.append(p_limpo)
            
            if palavras_desc_filtradas:
                descricao = ' '.join(palavras_desc_filtradas).strip()[:150]
            
            print(f"     Descricao: '{descricao}'")
            
            # Extrai PREÇO
            preco = 0.0
            
            if idx_quantidade > 0:
                for idx in range(idx_quantidade + 1, len(partes)):
                    p = partes[idx]
                    
                    if self._eh_numero(p) and (',' in p or '.' in p):
                        try:
                            preco_str = p.replace(',', '.')
                            preco = float(preco_str)
                            print(f"     Valor Un.: R$ {preco:.2f}")
                            break
                        except ValueError:
                            continue
            
            qtd = qtd_temp
            valor_total = qtd * preco
            
            return descricao, qtd, preco
        
        # MODO 2: Linha SEM EAN (descrição pura, em linha separada)
        else:
            # Limpa parênteses e caracteres especiais
            descricao = linha.replace('(un)', '').replace('[un)', '').replace('[unj', '').strip()
            descricao = ' '.join(descricao.split())[:150]
            print(f"     [DESC pura] '{descricao}'")
            return descricao, 1, 0.0
    
    def _extrair_desc_qtd_bahm(self, linha: str, ean: str) -> tuple:
        """Função legada - chama a nova versão e ignora preço."""
        descricao, qtd, _ = self._extrair_desc_qtd_preco_bahm(linha, ean)
        return descricao, qtd
    @staticmethod
    def _eh_numero(texto: str) -> bool:
        """Verifica se texto é um número (inteiro ou decimal com vírgula/ponto)."""
        if not texto:
            return False
        try:
            float(texto.replace(',', '.'))
            return True
        except ValueError:
            return False

    def _processar_linha_produto(self, linha: str, pedido_atual: str, 
                                 produtos_por_pedido: dict) -> None:
        """Processa uma linha de produto extraída da imagem."""
        # Pula linhas que são de informação, não de produto
        if any(x in linha for x in ["Numero Pedido:", "Filial:", "UF:", "Pedido:", "Tot.", "Total", "Vlr."]):
            return
        
        # Extrai EAN usando a nova função
        ean = extract_ean13(linha)
        
        if not ean:
            return
        
        # Encontra quantidade
        partes = linha.split()
        qtd = None
        
        # Procura por números após o EAN
        ean_idx = None
        for i, p in enumerate(partes):
            if p in ean or ean in p:
                ean_idx = i
                break
        
        if ean_idx is not None:
            for i in range(ean_idx + 1, len(partes)):
                try:
                    qtd = int(partes[i])
                    if qtd > 0:
                        break
                except ValueError:
                    try:
                        qtd = int(float(partes[i].replace(',', '.')))
                        if qtd > 0:
                            break
                    except ValueError:
                        pass
        
        if not qtd or qtd <= 0:
            qtd = 1  # Padrão: quantidade 1 se não encontrar
        
        if ean:
            produtos_por_pedido[pedido_atual]['produtos'].append({
                'barras': ean,
                'quantidade': qtd
            })

    def _criar_dataframe(self, produtos_por_pedido: dict) -> pd.DataFrame | None:
        """Cria DataFrame a partir dos dados extraídos."""
        dados = []
        
        for pedido, dados_pedido in produtos_por_pedido.items():
            cnpj = dados_pedido['cnpj']
            numero_pedido = dados_pedido.get('numero_pedido', pedido)
            
            for produto in dados_pedido['produtos']:
                ean_value = produto['barras']
                desc = produto.get('descricao', '')
                
                # Extrair multiplicador de fardos e normalizar descrição
                desc_limpa, multiplicador = extract_multiplicador_fardos(desc)
                
                # Aplicar multiplicador na quantidade
                qtde = int(produto['quantidade'] * multiplicador)
                preco = normalizar_preco(produto.get('preco_unitario', 0))
                
                dados.append({
                    'PEDIDO': numero_pedido,
                    'CODCLI': '',
                    'CNPJ': cnpj,
                    'EAN': ean_value,
                    'DESCRICAO': desc_limpa.strip(),
                    'PREÇO': preco,
                    'QTDE': qtde,
                    'TOTAL': qtde * preco if preco > 0 else 0
                })
        
        df = pd.DataFrame(dados) if dados else None
        
        # Reordenar colunas para incluir PEDIDO no início
        if df is not None:
            col_order = [col for col in ['PEDIDO', 'CODCLI', 'CNPJ', 'EAN', 'DESCRICAO', 'PREÇO', 'QTDE', 'TOTAL'] if col in df.columns]
            df = df[col_order]
        
        return df
