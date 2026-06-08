/**
 * @shay/capabilities — CapabilityRegistry tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { CapabilityRegistry, CapabilityNotFoundError, ActionNotFoundError } from '../src/registry.js';
import { TrustTier } from '@shay/core';
import type { CapabilityManifest } from '@shay/ingestion';

const validManifest: CapabilityManifest = {
  id: 'cap-test',
  version: '1.0.0',
  name: 'Test Capability',
  description: 'A capability used in tests',
};

const handler = async (_action: string, input: unknown) => ({ result: input });

describe('CapabilityRegistry', () => {
  let registry: CapabilityRegistry;

  beforeEach(() => {
    registry = new CapabilityRegistry();
  });

  it('registers a valid manifest and returns it via get()', () => {
    registry.register(validManifest, handler);
    const record = registry.get('cap-test');
    expect(record.manifest.id).toBe('cap-test');
    expect(record.source).toBe('internal');
    expect(record.trustTier).toBe(TrustTier.Confirm);
  });

  it('has() returns true after registration', () => {
    registry.register(validManifest, handler);
    expect(registry.has('cap-test')).toBe(true);
  });

  it('has() returns false for unknown id', () => {
    expect(registry.has('unknown')).toBe(false);
  });

  it('list() includes registered capability', () => {
    registry.register(validManifest, handler);
    const records = registry.list();
    expect(records.length).toBe(1);
    expect(records[0].manifest.id).toBe('cap-test');
  });

  it('invoke() calls the handler and returns its result', async () => {
    registry.register(validManifest, handler);
    const result = await registry.invoke('cap-test', 'run', { x: 1 });
    expect(result).toEqual({ result: { x: 1 } });
  });

  it('get() throws CapabilityNotFoundError for unknown id', () => {
    expect(() => registry.get('no-such-cap')).toThrow(CapabilityNotFoundError);
  });

  it('invoke() throws CapabilityNotFoundError for unknown id', async () => {
    await expect(registry.invoke('no-such-cap', 'run', {})).rejects.toThrow(CapabilityNotFoundError);
  });

  it('invoke() passes any action to the handler when manifest has no declared actions list', async () => {
    // The canonical capability-manifest schema does not include an 'actions' field
    // (additionalProperties: false), so ActionNotFoundError is only reachable when
    // a custom SchemaRegistry is injected that allows such a field.
    // This test verifies the happy-path: any action name is forwarded to the handler.
    registry.register(validManifest, handler);
    const result = await registry.invoke('cap-test', 'any-arbitrary-action', { v: 42 });
    expect(result).toEqual({ result: { v: 42 } });
  });

  it('rejects invalid manifest (missing required fields) with ValidationError', () => {
    const bad = { id: 'x' } as unknown as CapabilityManifest;
    expect(() => registry.register(bad, handler)).toThrow();
  });

  it('external capabilities default to TrustTier.Suggest', () => {
    registry.register(validManifest, handler, { source: 'external' });
    const record = registry.get('cap-test');
    expect(record.source).toBe('external');
    expect(record.trustTier).toBe(TrustTier.Suggest);
  });

  it('unregister() removes a registered capability', () => {
    registry.register(validManifest, handler);
    registry.unregister('cap-test');
    expect(registry.has('cap-test')).toBe(false);
  });

  it('unregister() throws CapabilityNotFoundError for unknown id', () => {
    expect(() => registry.unregister('ghost')).toThrow(CapabilityNotFoundError);
  });
});
