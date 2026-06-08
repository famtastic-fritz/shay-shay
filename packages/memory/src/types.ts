/**
 * MemoryRecord type definitions.
 *
 * Defines the contract for all memory records in the Shay memory fabric.
 * Tiers implement a 4-level recall hierarchy:
 *   T0 = always-in-context (SOUL, immediate state)
 *   T1 = session-active (current conversation, session metadata)
 *   T2 = recalled-on-demand (searchable vault, semantic index)
 *   T3 = archived (historical reference, deep memory)
 */

export type MemoryTier = "T0" | "T1" | "T2" | "T3";

/**
 * EmbeddingProvider interface.
 *
 * Any embedding implementation must provide an embed() method that
 * transforms text into a vector representation.
 */
export interface EmbeddingProvider {
  embed(text: string): Promise<number[]>;
}

/**
 * MemoryRecord interface.
 *
 * Properties:
 *   id - Unique identifier for this record (UUID v4 or similar)
 *   content - The text/data payload of the memory
 *   tier - The recall tier (T0, T1, T2, T3)
 *   importance - Numerical importance score (0-1 or 0-100; interpretation up to consumer)
 *   source - Origin/author of the record (e.g. "claude-code-session-123", "user-input", "system")
 *   validityStart - ISO 8601 timestamp when this record became valid
 *   validityEnd - Optional ISO 8601 timestamp after which this record is no longer authoritative
 *   embedding - Optional vector representation of the content (for semantic search)
 *   entities - Optional array of extracted entities or tags (e.g. ["task-123", "feature-brainstorm"])
 *   stale - Optional flag indicating the record has expired (validityEnd < now)
 */
export interface MemoryRecord {
  id: string;
  content: string;
  tier: MemoryTier;
  importance: number;
  source: string;
  validityStart: string;
  validityEnd?: string;
  embedding?: number[];
  entities?: string[];
  stale?: boolean;
}

/**
 * Recall options for semantic search.
 */
export interface RecallOptions {
  k?: number;
  tier?: MemoryTier;
}

/**
 * Decay options for importance degradation.
 */
export interface DecayOptions {
  importanceThreshold?: number;
  now?: string;
}
