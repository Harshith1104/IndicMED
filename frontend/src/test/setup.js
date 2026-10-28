import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Icons have no behavior under test. Avoid loading the complete Lucide ESM tree
// for jsdom tests on WSL's Windows-mounted filesystem; browser tests use real icons.
vi.mock('lucide-react', () => Object.fromEntries([
  'AlertCircle', 'ArrowDown', 'ArrowRight', 'ArrowUpRight', 'BookOpen', 'Check',
  'ChevronDown', 'Columns2', 'ExternalLink', 'FileText', 'HeartPulse', 'Info', 'Languages',
  'LoaderCircle', 'Moon', 'Search', 'SearchX', 'ShieldCheck', 'SlidersHorizontal', 'Sun',
].map(name => [name, () => null])));

afterEach(() => cleanup());
