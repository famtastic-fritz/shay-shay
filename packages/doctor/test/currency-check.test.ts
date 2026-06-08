/**
 * Hermetic tests for currencyCheck.
 *
 * Tests verify:
 * - HEALTHY fixture: mock senses.getAlerts() returns alert with affectsIngested === false, status === 'pass'
 * - BREAKING-FAIL fixture: alert with affectsIngested === true and releaseClass === 'breaking', status === 'fail'
 * - DEPRECATION-WARN fixture: alert with affectsIngested === true and releaseClass === 'deprecation', status === 'warn'
 * - Strictly disjoint test groups
 */

import { describe, it, expect } from 'vitest';
import { currencyCheck } from '../src/checks/currency-check.js';
import type { DoctorContext } from '../src/checks/types.js';
import type { ReleaseAlert } from '@shay/senses';

describe('currency-check', () => {
  describe('healthy', () => {
    it('should pass when alerts do not affect ingested sources', async () => {
      const mockAlert: ReleaseAlert = {
        event: {
          feedId: 'test-feed',
          source: 'Test Source',
          version: '2.0.0',
          publishedAt: new Date().toISOString(),
          url: 'https://example.com/release',
        },
        releaseClass: 'feature',
        relevance: 0.3,
        affectsIngested: false,
        suggestedAction: 'ignore',
      };

      const mockSenses = {
        getAlerts: () => [mockAlert],
      };

      const ctx: DoctorContext = {
        senses: mockSenses,
      };

      const result = await currencyCheck(ctx);

      expect(result.status).toBe('pass');
      expect(result.detail).toBeDefined();
      expect(result.remediation).toBeUndefined();
    });
  });

  describe('breaking-fail', () => {
    it('should fail when breaking change affects ingested source', async () => {
      const mockAlert: ReleaseAlert = {
        event: {
          feedId: 'breaking-feed',
          source: 'Breaking Source',
          version: '3.0.0',
          publishedAt: new Date().toISOString(),
          url: 'https://example.com/breaking-release',
          notes: 'Breaking API change',
        },
        releaseClass: 'breaking',
        relevance: 0.9,
        affectsIngested: true,
        ingestedSource: 'https://github.com/example/breaking-lib',
        suggestedAction: 're-ingest',
      };

      const mockSenses = {
        getAlerts: () => [mockAlert],
      };

      const ctx: DoctorContext = {
        senses: mockSenses,
      };

      const result = await currencyCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toContain('breaking');
      expect(result.remediation).toBe('re-ingest');
    });
  });

  describe('deprecation-warn', () => {
    it('should warn when deprecation affects ingested source', async () => {
      const mockAlert: ReleaseAlert = {
        event: {
          feedId: 'deprecation-feed',
          source: 'Deprecation Source',
          version: '2.5.0',
          publishedAt: new Date().toISOString(),
          url: 'https://example.com/deprecation-release',
          notes: 'Deprecated function X',
        },
        releaseClass: 'deprecation',
        relevance: 0.7,
        affectsIngested: true,
        ingestedSource: 'https://github.com/example/deprecated-lib',
        suggestedAction: 'review',
      };

      const mockSenses = {
        getAlerts: () => [mockAlert],
      };

      const ctx: DoctorContext = {
        senses: mockSenses,
      };

      const result = await currencyCheck(ctx);

      expect(result.status).toBe('warn');
      expect(result.detail).toContain('deprecation');
      expect(result.remediation).toBeDefined();
    });
  });
});
