/**
 * @shay/capabilities — importIngested tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { importIngested } from '../src/from-ingestion.js';
import { CapabilityRegistry } from '../src/registry.js';
import { TrustTier } from '@shay/core';
import { IngestedCapabilityStore } from '@shay/ingestion';

describe('importIngested', () => {
  let store: IngestedCapabilityStore;
  let registry: CapabilityRegistry;

  beforeEach(() => {
    store = new IngestedCapabilityStore();
    registry = new CapabilityRegistry();
  });

  it('imports entries from IngestedCapabilityStore into the registry', async () => {
    await store.ingest(
      { id: 'ext-cap', version: '1.0.0', name: 'External Cap', description: 'Test external' },
      { source: 'test-source', version: '1.0.0', ingestionDate: new Date().toISOString() }
    );

    importIngested(store, registry);
    expect(registry.has('ext-cap')).toBe(true);
  });

  it('tags imported entries as source:external with TrustTier.Suggest', async () => {
    await store.ingest(
      { id: 'ext-cap', version: '1.0.0', name: 'External Cap', description: 'Test external' },
      { source: 'test-source', version: '1.0.0', ingestionDate: new Date().toISOString() }
    );

    importIngested(store, registry);
    const record = registry.get('ext-cap');
    expect(record.source).toBe('external');
    expect(record.trustTier).toBe(TrustTier.Suggest);
  });

  it('imported capability handler throws on invoke (must use bridge)', async () => {
    await store.ingest(
      { id: 'ext-cap', version: '1.0.0', name: 'External Cap', description: 'Test external' },
      { source: 'test-source', version: '1.0.0', ingestionDate: new Date().toISOString() }
    );

    importIngested(store, registry);
    await expect(registry.invoke('ext-cap', 'run', {})).rejects.toThrow(/external ingested capability/);
  });

  it('skips already-registered IDs (idempotent import)', async () => {
    const manifest = { id: 'dup-cap', version: '1.0.0', name: 'Dup Cap', description: 'Duplicate test' };
    registry.register(manifest, async () => 'native-handler');

    await store.ingest(
      manifest,
      { source: 'test-source', version: '1.0.0', ingestionDate: new Date().toISOString() }
    );

    importIngested(store, registry);
    // The native internal handler should still be in place
    const result = await registry.invoke('dup-cap', 'any', {});
    expect(result).toBe('native-handler');
  });

  it('imports multiple entries', async () => {
    await store.ingest(
      [
        { id: 'a', version: '1.0.0', name: 'Cap A', description: 'A' },
        { id: 'b', version: '1.0.0', name: 'Cap B', description: 'B' },
      ],
      { source: 'batch-source', version: '1.0.0', ingestionDate: new Date().toISOString() }
    );

    importIngested(store, registry);
    expect(registry.has('a')).toBe(true);
    expect(registry.has('b')).toBe(true);
    expect(registry.list().length).toBe(2);
  });
});
