// Mesmo limite do backend (ChatRequest.message em app/utils/models.py).
export const MAX_MESSAGE_LENGTH = 1000;

const isMessageField = (item) => Array.isArray(item?.loc) && item.loc.includes('message');

/**
 * Texto de erro para mostrar no chat, a partir de um erro do axios.
 *
 * O backend responde em dois formatos: {"error": "..."} (erros da aplicação)
 * e {"detail": ...} (404 e validação do FastAPI). No erro de validação (422),
 * "detail" é uma lista de objetos, que não pode ir direto para a tela.
 */
export function getErrorMessage(error) {
  if (error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
    return 'A requisição demorou demais e foi cancelada.';
  }

  const response = error?.response;
  if (!response) {
    return 'Não foi possível falar com a API. Verifique se o backend está rodando.';
  }

  const { error: apiError, detail } = response.data || {};
  if (typeof apiError === 'string' && apiError) return apiError;
  if (typeof detail === 'string' && detail) return detail;

  if (response.status === 422) {
    if (Array.isArray(detail) && detail.some(isMessageField)) {
      return `A mensagem precisa ter entre 1 e ${MAX_MESSAGE_LENGTH} caracteres.`;
    }
    return 'A API recusou os dados enviados.';
  }

  return `A API respondeu com erro ${response.status}.`;
}
