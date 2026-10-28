import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { askQuestion, compareStrategies, ASK_TIMEOUT_MS, getOptions } from '../services/api';

vi.unmock('../services/api'); // This file tests the real transport after component mocks.

beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it('posts exact request values to the same-origin API', async () => {
  fetch.mockResolvedValue({ ok: true, json: async () => ({ answer: 'test' }) });
  const values = { query: 'మధుమేహం', language: 'te', retrieval_method: 'semantic', multilingual_strategy: 'direct', top_k: 2 };
  await askQuestion(values);
  expect(fetch).toHaveBeenCalledWith('/api/ask', expect.objectContaining({ method: 'POST', body: JSON.stringify(values),
    headers: { 'Content-Type': 'application/json' } }));
});

it('surfaces safe API errors and hides unstructured error bodies', async () => {
  fetch.mockResolvedValueOnce({ ok: false, json: async () => ({ code: 'translation_unavailable', message: 'Configure translation' }) });
  await expect(askQuestion({})).rejects.toMatchObject({ code: 'translation_unavailable', message: 'Configure translation' });
  fetch.mockResolvedValueOnce({ ok: false, json: async () => ({ detail: '/private/secret' }) });
  await expect(getOptions()).rejects.toThrow('The backend could not complete the request.');
});

it('handles network and malformed JSON responses', async () => {
  fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));
  await expect(getOptions()).rejects.toMatchObject({ code: 'network_error' });
  fetch.mockResolvedValueOnce({ ok: true, json: async () => { throw new Error('html'); } });
  await expect(getOptions()).rejects.toMatchObject({ code: 'invalid_response' });
});

it('times out a stalled inference request', async () => {
  vi.useFakeTimers();
  fetch.mockImplementation((_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
  }));
  const result = expect(askQuestion({})).rejects.toMatchObject({ code: 'timeout' });
  await vi.advanceTimersByTimeAsync(ASK_TIMEOUT_MS);
  await result;
});

it('forwards caller cancellation', async () => {
  fetch.mockImplementation((_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
  }));
  const controller = new AbortController();
  const result = expect(askQuestion({}, controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
  controller.abort();
  await result;
});

it('comparison sends only the shared question, language and top-k', async () => {
  fetch.mockResolvedValue({ ok: true, json: async () => ({ direct: {}, translate: {} }) });
  await compareStrategies({ query: 'ఆస్తమా', language: 'te', top_k: 2, retrieval_method: 'bm25', multilingual_strategy: 'direct' });
  expect(fetch).toHaveBeenCalledWith('/api/compare', expect.objectContaining({ method: 'POST',
    body: JSON.stringify({ query: 'ఆస్తమా', language: 'te', top_k: 2 }) }));
});
