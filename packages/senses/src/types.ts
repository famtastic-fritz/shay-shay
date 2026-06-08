/**
 * @shay/senses — Core domain types
 *
 * Defines the data shapes for the Release Monitor / Radar:
 * feed configuration, raw release events, classification labels,
 * and actionable alerts that may trigger downstream re-ingestion.
 */

/**
 * A configured upstream feed that the monitor watches.
 * `kind` controls which fetcher strategy is applied.
 * `watchedDeps` narrows relevance scoring to specific dependency names
 * within the source (e.g. package names inside a monorepo release).
 */
export interface ReleaseFeed {
  /** Stable identifier; used as a correlation key across poll cycles. */
  id: string;
  /** Human-readable label for the upstream source. */
  source: string;
  /** Canonical URL for the feed (GitHub releases API endpoint, RSS/Atom URL, or changelog URL). */
  url: string;
  /** Fetch strategy selector. */
  kind: 'github' | 'rss' | 'changelog';
  /** Optional list of dependency/package names to match inside this feed's releases. */
  watchedDeps?: string[];
}

/**
 * A single release discovered from a feed.
 */
export interface ReleaseEvent {
  /** ID of the originating feed. */
  feedId: string;
  /** Denormalized source label copied from the feed for convenience. */
  source: string;
  /** Version string as published (e.g. "v2.1.0", "2.1.0"). */
  version: string;
  /** ISO-8601 publish timestamp. */
  publishedAt: string;
  /** Canonical URL for the release page or entry. */
  url: string;
  /** Release notes body text, if available. */
  notes?: string;
}

/**
 * Semantic classification of a release.
 * Derived from keyword and semver heuristics — not AI-assisted.
 */
export type ReleaseClass =
  | 'security'
  | 'feature'
  | 'breaking'
  | 'deprecation'
  | 'other';

/**
 * An enriched, actionable summary of a release event.
 * Produced by ReleaseMonitor after classification, relevance scoring,
 * and ingestion linkage checks.
 */
export interface ReleaseAlert {
  /** The underlying release event that triggered this alert. */
  event: ReleaseEvent;
  /** Semantic classification of the release. */
  releaseClass: ReleaseClass;
  /**
   * Relevance score in [0, 1].
   * Higher = more relevant to currently ingested capabilities.
   */
  relevance: number;
  /** True when the release source overlaps with an ingested capability source. */
  affectsIngested: boolean;
  /** The matched ingested source identifier, when affectsIngested is true. */
  ingestedSource?: string;
  /**
   * Recommended follow-up action.
   * 're-ingest'  — source has changed; re-run ingestion to stay current.
   * 'review'     — notable change; manual review advised.
   * 'ignore'     — low-relevance or routine patch; safe to skip.
   */
  suggestedAction: 're-ingest' | 'review' | 'ignore';
}
