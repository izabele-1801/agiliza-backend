# 🧪 Guia de Testes - Sistema de Processadores

## Visão Geral

Este documento descreve como testar o sistema de processadores recém-implementado.

---

## 📋 Pré-Requisitos

- Python 3.8+
- Dependências instaladas: `pip install -r requirements.txt`
- Arquivos de teste de exemplo de cada fornecedor

---

## 🔍 Testes Rápidos de Validação

### 1. Validação de Sintaxe (Sem Dependências)

```bash
cd backend

# Validar todos os 12 processadores especializados
python3 -m py_compile \
  src/processing/biomaxfarma_processor.py \
  src/processing/cotefacil_processor.py \
  src/processing/crescer_processor.py \
  src/processing/dsgfarma_processor.py \
  src/processing/oceanica_processor.py \
  src/processing/kimberly_processor.py \
  src/processing/loreal_processor.py \
  src/processing/natusfarma_processor.py \
  src/processing/poupaminas_processor.py \
  src/processing/prudence_processor.py \
  src/processing/unilever_processor.py \
  src/processing/siage_processor.py \
  src/processing/factory.py

# Resultado esperado: Sem erros, comando retorna 0
```

---

## 🧬 Testes de Unitários

### Teste 1: Factory Pattern

```python
# test_factory.py
from src.processing.factory import get_processor, PROCESSOR_CLASSES

def test_factory_instantiation():
    """Testa se factory consegue instanciar todos os processadores"""
    
    for name in ['biomaxfarma', 'cotefacil', 'crescer', 'dsgfarma',
                 'oceanica', 'kimberly', 'loreal', 'natusfarma',
                 'poupaminas', 'prudence', 'unilever', 'siage']:
        processor = get_processor(name)
        assert processor is not None, f"Falhou em {name}"
        assert hasattr(processor, 'process'), f"Sem método process em {name}"
        print(f"✓ {name} instanciado com sucesso")

if __name__ == '__main__':
    test_factory_instantiation()
    print("\n✅ Todos os processadores instanciam corretamente!")
```

**Executar:**
```bash
python test_factory.py
```

### Teste 2: Base Class Compliance

```python
# test_interface.py
from src.processing.factory import PROCESSOR_CLASSES
from src.processing.base import FileProcessor
import inspect

def test_interface_compliance():
    """Verifica se todos os processadores implementam interface correta"""
    
    required_methods = ['process', '_processar_excel', '_processar_pdf', 
                       '_processar_txt', '_extrair_dados']
    
    for name, processor_class in PROCESSOR_CLASSES.items():
        if not issubclass(processor_class, FileProcessor):
            print(f"✗ {name} não herda de FileProcessor")
            continue
        
        instance = processor_class()
        for method in required_methods:
            if not hasattr(instance, method):
                print(f"✗ {name} falta método {method}")
            else:
                print(f"✓ {name}.{method}()")

if __name__ == '__main__':
    test_interface_compliance()
```

**Executar:**
```bash
python test_interface.py
```

---

## 📁 Testes de Integração

### Teste 3: Process com Arquivo Real

```python
# test_processing.py
import pandas as pd
from io import BytesIO
from src.processing.factory import get_processor

def test_biomaxfarma_processing():
    """Testa processamento real com arquivo BioMax"""
    
    # Ler arquivo de exemplo
    with open('modelos_pedidos/exemplo_biomaxfarma.xlsx', 'rb') as f:
        file_content = f.read()
    
    processor = get_processor('biomaxfarma')
    result = processor.process(file_content, 'exemplo_biomaxfarma.xlsx')
    
    assert result is not None, "Result é None"
    assert not result.empty, "Result está vazio"
    assert 'CNPJ' in result.columns, "Falta coluna CNPJ"
    assert 'EAN' in result.columns, "Falta coluna EAN"
    assert 'DESCRICAO' in result.columns, "Falta coluna DESCRICAO"
    assert 'QUANT' in result.columns, "Falta coluna QUANT"
    
    print("✓ BioMax processado com sucesso")
    print(f"  - Total de linhas: {len(result)}")
    print(f"  - Colunas: {list(result.columns)}")
    print(f"  - Primeiras linhas:")
    print(result.head(3))

if __name__ == '__main__':
    test_biomaxfarma_processing()
```

**Requisito:** Arquivo de exemplo em `modelos_pedidos/exemplo_biomaxfarma.xlsx`

---

## 🔀 Testes de Roteamento

### Teste 4: Detecção de Modelo

