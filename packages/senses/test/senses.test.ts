/**
 * @shay/senses — Hermetic test suite
 *
 * 27 vitest tests across 5 strictly-disjoint groups:
 *   1. Poll returns and deduplicates events (7 tests)
 *   2. Classify heuristics (security/CVE, BREAKING, major.0.0, deprecat, feat/add) (10 tests)
 *   3. scoreRelevance edge cases (empty deps=1, all match=1, no match=0, partial fraction) (7 tests)
 *   4. affectsIngested — emits 'senses:re-ingest-needed', sets suggestedAction, populates ingestedSource (4 tests)
 *   5. digest ordering (re-ingest > review > ignore; security > breaking > feature; ingested label) (5 tests)
 *
 * All hermetic — MockFetcher, no network calls.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { EventBus, SchemaRegistry } from '@shay/core';
import { MockFetcher } from '../src/fetcher.js';
import { ReleaseMonitor } from '../src/monitor.js';
import type { ReleaseFeed, ReleaseEvent, ReleaseAlert } from '../src/types.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const schemasDir = path.resolve(__dirname, '../../../schemas');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeRegistry(): SchemaRegistry {
  const r = new SchemaRegistry();
  r.loadFromDir(schemasDir);
  return r;
}

function makeBus(logPath: string): EventBus {
  return new EventBus(makeRegistry(), logPath);
}

function tmpLog(): string {
  return path.join(os.tmpdir(), `senses-test-${Date.now()}-${Math.random().toString(36).slice(2)}.jsonl`);
}

function makeEvent(overrides: Partial<ReleaseEvent> = {}): ReleaseEvent {
  return {
    feedId: 'test-feed',
    source: 'test-source',
    version: '1.2.3',
    publishedAt: '2026-06-08T00:00:00Z',
    url: 'https://example.com/releases/v1.2.3',
    notes: 'minor improvements',
    ...overrides,
  };
}

function makeAlert(
  overrides: Partial<ReleaseAlert> & { eventOverrides?: Partial<ReleaseEvent> } = {},
): ReleaseAlert {
  const { eventOverrides = {}, ...rest } = overrides;
  return {
    event: makeEvent(eventOverrides),
    releaseClass: 'other',
    relevance: 0.5,
    affectsIngested: false,
    suggestedAction: 'ignore',
    ...rest,
  };
}

// ===========================================================================
// GROUP 1: Poll returns and deduplicates events (7 tests)
// ===========================================================================

describe('GROUP 1: Poll returns and deduplicates events', () => {
  let logPath: string;
  let bus: EventBus;
  let monitor: ReleaseMonitor;

  beforeEach(() => {
    logPath = tmpLog();
    bus = makeBus(logPath);
    monitor = new ReleaseMonitor(bus);
  });

  afterEach(() => {
    if (fs.existsSync(logPath)) fs.unlinkSync(logPath);
  });

  it('should return empty array when no feeds are registered', async () => {
    const fetcher = new MockFetcher([]);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts).toEqual([]);
  });

  it('should return alerts from a single feed', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'TestLib', version: 'v1.0.0' }),
    ]);
    const alerts = await monitor.poll(fetcher, []);

    expect(alerts).toHaveLength(1);
    expect(alerts[0].event.version).toBe('v1.0.0');
  });

  it('should deduplicate events by version + publishedAt across poll cycles', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'TestLib', version: 'v1.0.0' }),
    ]);

    const alerts1 = await monitor.poll(fetcher, []);
    expect(alerts1).toHaveLength(1);

    const alerts2 = await monitor.poll(fetcher, []);
    expect(alerts2).toHaveLength(0);
  });

  it('should NOT deduplicate different versions of same source', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'TestLib', version: 'v1.0.0', publishedAt: '2026-01-01T00:00:00Z' }),
      makeEvent({ feedId: 'feed1', source: 'TestLib', version: 'v1.0.1', publishedAt: '2026-01-02T00:00:00Z' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts).toHaveLength(2);
    expect(alerts.map((a) => a.event.version)).toEqual(['v1.0.0', 'v1.0.1']);
  });

  it('should handle multiple feeds', async () => {
    // Register two feeds
    const feed1: ReleaseFeed = {
      id: 'feed1',
      source: 'LibA',
      url: 'https://example.com/liba',
      kind: 'github',
    };
    const feed2: ReleaseFeed = {
      id: 'feed2',
      source: 'LibB',
      url: 'https://example.com/libb',
      kind: 'github',
    };
    monitor.registerFeed(feed1);
    monitor.registerFeed(feed2);

    // MockFetcher returns the same events regardless of which feed
    // So when poll() iterates feed1 and feed2, each gets the same 2 events
    // = 4 total (but deduplicated). Test that we get events from the fetcher.
    const event1 = makeEvent({ feedId: 'feed1', source: 'LibA', version: 'v1.0.0' });
    const fetcher = new MockFetcher([event1]);

    const alerts = await monitor.poll(fetcher, []);
    // Fetcher returns 1 event, monitor polls 2 feeds (same events), so 2 alerts
    expect(alerts).toHaveLength(2);
    expect(alerts[0].event.source).toBe('LibA');
    expect(alerts[1].event.source).toBe('LibA');
  });

  it('should deduplicate within a single poll when same event returned twice', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const event = makeEvent({ feedId: 'feed1', source: 'TestLib', version: 'v1.0.0' });
    const fetcher = new MockFetcher([event, event]);
    const alerts = await monitor.poll(fetcher, []);

    expect(alerts).toHaveLength(1);
  });

  it('should preserve insertion order of alerts', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'TestLib', version: 'v1.0.0', publishedAt: '2026-01-01T00:00:00Z' }),
      makeEvent({ feedId: 'feed1', source: 'TestLib', version: 'v1.0.1', publishedAt: '2026-01-02T00:00:00Z' }),
      makeEvent({ feedId: 'feed1', source: 'TestLib', version: 'v1.0.2', publishedAt: '2026-01-03T00:00:00Z' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts.map((a) => a.event.version)).toEqual(['v1.0.0', 'v1.0.1', 'v1.0.2']);
  });
});

// ===========================================================================
// GROUP 2: Classify heuristics (security/CVE, BREAKING, major.0.0, deprecat, feat/add) (10 tests)
// ===========================================================================

describe('GROUP 2: Classify heuristics', () => {
  let logPath: string;
  let bus: EventBus;
  let monitor: ReleaseMonitor;

  beforeEach(() => {
    logPath = tmpLog();
    bus = makeBus(logPath);
    monitor = new ReleaseMonitor(bus);
  });

  afterEach(() => {
    if (fs.existsSync(logPath)) fs.unlinkSync(logPath);
  });

  it('should classify as security when notes contain "security"', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ notes: 'Fixed critical security vulnerability' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('security');
  });

  it('should classify as security when notes contain "CVE"', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ notes: 'Patched CVE-2026-12345' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('security');
  });

  it('should classify as breaking when notes contain "BREAKING"', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: 'v2.0.0', notes: 'BREAKING: Removed deprecated APIs' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('breaking');
  });

  it('should classify as breaking when version is x.0.0 (major bump >= 1)', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: 'v3.0.0', notes: 'Major version bump' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('breaking');
  });

  it('should classify as breaking for x.0.0 without v prefix', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: '2.0.0', notes: '' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('breaking');
  });

  it('should classify as deprecation when notes contain "deprecat"', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: 'v1.5.0', notes: 'Deprecated old API endpoint' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('deprecation');
  });

  it('should classify as feature when notes contain "feat"', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: 'v1.3.0', notes: 'feat: added streaming API' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('feature');
  });

  it('should classify as feature when notes contain "add"', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: 'v1.2.0', notes: 'Add support for HTTP/2' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('feature');
  });

  it('should classify as other when no keywords match', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: 'v1.0.5', notes: 'Bug fixes and improvements' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('other');
  });

  it('should prioritize security over breaking in classification', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: 'v2.0.0', notes: 'Security patch and BREAKING changes' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('security');
  });

  it('should use case-insensitive matching for keywords', async () => {
    const fetcher = new MockFetcher([
      makeEvent({ version: 'v1.1.0', notes: 'Deprecation notice: this API will be removed' }),
    ]);
    const feed: ReleaseFeed = { id: 'f1', source: 'Lib', url: 'https://example.com', kind: 'github' };
    monitor.registerFeed(feed);
    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].releaseClass).toBe('deprecation');
  });
});

// ===========================================================================
// GROUP 3: scoreRelevance edge cases (empty deps=1, all match=1, no match=0, partial fraction) (7 tests)
// ===========================================================================

describe('GROUP 3: scoreRelevance edge cases', () => {
  let logPath: string;
  let bus: EventBus;
  let monitor: ReleaseMonitor;

  beforeEach(() => {
    logPath = tmpLog();
    bus = makeBus(logPath);
    monitor = new ReleaseMonitor(bus);
  });

  afterEach(() => {
    if (fs.existsSync(logPath)) fs.unlinkSync(logPath);
  });

  it('should return 1 when watchedDeps is empty', async () => {
    const feed: ReleaseFeed = {
      id: 'f1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
      watchedDeps: [],
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ notes: 'Some release' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].relevance).toBe(1);
  });

  it('should return 1 when all watchedDeps are found', async () => {
    const feed: ReleaseFeed = {
      id: 'f1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
      watchedDeps: ['react', 'typescript'],
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ notes: 'Updated React and TypeScript' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].relevance).toBe(1);
  });

  it('should return 0 when no watchedDeps are found', async () => {
    const feed: ReleaseFeed = {
      id: 'f1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
      watchedDeps: ['redis', 'postgres'],
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ notes: 'Updated Node.js support' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].relevance).toBe(0);
  });

  it('should return fractional relevance when some deps match', async () => {
    const feed: ReleaseFeed = {
      id: 'f1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
      watchedDeps: ['react', 'vue', 'angular'],
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ notes: 'Updated React and Vue' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].relevance).toBeCloseTo(2 / 3);
  });

  it('should use case-insensitive matching for deps', async () => {
    const feed: ReleaseFeed = {
      id: 'f1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
      watchedDeps: ['React'],
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ notes: 'Updated react' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].relevance).toBe(1);
  });

  it('should match deps in version string', async () => {
    const feed: ReleaseFeed = {
      id: 'f1',
      source: 'next',
      url: 'https://example.com/releases',
      kind: 'github',
      watchedDeps: ['next'],
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ version: 'v14.0.0-next.1' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].relevance).toBe(1);
  });

  it('should return 0.5 when exactly half of deps match', async () => {
    const feed: ReleaseFeed = {
      id: 'f1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
      watchedDeps: ['dep1', 'dep2'],
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ notes: 'Updated dep1' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    expect(alerts[0].relevance).toBe(0.5);
  });
});

// ===========================================================================
// GROUP 4: affectsIngested — emit senses:re-ingest-needed, alert.suggestedAction, ingestedSource (4 tests)
// ===========================================================================

describe('GROUP 4: affectsIngested — EventBus emission and alert mutation', () => {
  let logPath: string;
  let bus: EventBus;
  let monitor: ReleaseMonitor;

  beforeEach(() => {
    logPath = tmpLog();
    bus = makeBus(logPath);
    monitor = new ReleaseMonitor(bus, '@shay/senses');
  });

  afterEach(() => {
    if (fs.existsSync(logPath)) fs.unlinkSync(logPath);
  });

  it('should emit senses:re-ingest-needed when release affects an ingested source', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'React',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    let eventEmitted = false;
    bus.subscribe('senses:re-ingest-needed', (event) => {
      expect(event.type).toBe('senses:re-ingest-needed');
      expect(event.payload.source).toBe('React');
      expect(event.payload.version).toBe('v18.0.0');
      expect(event.source).toBe('@shay/senses');
      eventEmitted = true;
    });

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'React', version: 'v18.0.0' }),
    ]);

    await monitor.poll(fetcher, ['React']);
    expect(eventEmitted).toBe(true);
  });

  it('should set suggestedAction to re-ingest when affectsIngested is true', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'Vue',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'Vue', version: 'v3.3.0' }),
    ]);

    const alerts = await monitor.poll(fetcher, ['Vue']);

    expect(alerts[0].affectsIngested).toBe(true);
    expect(alerts[0].suggestedAction).toBe('re-ingest');
  });

  it('should populate ingestedSource when match is found', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'TypeScript',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'TypeScript', version: 'v5.0.0' }),
    ]);

    const alerts = await monitor.poll(fetcher, ['TypeScript']);

    expect(alerts[0].ingestedSource).toBe('TypeScript');
  });

  it('should not emit when release does not affect ingested sources', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'UnrelatedLib',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    let eventEmitted = false;
    bus.subscribe('senses:re-ingest-needed', () => {
      eventEmitted = true;
    });

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'UnrelatedLib', version: 'v1.0.0' }),
    ]);

    await monitor.poll(fetcher, ['React', 'Vue']);
    expect(eventEmitted).toBe(false);
  });
});

// ===========================================================================
// GROUP 5: digest ordering (re-ingest > review > ignore; security > breaking; ingested label) (5 tests)
// ===========================================================================

describe('GROUP 5: digest ordering and ingested labels', () => {
  let logPath: string;
  let bus: EventBus;
  let monitor: ReleaseMonitor;

  beforeEach(() => {
    logPath = tmpLog();
    bus = makeBus(logPath);
    monitor = new ReleaseMonitor(bus);
  });

  afterEach(() => {
    if (fs.existsSync(logPath)) fs.unlinkSync(logPath);
  });

  it('should sort by suggestedAction: re-ingest first', async () => {
    const feed1: ReleaseFeed = {
      id: 'feed1',
      source: 'IngestedLib',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    const feed2: ReleaseFeed = {
      id: 'feed2',
      source: 'OtherLib',
      url: 'https://example.com/other',
      kind: 'github',
    };
    monitor.registerFeed(feed1);
    monitor.registerFeed(feed2);

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'IngestedLib', version: 'v1.0.0', publishedAt: '2026-01-01T00:00:00Z', notes: 'release' }),
      makeEvent({ feedId: 'feed2', source: 'OtherLib', version: 'v2.0.0', publishedAt: '2026-01-02T00:00:00Z', notes: 'Security fix' }),
    ]);

    // IngestedLib affects ingested -> re-ingest
    // OtherLib is security but doesn't affect ingested -> review
    const alerts = await monitor.poll(fetcher, ['IngestedLib']);
    const digest = monitor.digest(alerts);

    const lines = digest.split('\n');
    const reIngestLine = lines.find((l) => l.includes('[RE-INGEST]'));
    const reviewLine = lines.find((l) => l.includes('[REVIEW]'));

    expect(reIngestLine).toBeDefined();
    expect(reviewLine).toBeDefined();
    expect(lines.indexOf(reIngestLine!)).toBeLessThan(lines.indexOf(reviewLine!));
  });

  it('should sort by releaseClass within same action: security first', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ version: 'v1.1.0', publishedAt: '2026-01-01T00:00:00Z', notes: 'New feature' }),
      makeEvent({ version: 'v1.1.1', publishedAt: '2026-01-02T00:00:00Z', notes: 'Security patch' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    const digest = monitor.digest(alerts);

    const lines = digest.split('\n');
    const securityLine = lines.find((l) => l.includes('security'));
    const featureLine = lines.find((l) => l.includes('feature'));

    expect(securityLine).toBeDefined();
    expect(featureLine).toBeDefined();
    expect(lines.indexOf(securityLine!)).toBeLessThan(lines.indexOf(featureLine!));
  });

  it('should sort by relevance descending within same action and class', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'TestLib',
      url: 'https://example.com/releases',
      kind: 'github',
      watchedDeps: ['dep1', 'dep2', 'dep3'],
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ version: 'v1.1.0', publishedAt: '2026-01-01T00:00:00Z', notes: 'Updated dep1' }),
      makeEvent({ version: 'v1.1.1', publishedAt: '2026-01-02T00:00:00Z', notes: 'Updated dep1 and dep2' }),
    ]);

    const alerts = await monitor.poll(fetcher, []);
    const digest = monitor.digest(alerts);

    const lines = digest.split('\n');
    expect(lines[0]).toContain('v1.1.1');
    expect(lines[1]).toContain('v1.1.0');
  });

  it('should include ingested label when affectsIngested is true', async () => {
    const feed: ReleaseFeed = {
      id: 'feed1',
      source: 'React',
      url: 'https://example.com/releases',
      kind: 'github',
    };
    monitor.registerFeed(feed);

    const fetcher = new MockFetcher([
      makeEvent({ feedId: 'feed1', source: 'React', version: 'v18.0.0' }),
    ]);

    const alerts = await monitor.poll(fetcher, ['React']);
    const digest = monitor.digest(alerts);

    expect(digest).toContain('ingested: React');
  });

  it('should return (no new releases) for empty alerts', () => {
    const digest = monitor.digest([]);
    expect(digest).toBe('(no new releases)');
  });
});
