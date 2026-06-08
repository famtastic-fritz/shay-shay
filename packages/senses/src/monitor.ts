/**
 * @shay/senses — ReleaseMonitor
 *
 * Orchestrates the full radar loop:
 *   registerFeed → poll → classify → scoreRelevance → linkToIngested → alert
 *
 * Emits 'senses:re-ingest-needed' on the EventBus whenever a release
 * overlaps with an ingested source.  Returns ReleaseAlert[] from poll().
 * digest() produces a sorted, human-readable summary string.
 */

import { randomUUID } from 'node:crypto';
import { EventBus, ShayEvent } from '@shay/core';
import type { ReleaseFeed, ReleaseEvent, ReleaseClass, ReleaseAlert } from './types.js';
import type { ReleaseFetcher } from './fetcher.js';

// ---------------------------------------------------------------------------
// Semver helpers
// ---------------------------------------------------------------------------

/**
 * Extracts the numeric major version from a version string.
 * Returns null when the string is not parseable.
 */
function parseMajor(version: string): number | null {
  const cleaned = version.replace(/^v/, '');
  const [majorStr] = cleaned.split('.');
  const major = parseInt(majorStr ?? '', 10);
  return isNaN(major) ? null : major;
}

// ---------------------------------------------------------------------------
// ReleaseMonitor
// ---------------------------------------------------------------------------

export class ReleaseMonitor {
  private readonly feeds: Map<string, ReleaseFeed> = new Map();
  /** Tracks the most-recently-seen version per feedId to deduplicate across poll cycles. */
  private readonly seen: Map<string, Set<string>> = new Map();
  private readonly eventBus: EventBus;
  private readonly emitSource: string;

  /**
   * @param eventBus   EventBus instance from @shay/core.
   * @param emitSource Source label attached to emitted ShayEvents (defaults to '@shay/senses').
   */
  constructor(eventBus: EventBus, emitSource = '@shay/senses') {
    this.eventBus = eventBus;
    this.emitSource = emitSource;
  }

  // -------------------------------------------------------------------------
  // Feed registration
  // -------------------------------------------------------------------------

  registerFeed(feed: ReleaseFeed): void {
    this.feeds.set(feed.id, feed);
    if (!this.seen.has(feed.id)) {
      this.seen.set(feed.id, new Set());
    }
  }

  // -------------------------------------------------------------------------
  // Poll
  // -------------------------------------------------------------------------

  /**
   * Fetches events from all registered feeds using the supplied fetcher,
   * classifies them, scores relevance against watched deps, links them to
   * ingested sources, emits bus events where required, and returns alerts.
   *
   * @param fetcher         Fetcher implementation (real or mock).
   * @param ingestedSources List of source identifiers currently held in the
   *                        IngestedCapabilityStore (pass [] if not available).
   */
  async poll(
    fetcher: ReleaseFetcher,
    ingestedSources: string[] = [],
  ): Promise<ReleaseAlert[]> {
    const alerts: ReleaseAlert[] = [];

    for (const feed of this.feeds.values()) {
      const events = await fetcher.fetch(feed);

      for (const event of events) {
        const seenSet = this.seen.get(feed.id)!;
        const key = `${event.version}::${event.publishedAt}`;
        if (seenSet.has(key)) continue;
        seenSet.add(key);

        const releaseClass = this.classify(event);
        const relevance = this.scoreRelevance(event, feed.watchedDeps ?? []);
        const alert = this.linkToIngested(
          { event, releaseClass, relevance, affectsIngested: false, suggestedAction: 'ignore' },
          ingestedSources,
        );

        if (alert.affectsIngested) {
          const busEvent: ShayEvent = {
            id: randomUUID(),
            type: 'senses:re-ingest-needed',
            payload: { feedId: event.feedId, source: event.source, version: event.version },
            timestamp: new Date().toISOString(),
            source: this.emitSource,
          };
          this.eventBus.emit(busEvent);
          alert.suggestedAction = 're-ingest';
        } else if (releaseClass === 'security' || releaseClass === 'breaking') {
          alert.suggestedAction = 'review';
        } else if (relevance > 0) {
          alert.suggestedAction = 'review';
        }

        alerts.push(alert);
      }
    }

    return alerts;
  }

  // -------------------------------------------------------------------------
  // Classification
  // -------------------------------------------------------------------------

