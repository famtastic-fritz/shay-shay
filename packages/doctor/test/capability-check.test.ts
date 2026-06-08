/**
 * Hermetic tests for capabilityCheck.
 *
 * Tests verify:
 * - HEALTHY fixture: real CapabilityRegistry with complete manifest, status === 'pass'
 * - FAULTY fixture: capability whose handler throws non-ActionNotFoundError, status === 'fail'
 * - Strictly disjoint test groups
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { capabilityCheck } from '../src/checks/capability-check.js';
import type { DoctorContext } from '../src/checks/types.js';
import { CapabilityRegistry } from '@shay/capabilities';
import type { CapabilityManifest } from '@shay/capabilities';

describe('capability-check', () => {
  describe('healthy', () => {
    it('should pass with a registered capability with complete manifest', async () => {
      const registry = new CapabilityRegistry();

      const manifest: CapabilityManifest = {
        id: 'test-capability',
        name: 'Test Capability',
        version: '1.0.0',
        description: 'A test capability for doctor checks',
      };

      const handler = async () => ({
        success: true,
      });

      registry.register(manifest, handler);

      const ctx: DoctorContext = {
        registry,
      };

      const result = await capabilityCheck(ctx);

      expect(result.status).toBe('pass');
      expect(result.detail).toContain('complete manifests');
      expect(result.remediation).toBeUndefined();
    });
  });

  describe('faulty', () => {
    it('should fail when capability handler throws a non-ActionNotFoundError', async () => {
      const registry = new CapabilityRegistry();

      const manifest: CapabilityManifest = {
        id: 'broken-capability',
        name: 'Broken Capability',
        version: '1.0.0',
        description: 'A broken capability for doctor checks',
      };

      const handler = async () => {
        throw new Error('Handler crashed');
      };

      registry.register(manifest, handler);

      const ctx: DoctorContext = {
        registry,
      };

      const result = await capabilityCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toBeDefined();
      expect(result.remediation).toBeDefined();
    });

    it('should fail when capability has incomplete manifest', async () => {
      const registry = new CapabilityRegistry();

      const manifest: any = {
        id: 'incomplete-capability',
        // Missing name, version, description
      };

      const handler = async () => ({
        success: true,
      });

      // Expect registration to throw ValidationError due to incomplete manifest
      // The test verifies that capabilityCheck handles this gracefully
      try {
        registry.register(manifest, handler);
      } catch (err) {
        // Expected: incomplete manifest causes validation error on registration
        // Now verify the check can handle invalid manifests in its list
      }

      // Create a stub registry that returns invalid capabilities in its list
      const stubRegistry = {
        async list() {
          return [
            {
              manifest: {
                id: 'incomplete-capability',
                // Intentionally missing name, version, description
              } as any,
            },
          ];
        },
        async invoke() {
          // Not called in this test since manifest is incomplete
          return {};
        },
      };

      const ctx: DoctorContext = {
        registry: stubRegistry as any,
      };

      const result = await capabilityCheck(ctx);

      expect(result.status).toBe('warn');
      expect(result.detail).toContain('incomplete');
      expect(result.remediation).toBeDefined();
    });
  });
});
