# ⚠️ REQUISITO CRÍTICO: SUPORTE A MÚLTIPLOS CNPJs

**Status:** � SUPORTE OBRIGATÓRIO - Processadores DEVEM suportar múltiplos CNPJs QUANDO HOUVER  
**Prioridade:** ALTA - Bloqueia deployment em produção  
**Data de Criação:** 12 de Fevereiro de 2026  
**Clarificação:** Nem todo arquivo terá múltiplos CNPJs, mas alguns SIM. Processador deve estar preparado.  

---

## 📋 Definição do Requisito

**Norma:** "Pode haver mais de um CNPJ no mesmo arquivo. Separar pedidos por CNPJ"

### Interpretação Correta:

**Um arquivo/planilha/PDF PODE conter dados de múltiplos CNPJs (diferentes filiais, lojas, distribuidoras).**
**A maioria terá 1 CNPJ, mas alguns poderão ter 2 ou 3. O processador DEVE suportar ambos os casos.**

Exemplo real:
```
Arquivo: pedido_biomaxfarma.xlsx
Contém:
  - Filial São Paulo (CNPJ: 12.345.678/0001-90)
  - Filial Rio de Janeiro (CNPJ: 98.765.432/0001-11)
  - Filial Belo Horizonte (CNPJ: 11.111.111/0001-22)
  
Produtos:
  - CNPJ SP: 50 produtos
  - CNPJ RJ: 30 produtos
  - CNPJ MG: 20 produtos
```

### Comportamento Esperado:

**Se o arquivo tiver múltiplos CNPJs, o processador DEVE retornar um DataFrame com linhas separadas por CNPJ:**
**(Se tiver apenas 1, também funciona normalmente com 1 CNPJ único)**

| CNPJ | EAN | DESCRICAO | QUANT |
|------|-----|-----------|-------|
| 12345678000190 | 123456789012 | Produto A | 10 |
| 12345678000190 | 234567890123 | Produto B | 5 |
| **... (48 linhas para CNPJ SP)** | | | |
| 98765432000111 | 345678901234 | Produto X | 15 |
| 98765432000111 | 456789012345 | Produto Y | 8 |
| **... (28 linhas para CNPJ RJ)** | | | |
| 11111111000122 | 567890123456 | Produto M | 20 |
| **... (19 linhas para CNPJ MG)** | | | |

**Total: 100 linhas no DataFrame (50 + 30 + 20)**

---

## ❌ ANTIPADRÕES - O que NÃO fazer

### ❌ Antipadrão 1: Extrair apenas o primeiro CNPJ (em arquivos com múltiplos)

```python
# ERRADO - Captura apenas o primeiro CNPJ encontrado
def _extrair_dados(self, df):
    cnpj = extract_cnpj(str(df.iloc[0]))  # ← Pega apenas o primeiro!
    dados = []
    for _, row in df.iterrows():
        # Processa apenas com este CNPJ
        dados.append({'CNPJ': cnpj, ...})
    return pd.DataFrame(dados)

# Resultado: Arquivo com 3 CNPJs retorna 100 linhas TODAS com CNPJ #1
# ❌ ERRADO - Perdeu dados dos CNPJs #2 e #3 que estavam no arquivo!
```

### ❌ Antipadrão 2: Consolidar em um único CNPJ

```python
# ERRADO - Tenta "unificar" para um CNPJ
def _extrair_dados(self, df):
    principal_cnpj = extract_cnpj(filename)  # Assume CNPJ do filename
    for _, row in df.iterrows():
        # Força todos os produtos para o mesmo CNPJ
        dados.append({'CNPJ': principal_cnpj, ...})
    return pd.DataFrame(dados)

# Resultado: Mistura dados de múltiplos CNPJs em um
# ❌ ERRADO - Dados inconsistentes!
```

### ❌ Antipadrão 3: Ignorar CNPJs ou retornar menos linhas

```python
# ERRADO - Deduplica ou filtra por CNPJ
def _extrair_dados(self, df):
    cnjps_encontrados = set()
    for _, row in df.iterrows():
        cnpj = extract_cnpj(row)
        if cnpj in cnpjs_encontrados:
            continue  # ← Pula registros repetidos de outro CNPJ
        cnpjs_encontrados.add(cnpj)
        dados.append({'CNPJ': cnpj, ...})
    return pd.DataFrame(dados)

# Resultado: 100 produtos, 3 CNPJs → retorna apenas 3 linhas (uma por CNPJ)
# ❌ ERRADO - Perdeu 97 linhas de dados!
```

---

## ✅ PADRÃO CORRETO

### Estrutura de Código