  /**
   * Derives a ReleaseClass from keyword and semver heuristics applied to
   * the release notes and version string.  No external calls are made.
   *
   * Priority order (first match wins):
   *   1. 'security'    — notes contain 'security' or 'CVE' (case-insensitive)
   *   2. 'breaking'    — notes contain 'BREAKING' or version has a new major bump
   *   3. 'deprecation' — notes contain 'deprecat' (case-insensitive)
   *   4. 'feature'     — notes contain 'feat' or 'add' (case-insensitive)
   *   5. 'other'       — fallback
   */
  classify(event: ReleaseEvent): ReleaseClass {
    const text = `${event.version} ${event.notes ?? ''}`;

    if (/security|CVE/i.test(text)) return 'security';

    // Breaking: explicit keyword or a major-version bump (major >= 1, version starts new major)
    if (/BREAKING/i.test(text)) return 'breaking';
    const major = parseMajor(event.version);
    if (major !== null && major >= 1) {
      // Heuristic: if the version string starts exactly at a whole major (x.0.0)
      const cleaned = event.version.replace(/^v/, '');
      if (/^\d+\.0\.0/.test(cleaned)) return 'breaking';
    }

    if (/deprecat/i.test(text)) return 'deprecation';
    if (/feat|add/i.test(text)) return 'feature';

    return 'other';
  }

  // -------------------------------------------------------------------------
  // Relevance scoring
  // -------------------------------------------------------------------------

  /**
   * Scores relevance in [0, 1] based on how many watchedDeps appear in the
   * release notes or version string.
   *
   * Score = matched_count / total_watched  (or 0 when watchedDeps is empty).
   * Always returns 1 when no watchedDeps are provided (everything is relevant).
   */
  scoreRelevance(event: ReleaseEvent, watchedDeps: string[]): number {
    if (watchedDeps.length === 0) return 1;

    const haystack = `${event.source} ${event.version} ${event.notes ?? ''}`.toLowerCase();
    const matched = watchedDeps.filter((dep) =>
      haystack.includes(dep.toLowerCase()),
    ).length;

    return matched / watchedDeps.length;
  }

  // -------------------------------------------------------------------------
  // Ingested-source linkage
  // -------------------------------------------------------------------------

  /**
   * Checks whether the event's source matches any identifier in the list of
   * currently ingested sources and mutates the alert accordingly.
   * Matching is case-insensitive substring containment.
   */
  linkToIngested(
    alert: ReleaseAlert,
    ingestedSources: string[],
  ): ReleaseAlert {
    const sourceLower = alert.event.source.toLowerCase();
    const match = ingestedSources.find((s) =>
      sourceLower.includes(s.toLowerCase()) || s.toLowerCase().includes(sourceLower),
    );

    if (match !== undefined) {
      alert.affectsIngested = true;
      alert.ingestedSource = match;
    }

    return alert;
  }

  // -------------------------------------------------------------------------
  // Digest
  // -------------------------------------------------------------------------

  /**
   * Produces a human-readable summary of alerts sorted by:
   *   1. suggestedAction priority  ('re-ingest' > 'review' > 'ignore')
   *   2. releaseClass priority     (security > breaking > deprecation > feature > other)
   *   3. relevance descending
   *
   * Returns a multi-line string suitable for console output or a status panel.
   */
  digest(alerts: ReleaseAlert[]): string {
    const actionOrder: Record<string, number> = { 're-ingest': 0, review: 1, ignore: 2 };
    const classOrder: Record<string, number> = {
      security: 0, breaking: 1, deprecation: 2, feature: 3, other: 4,
    };

    const sorted = [...alerts].sort((a, b) => {
      const actionDiff = (actionOrder[a.suggestedAction] ?? 9) - (actionOrder[b.suggestedAction] ?? 9);
      if (actionDiff !== 0) return actionDiff;

      const classDiff = (classOrder[a.releaseClass] ?? 9) - (classOrder[b.releaseClass] ?? 9);
      if (classDiff !== 0) return classDiff;

      return b.relevance - a.relevance;
    });

    if (sorted.length === 0) return '(no new releases)';

    return sorted
      .map(
        (a) =>
          `[${a.suggestedAction.toUpperCase()}] ${a.event.source} ${a.event.version}` +
          ` (${a.releaseClass}, relevance=${a.relevance.toFixed(2)})` +
          (a.affectsIngested ? ` — ingested: ${a.ingestedSource}` : ''),
      )
      .join('\n');
  }
}
