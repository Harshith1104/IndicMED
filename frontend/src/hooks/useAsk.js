import { useCallback, useEffect, useRef, useState } from 'react';
import { askQuestion, compareStrategies } from '../services/api';

export function useAsk() {
  const [state, setState] = useState({ status: 'idle', result: null, error: null });
  const active = useRef(null);
  const sequence = useRef(0);

  const reset = useCallback(() => {
    sequence.current += 1;
    active.current?.abort();
    active.current = null;
    setState({ status: 'idle', result: null, error: null });
  }, []);

  useEffect(() => () => { sequence.current += 1; active.current?.abort(); }, []);

  const ask = useCallback(async (values, mode = 'ask') => {
    if (active.current) return; // Protect against double clicks before React rerenders.
    const id = ++sequence.current;
    const controller = new AbortController();
    active.current = controller;
    setState({ status: 'loading', result: null, error: null, mode });
    try {
      const result = await (mode === 'compare' ? compareStrategies : askQuestion)(values, controller.signal);
      if (id !== sequence.current) return;
      if (mode === 'compare') {
        setState({ status: 'comparison', result, error: null });
      } else if (result?.status && result.status !== 'success') {
        setState({ status: 'decision', result, error: null });
      } else if (!result?.answer || !result?.translated_answer) {
        setState({ status: 'empty', result: null, error: null });
      } else {
        setState({ status: 'success', result, error: null });
      }
    } catch (error) {
      if (id === sequence.current && !controller.signal.aborted) {
        setState({ status: error.code === 'no_results' ? 'empty' : 'error', result: null, error });
      }
    } finally {
      if (id === sequence.current) active.current = null;
    }
  }, []);
  return { ...state, ask, reset };
}
