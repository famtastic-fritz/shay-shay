/**
 * @shay/memory — Memory fabric for Shay agent.
 *
 * Exports:
 *   - MemoryRecord and MemoryTier types
 *   - EmbeddingProvider interface
 *   - OllamaNomicEmbedding and DeterministicEmbedding implementations
 *   - cosineSimilarity utility for vector comparison
 *   - MemoryStore class for semantic recall and persistence
 *   - BasicMemoryBridge class for reading markdown-based memory files
 */

export * from './types.js';
export * from './embedding.js';
export * from './store.js';
export * from './basic-memory-bridge.js';