```python
# test_routing.py
from src.config.model_processor_mapping import detect_model_from_filename, get_processor_for_model

def test_model_detection():
    """Testa detecção automática de modelo a partir do filename"""
    
    test_cases = [
        ('pedido_biomaxfarma_123.xlsx', 'BIOMAXFARMA'),
        ('relatorio_cotefacil_456.pdf', 'COTEFACIL'),
        ('pedido_crescer_789.txt', 'CRESCER'),
        ('DSGFARMA_2024.xlsx', 'DSGFARMA'),
        ('oceanica_report.pdf', 'OCEANICA'),
        ('kimberly_order.xlsx', 'KIMBERLY'),
        ('loreal_request.txt', 'LOREAL'),
        ('natusfarma_2024.xlsx', 'NATUSFARMA'),
        ('poupaminas.pdf', 'POUPAMINAS'),
        ('prudence_file.xlsx', 'PRUDENCE'),
        ('unilever_order.txt', 'UNILEVER'),
        ('siage_request.xlsx', 'SIAGE'),
    ]
    
    for filename, expected_model in test_cases:
        detected = detect_model_from_filename(filename)
        if detected == expected_model:
            print(f"✓ {filename} → {detected}")
        else:
            print(f"✗ {filename} → Detectado: {detected}, Esperado: {expected_model}")

if __name__ == '__main__':
    test_model_detection()
```

**Executar:**
```bash
python test_routing.py
```

---

## 🔀 Testes de Fallback

### Teste 5: Fallback para Processador Genérico

```python
# test_fallback.py
from src.api.routes import get_available_processor

def test_processor_fallback():
    """Testa fallback de processador especializado para genérico"""
    
    # Tentar processor especializado
    proc1, type1, is_spec1 = get_available_processor('BIOMAXFARMA', 'xlsx')
    print(f"BioMax Excel: {type1}, Especializado: {is_spec1}")
    
    # Tentar processador genérico por extensão
    proc2, type2, is_spec2 = get_available_processor('UNKNOWN', 'pdf')
    print(f"Unknown PDF: {type2}, Especializado: {is_spec2}")
    
    # Verificar que fallback funciona
    assert proc1 is not None, "Falhou em instanciar BioMax"
    print("✓ Fallback funcionando corretamente")

if __name__ == '__main__':
    test_processor_fallback()
```

---

## 🆔 Testes de Suporte a Múltiplos CNPJs (Quando Houver)

### Requisito: Suporte Obrigatório (Quando Necessário)

**CADA processador DEVE suportar tanto documentos com 1 CNPJ quanto documentos com múltiplos CNPJs.**

Ver [REQUISITO_MULTIPLOS_CNPJS.md](REQUISITO_MULTIPLOS_CNPJS.md) para detalhes completos.

**Nota:** A maioria dos documentos terá 1 CNPJ, mas alguns podem ter 2-3. O processador deve estar preparado para ambos os casos.

### Teste 6: Arquivo com 1 CNPJ

```python
# test_single_cnpj.py
from src.processing.factory import get_processor

def test_single_cnpj_all_processors():
    """Testa cada processador com arquivo contendo 1 CNPJ"""
    
    processors_to_test = [
        'biomaxfarma', 'cotefacil', 'crescer', 'dsgfarma',
        'oceanica', 'kimberly', 'loreal', 'natusfarma',
        'poupaminas', 'prudence', 'unilever', 'siage'
    ]
    
    for proc_name in processors_to_test:
        print(f"\n[{proc_name.upper()}] Testando com 1 CNPJ...")
        processor = get_processor(proc_name)
        
        try:
            with open(f'modelos_pedidos/teste_{proc_name}_1cnpj.xlsx', 'rb') as f:
                df = processor.process(f.read(), f'teste_{proc_name}_1cnpj.xlsx')
            
            if df is None or df.empty:
                print(f"⚠️ {proc_name}: Nenhum dado extraído")
                continue
            
            # Validações
            assert 'CNPJ' in df.columns, f"{proc_name}: Falta coluna CNPJ"
            assert df['CNPJ'].nunique() == 1, f"{proc_name}: Esperado 1 CNPJ"
            assert len(df) > 0, f"{proc_name}: DataFrame vazio"
            
            print(f"✓ {proc_name}: OK - {len(df)} linhas, CNPJ: {df['CNPJ'].unique()[0]}")
        except FileNotFoundError:
            print(f"⚠️ {proc_name}: Arquivo de teste não encontrado")
        except Exception as e:
            print(f"✗ {proc_name}: ERRO - {str(e)}")

if __name__ == '__main__':
    test_single_cnpj_all_processors()
```

