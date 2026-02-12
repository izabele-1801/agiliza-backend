# 📝 CLARIFICAÇÃO: Requisito de Múltiplos CNPJs

**Data:** 12 de Fevereiro de 2026  
**Status:** 🟡 SUPORTE OBRIGATÓRIO (Quando Houver)  
**Prioridade:** ALTA (Quando necessário)

---

## 🎯 Clarificação do Requisito

### O que foi dito inicialmente:
> "Não necessariamente terá mais de um, mas pode ter."

### O que isso significa:

**A maioria dos documentos terá 1 CNPJ (caso normal - ~90%)**  
**Alguns documentos podem ter múltiplos CNPJs (caso especial - ~10%)**

O processador DEVE estar preparado para **AMBOS os casos**.

---

## ✅ O que é Obrigatório

### SEMPRE (100% dos casos):
1. ✅ Processar documentos com **1 CNPJ** (caso principal)
2. ✅ Extrair todos os dados corretamente
3. ✅ Retornar DataFrame com coluna CNPJ preenchida

### QUANDO HOUVER (casos excepcionais):
1. ✅ Processar documentos com **2, 3 ou mais CNPJs**
2. ✅ Extrair TODOS os CNPJs (não apenas o primeiro)
3. ✅ Retornar múltiplas linhas (uma por CNPJ+EAN)
4. ✅ NÃO consolidar/descartar/simplificar para 1 CNPJ

---

## 📊 Cenários Esperados

### Cenário 1: Arquivo Típico (90% dos casos)
```
Arquivo: pedido_biomaxfarma_2024.xlsx
Conteúdo:
  - Filial: São Paulo (CNPJ: 12345678000190)
  - Produtos: 50 itens
  
Resultado esperado:
  - DataFrame com 50 linhas
  - Todas com CNPJ = 12345678000190
  
Status: ✅ Deve funcionar perfeitamente
```

### Cenário 2: Arquivo com Múltiplas Filiais (10% dos casos)
```
Arquivo: pedido_crescer_jan2024.xlsx
Conteúdo:
  - Filial Belo Horizonte (CNPJ: 12345678000190)
  - Filial Rio de Janeiro (CNPJ: 87654321000111)
  - Filial Salvador (CNPJ: 11111111000122)
  - Produtos: 150 itens (50 + 60 + 40 por filial)
  
Resultado esperado:
  - DataFrame com 150 linhas (todas as 150)
  - 50 linhas com CNPJ #1
  - 60 linhas com CNPJ #2
  - 40 linhas com CNPJ #3
  
Status: ✅ Deve funcionar corretamente
        ❌ NÃO resultar em 50 linhas com CNPJ #1 apenas
```

---

## 🔍 Como Implementar Corretamente

### Para Casos com 1 CNPJ (Modo Atual):
```python
def _extrair_dados(self, df):
    # Extração normal - funciona para 1 CNPJ
    cnpj = extract_cnpj(...)
    dados = []
    for _, row in df.iterrows():
        dados.append({'CNPJ': cnpj, 'EAN': ..., ...})
    return pd.DataFrame(dados)
```

### Para Suportar 1 OU Múltiplos CNPJs (Melhor Prática):
```python
def _extrair_dados(self, df):
    # Detecta TODOS os CNPJs
    cnpjs = self._extrair_todos_cnpjs(df)  # Novo método
    
    if len(cnpjs) == 1:
        # Caso típico: 1 CNPJ
        return self._processar_um_cnpj(df, cnpjs[0])
    else:
        # Caso excepcional: 2+ CNPJs
        dados = []
        for cnpj in cnpjs:
            linhas = self._extrair_linhas_para_cnpj(df, cnpj)
            for linha in linhas:
                linha['CNPJ'] = cnpj
                dados.append(linha)
        return pd.DataFrame(dados) if dados else None

def _extrair_todos_cnpjs(self, df):
    """Extrai lista de TODOS os CNPJs únicos"""
    cnpjs = set()
    for col in df.columns:
        if 'cnpj' in col.lower():
            for val in df[col].fillna(''):
                if cnpj := extract_cnpj(str(val)):
                    cnpjs.add(cnpj)
    return sorted(list(cnpjs))
```

