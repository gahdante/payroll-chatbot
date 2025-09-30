# Chatbot de Folha de Pagamento

Chatbot inteligente para consultas sobre folha de pagamento com RAG, busca na web e interface moderna.

## 🚀 Funcionalidades

- **Chat com LLM**: OpenAI GPT-4o-mini para conversas gerais
- **RAG de Folha**: Consultas específicas no dataset CSV
- **Web Search**: Busca informações de legislação trabalhista
- **Interface React**: Frontend moderno e responsivo
- **Memória de Conversa**: Contexto entre turnos
- **Evidências**: Citação de fontes em todas as respostas

## 🛠️ Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/gahdante/payroll-chatbot.git
cd payroll-chatbot
```

### 2. Configure o ambiente Python
```bash
# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env com suas chaves
nano .env
```

**Variáveis obrigatórias:**
```env
OPENAI_API_KEY=your_openai_api_key_here
```

**Variáveis opcionais:**
```env
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here
```

### 4. Configure o frontend React
```bash
cd frontend
npm install
cd ..
```

## 🚀 Como Executar

### Backend (Terminal 1)
```bash
# Ative o ambiente virtual
source venv/bin/activate

# Execute o backend
python run.py
```

### Frontend (Terminal 2)
```bash
cd frontend
npm start
```

### Acesse
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Documentação**: http://localhost:8000/docs

## 🧪 Testes

```bash
# Execute todos os testes
pytest tests/ -v

# Testes específicos do desafio
pytest tests/test_challenge_cases.py -v

# Com cobertura
pytest --cov=app tests/
```

## 📊 Casos de Teste

### Consultas RAG (Dados Específicos)
- "Quanto recebi (líquido) em maio/2025? (Ana Souza)"
- "Qual o total líquido de Ana Souza no 1º trimestre de 2025?"
- "Qual foi o desconto de INSS do Bruno em jun/2025?"
- "Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?"
- "Qual foi o maior bônus do Bruno e em que mês?"

### Consultas Web (Legislação)
- "Traga a taxa Selic atual e cite a fonte"
- "Como calcular férias proporcionais?"
- "Qual é o valor do FGTS?"

## 🔧 API

### Endpoint Principal
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Quanto recebi em maio/2025? (Ana Souza)"}'
```

### Outros Endpoints
- `GET /` - Health check
- `GET /health` - Status detalhado
- `GET /docs` - Documentação Swagger
- `GET /examples` - Exemplos de consultas

## 📁 Estrutura do Projeto

```
payroll-chatbot/
├── app/                    # Backend FastAPI
│   ├── core/              # Lógica central
│   ├── tools/             # RAG e Web Search
│   └── utils/             # Utilitários
├── frontend/              # Interface React
├── data/                  # Dataset CSV
├── tests/                 # Testes automatizados
├── requirements.txt       # Dependências Python
└── run.py                # Entry point
```

## 🎯 Tecnologias

- **Backend**: FastAPI, OpenAI, Pandas
- **Frontend**: React, Tailwind CSS
- **Testes**: Pytest
- **Formatação**: Valores em R$ e datas dd/mm/aaaa

## 📄 Licença

MIT License - veja o arquivo LICENSE para detalhes.