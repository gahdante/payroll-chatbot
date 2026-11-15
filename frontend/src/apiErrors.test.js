import { getErrorMessage, MAX_MESSAGE_LENGTH } from './apiErrors';

const httpError = (status, data) => ({
  message: `Request failed with status code ${status}`,
  response: { status, data },
});

describe('getErrorMessage', () => {
  test('requisição cancelada pelo tempo limite', () => {
    expect(getErrorMessage({ name: 'CanceledError', code: 'ERR_CANCELED' })).toMatch(
      /demorou demais/
    );
  });

  test('backend fora do ar (sem resposta)', () => {
    expect(getErrorMessage({ message: 'Network Error', code: 'ERR_NETWORK' })).toMatch(
      /backend está rodando/
    );
  });

  test('mensagem longa demais (422) não vira [object Object]', () => {
    const error = httpError(422, {
      detail: [
        {
          type: 'string_too_long',
          loc: ['body', 'message'],
          msg: 'String should have at most 1000 characters',
        },
      ],
    });
    const text = getErrorMessage(error);
    expect(text).not.toMatch(/object Object/);
    expect(text).toContain(String(MAX_MESSAGE_LENGTH));
  });

  test('422 em outro campo', () => {
    const error = httpError(422, { detail: [{ loc: ['body', 'session_id'], msg: 'invalid' }] });
    expect(getErrorMessage(error)).toBe('A API recusou os dados enviados.');
  });

  test('formato {"error"} da aplicação', () => {
    const error = httpError(500, { error: 'Erro interno ao processar a mensagem' });
    expect(getErrorMessage(error)).toBe('Erro interno ao processar a mensagem');
  });

  test('formato {"detail"} em texto', () => {
    expect(getErrorMessage(httpError(404, { detail: 'Not Found' }))).toBe('Not Found');
  });

  test('resposta sem corpo', () => {
    expect(getErrorMessage(httpError(502, undefined))).toBe('A API respondeu com erro 502.');
  });
});
