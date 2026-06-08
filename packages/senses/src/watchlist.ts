/**
 * @shay/senses — Default watchlist
 *
 * Static data-only module.  Exports DEFAULT_WATCHLIST, a curated array of
 * ReleaseFeed entries covering the upstream dependencies and protocols that
 * the @shay ecosystem depends on or monitors.
 *
 * No logic lives here — purely a feed registry seed.
 */

import type { ReleaseFeed } from './types.js';

/**
 * Curated list of upstream feeds the Release Radar watches by default.
 *
 * Covers:
 *   - AI model providers (anthropic/claude-code, openai/codex)
 *   - Community model hubs (nous-research/hermes)
 *   - Protocol specs (modelcontextprotocol, google/a2a)
 *   - Deployment infrastructure (netlify/cli)
 *   - @shay internal packages (core, memory, brain, ingestion, capabilities, bridge, senses, doctor, surfaces)
 */
export const DEFAULT_WATCHLIST: ReleaseFeed[] = [
  // -------------------------------------------------------------------------
  // AI model providers
  // -------------------------------------------------------------------------
  {
    id: 'anthropic-claude-code',
    source: 'anthropic/claude-code',
    url: 'https://api.github.com/repos/anthropics/claude-code/releases',
    kind: 'github',
    watchedDeps: ['claude-code', 'anthropic'],
  },
  {
    id: 'openai-codex',
    source: 'openai/codex',
    url: 'https://api.github.com/repos/openai/codex/releases',
    kind: 'github',
    watchedDeps: ['codex', 'openai'],
  },
  // -------------------------------------------------------------------------
  // Community model hubs
  // -------------------------------------------------------------------------
  {
    id: 'nous-hermes',
    source: 'nous-research/hermes',
    url: 'https://api.github.com/repos/NousResearch/hermes-function-calling/releases',
    kind: 'github',
    watchedDeps: ['hermes', 'nous-research'],
  },
  // -------------------------------------------------------------------------
  // Protocol specifications
  // -------------------------------------------------------------------------
  {
    id: 'modelcontextprotocol-spec',
    source: 'modelcontextprotocol/specification',
    url: 'https://api.github.com/repos/modelcontextprotocol/specification/releases',
    kind: 'github',
    watchedDeps: ['mcp', 'modelcontextprotocol'],
  },
  {
    id: 'google-a2a',
    source: 'google/agent2agent',
    url: 'https://api.github.com/repos/google/A2A/releases',
    kind: 'github',
    watchedDeps: ['a2a', 'agent2agent'],
  },
  // -------------------------------------------------------------------------
  // Deployment infrastructure
  // -------------------------------------------------------------------------
  {
    id: 'netlify-cli',
    source: 'netlify/cli',
    url: 'https://api.github.com/repos/netlify/cli/releases',
    kind: 'github',
    watchedDeps: ['netlify', 'netlify-cli'],
  },
  // -------------------------------------------------------------------------
  // @shay internal packages — tracked for self-update awareness
  // -------------------------------------------------------------------------
  {
    id: 'shay-core',
    source: '@shay/core',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/core'],
  },
  {
    id: 'shay-memory',
    source: '@shay/memory',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/memory'],
  },
  {
    id: 'shay-brain',
    source: '@shay/brain',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/brain'],
  },
  {
    id: 'shay-ingestion',
    source: '@shay/ingestion',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/ingestion'],
  },
  {
    id: 'shay-capabilities',
    source: '@shay/capabilities',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/capabilities'],
  },
  {
    id: 'shay-bridge',
    source: '@shay/bridge',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/bridge'],
  },
  {
    id: 'shay-senses',
    source: '@shay/senses',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/senses'],
  },
  {
    id: 'shay-doctor',
    source: '@shay/doctor',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/doctor'],
  },
  {
    id: 'shay-surfaces',
    source: '@shay/surfaces',
    url: 'https://api.github.com/repos/famtastic-fritz/shay-shay-build/releases',
    kind: 'github',
    watchedDeps: ['@shay/surfaces'],
  },
];
