/**
 * Hermetic tests for authorityCheck.
 *
 * Tests verify:
 * - HEALTHY fixture: IngestedCapabilityStore with entry at trustTier 1 (Suggest), status === 'pass'
 * - FAULTY fixture: entry at trustTier 3 (Confirm) without manual authority grant, status === 'fail'
 * - Strictly disjoint test groups
 */

import { describe, it, expect } from 'vitest';
import { authorityCheck } from '../src/checks/authority-check.js';
import type { DoctorContext } from '../src/checks/types.js';
import { IngestedCapabilityStore } from '@shay/ingestion';
import { AuthorityRegistry } from '@shay/core';
import type { CapabilityManifest } from '@shay/ingestion';

describe('authority-check', () => {
  describe('healthy', () => {
    it('should pass with IngestedCapabilityStore at trustTier 1 (Suggest)', async () => {
      const store = new IngestedCapabilityStore();
      const authority = new AuthorityRegistry();

      const manifest: CapabilityManifest = {
        id: 'safe-capability',
        name: 'Safe Capability',
        version: '1.0.0',
        description: 'Safe capability at Suggest tier',
        trustTier: 1, // Suggest
      };

      await store.ingest(manifest, {
        source: 'https://example.com/safe',
        version: '1.0.0',
        ingestionDate: new Date().toISOString(),
      });

      const ctx: DoctorContext = {
        ingestionStore: store,
        authority,
      };

      const result = await authorityCheck(ctx);

      expect(result.status).toBe('pass');
      expect(result.detail).toBeDefined();
      expect(result.remediation).toBeUndefined();
    });
  });

  describe('faulty', () => {
    it('should fail with entry at trustTier 3 (Confirm) without authority grant', async () => {
      const store = new IngestedCapabilityStore();
      const authority = new AuthorityRegistry();

      const manifest: CapabilityManifest = {
        id: 'privileged-capability',
        name: 'Privileged Capability',
        version: '1.0.0',
        description: 'Privileged capability at Confirm tier',
        trustTier: 3, // Confirm (requires manual authority)
      };

      await store.ingest(manifest, {
        source: 'https://example.com/privileged',
        version: '1.0.0',
        ingestionDate: new Date().toISOString(),
      });

      const ctx: DoctorContext = {
        ingestionStore: store,
        authority,
      };

      const result = await authorityCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toContain('privileged-capability');
      expect(result.remediation).toBeDefined();
    });

    it('should fail with entry at trustTier 4 (Auto) without authority grant', async () => {
      const store = new IngestedCapabilityStore();
      const authority = new AuthorityRegistry();

      const manifest: CapabilityManifest = {
        id: 'auto-capability',
        name: 'Auto Capability',
        version: '1.0.0',
        description: 'Automatic capability',
        trustTier: 4, // Auto (highest privilege)
      };

      await store.ingest(manifest, {
        source: 'https://example.com/auto',
        version: '1.0.0',
        ingestionDate: new Date().toISOString(),
      });

      const ctx: DoctorContext = {
        ingestionStore: store,
        authority,
      };

      const result = await authorityCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toBeDefined();
      expect(result.remediation).toBeDefined();
    });
  });
});
