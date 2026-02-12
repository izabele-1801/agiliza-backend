"""Parser genérico para PDFs em formato textual."""

import re
import pandas as pd
from typing import List, Dict, Optional
from src.utils.validators import extract_cnpj, extract_ean13, normalizar_preco, extract_multiplicador_fardos


class PDFTextParser:
    """Parse PDFs com estrutura textual (não tabelar)."""
    
    @staticmethod
    def extract_data_from_text(texto: str, cnpj_hint: str = "") -> Optional[pd.DataFrame]:
        """
        Extrai dados de um texto estruturado de PDF.
        
        Procura por padrão: coluna de códigos/EAN no início, descrição, quantidade, preço.
        """
        if not texto or not texto.strip():
            return None
        
        linhas = texto.split('\n')
        
        # Tentar encontrar header em todo o documento
        header_idx = None
        for i, linha in enumerate(linhas):
            linha_lower = linha.lower()
            # Procurar por linha com múltiplos termos característicos
            termo_count = sum(1 for p in ['mercadoria', 'descrição', 'código', 'barras', 'quantidade', 'qtd', 'produto', 'ref', 'emb'] if p in linha_lower)
            if termo_count >= 2:
                header_idx = i
                break
        
        if header_idx is None:
            return None
        
        # Extrair CNPJ do texto se não foi fornecido
        if not cnpj_hint:
            cnpj_matches = re.findall(r'\d{2}\.\d{3}\.\d{3}/0\d{3}-\d{2}', texto[:500])
            if cnpj_matches:
                cnpj_hint = cnpj_matches[0]
        
        # Processar linhas após header
        dados = []
        i = header_idx + 1
        
        while i < len(linhas):
            linha = linhas[i].strip()
            i += 1
            
            if not linha:
                continue
            
            # Parar se encontrar footer
            if any(p in linha.lower() for p in ['total', 'página de', 'fim', 'resumo', 'assinatura']):
                break
            
            # Procurar por EAN (13 dígitos começando com 3-8)
            if re.search(r'\b[3678]\d{12}\b', linha):
                produto = PDFTextParser._parse_linha_produto(linha, cnpj_hint)
                if produto:
                    dados.append(produto)
        
        return pd.DataFrame(dados) if dados else None

    @staticmethod
    def _parse_linha_produto(linha: str, cnpj: str) -> Optional[Dict]:
        """Parse uma linha de produto."""
        if not linha or len(linha) < 5:
            return None
        
        try:
            # Procurar por EAN (13 dígitos que começam com 3, 6, 7 ou 8)
            # Padrão brasileiro: 78XXXXXXXXXXX, 38XXXXXXXXXXX, 69XXXXXXXXXXX, 79XXXXXXXXXXX, etc
            ean_match = re.search(r'\b([3678]\d{12})\b', linha)
            if not ean_match:
                return None
            
            ean = ean_match.group(1)
            
            # Após o EAN, extrair quantidade e preço
            ean_pos = linha.find(ean)
            after_ean = linha[ean_pos + 13:].strip()
            
            # Padrão esperado após EAN: descrição + qtd + preço
            # Exemplo: "AGUA MICELAR LOREAL 400ML 2 UN 1 38,67"
            # Os números com virgula são preços
            
            # Primeiro, procurar preços (números com vírgula/ponto)
            preco_pattern = r'(\d+[.,]\d{2})'
            precos = re.findall(preco_pattern, after_ean)
            
            preco = None
            if precos:
                # Tomar o primeiro preço encontrado após o EAN
                preco_str = precos[0].replace(',', '.')
                try:
                    preco = float(preco_str)
                except:
                    pass
            
            # Procurar por quantidade (número inteiro pequeno, 1-999)
            qtde = 1
            qtde_pattern = r'\s(\d{1,3})\s'
            qtde_matches = re.findall(qtde_pattern, ' ' + after_ean + ' ')
            
            for match_qtde in qtde_matches:
                try:
                    val = int(match_qtde)
                    if 1 <= val <= 999:
                        qtde = val
                        break  # Pegar o primeiro encontrado
                except:
                    pass
            
            # Descrição é tudo entre EAN e a quantidade
            # Estratégia: limpar tudo que vem depois (números, preços)
            desc = re.sub(r'\s+\d+[.,]\d{2}', '', after_ean)  # Remove preços
            desc = re.sub(r'\s+\d+\s+', ' ', desc)  # Remove quantidade
            desc = desc.strip()
            
            # Limitar a 100 caracteres (proteção contra quebras de linha)
            if len(desc) > 100:
                desc = desc[:100]
            
            desc = desc.strip()
            
            if not desc or len(desc) < 3:
                return None
            
            # Aplicar multiplicador de fardo
            desc_limpa, mult = extract_multiplicador_fardos(desc)
            qtde = qtde * mult
            
            if not desc_limpa or qtde <= 0:
                return None
            
            return {
                'CNPJ': cnpj,
                'EAN': ean,
                'DESCRICAO': desc_limpa.strip(),
                'QTDE': qtde,
                'PREÇO': preco if preco and preco > 0 else None
            }
        except Exception:
            return None