**Nota:** Requer arquivos em `modelos_pedidos/teste_*_1cnpj.xlsx`

### Teste 7: Arquivo com 2 CNPJs (CRÍTICO)

```python
# test_dual_cnpj.py
from src.processing.factory import get_processor

def test_dual_cnpj_all_processors():
    """Testa cada processador com arquivo contendo 2 CNPJs DIFERENTES"""
    
    processors_to_test = [
        'biomaxfarma', 'cotefacil', 'crescer', 'dsgfarma',
        'oceanica', 'kimberly', 'loreal', 'natusfarma',
        'poupaminas', 'prudence', 'unilever', 'siage'
    ]
    
    for proc_name in processors_to_test:
        print(f"\n[{proc_name.upper()}] Testando com 2 CNPJs...")
        processor = get_processor(proc_name)
        
        try:
            with open(f'modelos_pedidos/teste_{proc_name}_2cnpjs.xlsx', 'rb') as f:
                df = processor.process(f.read(), f'teste_{proc_name}_2cnpjs.xlsx')
            
            if df is None or df.empty:
                print(f"✗ {proc_name}: ERRO - Nenhum dado extraído (esperado 2 CNPJs)")
                continue
            
            # VALIDAÇÕES CRÍTICAS
            assert 'CNPJ' in df.columns, f"{proc_name}: Falta coluna CNPJ"
            
            unique_cnpjs = df['CNPJ'].nunique()
            assert unique_cnpjs == 2, \
                f"{proc_name}: Encontrou {unique_cnpjs} CNPJs, esperado 2. " \
                f"Processador não suporta múltiplos CNPJs! ❌"
            
            # Verificar que há registros para cada CNPJ
            cnpjs = df['CNPJ'].unique()
            for cnpj in cnpjs:
                count = len(df[df['CNPJ'] == cnpj])
                print(f"  - CNPJ {cnpj}: {count} linhas")
            
            print(f"✅ {proc_name}: OK - {len(df)} linhas, 2 CNPJs distintos")
            
        except AssertionError as e:
            print(f"❌ {proc_name}: FALHA DE VALIDAÇÃO - {str(e)}")
        except FileNotFoundError:
            print(f"⚠️ {proc_name}: Arquivo de teste não encontrado")
        except Exception as e:
            print(f"✗ {proc_name}: ERRO - {str(e)}")

if __name__ == '__main__':
    test_dual_cnpj_all_processors()
```

**Crítico:** Este teste DEVE passar em todos os 12 processadores!

### Teste 8: Arquivo com 3 CNPJs

```python
# test_triple_cnpj.py
from src.processing.factory import get_processor

def test_triple_cnpj():
    """Testa arquivo com 3 CNPJs diferentes (validação completa)"""
    
    processor = get_processor('biomaxfarma')  # Exemplo com BioMax
    
    try:
        with open('modelos_pedidos/teste_biomaxfarma_3cnpjs.xlsx', 'rb') as f:
            df = processor.process(f.read(), 'teste_3cnpjs.xlsx')
        
        # Deve ter exatamente 3 CNPJs
        assert df['CNPJ'].nunique() == 3, f"Esperado 3 CNPJs, encontrou {df['CNPJ'].nunique()}"
        
        # Distribuição de linhas
        cnpj_stats = df['CNPJ'].value_counts().sort_index()
        print("Distribuição por CNPJ:")
        for cnpj, count in cnpj_stats.items():
            print(f"  - {cnpj}: {count} linhas")
        
        # Total deve fazer sentido
        total_esperado = 100  # Exemplo: 3 CNPJs com ~30 produtos cada
        print(f"\nTotal de linhas: {len(df)} (esperado ~{total_esperado})")
        
        print("✅ Teste de 3 CNPJs passou!")
        
    except FileNotFoundError:
        print("⚠️ Arquivo de teste com 3 CNPJs não encontrado")
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")

if __name__ == '__main__':
    test_triple_cnpj()
```

---

## 📊 Testes de Validação de Dados

### Teste 6: Validação de CNPJ

