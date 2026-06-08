import { describe, it, expect, beforeAll } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { TrustTier } from '@shay/core';
import { HermesSkillAdapter } from '../src/adapters/hermes-skill-adapter.js';
import { ClaudeSkillAdapter } from '../src/adapters/claude-skill-adapter.js';
import { McpToolAdapter } from '../src/adapters/mcp-tool-adapter.js';
import { A2aCardAdapter } from '../src/adapters/a2a-card-adapter.js';
import { ArtifactFormat } from '../src/types.js';
import type { RawArtifact, CapabilityManifest, SkillRecord } from '../src/types.js';

const fixturesDir = path.join(import.meta.url.replace('file://', ''), '..', 'fixtures');

describe('HermesSkillAdapter', () => {
  let adapter: HermesSkillAdapter;
  let sampleContent: string;

  beforeAll(() => {
    adapter = new HermesSkillAdapter();
    const fixturePath = path.join(fixturesDir, 'sample-SKILL.md');
    sampleContent = fs.readFileSync(fixturePath, 'utf-8');
  });

  it('canHandle returns true for hermes-skill format', () => {
    const artifact: RawArtifact = {
      id: 'test-skill',
      source: '/fixtures/sample-SKILL.md',
      format: 'hermes-skill',
      content: sampleContent,
      timestamp: Date.now(),
    };
    // Check the metadata-based detection used in the adapter
    artifact.metadata = { type: 'hermes-skill' };
    // Since the adapter checks format field not metadata, we need to test the format field
    artifact.format = 'hermes-skill';
    expect(adapter.canHandle({ ...artifact, rawContent: sampleContent } as any)).toBe(true);
  });

  it('canHandle returns false for other formats', () => {
    const artifact: RawArtifact = {
      id: 'test-skill',
      source: '/fixtures/sample-SKILL.md',
      format: 'mcp-tool',
      content: sampleContent,
      timestamp: Date.now(),
    };
    expect(adapter.canHandle({ ...artifact, rawContent: sampleContent } as any)).toBe(false);
  });

  it('translate produces SkillRecord with correct fields', () => {
    const artifact: RawArtifact = {
      id: 'example-hermes-skill',
      source: '/fixtures/sample-SKILL.md',
      format: 'hermes-skill',
      content: sampleContent,
      timestamp: Date.now(),
    };
    const result = adapter.translate(artifact);
    const skillRecord = result as SkillRecord;

    expect(skillRecord.id).toBe('example-hermes-skill');
    expect(skillRecord.name).toBe('Example Hermes Skill');
    expect(skillRecord.version).toBe('1.0.0');
    expect(skillRecord.description).toBe('A sample skill in Hermes format for testing YAML frontmatter parsing');
    expect(skillRecord.trustTier).toBe(TrustTier.Suggest);
    expect(skillRecord.permissions).toContain('read:files');
    expect(skillRecord.permissions).toContain('write:memory');
    expect(skillRecord.tags).toContain('test');
    expect(skillRecord.tags).toContain('example');
    expect(skillRecord.entrypoint).toBe('dist/index.js');
  });
});

