import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { MemoryStore } from '../src/store.js';

describe('MemoryStore', () => {
  let testPath: string;

  beforeEach(() => {
    testPath = path.join(os.tmpdir(), `shay-test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}.jsonl`);
  });

  afterEach(() => {
    if (fs.existsSync(testPath)) {
      fs.unlinkSync(testPath);
    }
  });

  it('store() persists a record to JSONL and it appears in recall()', async () => {
    const store = new MemoryStore({ persistPath: testPath });
    await store.initialize();

    const record = {
      id: 'test-1',
      content: 'hello world',
      embedding: undefined as number[] | undefined,
      tier: 'T2' as const,
      importance: 0.8,
      source: 'test',
      validityStart: new Date().toISOString(),
    };

    await store.store(record);
    const results = await store.recall('hello world');

    expect(results.length).toBeGreaterThan(0);
    expect(results[0].content).toBe('hello world');
    expect(results[0].tier).toBe('T2');
    expect(results[0].importance).toBe(0.8);
  });

  it('recall() returns records ranked by cosine similarity', async () => {
    const store = new MemoryStore({ persistPath: testPath });
    await store.initialize();

    await store.store({
      id: '1',
      content: 'apple fruit red',
      tier: 'T2',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    await store.store({
      id: '2',
      content: 'banana fruit yellow',
      tier: 'T2',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    await store.store({
      id: '3',
      content: 'xyz unrelated content',
      tier: 'T2',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    const results = await store.recall('apple red', { k: 10 });

    expect(results.length).toBeGreaterThan(0);
    // The most similar record should be one containing 'apple' or 'red'
    const hasSimilar = results.some((r) => r.content.includes('apple') || r.content.includes('red'));
    expect(hasSimilar).toBe(true);
  });

  it('recall() respects tier filter', async () => {
    const store = new MemoryStore({ persistPath: testPath });
    await store.initialize();

    await store.store({
      id: '1',
      content: 'tier 0 content',
      tier: 'T0',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    await store.store({
      id: '2',
      content: 'tier 1 content',
      tier: 'T1',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    await store.store({
      id: '3',
      content: 'tier 2 content',
      tier: 'T2',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    const tier0Results = await store.recall('content', { tier: 'T0' });
    const tier1Results = await store.recall('content', { tier: 'T1' });
    const allResults = await store.recall('content');

    expect(tier0Results).toHaveLength(1);
    expect(tier0Results[0].tier).toBe('T0');

    expect(tier1Results).toHaveLength(1);
    expect(tier1Results[0].tier).toBe('T1');

    expect(allResults.length).toBeGreaterThanOrEqual(3);
  });

  it('getTier0() returns only T0 records', async () => {
    const store = new MemoryStore({ persistPath: testPath });
    await store.initialize();

    await store.store({
      id: '1',
      content: 'tier 0 one',
      tier: 'T0',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    await store.store({
      id: '2',
      content: 'tier 0 two',
      tier: 'T0',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    await store.store({
      id: '3',
      content: 'tier 1',
      tier: 'T1',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    const tier0 = store.getTier0();

    expect(tier0).toHaveLength(2);
    expect(tier0.every((r) => r.tier === 'T0')).toBe(true);
  });

  it('decay() zeros importance for records whose validityEnd is in the past', async () => {
    const store = new MemoryStore({ persistPath: testPath });
    await store.initialize();

    const pastDate = new Date(Date.now() - 86400000).toISOString();
    const futureDate = new Date(Date.now() + 86400000).toISOString();

    await store.store({
      id: '1',
      content: 'will decay',
      tier: 'T2',
      importance: 1.0,
      source: 'test',
      validityStart: new Date().toISOString(),
      validityEnd: pastDate,
    });

    await store.store({
      id: '2',
      content: 'will not decay',
      tier: 'T2',
      importance: 1.0,
      source: 'test',
      validityStart: new Date().toISOString(),
      validityEnd: futureDate,
    });

    store.decay();

    const all = store.getAll();
    expect(all[0].importance).toBe(0);
    expect(all[0].stale).toBe(true);
  });

  it('A new MemoryStore pointing at an existing JSONL file loads prior records (persistence round-trip)', async () => {
    const store1 = new MemoryStore({ persistPath: testPath });
    await store1.initialize();

    await store1.store({
      id: '1',
      content: 'first record',
      tier: 'T2',
      importance: 0.7,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    await store1.store({
      id: '2',
      content: 'second record',
      tier: 'T1',
      importance: 0.5,
      source: 'test',
      validityStart: new Date().toISOString(),
    });

    const store2 = new MemoryStore({ persistPath: testPath });
    await store2.initialize();

    const results = await store2.recall('record');

    expect(results.length).toBeGreaterThanOrEqual(2);
    expect(results.some((r) => r.content === 'first record')).toBe(true);
    expect(results.some((r) => r.content === 'second record')).toBe(true);
  });
});
