import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1', port: 5173, strictPort: true,
      // Windows IDE writes are not reported by inotify on WSL-mounted drives.
      watch: process.env.WSL_DISTRO_NAME ? { usePolling: true, interval: 500 } : undefined,
      // A relative /api works in development and behind a deployment reverse proxy.
      proxy: { '/api': { target: env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true, timeout: 660000, proxyTimeout: 660000 } },
    },
    preview: { host: '127.0.0.1', port: 4173, strictPort: true },
    test: { environment: 'jsdom', setupFiles: './src/test/setup.js', restoreMocks: true,
      // Reuse one jsdom worker: repeated cold starts on /mnt/f can exceed
      // Vitest's fixed worker startup deadline. Tests restore mocks and globals.
      include: ['src/**/*.test.{js,jsx}'], maxWorkers: 1, pool: 'threads', isolate: false },
  };
});