---

## 🧪 Testes Recomendados

### Teste Obrigatório: 1 CNPJ
```bash
# DEVE passar
python -c "
processor = get_processor('biomaxfarma')
df = processor.process(arquivo_1_cnpj.xlsx)
assert df['CNPJ'].nunique() == 1  # ✅ Passa
"
```

### Teste Opcional: Múltiplos CNPJs
```bash
# DEVE passar IF arquivo com múltiplos CNPJs for fornecido
python -c "
processor = get_processor('biomaxfarma')
df = processor.process(arquivo_2_cnpjs.xlsx)  # Se existir
assert df['CNPJ'].nunique() == 2  # ✅ Passaria
"
```

---

## ⏰ Timeline de Implementação

### Imediato (Agora):
- ✅ Documentar que processadores devem suportar múltiplos CNPJs QUANDO HOUVER
- ✅ Criar exemplos de código correto

### Curto Prazo (Quando Cliente Solicitar):
- [ ] Se cliente enviar arquivo com 2+ CNPJs
- [ ] Testar se processador funciona
- [ ] Se falhar: implementar suporte seguindo o padrão acima

### Prioridade de Implementação:
1. 🔴 **Crítica**: Se cliente reportar arquivo com 2+ CNPJs
2. 🟡 **Alta**: Fornecedores conhecidos por ter múltiplas filiais (Crescer, DSG, etc.)
3. 🟢 **Normal**: Outros fornecedores

---

## 📋 Checklist Por Fornecedor

Fornecedores mais propensos a ter múltiplos CNPJs:

| Fornecedor | Probabilidade | Ação |
|-----------|---------------|------|
| BioMax Farma | Média | Testar com 2 CNPJs quando possível |
| Cotefácil | Média | Testar com 2 CNPJs quando possível |
| **Crescer** | **ALTA** | Priorizar teste com múltiplos |
| **DSG Farma** | **ALTA** | Priorizar teste com múltiplos |
| Oceânica | Média | Testar com 2 CNPJs quando possível |
| Kimberly | Baixa | Implementação quando necessário |
| **L'Oréal** | **ALTA** | Priorizar teste com múltiplos |
| Natus | Média | Testar com 2 CNPJs quando possível |
| **Poupaminas** | **ALTA** | Priorizar teste com múltiplos |
| Prudence | Média | Testar com 2 CNPJs quando possível |
| Unilever | Baixa | Implementação quando necessário |
| Siage | Média | Testar com 2 CNPJs quando possível |

---

## 🎓 Resumo Executivo

### O Requisito em 3 Pontos:

1. ✅ **SEMPRE** funcionar com 1 CNPJ (obrigatório, caso normal)
2. ✅ **DEVE suportar** múltiplos CNPJs quando o arquivo tiver (obrigatório funcional)
3. 🟢 **NÃO precisa** forçar múltiplos CNPJs em arquivos com 1 CNPJ

### Implementação:
- **Agora**: Documentado, exemplos criados
- **Quando necessário**: Implementar suporte na ordem de probabilidade

### Testes:
- **Obrigatório**: 1 CNPJ deve funcionar (já funciona)
- **Validação**: Múltiplos CNPJs devem funcionar quando enviado
- **Prioridade**: Testar Crescer, DSG, L'Oréal, Poupaminas com múltiplos

---

## ✅ Conclusão

**O requisito foi clarificado como:**
> "O processador DEVE suportar múltiplos CNPJs QUANDO HOUVER, mas não precisa forçá-los em arquivos com 1 CNPJ"

**Status:**
- 🟢 **Implementação atual**: Funciona com 1 CNPJ
- 🟡 **Suporte futuro**: Será adicionado conforme necessário
- 🟡 **Prioridade**: ALTA para fornecedores com múltiplas filiais

---

**Documento criado em:** 12 de Fevereiro de 2026  
**Versão:** 1.1  
**Status:** ✅ CLARIFICAÇÃO COMPLETA
