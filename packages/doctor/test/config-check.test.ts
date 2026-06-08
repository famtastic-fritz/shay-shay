/**
 * Hermetic tests for configCheck.
 *
 * Tests verify:
 * - HEALTHY fixture: SchemaRegistry loaded with config.schema.json, valid config object, status === 'pass'
 * - FAULTY fixture: config missing required 'name' field, status === 'fail'
 * - Strictly disjoint test groups
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { configCheck } from '../src/checks/config-check.js';
import type { DoctorContext } from '../src/checks/types.js';
import { SchemaRegistry } from '@shay/core';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

describe('config-check', () => {
  describe('healthy', () => {
    let schemaRegistry: SchemaRegistry;

    beforeEach(() => {
      schemaRegistry = new SchemaRegistry();

      // Load the config schema from the schemas directory
      const __filename = fileURLToPath(import.meta.url);
      const __dirname = path.dirname(__filename);
      const schemasDir = path.resolve(__dirname, '../../../schemas');

      schemaRegistry.loadFromDir(schemasDir);
    });

    it('should pass with valid config object', async () => {
      const validConfig = {
        version: '1.0.0',
        name: 'shay',
        description: 'Shay AI Boss',
      };

      const ctx: DoctorContext = {
        config: validConfig,
        schemaRegistry,
      };

      const result = await configCheck(ctx);

      expect(result.status).toBe('pass');
      expect(result.detail).toBeDefined();
      expect(result.remediation).toBeUndefined();
    });
  });

  describe('faulty', () => {
    let schemaRegistry: SchemaRegistry;

    beforeEach(() => {
      schemaRegistry = new SchemaRegistry();

      // Load the config schema from the schemas directory
      const __filename = fileURLToPath(import.meta.url);
      const __dirname = path.dirname(__filename);
      const schemasDir = path.resolve(__dirname, '../../../schemas');

      schemaRegistry.loadFromDir(schemasDir);
    });

    it('should fail when config is missing required name field', async () => {
      const invalidConfig: any = {
        version: '1.0.0',
        // Missing required 'name' field
      };

      const ctx: DoctorContext = {
        config: invalidConfig,
        schemaRegistry,
      };

      const result = await configCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toContain('validation');
      expect(result.remediation).toBeDefined();
    });

    it('should fail when config is missing required version field', async () => {
      const invalidConfig: any = {
        name: 'shay',
        // Missing required 'version' field
      };

      const ctx: DoctorContext = {
        config: invalidConfig,
        schemaRegistry,
      };

      const result = await configCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toContain('validation');
      expect(result.remediation).toBeDefined();
    });

    it('should fail when schemaRegistry is not provided', async () => {
      const validConfig = {
        version: '1.0.0',
        name: 'shay',
      };

      const ctx: DoctorContext = {
        config: validConfig,
        schemaRegistry: undefined,
      };

      const result = await configCheck(ctx);

      expect(result.status).toBe('warn');
      expect(result.detail).toContain('not provided');
    });
  });
});
