import { describe, it, expect } from 'vitest';
import { DeterministicEmbedding, cosineSimilarity } from '../src/embedding.js';

describe('DeterministicEmbedding', () => {
  const embedding = new DeterministicEmbedding();

  it('embed() returns a number[] of length 32 for any input string', async () => {
    const result1 = await embedding.embed('hello world');
    const result2 = await embedding.embed('the quick brown fox');
    const result3 = await embedding.embed('');

    expect(result1).toHaveLength(32);
    expect(result2).toHaveLength(32);
    expect(result3).toHaveLength(32);

    expect(result1.every((v) => typeof v === 'number')).toBe(true);
  });

  it('embed() is deterministic — same input yields identical array twice', async () => {
    const input = 'test deterministic behavior';
    const first = await embedding.embed(input);
    const second = await embedding.embed(input);

    expect(first).toEqual(second);
  });

  it('embed() produces different output for different inputs', async () => {
    const vector1 = await embedding.embed('input one');
    const vector2 = await embedding.embed('input two');

    const isDifferent = vector1.some((v, i) => v !== vector2[i]);
    expect(isDifferent).toBe(true);
  });

  it('embed() produces values in the range [-1, 1]', async () => {
    const result = await embedding.embed('range test');

    for (const value of result) {
      expect(value).toBeGreaterThanOrEqual(-1);
      expect(value).toBeLessThanOrEqual(1);
    }
  });
});

describe('cosineSimilarity', () => {
  it('cosineSimilarity of a vector with itself is approximately 1', () => {
    const vector = [1, 2, 3, 4, 5];
    const similarity = cosineSimilarity(vector, vector);

    expect(similarity).toBeCloseTo(1, 5);
  });

  it('cosineSimilarity of two zero vectors returns 0', () => {
    const zero1 = [0, 0, 0, 0];
    const zero2 = [0, 0, 0, 0];
    const similarity = cosineSimilarity(zero1, zero2);

    expect(similarity).toBe(0);
  });

  it('cosineSimilarity is commutative (a,b) === (b,a)', () => {
    const a = [1, 2, 3];
    const b = [4, 5, 6];

    const ab = cosineSimilarity(a, b);
    const ba = cosineSimilarity(b, a);

    expect(ab).toBe(ba);
  });

  it('cosineSimilarity handles orthogonal vectors', () => {
    const a = [1, 0, 0];
    const b = [0, 1, 0];
    const similarity = cosineSimilarity(a, b);

    expect(similarity).toBeCloseTo(0, 5);
  });

  it('cosineSimilarity handles opposite vectors', () => {
    const a = [1, 0, 0];
    const b = [-1, 0, 0];
    const similarity = cosineSimilarity(a, b);

    expect(similarity).toBeCloseTo(-1, 5);
  });

  it('cosineSimilarity throws for mismatched vector lengths', () => {
    const a = [1, 2, 3];
    const b = [4, 5];

    expect(() => {
      cosineSimilarity(a, b);
    }).toThrow();
  });
});
