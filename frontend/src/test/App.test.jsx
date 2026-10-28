import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import { ApiError, askQuestion, compareStrategies, getOptions } from '../services/api';
import { answer, options } from './fixtures';

vi.mock('../services/api', async importOriginal => {
  const actual = await importOriginal();
  return { ...actual, getOptions: vi.fn(), askQuestion: vi.fn(), compareStrategies: vi.fn() };
});

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  document.documentElement.dataset.theme = 'light';
  getOptions.mockResolvedValue(options);
  askQuestion.mockResolvedValue(answer);
});

async function ready() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByLabelText('Your health question');
  return user;
}

async function submit(user, query = 'What is asthma?') {
  await user.type(screen.getByLabelText('Your health question'), query);
  await user.click(screen.getByRole('button', { name: /Ask IndicMed/ }));
}

describe('question interface', () => {
  it('renders the initial state with all four language examples and no invented answer', async () => {
    await ready();
    expect(screen.getByRole('heading', { name: /Health information/ })).toBeVisible();
    expect(screen.getByRole('button', { name: /మైగ్రేన్/ })).toBeVisible();
    expect(screen.queryByText('RETRIEVED ANSWER')).not.toBeInTheDocument();
    expect(screen.getByText(/not a substitute for professional medical advice/)).toBeVisible();
  });

  it('validates an empty question without calling the API', async () => {
    const user = await ready();
    await user.click(screen.getByRole('button', { name: /Ask IndicMed/ }));
    expect(screen.getByRole('alert')).toHaveTextContent('Please enter a health question.');
    expect(askQuestion).not.toHaveBeenCalled();
  });

  it.each(['en', 'hi', 'te', 'ta'])('sends the selected %s language and settings', async language => {
    const user = await ready();
    await user.selectOptions(screen.getByLabelText('Question language'), language);
    await user.click(screen.getByText('Advanced retrieval settings'));
    await user.selectOptions(screen.getByLabelText('Retrieval method'), 'bm25');
    fireEvent.change(screen.getByLabelText(/Retrieved results/), { target: { value: '5' } });
    await submit(user);
    expect(askQuestion).toHaveBeenCalledWith({ query: 'What is asthma?', language,
      retrieval_method: 'bm25', multilingual_strategy: 'translate', top_k: 5 }, expect.any(AbortSignal));
  });

  it('disables incompatible settings without silently changing selections', async () => {
    const user = await ready();
    await user.click(screen.getByText('Advanced retrieval settings'));
    await user.selectOptions(screen.getByLabelText('Multilingual strategy'), 'direct');
    expect(screen.getByRole('option', { name: 'TF-IDF' })).toBeDisabled();
    expect(screen.getByRole('option', { name: 'BM25' })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText('Multilingual strategy'), 'translate');
    await user.selectOptions(screen.getByLabelText('Retrieval method'), 'tfidf');
    expect(screen.getByRole('option', { name: 'Direct multilingual retrieval' })).toBeDisabled();
    expect(screen.getByLabelText('Retrieval method')).toHaveValue('tfidf');
    expect(screen.getByText(/Direct multilingual retrieval requires Semantic/)).toBeVisible();
  });

  it('fills examples and preserves manually selected settings', async () => {
    const user = await ready();
    await user.click(screen.getByRole('button', { name: /మైగ్రేన్/ }));
    expect(screen.getByLabelText('Your health question')).toHaveValue('మైగ్రేన్‌కు కారణాలు ఏమిటి?');
    expect(screen.getByLabelText('Question language')).toHaveValue('auto');
    await user.selectOptions(screen.getByLabelText('Question language'), 'hi');
    expect(screen.queryByRole('button', { name: /మైగ్రేన్/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /मधुमेह/ }));
    expect(screen.getByLabelText('Question language')).toHaveValue('hi');
  });
});

