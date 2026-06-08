/**
 * @shay/ingestion
 *
 * Public API barrel for ingestion protocol, types, sources, adapters, and registry.
 * Exports all public interfaces and classes for the ingestion pipeline.
 */

// Protocol
export { IngestionProtocol } from './protocol.js';
export type { IngestionProtocolOptions } from './protocol.js';

// Types
export type {
  RawArtifact,
  SkillRecord,
  CapabilityManifest,
  IngestionManifest,
  IngestionCounts,
  FailedItem,
  UntestedItem,
  ArtifactFormat,
  IngestionStage,
  TrustTier,
} from './types.js';

// Sources
export { HermesSource } from './sources/hermes-source.js';

// Adapters
export { AdapterRegistry } from './adapters/adapter.js';
export type { SkillAdapter } from './adapters/adapter.js';
export { HermesSkillAdapter } from './adapters/hermes-skill-adapter.js';
export { ClaudeSkillAdapter } from './adapters/claude-skill-adapter.js';
export { McpToolAdapter } from './adapters/mcp-tool-adapter.js';
export { A2aCardAdapter } from './adapters/a2a-card-adapter.js';

// Registry
export { IngestedCapabilityStore } from './registry.js';
export type { IngestedEntry } from './registry.js';

// Verify
export { VerifyStage } from './verify.js';
export type { VerifyResult } from './verify.js';
