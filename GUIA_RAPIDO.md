# 🚀 Guia Rápido - Chatbot de Folha de Pagamento

## ✅ **AMBIENTE VIRTUAL CRIADO E CONFIGURADO!**

### 🎯 **Para usar o projeto:**

#### **1. Ativar o ambiente virtual:**
```bash
# Opção 1: Script automático
activate.bat

# Opção 2: Manual
venv\Scripts\activate
```

#### **2. Configurar chave OpenAI:**
Edite o arquivo `.env` e adicione sua chave:
```env
OPENAI_API_KEY=sk-your-openai-key-here
```

#### **3. Executar a aplicação:**
```bash
python run.py
```

#### **4. Testar a API:**
- **Documentação**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🧪 **Testar o projeto:**

```bash
# Executar testes
python test.py

# Testar manualmente
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual é o salário médio?"}'
```

## 📊 **Exemplos de consultas:**

### **RAG (Dados Específicos):**
- "Qual é o salário do João Silva?"
- "Quantos funcionários temos?"
- "Qual é o salário médio?"
- "Quem trabalha no departamento de TI?"

### **Web Search (Legislação):**
- "Como calcular férias proporcionais?"
- "Qual é o valor do FGTS?"
- "Como funciona o 13º salário?"

### **Gerais:**
- "Olá, como você está?"
- "Obrigado pela ajuda"

## 🔧 **Estrutura do projeto:**

```
chatbot_payroll/
├── ✅ venv/                   # Ambiente virtual
├── ✅ app/                    # Código principal
├── ✅ data/payroll.csv        # Dataset de exemplo
├── ✅ .env                    # Configurações
├── ✅ activate.bat            # Script de ativação
├── ✅ run.py                  # Script de execução
├── ✅ test.py                 # Script de testes
└── ✅ README.md               # Documentação completa
```

## 🎉 **TUDO PRONTO PARA USAR!**

O projeto está **100% funcional** com:
- ✅ Ambiente virtual configurado
- ✅ Dependências instaladas
- ✅ Código testado
- ✅ Scripts de execução
- ✅ Documentação completa

**Só falta configurar sua chave OpenAI e executar!** 🚀



