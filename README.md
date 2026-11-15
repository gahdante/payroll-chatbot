# Chatbot de Folha de Pagamento

Chatbot inteligente para consultas sobre folha de pagamento com RAG, busca na web e interface moderna.

## 🚀 Funcionalidades

- **Chat com LLM**: OpenAI (padrão `gpt-4o-mini`) para conversas gerais
- **RAG de Folha**: consultas determinísticas no CSV (valores e datas nunca são reescritos pelo LLM)
- **Web Search**: a taxa Selic vem ao vivo da API pública do Banco Central (sem chave). Os demais temas usam o Google Custom Search quando configurado; caso contrário, uma base de referência local (a resposta avisa que o dado pode estar desatualizado)
  - ⚠️ A Google Custom Search JSON API não aceita novos clientes e será desligada pelo Google em 01/01/2027
- **Interface React**: frontend responsivo com envio de `session_id`
- **Memória de Conversa**: contexto entre turnos por sessão (`session_id` devolvido em cada resposta). Perguntas de seguimento como "E em junho?", "E o Bruno?" ou "E o INSS?" reaproveitam o funcionário, a competência e a métrica da consulta anterior
- **Evidências**: cada resposta de RAG/web devolve `evidence.sources` com as fontes

## 🛠️ Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/gahdante/payroll-chatbot.git
cd payroll-chatbot
```

### 2. Configure o ambiente Python
Requer Python 3.11 ou superior.

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
cp .env.example .env
# edite .env e preencha OPENAI_API_KEY
```

**Obrigatória:** `OPENAI_API_KEY`
**Opcionais:** `OPENAI_MODEL`, `GOOGLE_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` (busca web ao vivo),
`HOST`, `PORT`, `LOG_LEVEL`, `ALLOWED_ORIGINS`.

### 4. Configure o frontend React
```bash
cd frontend
npm install
cp .env.example .env   # opcional: ajuste REACT_APP_API_URL
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
# Todos os testes (configuração em pytest.ini)
pytest

# Só os casos do desafio
pytest tests/test_challenge_cases.py -v

# Com cobertura
pytest --cov=app
```

### Qualidade de código

As regras do Ruff e do basedpyright ficam no `pyproject.toml`, e as extensões
do editor usam a mesma configuração.

```bash
ruff check .       # lint
ruff format .      # formatação
basedpyright       # tipos (pip install basedpyright)
```

## 📊 Casos de Teste

### Consultas RAG (Dados Específicos)
- "Quanto recebi (líquido) em maio/2025? (Ana Souza)"
- "Qual o total líquido de Ana Souza no 1º trimestre de 2025?"
- "Qual foi o desconto de INSS do Bruno em jun/2025?"
- "Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?"
- "Qual foi o maior bônus do Bruno e em que mês?"

Também funcionam, entre outras:
- "Qual foi o desconto do Bruno em abril/2025?" (INSS, IRRF, outros descontos e total)
- "Holerite do Bruno em abril/2025" (todos os campos do registro)
- "Qual o total de INSS da Ana no último trimestre?"
- "Qual o menor bônus do Bruno?" (empates aparecem todos)
- Seguimento: "Quanto a Ana recebeu em maio/2025?" → "E em junho?" → "E o Bruno?"

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
- `GET /` - status básico
- `GET /health` - status detalhado das dependências (`healthy`/`degraded`)
- `POST /chat/{session_id}` - chat vinculado a uma sessão pela URL
- `GET /sessions/{session_id}/context` - resumo do contexto da sessão
- `GET /sessions/stats` - estatísticas das sessões
- `DELETE /sessions/{session_id}` - remove a sessão (404 se não existir)
- `GET /docs` - documentação Swagger
- `GET /examples` - exemplos de consultas

Para manter contexto entre mensagens, reenvie o `session_id` retornado na
resposta anterior (o `POST /chat` aceita `session_id` no corpo).

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