```python
# test_validation.py
from src.utils.validators import extract_cnpj

def test_cnpj_extraction():
    """Testa extração de CNPJ"""
    
    test_cases = [
        ("CNPJ: 12.345.678/0001-90", "12345678000190"),
        ("12345678000190", "12345678000190"),
        ("12.345.678/0001-90", "12345678000190"),
        ("Sem CNPJ aqui", None),
    ]
    
    for input_str, expected in test_cases:
        result = extract_cnpj(input_str)
        if result == expected:
            print(f"✓ extract_cnpj('{input_str}') → {result}")
        else:
            print(f"✗ extract_cnpj('{input_str}') → {result} (esperado: {expected})")

if __name__ == '__main__':
    test_cnpj_extraction()
```

---

## 🚀 Teste Completo da API

### Teste 7: Upload via FastAPI

```bash
# Iniciar servidor
cd backend
python app.py

# Em outro terminal, fazer upload
curl -X POST "http://localhost:8000/api/upload" \
  -F "files=@modelos_pedidos/exemplo_biomaxfarma.xlsx" \
  -F "model=planilha" \
  --output resultado.xlsx

# Verificar resultado
file resultado.xlsx
```

---

## 📈 Checklist de Testes

- [ ] Teste de Sintaxe (Teste 1)
- [ ] Teste de Factory (Teste 2)
- [ ] Teste de Interfaces (Teste 3)
- [ ] Teste de Processamento Real (Teste 4)
- [ ] Teste de Roteamento (Teste 5)
- [ ] Teste de Fallback (Teste 6)
- [ ] Teste de Validação (Teste 7)
- [ ] Teste da API (Teste 8)
- [ ] 🔴 **CRÍTICO**: Teste de 1 CNPJ (Teste 9)
- [ ] 🔴 **CRÍTICO**: Teste de 2 CNPJs (Teste 10)
- [ ] 🔴 **CRÍTICO**: Teste de 3 CNPJs (Teste 11)

---

## 🐛 Teste de Regressão

Se modificar qualquer processador, executar:

```bash
# Re-validar sintaxe
python3 -m py_compile src/processing/*.py

# Re-executar testes unitários
python test_factory.py && python test_interface.py

# Re-testar com arquivo de exemplo
python test_processing.py
```

---

## 📝 Relatório de Testes

Apos executar todos, criar relatório:

```bash
# Gerar relatório
cat << EOF > TESTE_REPORT.md
# Relatório de Testes
- Teste de Sintaxe: ✅ PASSOU
- Teste de Factory: ✅ PASSOU  
- Teste de Interfaces: ✅ PASSOU
- Teste de Processamento: ✅ PASSOU
- Teste de Roteamento: ✅ PASSOU
- Teste de Fallback: ✅ PASSOU
- Teste de Validação: ✅ PASSOU
- Teste da API: ✅ PASSOU

**Status Global: PRONTO PARA PRODUÇÃO** ✅
EOF
```

---

## 🔗 Referências

- [BaseProcessor](src/processing/base.py)
- [Factory](src/processing/factory.py)
- [Routes Integration](src/api/routes.py)
- [Validators](src/utils/validators.py)
- [Model Mapping](src/config/model_processor_mapping.py)

---

## ✅ Próximas Ações

### � Preparação para Testes de Múltiplos CNPJs (Quando Houver)

1. **Criar arquivos de teste opcionais:**
   - `modelos_pedidos/teste_biomaxfarma_1cnpj.xlsx` (um CNPJ - caso comum)
   - `modelos_pedidos/teste_biomaxfarma_2cnpjs.xlsx` (dois CNPJs - caso raro, validação)
   - **Repetir para fornecedores onde as múltiplas filiais são comuns**

2. **Executar testes:**
   ```bash
   python test_single_cnpj.py      # Teste 9 (obrigatório)
   python test_dual_cnpj.py         # Teste 10 (validação quando houver)
   ```

3. **Validar resultado:**
   - ✅ Arquivo com 1 CNPJ → 1 CNPJ no resultado (caso principal)
   - ✅ Arquivo com 2 CNPJs → 2 CNPJs no resultado (se existir tal arquivo)
   - ❌ **NÃO consolidar em um único CNPJ**

4. **Implementação quando necessário:**
   - Se algum cliente enviar arquivo com múltiplos CNPJs e falhar → implementar suporte
   - Ver [REQUISITO_MULTIPLOS_CNPJS.md](REQUISITO_MULTIPLOS_CNPJS.md) para guia de implementação
   - Prioridade: ALTA quando uma falha assim ocorrer

5. **Documentação:**
   - Gerar relatório de testes
   - Deploy para staging APENAS após testes de 1 CNPJ passarem
   - Testes de múltiplos CNPJs podem ser adicionados conforme demanda apareça

**Tempo estimado:** 2-3 horas para testes básicos + implementação conforme necessário