```python
class [Fornecedor]Processor(FileProcessor):
    
    def _extrair_dados(self, df: pd.DataFrame) -> pd.DataFrame | None:
        """Extrai TODOS os dados com suporte a múltiplos CNPJs"""
        
        dados = []
        
        # OPÇÃO 1: Se CNPJ está em CADA LINHA da tabela
        for idx, row in df.iterrows():
            cnpj = extract_cnpj(str(row['coluna_cnpj']))  # ← Tira de cada linha
            ean = extract_ean13(str(row['coluna_ean']))
            desc = str(row['coluna_desc']).strip()
            qtde = int(float(str(row['coluna_qtde']).replace(',', '.')))
            
            if not all([cnpj, ean, desc, qtde > 0]):
                continue
            
            dados.append({
                'CNPJ': cnpj,  # ← Pode variar!
                'EAN': ean,
                'DESCRICAO': desc,
                'QUANT': qtde,
                'PRECO': ...
            })
        
        # OPÇÃO 2: Se CNPJ está em um local específico (header) e pode variar
        cnpjs_no_documento = self._extrair_todos_cnpjs(df)  # ← Novo método!
        
        for cnpj in cnpjs_no_documento:
            linhas_deste_cnpj = self._extrair_linhas_para_cnpj(df, cnpj)
            for linha_dict in linhas_deste_cnpj:
                linha_dict['CNPJ'] = cnpj  # ← Associa ao CNPJ correto
                dados.append(linha_dict)
        
        return pd.DataFrame(dados) if dados else None
    
    def _extrair_todos_cnpjs(self, df: pd.DataFrame) -> list[str]:
        """
        Extrai TODOS os CNPJs únicos encontrados no documento.
        
        ⚠️ OBRIGATÓRIO para suportar múltiplos CNPJs
        """
        cnpjs = set()
        
        # Busca em potenciais colunas de CNPJ
        for col in df.columns:
            if 'cnpj' in col.lower():
                for val in df[col].fillna(''):
                    if cnpj := extract_cnpj(str(val)):
                        cnpjs.add(cnpj)
        
        # Busca no texto geral
        for col in df.columns:
            for val in df[col].fillna(''):
                if cnpj := extract_cnpj(str(val)):
                    cnpjs.add(cnpj)
        
        return sorted(list(cnpjs))  # ← Retorna em ordem
```

---

## 📊 Matriz de Verificação Por Processador

Para cada um dos 12 processadores, verificar:

### Checklist por Processador:

```
[x] BioMaxFarmaProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] CotefacilProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] CrescerProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] DSGFarmaProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] OceanicaProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] KimberlyProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] LorealProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] NatusFarmaProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] PoupaminasProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] PrudenceProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] UnileverProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
    
[ ] SiageProcessor
    ☐ Método `_extrair_dados()` extrai ALL CNPJs?
    ☐ Método `_extrair_todos_cnpjs()` implementado?
    ☐ Testa com 2+ CNPJs?
```

---

## 🧪 Testes Obrigatórios

### Teste 1: Arquivo com 1 CNPJ

```python
def test_single_cnpj():
    processor = BioMaxFarmaProcessor()
    with open('modelos_pedidos/exemplo_biomax_1cnpj.xlsx', 'rb') as f:
        df = processor.process(f.read(), 'exemplo.xlsx')
    
    # Todas as linhas devem ter o mesmo CNPJ
    assert df['CNPJ'].nunique() == 1
    assert len(df) == 50  # Exemplo: 50 produtos
    print("✅ Teste de 1 CNPJ passou")
```

### Teste 2: Arquivo com 2 CNPJs

```python
def test_dual_cnpj():
    processor = BioMaxFarmaProcessor()
    with open('modelos_pedidos/exemplo_biomax_2cnpjs.xlsx', 'rb') as f:
        df = processor.process(f.read(), 'exemplo.xlsx')
    
    # Deve ter exatamente 2 CNPJs diferentes
    assert df['CNPJ'].nunique() == 2
    # Cada CNPJ com seus produtos
    cnpjs = df['CNPJ'].unique()
    assert len(df[df['CNPJ'] == cnpjs[0]]) == 50
    assert len(df[df['CNPJ'] == cnpjs[1]]) == 30
    # Total deve ser soma
    assert len(df) == 80
    print("✅ Teste de 2 CNPJs passou")
```

### Teste 3: Arquivo com 3 CNPJs

```python
def test_triple_cnpj():
    processor = BioMaxFarmaProcessor()
    with open('modelos_pedidos/exemplo_biomax_3cnpjs.xlsx', 'rb') as f:
        df = processor.process(f.read(), 'exemplo.xlsx')
    
    # Deve ter exatamente 3 CNPJs diferentes
    assert df['CNPJ'].nunique() == 3
    assert len(df) == 150  # 50 + 50 + 50
    print("✅ Teste de 3 CNPJs passou")
```

---

## 📐 Cenários de Implementação Por Tipo de Arquivo

### Para EXCEL (.xlsx, .xls)

