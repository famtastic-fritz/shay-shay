/**
 * @shay/senses — Public API barrel
 *
 * Release Monitor / "stay current" Radar.
 * Exports all public types, interfaces, classes, and data for external use.
 */

export type { ReleaseFeed, ReleaseEvent, ReleaseClass, ReleaseAlert } from './types.js';
export type { ReleaseFetcher } from './fetcher.js';
export { GithubReleasesFetcher, MockFetcher } from './fetcher.js';
export { ReleaseMonitor } from './monitor.js';
export { DEFAULT_WATCHLIST } from './watchlist.js';
