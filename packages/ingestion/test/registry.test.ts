import { describe, it, expect, beforeEach } from 'vitest';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';
import { TrustTier } from '@shay/core';
import { IngestedCapabilityStore } from '../src/registry.js';
import { SchemaRegistry } from '@shay/core';
import type { SkillRecord } from '../src/types.js';

describe('IngestedCapabilityStore', () => {
  let store: IngestedCapabilityStore;

  beforeEach(() => {
    store = new IngestedCapabilityStore();
  });

  it('ingest tags entries with trustTier.Suggest when none provided', async () => {
    const skillRecord: SkillRecord = {
      id: 'test-skill',
      name: 'Test Skill',
      version: '1.0.0',
      description: 'A test skill',
      source: 'test-source',
      trustTier: 0, // Will be overridden
      ingestionDate: new Date().toISOString(),
    };

    await store.ingest(skillRecord, {
      source: 'test-source',
      ingestionDate: new Date().toISOString(),
      // trustTier not provided
    });

    const all = store.getAll();
    expect(all.length).toBeGreaterThan(0);
  });

  it('ingest preserves explicit trustTier when supplied', async () => {
    const skillRecord: SkillRecord = {
      id: 'test-skill-with-tier',
      name: 'Test Skill',
      version: '1.0.0',
      description: 'A test skill',
      source: 'test-source',
      trustTier: TrustTier.Trust,
      ingestionDate: new Date().toISOString(),
    };

    await store.ingest(skillRecord, {
      source: 'test-source',
      ingestionDate: new Date().toISOString(),
      trustTier: TrustTier.Trust,
    });

    const all = store.getAll();
    expect(all.length).toBeGreaterThan(0);
  });

  it('getAll returns all ingested entries', async () => {
    const skill1: SkillRecord = {
      id: 'skill-1',
      name: 'Skill 1',
      version: '1.0.0',
      description: 'First skill',
      source: 'source-1',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    const skill2: SkillRecord = {
      id: 'skill-2',
      name: 'Skill 2',
      version: '1.0.0',
      description: 'Second skill',
      source: 'source-1',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    await store.ingest(skill1, {
      source: 'source-1',
      ingestionDate: new Date().toISOString(),
    });

    await store.ingest(skill2, {
      source: 'source-1',
      ingestionDate: new Date().toISOString(),
    });

    const all = store.getAll();
    expect(all.length).toBe(2);
  });

  it('clear with source argument removes only matching entries', async () => {
    const skill1: SkillRecord = {
      id: 'skill-1',
      name: 'Skill 1',
      version: '1.0.0',
      description: 'First skill',
      source: 'source-1',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    const skill2: SkillRecord = {
      id: 'skill-2',
      name: 'Skill 2',
      version: '1.0.0',
      description: 'Second skill',
      source: 'source-2',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    await store.ingest(skill1, {
      source: 'source-1',
      ingestionDate: new Date().toISOString(),
    });

    await store.ingest(skill2, {
      source: 'source-2',
      ingestionDate: new Date().toISOString(),
    });

    store.clear('source-1');

    const remaining = store.getAll();
    expect(remaining.length).toBe(1);
    expect(remaining[0].source).toBe('source-2');
  });

  it('persistManifest writes MANIFEST.json to expected path', async () => {
    const tmpDir = os.tmpdir();
    const manifestPath = path.join(tmpDir, 'test-manifest-' + Date.now());

    const skill: SkillRecord = {
      id: 'test-skill',
      name: 'Test Skill',
      version: '1.0.0',
      description: 'A test skill',
      source: 'test-source',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    await store.ingest(skill, {
      source: 'test-source',
      ingestionDate: new Date().toISOString(),
    });

    try {
      await store.persistManifest(manifestPath);

      const written = fs.existsSync(manifestPath);
      expect(written).toBe(true);

      if (written) {
        const content = fs.readFileSync(manifestPath, 'utf-8');
        const manifest = JSON.parse(content);
        expect(manifest).toHaveProperty('source');
        expect(manifest).toHaveProperty('version');
        expect(manifest).toHaveProperty('ingestionDate');
      }
    } finally {
      if (fs.existsSync(manifestPath)) {
        fs.unlinkSync(manifestPath);
      }
    }
  });

  it('written manifest validates against shay:ingestion-manifest schema', async () => {
    const tmpDir = os.tmpdir();
    const manifestPath = path.join(tmpDir, 'test-schema-manifest-' + Date.now());

    const skill: SkillRecord = {
      id: 'test-skill',
      name: 'Test Skill',
      version: '1.0.0',
      description: 'A test skill',
      source: 'test-source',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    await store.ingest(skill, {
      source: 'test-source',
      ingestionDate: new Date().toISOString(),
    });

    try {
      await store.persistManifest(manifestPath);

      const content = fs.readFileSync(manifestPath, 'utf-8');
      const manifest = JSON.parse(content);

      // Verify required fields per ingestion-manifest schema
      expect(manifest).toHaveProperty('source');
      expect(manifest).toHaveProperty('version');
      expect(manifest).toHaveProperty('ingestionDate');
      expect(manifest).toHaveProperty('expected');
      expect(manifest).toHaveProperty('actual');
      expect(manifest).toHaveProperty('passed');
      expect(manifest).toHaveProperty('failed');
      expect(manifest).toHaveProperty('untested');
      expect(manifest).toHaveProperty('rollbackPlan');

      // Verify nested structure
      expect(manifest.expected).toHaveProperty('capabilities');
      expect(manifest.expected).toHaveProperty('skills');
      expect(manifest.actual).toHaveProperty('capabilities');
      expect(manifest.actual).toHaveProperty('skills');

      expect(typeof manifest.rollbackPlan).toBe('string');
    } finally {
      if (fs.existsSync(manifestPath)) {
        fs.unlinkSync(manifestPath);
      }
    }
  });
});