describe('answers and request lifecycle', () => {
  it('renders the answer, safe source, score, related questions and technical details', async () => {
    const user = await ready();
    await submit(user);
    expect(await screen.findByText('RETRIEVED ANSWER')).toBeVisible();
    expect(screen.getByText('A grounded test answer.', { selector: '.answer-text' })).toBeVisible();
    expect(screen.getByRole('link', { name: /Test source/ })).toHaveAttribute('href', answer.source_url);
    expect(screen.getByText('0.734', { selector: '.score strong' })).toBeVisible();
    expect(screen.getByText(/does not represent medical accuracy or clinical confidence/)).toBeVisible();
    expect(screen.getByText('What causes asthma?')).toBeVisible();
    await user.click(screen.getByText('Technical details'));
    expect(screen.getByText('test-document')).toBeVisible();
    await user.type(screen.getByLabelText('Your health question'), '?');
    expect(screen.queryByText('RETRIEVED ANSWER')).not.toBeInTheDocument();
  });

  it.each(['Question language', 'Retrieval method', 'Multilingual strategy'])('clears answers when %s changes', async label => {
    const user = await ready();
    await submit(user);
    await screen.findByText('RETRIEVED ANSWER');
    if (label !== 'Question language') await user.click(screen.getByText('Advanced retrieval settings'));
    await user.selectOptions(screen.getByLabelText(label), label === 'Question language' ? 'ta' : label === 'Retrieval method' ? 'tfidf' : 'direct');
    expect(screen.queryByText('RETRIEVED ANSWER')).not.toBeInTheDocument();
  });

  it('prevents duplicates, aborts on edits, and ignores stale responses even if abort is ignored', async () => {
    let finishOld;
    askQuestion.mockImplementationOnce(() => new Promise(resolve => { finishOld = resolve; }));
    const user = await ready();
    await submit(user);
    expect(screen.getByText('Finding your answer')).toBeVisible();
    expect(screen.getByRole('button', { name: /Searching/ })).toBeDisabled();
    expect(askQuestion).toHaveBeenCalledTimes(1);
    const signal = askQuestion.mock.calls[0][1];
    await user.clear(screen.getByLabelText('Your health question'));
    expect(signal.aborted).toBe(true);
    askQuestion.mockResolvedValueOnce({ ...answer, category: 'New result' });
    await submit(user, 'A newer question');
    await screen.findByRole('heading', { name: 'New result' });
    await act(async () => finishOld({ ...answer, category: 'Stale result' }));
    expect(screen.queryByRole('heading', { name: 'Stale result' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'New result' })).toBeVisible();
  });

  it.each(['network_error', 'timeout', 'translation_unavailable', 'pipeline_busy', 'invalid_request'])('shows %s errors', async code => {
    askQuestion.mockRejectedValueOnce(new ApiError(`Test ${code}`, code));
    const user = await ready();
    await submit(user);
    expect(await screen.findByRole('alert')).toHaveTextContent(`Test ${code}`);
    expect(screen.queryByText('RETRIEVED ANSWER')).not.toBeInTheDocument();
  });

  it('handles no results', async () => {
    askQuestion.mockRejectedValueOnce(new ApiError('No relevant FAQ', 'no_results'));
    const user = await ready();
    await submit(user);
    expect(await screen.findByText('No matching FAQ found')).toBeVisible();
  });

  it('shows the English fallback and translation warning', async () => {
    askQuestion.mockResolvedValueOnce({ ...answer, selected_language: 'te', detected_language: 'te',
      translation_warning: 'Answer translation unavailable; showing grounded English answer.' });
    const user = await ready();
    await submit(user);
    expect(await screen.findByText('English fallback')).toBeVisible();
    expect(screen.getByText(/Answer translation unavailable/)).toBeVisible();
    expect(screen.getByText('A grounded test answer.', { selector: '.answer-text' })).toHaveAttribute('lang', 'en');
  });

  it('reconnects after an unavailable options endpoint', async () => {
    getOptions.mockRejectedValueOnce(new ApiError('Backend unavailable'));
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable');
    await user.click(screen.getByRole('button', { name: /Reconnect/ }));
    expect(await screen.findByLabelText('Your health question')).toBeVisible();
  });

  it('toggles and persists light/dark mode', async () => {
    const user = await ready();
    await user.click(screen.getByRole('button', { name: 'Switch to dark mode' }));
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(localStorage.getItem('indicmed-theme')).toBe('dark');
    await user.click(screen.getByRole('button', { name: 'Switch to light mode' }));
    expect(document.documentElement).toHaveAttribute('data-theme', 'light');
  });

  it('shows out-of-scope feedback with examples and no unrelated answer', async () => {
    askQuestion.mockResolvedValueOnce({ status: 'out_of_scope', selected_language: 'en', reason: 'non_medical_context' });
    const user = await ready();
    await submit(user, 'Who is Allu Arjun?');
    expect(await screen.findByText("This question is outside IndicMed's medical scope.")).toBeVisible();
    expect(screen.queryByText('RETRIEVED ANSWER')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'What are the symptoms of diabetes?' }));
    expect(screen.getByLabelText('Your health question')).toHaveValue('What are the symptoms of diabetes?');
  });

  it('shows localized evidence feedback', async () => {
    askQuestion.mockResolvedValueOnce({ status: 'insufficient_evidence', selected_language: 'te', reason: 'weak_retrieval_evidence' });
    const user = await ready();
    await submit(user);
    expect(await screen.findByText('తగిన సంబంధిత వైద్య సమాచారం కనుగొనలేకపోయాము.')).toBeVisible();
    expect(screen.queryByText('RETRIEVED ANSWER')).not.toBeInTheDocument();
  });

  it('compares Semantic independently of Ask settings and preserves partial results', async () => {
    const failed = { status: 'insufficient_evidence', selected_language: 'en', reason: 'weak_retrieval_evidence' };
    compareStrategies.mockResolvedValueOnce({ query: 'What is asthma?', selected_language: 'en', top_k: 3,
      equivalent: false, direct: failed, translate: { ...answer, status: 'success', retrieval_query: 'What is asthma?' } });
    const user = await ready();
    await user.click(screen.getByText('Advanced retrieval settings'));
    await user.selectOptions(screen.getByLabelText('Retrieval method'), 'bm25');
    await user.type(screen.getByLabelText('Your health question'), 'What is asthma?');
    await user.click(screen.getByRole('button', { name: 'Compare Strategies' }));
    expect(await screen.findByRole('heading', { name: 'Compare retrieval strategies' })).toBeVisible();
    expect(screen.getByLabelText('Retrieval method')).toHaveValue('bm25');
    expect(compareStrategies).toHaveBeenCalledTimes(1);
    expect(screen.getByText("We couldn't find sufficiently relevant medical information.")).toBeVisible();
    expect(screen.getByText('A grounded test answer.', { selector: '.answer-text' })).toBeVisible();
    expect(screen.getAllByText('RETRIEVAL SIMILARITY SCORE').length).toBeGreaterThan(0);
    await user.type(screen.getByLabelText('Your health question'), '?');
    expect(screen.queryByRole('heading', { name: 'Compare retrieval strategies' })).not.toBeInTheDocument();
  });

  it('prevents duplicate comparisons and ignores a response after input changes', async () => {
    let finish;
    compareStrategies.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const user = await ready();
    await user.type(screen.getByLabelText('Your health question'), 'What is asthma?');
    await user.click(screen.getByRole('button', { name: 'Compare Strategies' }));
    expect(screen.getByText('Comparing both strategies')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Compare Strategies' })).toBeDisabled();
    expect(compareStrategies).toHaveBeenCalledTimes(1);
    const signal = compareStrategies.mock.calls[0][1];
    await user.type(screen.getByLabelText('Your health question'), '?');
    expect(signal.aborted).toBe(true);
    await act(async () => finish({ query: 'old', top_k: 3, direct: answer, translate: answer }));
    expect(screen.queryByRole('heading', { name: 'Compare retrieval strategies' })).not.toBeInTheDocument();
  });
});
