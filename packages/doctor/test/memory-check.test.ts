/**
 * Hermetic tests for memoryCheck.
 *
 * Tests verify:
 * - HEALTHY fixture: real MemoryStore with DeterministicEmbedding, status === 'pass'
 * - FAULTY fixture: mock MemoryStore with throwing store() method, status === 'fail'
 * - No real network, no real timers
 * - Strictly disjoint test groups
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { memoryCheck } from '../src/checks/memory-check.js';
import type { DoctorContext } from '../src/checks/types.js';
import { MemoryStore, DeterministicEmbedding } from '@shay/memory';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

describe('memory-check', () => {
  describe('healthy', () => {
    let tmpdir: string;

    beforeEach(() => {
      tmpdir = fs.mkdtempSync(path.join(os.tmpdir(), 'shay-doctor-test-'));
    });

    it('should pass with a real MemoryStore', async () => {
      const embedding = new DeterministicEmbedding();
      const store = new MemoryStore(embedding, tmpdir);

      const ctx: DoctorContext = {
        memory: store,
      };

      const result = await memoryCheck(ctx);

      expect(result.status).toBe('pass');
      expect(result.detail).toBeDefined();
      expect(result.remediation).toBeUndefined();
    });
  });

  describe('faulty', () => {
    it('should fail when store() throws', async () => {
      const mockStore = {
        store: async () => {
          throw new Error('Store is broken');
        },
        recall: async () => [],
        all: async () => [],
      };

      const ctx: DoctorContext = {
        memory: mockStore,
      };

      const result = await memoryCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toBeDefined();
      expect(result.remediation).toBeDefined();
    });

    it('should fail when existing records contain invalid tier', async () => {
      const mockStore = {
        store: async () => {},
        recall: async () => [{ id: 'test', content: 'test', tier: 'T1' }],
        all: async () => [
          { id: 'bad-tier', content: 'test', tier: 'INVALID' },
        ],
      };

      const ctx: DoctorContext = {
        memory: mockStore,
      };

      const result = await memoryCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toContain('invalid tier');
      expect(result.remediation).toBeDefined();
    });
  });
});
