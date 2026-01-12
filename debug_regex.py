#!/usr/bin/env python3
import re

with open('c:\\projetos\\gerador_planilhas\\exemplos_pedidos\\exemplo_com_numero_pedido.txt', 'r', encoding='utf-8') as f:
    linhas = f.readlines()

for idx, linha in enumerate(linhas[:15]):
    if 'Número' in linha or 'NÚMERO' in linha:
        print(f"Linha {idx}: {repr(linha[:80])}")
        match = re.search(r'(?:PEDIDO|Pedido|Numero Pedido|NUMERO PEDIDO)[:\s.]+(\d+)', linha, re.IGNORECASE)
        print(f"Match com [PEDIDO]: {match}")
        
        match2 = re.search(r'(?:Número Pedido|NÚMERO PEDIDO|Numero Pedido|NUMERO PEDIDO)[:\s.]+(\d+)', linha, re.IGNORECASE)
        print(f"Match com [Número Pedido]: {match2}")
        
        if match2:
            print(f"Valor: {match2.group(1)}")
        
        # Teste simples
        match3 = re.search(r'Número Pedido[:\s.]+(\d+)', linha, re.IGNORECASE)
        print(f"Match simples: {match3}")
        if match3:
            print(f"Valor simples: {match3.group(1)}")
