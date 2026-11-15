import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send,
  Bot,
  User,
  Trash2,
  Database,
  Globe,
  MessageCircle,
  Menu,
  X,
} from 'lucide-react';
import axios from 'axios';
import { getErrorMessage, MAX_MESSAGE_LENGTH } from './apiErrors';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const REQUEST_TIMEOUT_MS = 20000;
const SESSION_STORAGE_KEY = 'pc_session_id';
// O contador de caracteres só aparece perto do limite.
const COUNTER_THRESHOLD = Math.floor(MAX_MESSAGE_LENGTH * 0.8);

const readStoredSession = () => {
  try {
    return localStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
};

const formatBRL = (value) =>
  typeof value === 'number'
    ? value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : value;

const formatDatePt = (value) => {
  if (!value) return '';
  const [y, m, d] = String(value).split('-');
  return d ? `${d}/${m}/${y}` : value;
};

const EXAMPLES = [
  'Quanto recebi (líquido) em maio/2025? (Ana Souza)',
  'Qual o total líquido de Ana Souza no 1º trimestre de 2025?',
  'Qual foi o desconto de INSS do Bruno em jun/2025?',
  'Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?',
  'Qual foi o maior bônus do Bruno e em que mês?',
  'Traga a taxa Selic atual e cite a fonte',
];

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');
  const [sessionId, setSessionId] = useState(readStoredSession);
  // Só tem efeito em telas pequenas; a partir de "md" a barra lateral fica sempre visível.
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const idRef = useRef(0);

  const nextId = () => {
    idRef.current += 1;
    return `${Date.now()}-${idRef.current}`;
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    try {
      if (sessionId) localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
      else localStorage.removeItem(SESSION_STORAGE_KEY);
    } catch {
      /* localStorage indisponível: segue sem persistir */
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isSidebarOpen) return undefined;
    const closeOnEscape = (e) => {
      if (e.key === 'Escape') setIsSidebarOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isSidebarOpen]);

  const checkApiStatus = useCallback(async () => {
    try {
      await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 });
      setApiStatus('online');
    } catch {
      setApiStatus('offline');
    }
  }, []);

  useEffect(() => {
    checkApiStatus();
  }, [checkApiStatus]);

  const sendMessage = async (message) => {
    const text = message.trim();
    if (!text || isLoading) return;

    setMessages((prev) => [
      ...prev,
      { id: nextId(), type: 'user', content: text, timestamp: new Date() },
    ]);
    setIsLoading(true);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const { data } = await axios.post(
        `${API_BASE_URL}/chat`,
        { message: text, session_id: sessionId },
        { signal: controller.signal }
      );

      setApiStatus('online');
      if (data.session_id) setSessionId(data.session_id);

      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          type: 'assistant',
          content: data.response,
          evidence: data.evidence,
          tool_used: data.tool_used,
          timestamp: new Date(),
        },
      ]);
    } catch (error) {
      // Sem resposta e sem ter sido cancelada: o backend caiu depois da checagem inicial.
      if (!error.response && !axios.isCancel(error)) setApiStatus('offline');
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          type: 'assistant',
          content: `Erro: ${getErrorMessage(error)}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      clearTimeout(timer);
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;
    sendMessage(inputMessage);
    setInputMessage('');
  };

  const clearChat = () => {
    setMessages([]);
    setSessionId(null);
  };

  const chooseExample = (example) => {
    setInputMessage(example);
    setIsSidebarOpen(false);
    inputRef.current?.focus();
  };

  const getToolIcon = (tool) => {
    switch (tool) {
      case 'rag':
        return <Database className="w-4 h-4" />;
      case 'web':
        return <Globe className="w-4 h-4" />;
      default:
        return <MessageCircle className="w-4 h-4" />;
    }
  };

  const getToolColor = (tool) => {
    switch (tool) {
      case 'rag':
        return 'bg-blue-100 text-blue-800';
      case 'web':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const renderEvidence = (evidence) => {
    const sources = evidence?.sources;
    if (!sources || sources.length === 0) return null;
    return (
      <div className="mt-3 space-y-2">
        <div className="text-xs font-medium opacity-75 mb-2">📊 Evidências</div>
        {sources.map((source, index) => (
          <div key={index} className="evidence-card p-3 rounded-lg text-xs">
            {source.employee_id ? (
              <>
                <div className="font-medium text-gray-900">
                  {source.employee_id} — {source.name}
                </div>
                <div className="text-gray-600 mt-1">
                  Competência {source.competency} · líquido {formatBRL(source.net_pay)} · pago em{' '}
                  {formatDatePt(source.payment_date)}
                </div>
              </>
            ) : (
              <>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-blue-700 underline break-words"
                >
                  {source.title || source.url}
                </a>
                {source.snippet && <div className="text-gray-600 mt-1">{source.snippet}</div>}
              </>
            )}
          </div>
        ))}
      </div>
    );
  };

  const charCount = inputMessage.length;

  return (
    <div className="app-shell bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col">
      <div className="bg-white shadow-sm border-b flex-shrink-0">
        <div className="max-w-4xl mx-auto px-4 py-3 md:py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <button
                type="button"
                onClick={() => setIsSidebarOpen(true)}
                className="md:hidden p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Abrir exemplos de perguntas"
                aria-expanded={isSidebarOpen}
                aria-controls="sidebar"
              >
                <Menu className="w-5 h-5" />
              </button>
              <div className="w-10 h-10 flex-shrink-0 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="text-base sm:text-xl font-semibold text-gray-900 truncate">
                  Chatbot de Folha de Pagamento
                </h1>
                <p className="hidden sm:block text-sm text-gray-600 truncate">
                  Assistente inteligente para consultas de folha
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <div
                className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
                  apiStatus === 'online'
                    ? 'bg-green-100 text-green-800'
                    : apiStatus === 'offline'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}
              >
                {apiStatus === 'online'
                  ? '🟢 Online'
                  : apiStatus === 'offline'
                  ? '🔴 Offline'
                  : '🟡 Verificando...'}
              </div>
              <button
                type="button"
                onClick={clearChat}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Nova conversa"
                aria-label="Nova conversa"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {isSidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/40 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        <aside
          id="sidebar"
          className={`fixed inset-y-0 left-0 z-30 w-72 max-w-[85vw] bg-white shadow-lg overflow-y-auto transition-[transform,visibility] duration-200 md:static md:z-auto md:w-80 md:max-w-none md:flex-shrink-0 md:shadow-sm md:border-r md:translate-x-0 md:visible ${
            isSidebarOpen ? 'translate-x-0 visible' : '-translate-x-full invisible'
          }`}
        >
          {/* Fora do bloco com space-y: escondido no desktop, ainda contaria no espaçamento. */}
          <div className="flex items-center justify-between px-6 pt-6 md:hidden">
            <span className="text-lg font-semibold text-gray-900">Menu</span>
            <button
              type="button"
              onClick={() => setIsSidebarOpen(false)}
              className="p-2 -mr-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Fechar menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-6 space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">💡 Exemplos de Perguntas</h3>
              <div className="space-y-2">
                {EXAMPLES.map((example) => (
                  <button
                    type="button"
                    key={example}
                    onClick={() => chooseExample(example)}
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
        </aside>

        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-8 md:py-12">
                <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Bem-vindo ao Chatbot!</h3>
                <p className="text-gray-600 mb-4">
                  Faça perguntas sobre folha de pagamento ou legislação trabalhista.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {EXAMPLES.slice(0, 3).map((example) => (
                    <button
                      type="button"
                      key={example}
                      onClick={() => chooseExample(example)}
                      className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm hover:bg-blue-200 transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`fade-in ${message.type === 'user' ? 'flex justify-end' : 'flex justify-start'}`}
              >
                <div
                  className={`message-bubble ${message.type} ${
                    message.type === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'
                  } rounded-2xl px-4 py-3 max-w-2xl`}
                >
                  <div className="flex items-start space-x-2">
                    {message.type === 'user' ? (
                      <User className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    ) : (
                      <Bot className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="whitespace-pre-wrap">{message.content}</div>
                      {renderEvidence(message.evidence)}
                      <div className="flex items-center justify-between gap-2 mt-2">
                        <div className="text-xs opacity-75">
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                        {message.tool_used && (
                          <div
                            className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${getToolColor(
                              message.tool_used
                            )}`}
                          >
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

          <div className="bg-white border-t p-3 md:p-4 flex-shrink-0">
            <form onSubmit={handleSubmit} className="flex items-start gap-2 md:gap-3">
              <div className="flex-1 min-w-0">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  maxLength={MAX_MESSAGE_LENGTH}
                  placeholder="Digite sua mensagem..."
                  aria-label="Mensagem"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  disabled={isLoading}
                />
                {charCount >= COUNTER_THRESHOLD && (
                  <div
                    className={`mt-1 text-right text-xs ${
                      charCount >= MAX_MESSAGE_LENGTH ? 'text-red-600' : 'text-gray-500'
                    }`}
                  >
                    {charCount}/{MAX_MESSAGE_LENGTH} caracteres
                  </div>
                )}
              </div>
              <button
                type="submit"
                disabled={isLoading || !inputMessage.trim()}
                aria-label="Enviar mensagem"
                className="px-4 md:px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <Send className="w-5 h-5" />
                <span className="hidden sm:inline">Enviar</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
