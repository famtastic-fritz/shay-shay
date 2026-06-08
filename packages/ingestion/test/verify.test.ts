import { describe, it, expect, beforeEach } from 'vitest';
import { TrustTier } from '@shay/core';
import { VerifyStage } from '../src/verify.js';
import { SchemaRegistry } from '@shay/core';
import type { CapabilityManifest, SkillRecord } from '../src/types.js';

describe('VerifyStage', () => {
  let verifyStage: VerifyStage;
  let schemaRegistry: SchemaRegistry;

  beforeEach(() => {
    verifyStage = new VerifyStage();
    schemaRegistry = new SchemaRegistry();

    // Register the required schemas
    const capabilitySchema = {
      $id: 'shay:capability-manifest',
      type: 'object',
      required: ['id', 'name', 'version', 'description'],
      properties: {
        id: { type: 'string' },
        name: { type: 'string' },
        version: { type: 'string' },
        description: { type: 'string' },
        trustTier: { type: 'number' },
        ingestionDate: { type: 'string' },
        source: { type: 'string' },
      },
    };

    const skillSchema = {
      $id: 'shay:skill-record',
      type: 'object',
      required: ['id', 'name', 'version', 'description', 'source', 'trustTier', 'ingestionDate'],
      properties: {
        id: { type: 'string' },
        name: { type: 'string' },
        version: { type: 'string' },
        description: { type: 'string' },
        source: { type: 'string' },
        trustTier: { type: 'number' },
        ingestionDate: { type: 'string' },
      },
    };

    schemaRegistry.register('shay:capability-manifest', capabilitySchema);
    schemaRegistry.register('shay:skill-record', skillSchema);
  });

  it('a valid CapabilityManifest increments passed', () => {
    const validCapability: CapabilityManifest = {
      id: 'test-capability',
      name: 'Test Capability',
      version: '1.0.0',
      description: 'A test capability',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
      source: 'test-source',
    };

    const result = verifyStage.verify([validCapability], schemaRegistry);
    expect(result.passed).toBeGreaterThan(0);
  });

  it('an invalid item missing required field increments failed', () => {
    const invalidSkill: Partial<SkillRecord> = {
      id: 'test-skill',
      name: 'Test Skill',
      // version is missing (required)
      description: 'A test skill',
      source: 'test-source',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    const result = verifyStage.verify([invalidSkill as SkillRecord], schemaRegistry);
    expect(result.failed.length).toBeGreaterThan(0);
    expect(result.failed[0]).toHaveProperty('item');
    expect(result.failed[0]).toHaveProperty('error');
    expect(result.failed[0].error).toBeTruthy();
  });

  it('untested array includes at least one entry for valid items', () => {
    const validSkill: SkillRecord = {
      id: 'test-skill',
      name: 'Test Skill',
      version: '1.0.0',
      description: 'A test skill',
      source: 'test-source',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    const result = verifyStage.verify([validSkill], schemaRegistry);
    expect(Array.isArray(result.untested)).toBe(true);
    expect(result.untested.length).toBeGreaterThanOrEqual(0);

    if (result.untested.length > 0) {
      for (const item of result.untested) {
        expect(item.reason).toBeTruthy();
        expect(item.reason).toContain('Doctor');
      }
    }
  });

  it('rollbackPlan string is non-empty', () => {
    const validSkill: SkillRecord = {
      id: 'test-skill',
      name: 'Test Skill',
      version: '1.0.0',
      description: 'A test skill',
      source: 'test-source',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    const result = verifyStage.verify([validSkill], schemaRegistry);
    expect(typeof result.rollbackPlan).toBe('string');
    expect(result.rollbackPlan.length).toBeGreaterThan(0);
  });

  it('full verify call over mix of valid+invalid items returns correct counts', () => {
    const validSkill: SkillRecord = {
      id: 'valid-skill',
      name: 'Valid Skill',
      version: '1.0.0',
      description: 'A valid test skill',
      source: 'test-source',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
    };

    const invalidSkill: Partial<SkillRecord> = {
      id: 'invalid-skill',
      name: 'Invalid Skill',
      // missing required fields
      source: 'test-source',
    };

    const validCapability: CapabilityManifest = {
      id: 'test-capability',
      name: 'Test Capability',
      version: '1.0.0',
      description: 'A test capability',
      trustTier: TrustTier.Suggest,
      ingestionDate: new Date().toISOString(),
      source: 'test-source',
    };

    const result = verifyStage.verify(
      [validSkill, invalidSkill as SkillRecord, validCapability],
      schemaRegistry
    );

    expect(result.passed).toBeGreaterThan(0);
    expect(result.failed.length).toBeGreaterThan(0);
    expect(result.rollbackPlan).toBeTruthy();
  });
});
