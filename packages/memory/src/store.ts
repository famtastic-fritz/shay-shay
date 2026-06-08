import { promises as fs } from 'node:fs';
import { tmpdir } from 'node:os';
import type { MemoryRecord, EmbeddingProvider, RecallOptions, DecayOptions } from './types.js';
import { DeterministicEmbedding, cosineSimilarity } from './embedding.js';

/**
 * MemoryStore — in-memory store with optional persistence.
 *
 * Manages a collection of MemoryRecords with embedding-based semantic recall.
 * Records are loaded from persistPath on construction (if it exists) and appended
 * as new records are added.
 */
export class MemoryStore {
  private records: MemoryRecord[] = [];
  private embeddingProvider: EmbeddingProvider;
  private persistPath: string;

  constructor(options?: {
    embeddingProvider?: EmbeddingProvider;
    persistPath?: string;
  }) {
    this.embeddingProvider =
      options?.embeddingProvider ?? new DeterministicEmbedding();
    this.persistPath =
      options?.persistPath ?? `${tmpdir()}/shay-memory-${process.pid}.jsonl`;
  }

  /**
   * Load existing records from persistPath (if it exists).
   */
  async initialize(): Promise<void> {
    try {
      const content = await fs.readFile(this.persistPath, 'utf-8');
      const lines = content.split('\n').filter((line) => line.trim());
      for (const line of lines) {
        try {
          const record = JSON.parse(line) as MemoryRecord;
          this.records.push(record);
        } catch {
          // Skip malformed lines
        }
      }
    } catch {
      // File doesn't exist yet; that's okay
    }
  }

  /**
   * Store a record — compute embedding if missing, append to file, add to memory.
   */
  async store(record: MemoryRecord): Promise<void> {
    // Compute embedding if not provided
    if (!record.embedding) {
      record.embedding = await this.embeddingProvider.embed(record.content);
    }

    // Append to JSONL file
    await fs.appendFile(
      this.persistPath,
      JSON.stringify(record) + '\n'
    );

    // Add to in-memory array
    this.records.push(record);
  }

  /**
   * Recall records by semantic similarity.
   *
   * Embeds the query, filters by tier if provided, ranks by cosine similarity,
   * returns top k results.
   */
  async recall(query: string, opts?: RecallOptions): Promise<MemoryRecord[]> {
    const k = opts?.k ?? 5;
    const tier = opts?.tier;

    // Embed the query
    const queryEmbedding = await this.embeddingProvider.embed(query);

    // Filter records
    let candidates = this.records;
    if (tier) {
      candidates = candidates.filter((r) => r.tier === tier);
    }

    // Rank by similarity
    const ranked = candidates
      .map((record) => {
        if (!record.embedding) {
          return { record, similarity: 0 };
        }
        return {
          record,
          similarity: cosineSimilarity(queryEmbedding, record.embedding),
        };
      })
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, k)
      .map((item) => item.record);

    return ranked;
  }

  /**
   * Get all T0 records (always-in-context).
   */
  getTier0(): MemoryRecord[] {
    return this.records.filter((r) => r.tier === 'T0');
  }

  /**
   * Decay importance over time.
   *
   * For records with validityEnd < now, set importance to 0 and mark stale.
   * For other records, reduce importance by 0.01 (floor at 0).
   * Does NOT persist the decay — it's in-memory only.
   */
  decay(opts?: DecayOptions): void {
    const now = opts?.now ?? new Date().toISOString();
    const threshold = opts?.importanceThreshold ?? 0;

    for (const record of this.records) {
      if (record.validityEnd && record.validityEnd < now) {
        record.importance = 0;
        record.stale = true;
      } else if (record.importance > threshold) {
        record.importance = Math.max(0, record.importance - 0.01);
      }
    }
  }

  /**
   * Get all stored records (for testing/inspection).
   */
  getAll(): MemoryRecord[] {
    return this.records;
  }

  /**
   * Clear all records (for testing).
   */
  clear(): void {
    this.records = [];
  }
}
