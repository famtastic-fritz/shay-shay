/**
 * Trust tier for capabilities and skills (1=Suggest, 2=Observe, 3=Act, 4=Auto)
 */
export type TrustTier = 1 | 2 | 3 | 4;

/**
 * Ingestion stage in the protocol lifecycle
 */
export type IngestionStage = 'DISCOVER' | 'TRANSLATE' | 'INGEST' | 'VERIFY';

/**
 * Supported artifact format types for ingestion
 */
export type ArtifactFormat = 'hermes-skill' | 'claude-skill' | 'mcp-tool' | 'a2a-card';

/**
 * Raw artifact as discovered from the filesystem or external source
 */
export interface RawArtifact {
  /** Unique identifier for the artifact */
  id: string;
  /** File path or identifier of the raw artifact */
  path: string;
  /** Format type of the artifact */
  format: ArtifactFormat;
  /** Raw unparsed content of the artifact */
  rawContent: string;
}

/**
 * Skill record with all metadata fields
 * Mirrors skill-record.schema.json fields plus trustTier
 */
export interface SkillRecord {
  /** Unique identifier for the skill */
  id: string;
  /** Human-readable name */
  name: string;
  /** Detailed description of what the skill does */
  description: string;
  /** Semantic version string */
  version: string;
  /** Source location or origin of the skill */
  source: string;
  /** Trust tier for this skill's operations */
  trustTier: TrustTier;
  /** ISO 8601 date-time string indicating when the skill was ingested */
  ingestionDate: string;
  /** Optional list of required permissions */
  permissions?: string[];
  /** Optional list of skill IDs this depends on */
  dependencies?: string[];
  /** Optional metadata object for additional properties */
  metadata?: Record<string, unknown>;
}

/**
 * Capability manifest with ingestion provenance
 * Mirrors capability-manifest.schema.json fields plus source/ingestionDate/trustTier
 */
export interface CapabilityManifest {
  /** Unique identifier for the capability */
  id: string;
  /** Semantic version string */
  version: string;
  /** Human-readable name for the capability */
  name: string;
  /** Detailed description of what the capability provides */
  description: string;
  /** Optional list of required permissions */
  permissions?: string[];
  /** Optional list of capability IDs this depends on */
  dependencies?: string[];
  /** Optional path to the main export file */
  entrypoint?: string;
  /** Source of the ingestion (directory path, repository URL, or identifier) */
  source?: string;
  /** ISO 8601 date-time string indicating when the capability was ingested */
  ingestionDate?: string;
  /** Trust tier for this capability's operations */
  trustTier?: TrustTier;
}

/**
 * Failed ingestion item with error details
 */
export interface FailedItem {
  /** Identifier or path of the failed item */
  item: string;
  /** Description of the error that occurred */
  error: string;
}

/**
 * Untested ingestion item with reason
 */
export interface UntestedItem {
  /** Identifier or path of the untested item */
  item: string;
  /** Reason why the item was not tested */
  reason: string;
}

/**
 * Counts of ingested artifacts by type
 */
export interface IngestionCounts {
  /** Number of capabilities ingested */
  capabilities: number;
  /** Number of skills ingested */
  skills: number;
  /** Number of tools ingested */
  tools: number;
  /** Number of memory records ingested */
  memoryRecords: number;
}

/**
 * Complete record of an ingestion run
 * Mirrors ingestion-manifest.schema.json fields
 */
export interface IngestionManifest {
  /** The source of the ingestion (e.g., directory path, repository URL, or identifier) */
  source: string;
  /** Semantic version of the source being ingested */
  version: string;
  /** ISO 8601 date-time string indicating when the ingestion occurred */
  ingestionDate: string;
  /** Expected counts of ingested artifacts */
  expected: IngestionCounts;
  /** Actual counts of successfully ingested artifacts */
  actual: IngestionCounts;
  /** Total number of items that passed validation */
  passed: number;
  /** Items that failed ingestion or validation */
  failed: FailedItem[];
  /** Items that were not tested during ingestion */
  untested: UntestedItem[];
  /** Instructions for rolling back the ingestion if issues are discovered */
  rollbackPlan: string;
}
