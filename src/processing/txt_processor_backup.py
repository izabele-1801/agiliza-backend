"""Processador de arquivos TXT."""

import re
import pandas as pd
from src.processing.base import FileProcessor
from src.utils.constants import EXCEL_COLUMNS
from src.utils.validators import extract_cnpj, is_valid_cnpj, extract_ean13, normalizar_preco, extract_multiplicador_fardos


class TXTProcessor(FileProcessor):
    """Processa arquivos TXT."""

    def process(self, file_content: bytes) -> pd.DataFrame | None:
        """Processa TXT e extrai dados."""
        try:
            texto = file_content.decode('utf-8', errors='ignore')
            return self._extract_data(texto)
        except Exception as e:
            print(f"Erro ao processar TXT: {e}")
            return None

    def _extract_data(self, texto: str) -> pd.DataFrame | None:
        """Extrai dados do TXT."""
        linhas = texto.split('\n')
        produtos_por_pedido = {}
        pedido_atual = None
        cnpj_atual = None
        
        for linha in linhas:
            linha_strip = linha.strip()
            if not linha_strip:
                continue
            
            # Tenta extrair CNPJ
            if "CNPJ" in linha:
                cnpj = extract_cnpj(linha)
                if cnpj:
                    # Aceita CNPJ sem validação rigorosa, só se encontrou um número de 14 dígitos
                    cnpj_atual = cnpj
                    if cnpj not in produtos_por_pedido:
                        produtos_por_pedido[cnpj] = {
                            'cnpj': cnpj, 'produtos': []
                        }
                    pedido_atual = cnpj
            
            # Tenta extrair número do pedido
            elif "PEDIDO" in linha and ":" in linha:
                match = re.search(r'(?:PEDIDO|Pedido|Numero Pedido)[:\s.]+([S\d\-]+)', linha, re.IGNORECASE)
                if match:
                    pedido_num = match.group(1).strip()
                    if pedido_atual:
                        produtos_por_pedido[pedido_atual]['pedido'] = pedido_num
            
            # Processa linhas que contêm produtos (têm "Código de Barras" ou estão em formato tabular)
            # Opção 1: linha com "Código de Barras:"
            elif "Código de Barras:" in linha or "Codigo de Barras:" in linha:
                if not pedido_atual:
                    # Cria pedido padrão quando não há CNPJ mas há itens
                    pedido_atual = 'SEM_CNPJ'
                    produtos_por_pedido[pedido_atual] = {'cnpj': cnpj_atual or '', 'produtos': []}
                self._processar_linha_produto(linha, pedido_atual, produtos_por_pedido)
            
            # Opção 2: formato tabular com :XXXXXXXX: (tipo :7896018750845: )
            elif re.search(r':\d{13}\s', linha):
                if not pedido_atual:
                    pedido_atual = 'SEM_CNPJ'
                    produtos_por_pedido[pedido_atual] = {'cnpj': cnpj_atual or '', 'produtos': []}
                self._processar_linha_produto(linha, pedido_atual, produtos_por_pedido)
            
            # Opção 3: linhas tabulares iniciando com EAN-13 ou EAN-14 (14 dígitos começando com 0)
            else:
                # Busca por EAN-13 ou EAN-14 no início da linha
                if re.match(r'^\s*0?\d{13}', linha):
                    if not pedido_atual:
                        pedido_atual = 'SEM_CNPJ'
                        produtos_por_pedido[pedido_atual] = {'cnpj': cnpj_atual or '', 'produtos': []}
                    self._processar_linha_produto(linha, pedido_atual, produtos_por_pedido)
                else:
                    # Tenta buscar EAN-13 em qualquer lugar da linha
                    ean_inline = extract_ean13(linha)
                    if ean_inline:
                        if not pedido_atual:
                            pedido_atual = 'SEM_CNPJ'
                            produtos_por_pedido[pedido_atual] = {'cnpj': cnpj_atual or '', 'produtos': []}
                        self._processar_linha_produto(linha, pedido_atual, produtos_por_pedido)
        
        if not produtos_por_pedido:
            return None
        
        return self._criar_dataframe(produtos_por_pedido)

    def _processar_linha_produto(self, linha: str, pedido_atual: str, 
                                 produtos_por_pedido: dict) -> None:
        """Processa uma linha de produto."""
        # Pula linhas que são separadores ou não têm dados
        if any(x in linha.upper() for x in ["----", "COD. BARRAS", "CODIGO", "PRODUTO", "DESCRI", "QUANTIDADE", "PRE�O", "PREÇO"]):
            return
        
        # Tenta extrair EAN-14 (14 dígitos começando com 0) ou EAN-13
        ean = self._extrair_ean(linha)
        
        if not ean:
            return
        
        # Encontra quantidade usando múltiplas estratégias
        qtd = self._extrair_quantidade_linha(linha, ean)
        
        if not qtd or qtd <= 0:
            qtd = 1  # Padrão: quantidade 1 se não encontrar
        
        if ean:
            produtos_por_pedido[pedido_atual]['produtos'].append({
                'barras': ean,
                'quantidade': qtd
            })
    
    def _extrair_ean(self, linha: str) -> str | None:
        """Extrai EAN-14 (começando com 0) ou EAN-13 da linha."""
        # Primeiro tenta EAN-14 (14 dígitos começando com 0)
        match = re.search(r'\b(0\d{13})\b', linha)
        if match:
            ean14 = match.group(1)
            # Remove o zero inicial para converter em EAN-13
            return ean14[1:]
        
        # Depois tenta EAN-13 padrão
        return extract_ean13(linha)
    
    def _extrair_quantidade_linha(self, linha: str, ean: str) -> int:
        """Extrai quantidade de uma linha de produto com múltiplas estratégias."""
        qtd = None

        # Estratégia para formato: EAN-14 + DESCRIÇÃO + QUANTIDADE + PREÇO
        # Exemplo: "07896110007502    ABS SYM PROT DIARIO 15UN C/PERF                                2            4,55"
        match_novo_formato = re.search(r'^\s*0?\d{13}\s+.*?\s+(\d{1,4})\s+[\d,\.]+\s*$', linha)
        if match_novo_formato:
            try:
                num = int(match_novo_formato.group(1))
                if 0 < num < 10000:
                    return num
            except ValueError:
                pass

        # Estratégia GAMA: linha tabular inicia com EAN e a quantidade vem antes do primeiro preço
        # Exemplo: "7891000261965 0365685 LEITE ...   12    34.99"
        match_tabular = re.search(r'^\s*\d{13}.*?\s(\d{1,4})\s+[\d]{1,3}[.,]\d{2}\b', linha)
        if match_tabular:
        """Extrai quantidade de uma linha de produto com múltiplas estratégias."""
        qtd = None

        # Estratégia GAMA: linha tabular inicia com EAN e a quantidade vem antes do primeiro preço
        # Exemplo: "7891000261965 0365685 LEITE ...   12    34.99"
        match_tabular = re.search(r'^\s*\d{13}.*?\s(\d{1,4})\s+[\d]{1,3}[.,]\d{2}\b', linha)
        if match_tabular:
            try:
                num = int(match_tabular.group(1))
                if 0 < num < 10000:
                    return num
            except ValueError:
                pass
        
        # Estratégia 0: CRÍTICA - Procura por padrões numéricos específicos antes de tudo
        # Procura por :00X: (quantidade em coluna com padding) - mais específico
        match = re.search(r':\s*(\d{1,2})\s*(?:$|[\r\n|:])', linha)
        if match:
            num_str = match.group(1)
            try:
                num = int(num_str)
                if 0 < num < 100:  # Quantidade razoável
                    return num
            except ValueError:
                pass
        
        # Estratégia 1: Procura pela posição após o EAN (para formato tabular :EAN:DESC:FAB:QTD)
        ean_pos = linha.find(ean)
        if ean_pos >= 0:
            # Tudo após o EAN
            depois_ean = linha[ean_pos + len(ean):]
            
            # Split por : para pegar cada coluna
            partes = depois_ean.split(':')
            
            # A quantidade geralmente é a última coluna (após fabricante)
            # Procura do final para o início por um número inteiro válido
            for parte in reversed(partes):
                numeros = parte.strip().split()
                for num_str in reversed(numeros):
                    try:
                        num = int(num_str)
                        # Filtra números muito grandes (tipo 360 de "360ML") vs quantidade
                        if 0 < num < 1000 and num < 200:  # Quantidade típica < 200
                            return num
                    except ValueError:
                        pass
        
        # Estratégia 2: Procura por "Qtd:" ou variações (mais específico)
        match = re.search(r'(?:Qtd|QTD|Qtde|QTDE|quantidade)[.:\s]+(\d+)', linha, re.IGNORECASE)
        if match:
            try:
                qtd = int(match.group(1))
                if qtd > 0:
                    return qtd
            except ValueError:
                pass
        
        # Estratégia 3: Procura por padrão tabular com | (pipe) também
        # Alguns arquivos usam | em vez de :
        if '|' in linha:
            partes = linha.split('|')
            for parte in reversed(partes):
                numeros = parte.strip().split()
                for num_str in reversed(numeros):
                    try:
                        num = int(num_str)
                        if 0 < num < 1000 and num < 200:
                            return num
                    except ValueError:
                        pass
        
        # Estratégia 4: Procura pelo último número menor que 100 (quantidade típica)
        # Isso ajuda a evitar pegar 360, 200ML, etc
        import re as regex_module
        todos_numeros = regex_module.findall(r'\b(\d+)\b', linha)
        
        # Filtra para apenas números que parecem ser quantidade (< 100)
        quantidades_possiveis = []
        for num_str in reversed(todos_numeros):
            try:
                num = int(num_str)
                if 0 < num < 100:  # Quantidade típica
                    quantidades_possiveis.append(num)
            except ValueError:
                pass
        
        if quantidades_possiveis:
            return quantidades_possiveis[0]
        
        # Estratégia 5: Se ainda não encontrou, procura por qualquer número válido
        partes = linha.split(':')
        if len(partes) > 0:
            ultima_parte = partes[-1].strip()
            numeros = ultima_parte.split()
            
            for num_str in reversed(numeros):
                try:
                    qtd = int(num_str)
                    if 0 < qtd < 10000:
                        return qtd
                except ValueError:
                    try:
                        qtd = int(float(num_str.replace(',', '.')))
                        if 0 < qtd < 10000:
                            return qtd
                    except ValueError:
                        pass
        
        return 1  # Padrão

    def _criar_dataframe(self, produtos_por_pedido: dict) -> pd.DataFrame | None:
        """Cria DataFrame a partir dos dados extraídos."""
        dados = []
        
        for pedido, dados_pedido in produtos_por_pedido.items():
            cnpj = dados_pedido['cnpj']
            
            for produto in dados_pedido['produtos']:
                # Extrair multiplicador de fardos e normalizar descrição
                desc = produto.get('descricao', '')
                desc_limpa, multiplicador = extract_multiplicador_fardos(desc)
                
                # Aplicar multiplicador na quantidade
                qtde = int(produto['quantidade'] * multiplicador)
                preco = normalizar_preco(produto.get('preco', 0))
                
                ean_value = produto['barras']
                dados.append({
                    'CODCLI': ean_value,
                    'CNPJ': cnpj,
                    'EAN': ean_value,
                    'DESCRICAO': desc_limpa.strip(),
                    'QTDE': qtde,
                    'PREÇO': preco,
                    'TOTAL': qtde * preco if preco > 0 else 0
                })
        
        df = pd.DataFrame(dados) if dados else None
        
        # Reordenar colunas
        if df is not None:
            col_order = [col for col in ['CODCLI', 'CNPJ', 'EAN', 'DESCRICAO', 'PREÇO', 'QTDE', 'TOTAL'] if col in df.columns]
            df = df[col_order]
        
        return df