describe('ClaudeSkillAdapter', () => {
  let adapter: ClaudeSkillAdapter;
  let sampleContent: string;

  beforeAll(() => {
    adapter = new ClaudeSkillAdapter();
    const fixturePath = path.join(fixturesDir, 'sample-CLAUDE.md');
    sampleContent = fs.readFileSync(fixturePath, 'utf-8');
  });

  it('canHandle returns true for claude-skill format', () => {
    const artifact: RawArtifact = {
      id: 'claude-test',
      source: '/fixtures/sample-CLAUDE.md',
      format: 'hermes-skill',
      content: sampleContent,
      metadata: { type: 'claude-skill' },
      timestamp: Date.now(),
      rawContent: sampleContent,
    } as any;
    expect(adapter.canHandle(artifact)).toBe(true);
  });

  it('canHandle returns false for other formats', () => {
    const artifact: RawArtifact = {
      id: 'claude-test',
      source: '/fixtures/sample-CLAUDE.md',
      format: 'mcp-tool',
      content: sampleContent,
      timestamp: Date.now(),
      rawContent: sampleContent,
    } as any;
    expect(adapter.canHandle(artifact)).toBe(false);
  });

  it('translate parses H1 heading and description', () => {
    const artifact: RawArtifact = {
      id: 'claude-test',
      source: '/fixtures/sample-CLAUDE.md',
      format: 'hermes-skill',
      content: sampleContent,
      timestamp: Date.now(),
      rawContent: sampleContent,
    } as any;
    const result = adapter.translate(artifact);
    const skillRecord = result as SkillRecord;

    expect(skillRecord.name).toBe('Sample Claude Skill');
    expect(skillRecord.description).toMatch(/simple skill descriptor/);
    expect(skillRecord.trustTier).toBe(TrustTier.Suggest);
  });
});

describe('McpToolAdapter', () => {
  let adapter: McpToolAdapter;
  let sampleToolContent: string;

  beforeAll(() => {
    adapter = new McpToolAdapter();
    const fixturePath = path.join(fixturesDir, 'sample-mcp-tool.json');
    sampleToolContent = fs.readFileSync(fixturePath, 'utf-8');
  });

  it('canHandle returns true for mcp-tool format', () => {
    const artifact: RawArtifact = {
      id: 'example-mcp-tool',
      source: '/fixtures/sample-mcp-tool.json',
      format: 'hermes-skill',
      content: sampleToolContent,
      metadata: { type: 'mcp-tool' },
      timestamp: Date.now(),
      rawContent: sampleToolContent,
    } as any;
    expect(adapter.canHandle(artifact)).toBe(true);
  });

  it('translate parses MCP tool schema', () => {
    const artifact: RawArtifact = {
      id: 'example-mcp-tool',
      source: '/fixtures/sample-mcp-tool.json',
      format: 'hermes-skill',
      content: sampleToolContent,
      timestamp: Date.now(),
      rawContent: sampleToolContent,
    } as any;
    const result = adapter.translate(artifact);
    const skillRecord = result as SkillRecord;

    expect(skillRecord.id).toBe('example-mcp-tool');
    expect(skillRecord.name).toBe('example-mcp-tool');
    expect(skillRecord.description).toBe('An example MCP tool for testing schema parsing');
    expect(skillRecord.trustTier).toBe(TrustTier.Suggest);
  });
});

describe('A2aCardAdapter', () => {
  let adapter: A2aCardAdapter;
  let sampleCardContent: string;

  beforeAll(() => {
    adapter = new A2aCardAdapter();
    const fixturePath = path.join(fixturesDir, 'sample-a2a-card.json');
    sampleCardContent = fs.readFileSync(fixturePath, 'utf-8');
  });

  it('canHandle returns true for a2a-card format', () => {
    const artifact: RawArtifact = {
      id: 'example-a2a-agent',
      source: '/fixtures/sample-a2a-card.json',
      format: 'hermes-skill',
      content: sampleCardContent,
      metadata: { type: 'a2a-card' },
      timestamp: Date.now(),
      rawContent: sampleCardContent,
    } as any;
    expect(adapter.canHandle(artifact)).toBe(true);
  });

  it('translate parses A2A Agent Card', () => {
    const artifact: RawArtifact = {
      id: 'example-a2a-agent',
      source: '/fixtures/sample-a2a-card.json',
      format: 'hermes-skill',
      content: sampleCardContent,
      timestamp: Date.now(),
      rawContent: sampleCardContent,
    } as any;
    const result = adapter.translate(artifact);
    const skillRecord = result as SkillRecord;

    expect(skillRecord.name).toBe('example-a2a-agent');
    expect(skillRecord.description).toBe('An example A2A Agent Card for testing schema parsing');
    expect(skillRecord.version).toBe('1.0.0');
    expect(skillRecord.trustTier).toBe(TrustTier.Suggest);
  });
});
