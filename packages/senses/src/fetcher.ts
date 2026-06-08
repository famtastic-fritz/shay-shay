/**
 * @shay/senses — Fetcher interface and implementations
 *
 * Defines ReleaseFetcher (interface), GithubReleasesFetcher (real implementation
 * backed by an injected httpGet function), and MockFetcher (hermetic test double).
 *
 * No live network I/O is performed by default — all outbound calls are routed
 * through the injected httpGet dependency.
 */

import type { ReleaseFeed, ReleaseEvent } from './types.js';

// ---------------------------------------------------------------------------
// Fetcher interface
// ---------------------------------------------------------------------------

/**
 * Strategy interface for retrieving ReleaseEvents from a feed.
 * Implementations are injected into ReleaseMonitor.poll().
 */
export interface ReleaseFetcher {
  fetch(feed: ReleaseFeed): Promise<ReleaseEvent[]>;
}

// ---------------------------------------------------------------------------
// GitHub Releases fetcher
// ---------------------------------------------------------------------------

/**
 * Shape of a single item returned by the GitHub Releases REST API.
 * Only the fields we map are typed here.
 */
interface GithubReleaseItem {
  tag_name?: string;
  name?: string;
  published_at?: string;
  html_url?: string;
  body?: string;
}

/**
 * Fetches releases from the GitHub Releases API.
 *
 * @param httpGet - Injected HTTP GET function.
 *   Signature: (url: string) => Promise<string>
 *   The response body must be valid JSON.  Pass a real fetch wrapper in
 *   production; pass a stub in tests.
 *
 * Only handles feeds with kind === 'github'.
 * Returns an empty array for unsupported kinds or unparsable responses.
 */
export class GithubReleasesFetcher implements ReleaseFetcher {
  constructor(private readonly httpGet: (url: string) => Promise<string>) {}

  async fetch(feed: ReleaseFeed): Promise<ReleaseEvent[]> {
    if (feed.kind !== 'github') {
      return [];
    }

    let raw: string;
    try {
      raw = await this.httpGet(feed.url);
    } catch {
      return [];
    }

    let items: GithubReleaseItem[];
    try {
      items = JSON.parse(raw) as GithubReleaseItem[];
      if (!Array.isArray(items)) return [];
    } catch {
      return [];
    }

    return items.map((item): ReleaseEvent => ({
      feedId: feed.id,
      source: feed.source,
      version: item.tag_name ?? item.name ?? 'unknown',
      publishedAt: item.published_at ?? new Date(0).toISOString(),
      url: item.html_url ?? feed.url,
      notes: item.body ?? undefined,
    }));
  }
}

// ---------------------------------------------------------------------------
// Mock fetcher (hermetic test double)
// ---------------------------------------------------------------------------

/**
 * Hermetic test double for ReleaseFetcher.
 * Returns a pre-configured list of events regardless of the feed passed in.
 * Safe to use in unit tests — performs no network I/O.
 */
export class MockFetcher implements ReleaseFetcher {
  private readonly events: ReleaseEvent[];

  constructor(events: ReleaseEvent[]) {
    this.events = events;
  }

  async fetch(_feed: ReleaseFeed): Promise<ReleaseEvent[]> {
    return [...this.events];
  }
}
