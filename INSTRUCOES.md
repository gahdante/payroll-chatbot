# 📋 Instruções de Uso - Chatbot de Folha de Pagamento

## 🚀 Início Rápido

### 1. Configuração Inicial
```bash
# Navegue para o diretório do projeto
cd chatbot_payroll

# Configure o projeto
python setup.py

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configuração das Chaves de API
Edite o arquivo `.env` (criado pelo setup.py) e configure:

```env
# OBRIGATÓRIO: Chave da OpenAI
OPENAI_API_KEY=sk-your-openai-key-here

# OPCIONAL: Para busca na web
GOOGLE_API_KEY=your-google-api-key
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id
```

### 3. Executar a Aplicação
```bash
# Opção 1: Script de execução
python run.py

# Opção 2: Comando direto
python -m uvicorn app.main:app --reload
```

### 4. Testar a API
- **Documentação**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Endpoint Principal**: POST http://localhost:8000/chat

## 🧪 Executando Testes

```bash
# Todos os testes
python test.py

# Com cobertura de código
python test.py --coverage

# Modo rápido
python test.py --fast

# Comando direto
pytest tests/ -v
```

## 📊 Exemplos de Uso

### 1. Consultas RAG (Dados Específicos)
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual é o salário do João Silva?"}'
```

### 2. Consultas Web (Legislação)
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Como calcular férias proporcionais?"}'
```

### 3. Consultas Gerais
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá, como você está?"}'
```

## 🔧 Estrutura do Projeto

```
chatbot_payroll/
├── app/                    # Código principal
│   ├── main.py            # FastAPI app
│   ├── core/              # Lógica central
│   │   ├── agent.py       # Agente principal
│   │   └── llm.py         # Configuração LLM
│   ├── tools/              # Ferramentas
│   │   ├── payroll_rag.py # Sistema RAG
│   │   └── web_search.py  # Busca na web
│   └── utils/              # Utilitários
│       ├── formatting.py  # Formatação brasileira
│       └── models.py      # Modelos Pydantic
├── data/                   # Dados
│   └── payroll.csv        # Dataset de folha
├── tests/                  # Testes
│   ├── conftest.py        # Fixtures
│   └── test_queries.py    # Testes principais
├── requirements.txt        # Dependências
├── config.example         # Configuração exemplo
├── setup.py              # Script de configuração
├── run.py                 # Script de execução
├── test.py                # Script de testes
└── README.md              # Documentação
```

## 🎯 Tipos de Consultas Suportadas

### RAG (Dados Específicos)
- "Qual é o salário do João Silva?"
- "Quantos funcionários temos?"
- "Qual é o salário médio?"
- "Quem trabalha no departamento de TI?"
- "Qual é o maior salário?"

### Web Search (Legislação)
- "Como calcular férias proporcionais?"
- "Qual é o valor do FGTS?"
- "Como funciona o 13º salário?"
- "Quais são os direitos trabalhistas?"
- "Como calcular encargos sociais?"

### Gerais
- "Olá, como você está?"
- "Obrigado pela ajuda"
- "Preciso de mais informações"

## 🔍 Funcionalidades

### Sistema RAG
- ✅ Consulta por funcionário específico
- ✅ Estatísticas agregadas (média, total, etc.)
- ✅ Filtros por departamento e cargo
- ✅ Formatação brasileira de valores
- ✅ Tratamento de erros robusto

### Web Search
- ✅ Busca em legislação trabalhista
- ✅ Filtragem de resultados relevantes
- ✅ Fallback para demonstração
- ✅ Formatação de respostas

### Formatação
- ✅ Valores em Real (R$)
- ✅ Datas no formato brasileiro
- ✅ Números com separadores
- ✅ Limpeza de texto

## 🛠️ Desenvolvimento

### Adicionando Novos Tipos de Consulta
1. Edite `app/core/agent.py`
2. Adicione palavras-chave em `rag_keywords` ou `web_keywords`
3. Implemente lógica específica se necessário

### Adicionando Novos Campos ao Dataset
1. Edite `data/payroll.csv`
2. Atualize `app/tools/payroll_rag.py`
3. Adicione testes em `tests/test_queries.py`

### Modificando Formatação
1. Edite `app/utils/formatting.py`
2. Adicione novas funções de formatação
3. Teste com `python test.py`

## 🐛 Solução de Problemas

### Erro: "OPENAI_API_KEY não encontrada"
- Verifique se o arquivo `.env` existe
- Confirme se a chave está configurada corretamente
- Execute `python setup.py` novamente

### Erro: "Dataset não disponível"
- Verifique se `data/payroll.csv` existe
- Confirme se o arquivo tem as colunas corretas
- Execute `python setup.py` para recriar

### Erro: "Módulo não encontrado"
- Execute `pip install -r requirements.txt`
- Verifique se está no diretório correto
- Execute `python setup.py`

### Erro: "Porta 8000 já está em uso"
- Pare outros processos na porta 8000
- Use uma porta diferente: `uvicorn app.main:app --port 8001`

## 📈 Próximos Passos

1. **Configure suas chaves de API**
2. **Teste a aplicação localmente**
3. **Execute os testes para verificar funcionamento**
4. **Personalize o dataset conforme necessário**
5. **Implemente melhorias específicas**

## 🤝 Suporte

- 📚 Documentação: README.md
- 🧪 Testes: `python test.py`
- 🔧 Configuração: `python setup.py`
- 🚀 Execução: `python run.py`
