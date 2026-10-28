import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import AnswerCard, { safeSourceUrl } from '../components/AnswerCard';
import { answer } from './fixtures';

it.each(['javascript:alert(1)', 'data:text/html,test', '//example.test', 'file:///private',
  'https://user:password@example.test', 'not a url'])('blocks unsafe source URLs: %s', value => {
  expect(safeSourceUrl(value)).toBeNull();
  render(<AnswerCard result={{ ...answer, source_url: value }} />);
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});

it('renders retrieved HTML as inert text', () => {
  const text = '<img src=x onerror=alert(1) />';
  const { container } = render(<AnswerCard result={{ ...answer, translated_answer: text }} />);
  expect(screen.getByText(text)).toBeVisible();
  expect(container.querySelector('img')).toBeNull();
});

it('does not present an untranslated direct query as an English translation', () => {
  render(<AnswerCard result={{ ...answer, query: 'మధుమేహం', english_query: 'మధుమేహం', retrieval_strategy: 'direct_semantic' }} />);
  expect(screen.getByText(/Direct retrieval uses the original query/)).toBeInTheDocument();
});
