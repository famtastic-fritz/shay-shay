/**
 * @shay/bridge — A2A protocol tests
 */

import { describe, it, expect } from 'vitest';
import { parseAgentCard, toCapabilityManifests, produceAgentCard } from '../src/a2a.js';
import type { AgentCard } from '../src/a2a.js';

const sampleCard: AgentCard = {
  name: 'remote-agent',
  version: '1.0.0',
  description: 'A remote agent for testing',
  capabilities: ['search', 'summarize'],
};

describe('parseAgentCard()', () => {
  it('parses a valid agent card JSON object', () => {
    const raw = { name: 'remote-agent', version: '1.0.0', capabilities: ['search'] };
    const card = parseAgentCard(raw);
    expect(card.name).toBe('remote-agent');
    expect(card.version).toBe('1.0.0');
    expect(card.capabilities).toEqual(['search']);
  });

  it('includes optional description when present', () => {
    const raw = { name: 'x', version: '1.0.0', description: 'desc', capabilities: [] };
    const card = parseAgentCard(raw);
    expect(card.description).toBe('desc');
  });

  it('omits description when not a string', () => {
    const raw = { name: 'x', version: '1.0.0', capabilities: [] };
    const card = parseAgentCard(raw);
    expect(card.description).toBeUndefined();
  });

  it('throws TypeError for missing name', () => {
    expect(() => parseAgentCard({ version: '1.0.0', capabilities: [] })).toThrow(TypeError);
  });

  it('throws TypeError for missing version', () => {
    expect(() => parseAgentCard({ name: 'x', capabilities: [] })).toThrow(TypeError);
  });

  it('throws TypeError for non-array capabilities', () => {
    expect(() => parseAgentCard({ name: 'x', version: '1.0.0', capabilities: 'oops' })).toThrow(TypeError);
  });

  it('throws TypeError for non-object input', () => {
    expect(() => parseAgentCard(null)).toThrow(TypeError);
    expect(() => parseAgentCard('string')).toThrow(TypeError);
  });
});

describe('toCapabilityManifests()', () => {
  it('maps each capability to a manifest', () => {
    const manifests = toCapabilityManifests(sampleCard);
    expect(manifests).toHaveLength(2);
    expect(manifests[0].id).toBe('remote-agent::search');
    expect(manifests[1].id).toBe('remote-agent::summarize');
  });

  it('manifests carry the card version', () => {
    const [m] = toCapabilityManifests(sampleCard);
    expect(m.version).toBe(sampleCard.version);
  });

  it('returns empty array for card with no capabilities', () => {
    const empty: AgentCard = { name: 'empty', version: '0.1.0', capabilities: [] };
    expect(toCapabilityManifests(empty)).toHaveLength(0);
  });
});

describe('produceAgentCard()', () => {
  it('produces a card from manifests', () => {
    const manifests = toCapabilityManifests(sampleCard);
    const card = produceAgentCard(manifests, 'shay', '0.1.0');
    expect(card.name).toBe('shay');
    expect(card.version).toBe('0.1.0');
    expect(card.capabilities).toHaveLength(2);
    expect(card.capabilities).toContain('remote-agent::search');
  });

  it('round-trips: parseAgentCard(produceAgentCard(...)) is stable', () => {
    const manifests = toCapabilityManifests(sampleCard);
    const produced = produceAgentCard(manifests, 'shay', '0.1.0');
    const reparsed = parseAgentCard(produced);
    expect(reparsed.name).toBe('shay');
    expect(reparsed.capabilities).toEqual(produced.capabilities);
  });
});
