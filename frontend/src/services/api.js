const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
export const ASK_TIMEOUT_MS = 300000;

export class ApiError extends Error {
  constructor(message, code = 'network_error') {
    super(message);
    this.name = 'ApiError';
    this.code = code;
  }
}

async function request(path, { signal, timeout = 15000, ...options } = {}) {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal?.addEventListener('abort', cancel, { once: true });
  if (signal?.aborted) controller.abort();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
    let body;
    try { body = await response.json(); } catch {
      throw new ApiError('The backend returned an unreadable response. Check that the API is running.', 'invalid_response');
    }
    if (!response.ok) {
      // Only show messages from our structured error contract, never raw HTML/tracebacks.
      throw new ApiError(typeof body.message === 'string' && typeof body.code === 'string'
        ? body.message : 'The backend could not complete the request. Please try again.', body.code || 'server_error');
    }
    return body;
  } catch (error) {
    if (timedOut) throw new ApiError('The search timed out. The first model load can take longer; wait a moment and retry.', 'timeout');
    if (signal?.aborted) throw error;
    if (error instanceof ApiError) throw error;
    throw new ApiError('Cannot reach the backend. Check your connection and that FastAPI is running.', 'network_error');
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}

export const getOptions = (signal) => request('/options', { signal });
export const askQuestion = (values, signal) => request('/ask', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(values), signal, timeout: ASK_TIMEOUT_MS,
});
export const compareStrategies = ({ query, language, top_k }, signal) => request('/compare', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query, language, top_k }), signal, timeout: ASK_TIMEOUT_MS * 2,
});
