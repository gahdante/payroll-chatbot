import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Trash2, Lightbulb, Database, Globe, MessageCircle } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    checkApiStatus();
  }, []);

  const checkApiStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 });
      setApiStatus('online');
    } catch (error) {
      setApiStatus('offline');
    }
  };

  const sendMessage = async (message) => {
    if (!message.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: message,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: message
      });

      const botMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.data.response,
        evidence: response.data.evidence,
        tool_used: response.data.tool_used,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: `❌ Erro: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputMessage.trim()) {
      sendMessage(inputMessage);
      setInputMessage('');
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const loadExample = (example) => {
    setInputMessage(example);
  };

  const examples = [
    "Quanto recebi (líquido) em maio/2025? (Ana Souza)",
    "Qual o total líquido de Ana Souza no 1º trimestre de 2025?",
    "Qual foi o desconto de INSS do Bruno em jun/2025?",
    "Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?",
    "Qual foi o maior bônus do Bruno e em que mês?",
    "Traga a taxa Selic atual e cite a fonte"
  ];

  const getToolIcon = (tool) => {
    switch (tool) {
      case 'rag': return <Database className="w-4 h-4" />;
      case 'web': return <Globe className="w-4 h-4" />;
      default: return <MessageCircle className="w-4 h-4" />;
    }
  };

  const getToolColor = (tool) => {
    switch (tool) {
      case 'rag': return 'bg-blue-100 text-blue-800';
      case 'web': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Chatbot de Folha de Pagamento</h1>
                <p className="text-sm text-gray-600">Assistente inteligente para consultas de folha</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                apiStatus === 'online' ? 'bg-green-100 text-green-800' : 
                apiStatus === 'offline' ? 'bg-red-100 text-red-800' : 
                'bg-yellow-100 text-yellow-800'
              }`}>
                {apiStatus === 'online' ? '🟢 Online' : 
                 apiStatus === 'offline' ? '🔴 Offline' : 
                 '🟡 Verificando...'}
              </div>
              <button
                onClick={clearChat}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Limpar conversa"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto flex">
        {/* Sidebar */}
        <div className="w-80 bg-white shadow-sm border-r min-h-screen p-6">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">💡 Exemplos de Perguntas</h3>
              <div className="space-y-2">
                {examples.map((example, index) => (
                  <button
                    key={index}
                    onClick={() => loadExample(example)}
                    className="w-full text-left p-3 text-sm bg-gray-50 hover:bg-blue-50 hover:text-blue-700 rounded-lg transition-colors border border-gray-200"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">🔧 Funcionalidades</h3>
              <div className="space-y-3">
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <Database className="w-4 h-4 text-blue-600" />
                  <span>Consulta dados de folha</span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <Globe className="w-4 h-4 text-green-600" />
                  <span>Busca na web</span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <MessageCircle className="w-4 h-4 text-purple-600" />
                  <span>Conversa geral</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Bem-vindo ao Chatbot!</h3>
                <p className="text-gray-600 mb-4">Faça perguntas sobre folha de pagamento ou legislação trabalhista.</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {examples.slice(0, 3).map((example, index) => (
                    <button
                      key={index}
                      onClick={() => loadExample(example)}
                      className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm hover:bg-blue-200 transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div key={message.id} className={`fade-in ${message.type === 'user' ? 'flex justify-end' : 'flex justify-start'}`}>
                <div className={`message-bubble ${message.type} ${
                  message.type === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-100 text-gray-900'
                } rounded-2xl px-4 py-3 max-w-2xl`}>
                  <div className="flex items-start space-x-2">
                    {message.type === 'user' ? (
                      <User className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    ) : (
                      <Bot className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="flex-1">
                      <div className="whitespace-pre-wrap">{message.content}</div>
                      
                      {message.evidence && message.evidence.sources && (
                        <div className="mt-3 space-y-2">
                          <div className="text-xs font-medium opacity-75 mb-2">📊 Evidências:</div>
                          {message.evidence.sources.map((source, index) => (
                            <div key={index} className="evidence-card p-3 rounded-lg text-xs">
                              <div className="font-medium text-gray-900">
                                {source.employee_id} - {source.name}
                              </div>
                              <div className="text-gray-600 mt-1">
                                Competência: {source.competency} | 
                                Pagamento: {source.payment_date}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      <div className="flex items-center justify-between mt-2">
                        <div className="text-xs opacity-75">
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                        {message.tool_used && (
                          <div className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${getToolColor(message.tool_used)}`}>
                            {getToolIcon(message.tool_used)}
                            <span>{message.tool_used.toUpperCase()}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="message-bubble assistant bg-gray-100 text-gray-900 rounded-2xl px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <Bot className="w-5 h-5" />
                    <div className="loading-dots">Pensando</div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="bg-white border-t p-4">
            <form onSubmit={handleSubmit} className="flex space-x-3">
              <div className="flex-1">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Digite sua mensagem..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  disabled={isLoading}
                />
              </div>
              <button
                type="submit"
                disabled={isLoading || !inputMessage.trim()}
                className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
              >
                <Send className="w-5 h-5" />
                <span>Enviar</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
