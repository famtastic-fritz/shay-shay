import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  resolve: {
    alias: [
      { find: /^@shay\/([^/]+)$/, replacement: root + 'packages/$1/src/index.ts' },
    ],
  },
  test: {
    include: ['packages/*/test/**/*.test.ts'],
  },
});
