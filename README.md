# Chatbot de Folha de Pagamento

Um chatbot inteligente para consultas sobre folha de pagamento, desenvolvido com FastAPI, OpenAI e sistema RAG.

## 🚀 Funcionalidades

- **Consultas RAG**: Busca dados específicos no dataset de folha de pagamento
- **Web Search**: Consulta informações de legislação trabalhista na web
- **Formatação Brasileira**: Valores em Real (R$) e datas no formato brasileiro
- **API RESTful**: Endpoint `/chat` para interação com o chatbot
- **Testes Abrangentes**: Cobertura de testes para todas as funcionalidades

## 📁 Estrutura do Projeto

```
/chatbot_payroll
├── .env.example              # Variáveis de ambiente de exemplo
├── requirements.txt           # Dependências Python
├── README.md                 # Documentação do projeto
├── /app
│   ├── main.py               # Entry point do FastAPI
│   ├── /core
│   │   ├── agent.py          # Lógica central do agente
│   │   └── llm.py            # Configuração do LLM
│   ├── /tools
│   │   ├── __init__.py
│   │   ├── payroll_rag.py    # Sistema RAG para CSV
│   │   └── web_search.py     # Busca na web
│   └── /utils
│       ├── formatting.py     # Formatação brasileira
│       └── models.py         # Modelos Pydantic
├── /data
│   └── payroll.csv           # Dataset de folha de pagamento
└── /tests
    ├── conftest.py           # Fixtures para testes
    └── test_queries.py       # Testes abrangentes
```

## 🛠️ Instalação

1. **Clone o repositório**
   ```bash
   git clone https://github.com/gahdante/payroll-chatbot.git
   cd payroll-chatbot
   ```

2. **Crie um ambiente virtual**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # ou
   source venv/bin/activate  # Linux/Mac
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as variáveis de ambiente**
   ```bash
   cp config.example .env
   # Edite o arquivo .env com suas chaves de API
   ```

5. **Execute a aplicação**
   ```bash
   python run.py
   ```

## 🔧 Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` baseado no `config.example`:

```env
# Configurações do LLM
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Configurações de Web Search (opcional)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here

# Configurações da aplicação
DEBUG=True
LOG_LEVEL=INFO
```

### Chaves de API

- **OpenAI API**: Necessária para o funcionamento do LLM
- **Google Search API**: Opcional, para busca na web (usa fallback se não configurada)

## 📊 Dataset

O arquivo `data/payroll.csv` deve conter as seguintes colunas:

- `nome`: Nome do funcionário
- `cargo`: Cargo do funcionário
- `departamento`: Departamento
- `salario`: Salário em reais
- `data`: Data de referência

## 🚀 Uso da API

### Endpoint Principal

**POST** `/chat`

```json
{
  "message": "Qual é o salário médio dos funcionários?"
}
```

**Resposta:**
```json
{
  "response": "O salário médio dos funcionários é R$ 7.375,00",
  "evidence": "Baseado em 15 funcionários",
  "tool_used": "rag"
}
```

### Outros Endpoints

- **GET** `/` - Health check
- **GET** `/health` - Health check detalhado
- **GET** `/docs` - Documentação Swagger

## 🧪 Testes

Execute os testes com:

```bash
# Todos os testes
python test.py

# Testes específicos
pytest tests/test_queries.py

# Com cobertura
pytest --cov=app tests/
```

## 🔍 Tipos de Consultas

### 1. Consultas RAG (Dados Específicos)
- "Qual é o salário do João Silva?"
- "Quantos funcionários temos?"
- "Qual é o salário médio?"
- "Quem trabalha no departamento de TI?"

### 2. Consultas Web (Legislação)
- "Como calcular férias proporcionais?"
- "Qual é o valor do FGTS?"
- "Como funciona o 13º salário?"
- "Quais são os direitos trabalhistas?"

### 3. Consultas Gerais
- "Olá, como você está?"
- "Obrigado pela ajuda"
- "Preciso de mais informações"

## 🎯 Funcionalidades do Sistema

### Sistema RAG
- Consulta por funcionário específico
- Estatísticas agregadas (média, total, etc.)
- Filtros por departamento e cargo
- Formatação brasileira de valores

### Web Search
- Busca em legislação trabalhista
- Filtragem de resultados relevantes
- Fallback para demonstração

### Formatação
- Valores em Real (R$)
- Datas no formato brasileiro (dd/mm/aaaa)
- Números com separadores de milhares
- Limpeza e normalização de texto

## 🔧 Desenvolvimento

### Estrutura de Código

- **FastAPI**: Framework web moderno e rápido
- **Pydantic**: Validação de dados e modelos
- **Pandas**: Manipulação de dados CSV
- **OpenAI**: Integração com LLM
- **Pytest**: Framework de testes

### Padrões de Código

- Type hints em todas as funções
- Docstrings detalhadas
- Tratamento de erros robusto
- Logging estruturado
- Testes abrangentes

## 📈 Melhorias Futuras

- [ ] Integração com banco de dados
- [ ] Cache de consultas frequentes
- [ ] Autenticação e autorização
- [ ] Métricas e monitoramento
- [ ] Interface web
- [ ] Suporte a múltiplos idiomas

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para detalhes.

## 📞 Suporte

Para dúvidas ou suporte, abra uma issue no repositório.