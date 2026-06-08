import { createHash } from 'node:crypto';
import type { EmbeddingProvider } from './types.js';

/**
 * Ollama Nomic Embedding provider.
 *
 * Uses a local Ollama instance (default: http://localhost:11434) to embed text.
 * Falls back to deterministic embedding if Ollama is unavailable.
 */
export class OllamaNomicEmbedding implements EmbeddingProvider {
  private baseUrl: string;
  private fallback: DeterministicEmbedding;

  constructor(baseUrl = 'http://localhost:11434') {
    this.baseUrl = baseUrl;
    this.fallback = new DeterministicEmbedding();
  }

  async embed(text: string): Promise<number[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/embed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'nomic-embed-text',
          input: text,
        }),
      });

      if (!response.ok) {
        throw new Error(`Ollama returned ${response.status}`);
      }

      const data = (await response.json()) as {
        embeddings?: number[][];
      };
      const embeddings = data.embeddings;
      if (embeddings && embeddings.length > 0) {
        return embeddings[0];
      }
      throw new Error('No embeddings in response');
    } catch {
      // Fallback to deterministic embedding
      return this.fallback.embed(text);
    }
  }
}

/**
 * Deterministic Embedding provider.
 *
 * Uses SHA-256 hash to produce a deterministic vector from text.
 * Not semantically meaningful but useful for testing and fallback.
 * Output is a 256-dimensional vector (one float per hash byte).
 */
export class DeterministicEmbedding implements EmbeddingProvider {
  async embed(text: string): Promise<number[]> {
    const hash = createHash('sha256').update(text).digest();
    const embedding: number[] = [];
    for (let i = 0; i < hash.length; i++) {
      // Normalize byte (0-255) to float (-1, 1)
      embedding.push((hash[i] - 127.5) / 127.5);
    }
    return embedding;
  }
}

/**
 * Computes cosine similarity between two embedding vectors.
 *
 * Returns a value between -1 and 1, where 1 is identical vectors
 * and -1 is opposite vectors. Returns 0 if either vector is empty.
 */
export function cosineSimilarity(vecA: number[], vecB: number[]): number {
  if (vecA.length === 0 || vecB.length === 0) {
    return 0;
  }

  if (vecA.length !== vecB.length) {
    throw new Error('Vectors must have the same length');
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }

  normA = Math.sqrt(normA);
  normB = Math.sqrt(normB);

  if (normA === 0 || normB === 0) {
    return 0;
  }

  return dotProduct / (normA * normB);
}