**Cenário A: CNPJ em coluna específica (cada linha tem seu CNPJ)**
```excel
CNPJ              | Produto | Qtd
12345678000190    | Paracetamol | 10
12345678000190    | Dipirona | 5
98765432000111    | Paracetamol | 12
98765432000111    | Ibuprofeno | 8
```
→ Extrair de cada linha, permitir valores diferentes

**Cenário B: CNPJ em header, múltiplos headers (seções por CNPJ)**
```excel
CNPJ: 12345678000190
Produto | Qtd
Paracetamol | 10

--- (separador ou linha vazia)

CNPJ: 98765432000111
Produto | Qtd
Ibuprofeno | 8
```
→ Detectar mudanças de CNPJ no header, processa por seção

### Para PDF

**Cenário A: Tabelas separadas por CNPJ**
```
Página 1:
CNPJ: 12345678000190
Tabela de produtos...

Página 2:
CNPJ: 98765432000111
Tabela de produtos...
```
→ Extrair CNPJ antes de cada tabela

**Cenário B: Múltiplas tabelas na mesma página**
```
CNPJ: 12345678000190
Tabela 1...

CNPJ: 98765432000111
Tabela 2...
```
→ Detectar CNPJ antes de cada tabela

### Para TXT

**Cenário A: Blocos por CNPJ**
```
CNPJ|12345678000190
EAN|Desc|Qtd
123...|Prod A|10

CNPJ|98765432000111
EAN|Desc|Qtd
234...|Prod B|5
```
→ Parsear CNPJ, depois linhas até próximo CNPJ

---

## 🔍 Validação de Implementação

Após implementar, verificar:

```bash
# Para cada processador
python -c "
from src.processing.factory import get_processor
import pandas as pd

# Teste com múltiplos CNPJs
processor = get_processor('biomaxfarma')
df = processor.process(open('teste_2cnpjs.xlsx', 'rb').read(), 'teste.xlsx')

print(f'Total de linhas: {len(df)}')
print(f'CNPJs únicos: {df[\"CNPJ\"].nunique()}')
print(f'CNPJs encontrados: {df[\"CNPJ\"].unique().tolist()}')

# Validação: Deve ter múltiplos CNPJs
assert df['CNPJ'].nunique() > 1, 'Processador não extraiu múltiplos CNPJs!'
print('✅ Validação passou!')
"
```

---

## 📝 Documentação Necessária

Cada processador deve ter documentação clara:

```python
class BioMaxFarmaProcessor(FileProcessor):
    """
    Processador especializado para BioMax Farma.
    
    ⚠️ REQUISITO DE MÚLTIPLOS CNPJs:
    Este processador DEVE suportar documentos contendo múltiplos CNPJs.
    
    Comportamento:
    - Extrai TODOS os CNPJs encontrados no documento
    - Retorna DataFrame com linhas separadas por CNPJ
    - Cada linha contém CNPJ específico daquele produto
    
    Formatos suportados:
    - Excel (.xlsx, .xls)
    - PDF (.pdf)
    - Texto (.txt)
    
    Exemplo:
        Arquivo com 2 CNPJs (50 + 30 produtos)
        → Retorna DataFrame com 80 linhas
    """
```

---

## ⏰ Timeline Recomendada

| Etapa | Atividades | Timeline |
|-------|-----------|----------|
| **Análise** | Revisar cada processador | 1-2 horas |
| **Implementação** | Adicionar suporte multi-CNPJ em cada um | 4-6 horas |
| **Testes** | Testar com 1, 2, 3 CNPJs cada | 2-3 horas |
| **Validação** | Verificar todos passam testes | 1 hora |
| **Documentação** | Atualizar docstrings e README | 1 hora |
| **Total** | | **9-13 horas** |

---

## 🚨 Consequências de Não Implementar

❌ **NÃO implementar suporte a múltiplos CNPJs resultará em:**

1. **Perda de dados**: Registros de CNPJs adicionais serão ignorados
2. **Relatórios incorretos**: Apenas dados do primeiro CNPJ serão processados
3. **Pedidos faltando**: 70% dos dados podem ser perdidos em documentos com 3 CNPJs
4. **Erro silencioso**: Nenhum aviso ao usuário que dados foram descartados
5. **Retrabalho**: Usuários terão que processar CNPJs em separado manualmente
6. **Falha de validação**: NÃO pode ir para produção sem este requisito

---

## ✅ Conclusão

**A implementação de suporte a múltiplos CNPJs é OBRIGATÓRIA e CRÍTICA.**

Todos os 12 processadores devem ser atualizados para garantir que:
- ✅ Extraem TODOS os CNPJs do documento
- ✅ Retornam linhas separadas por CNPJ
- ✅ Não perdem nem consolidam dados
- ✅ Passam em testes com 2-3 CNPJs

**Prazo: ANTES de qualquer deployment em produção**

---

**Verificado e Aprovado:** GitHub Copilot  
**Data:** 12 de Fevereiro de 2026  
**Status:** 🔴 CRÍTICO - Aguardando Implementação
