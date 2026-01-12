#!/usr/bin/env python3
import sys
sys.path.insert(0, "c:\\projetos\\gerador_planilhas\\backend")

from src.processing.txt_processor import TXTProcessor
import re

# Ler o arquivo
with open("c:\\projetos\\gerador_planilhas\\exemplos_pedidos\\exemplo_com_numero_pedido.txt", "rb") as f:
    file_content = f.read()

# Simular o processamento manual
texto = file_content.decode('utf-8', errors='ignore')
linhas = texto.split('\n')

numero_pedido_pendente = None
cnpj_atual = None

print("DEBUG: Processando linhas...")
for idx, linha in enumerate(linhas):
    linha_strip = linha.strip()
    if not linha_strip:
        continue
    
    print(f"\nLinha {idx}: {repr(linha_strip[:80])}")
    
    # Tenta extrair número do pedido primeiro (pode vir antes do CNPJ)
    # Padrão mais específico para evitar pegar "08" de datas como "08/01/2026"
    if ("NÚMERO PEDIDO" in linha.upper() or "NUMERO PEDIDO" in linha.upper() or 
        (linha.count("Pedido") > 0 and "DT." not in linha and "DATA" not in linha.upper() and "EMISSÃO" not in linha.upper())):
        print(f"  -> Encontrou PEDIDO (sem ser data):")
        match = re.search(r'(?:Número\s+Pedido|NÚMERO\s+PEDIDO|Numero\s+Pedido|NUMERO\s+PEDIDO)[:\s.]+(\d+)', linha, re.IGNORECASE)
        if match:
            numero_pedido_pendente = match.group(1).strip()
            print(f"  -> Extraído número do pedido: '{numero_pedido_pendente}'")
        else:
            print(f"  -> Regex não fez match!")
    else:
        if "PEDIDO" in linha.upper():
            print(f"  -> Encontrou PEDIDO (mas parece ser data/outro contexto)")
    
    # Tenta extrair CNPJ
    if "CNPJ" in linha:
        print(f"  -> Encontrou CNPJ")
        from src.utils.validators import extract_cnpj
        cnpj = extract_cnpj(linha)
        if cnpj:
            cnpj_atual = cnpj
            print(f"  -> Extraído CNPJ: '{cnpj}'")

print(f"\n\nRESULTADO FINAL:")
print(f"numero_pedido_pendente: {repr(numero_pedido_pendente)}")
print(f"cnpj_atual: {repr(cnpj_atual)}")
