/**
 * IngestionProtocol — Protocol Engine
 *
 * Orchestrates the 4-stage ingestion pipeline:
 * 1. DISCOVER — reads raw artifacts from source via HermesSource
 * 2. TRANSLATE — converts artifacts to CapabilityManifest|SkillRecord via AdapterRegistry
 * 3. INGEST — stores translated artifacts via IngestedCapabilityStore
 * 4. VERIFY — validates against schema registry
 *
 * Full dependency injection for testability: source, adapters, store, schema registry.
 * Default implementations provided for all collaborators.
 */

import type { RawArtifact, SkillRecord, CapabilityManifest, IngestionManifest } from './types.js';
import type { HermesSource } from './sources/hermes-source.js';
import { HermesSource as HermesSourceImpl } from './sources/hermes-source.js';
import { VerifyStage, type VerifyResult } from './verify.js';

/**
 * AdapterRegistry resolves RawArtifact types to translation handlers.
 * Each adapter implements translate(): Promise<CapabilityManifest|SkillRecord>
 */
export interface Adapter {
  translate(artifact: RawArtifact): Promise<CapabilityManifest | SkillRecord>;
}

export interface AdapterRegistry {
  resolve(artifact: RawArtifact): Adapter;
  register(format: string, adapter: Adapter): void;
}

/**
 * IngestedCapabilityStore persists translated artifacts with metadata.
 * Tracks source, version, ingestion date, and trust tier.
 */
export interface IngestedCapabilityStore {
  ingest(
    item: CapabilityManifest | SkillRecord,
    metadata: {
      source: string;
      version?: string;
      ingestionDate: string;
      trustTier?: number;
    }
  ): Promise<void>;

  list(): Promise<Array<CapabilityManifest | SkillRecord>>;
}

/**
 * SchemaRegistry interface for validation
 */
export interface ISchemaRegistry {
  validate(name: string, payload: unknown): void;
  has(name: string): boolean;
}

/**
 * IngestionProtocolOptions — full dependency injection.
 * All fields optional; defaults provided for production use.
 */
export interface IngestionProtocolOptions {
  source?: string;
  skillsDir?: string;
  schemaRegistry?: ISchemaRegistry;
  store?: IngestedCapabilityStore;
  hermesSource?: HermesSource;
  adapterRegistry?: AdapterRegistry;
}

/**
 * IngestionProtocol — main orchestrator.
 * Executes the 4-stage pipeline: DISCOVER → TRANSLATE → INGEST → VERIFY.
 */
export class IngestionProtocol {
  private source: string;
  private skillsDir: string;
  private schemaRegistry: ISchemaRegistry;
  private store: IngestedCapabilityStore;
  private hermesSource: HermesSource;
  private adapterRegistry: AdapterRegistry;
  private verifyStage: VerifyStage;

  constructor(options: IngestionProtocolOptions = {}) {
    this.source = options.source ?? 'default-source';
    this.skillsDir = options.skillsDir ?? './skills';
    this.schemaRegistry = options.schemaRegistry ?? this._createDefaultSchemaRegistry();
    this.store = options.store ?? this._createDefaultStore();
    this.hermesSource = options.hermesSource ?? this._createDefaultHermesSource();
    this.adapterRegistry = options.adapterRegistry ?? this._createDefaultAdapterRegistry();
    this.verifyStage = new VerifyStage();
  }

  /**
   * Execute the full 4-stage pipeline.
   * Returns an IngestionManifest with counts, results, and rollback plan.
   */
  async run(source: string): Promise<IngestionManifest> {
    this.source = source;

    // Stage 1: DISCOVER — read raw artifacts from source
    const rawArtifacts = await this._discover();

    // Stage 2: TRANSLATE — adapt artifacts to CapabilityManifest|SkillRecord
    const { translated, failed: failedTranslate } = await this._translate(rawArtifacts);

    // Stage 3: INGEST — store translated artifacts
    const { ingested, failed: failedIngest } = await this._ingest(translated);

    // Stage 4: VERIFY — validate against schema registry
    const verifyResult = await this._verify(translated);

    // Assemble and return IngestionManifest
    return this._assembleManifest(
      rawArtifacts,
      translated,
      ingested,
      failedTranslate,
      failedIngest,
      verifyResult
    );
  }

  /**
   * Stage 1: DISCOVER — read raw artifacts from HermesSource
   */
  private async _discover(): Promise<RawArtifact[]> {
    try {
      const artifacts = await this.hermesSource.discover();
      return artifacts;
    } catch (error) {
      console.error('DISCOVER failed:', error);
      return [];
    }
  }

  /**
   * Stage 2: TRANSLATE — convert raw artifacts via AdapterRegistry
   */
  private async _translate(
    artifacts: RawArtifact[]
  ): Promise<{ translated: Array<CapabilityManifest | SkillRecord>; failed: string[] }> {
    const translated: Array<CapabilityManifest | SkillRecord> = [];
    const failed: string[] = [];

    for (const artifact of artifacts) {
      try {
        const adapter = this.adapterRegistry.resolve(artifact);
        const result = await adapter.translate(artifact);
        translated.push(result);
      } catch (error) {
        failed.push(`${artifact.id}: ${String(error)}`);
      }
    }

    return { translated, failed };
  }

  /**
   * Stage 3: INGEST — store translated artifacts with metadata
   */
  private async _ingest(
    items: Array<CapabilityManifest | SkillRecord>
  ): Promise<{ ingested: Array<CapabilityManifest | SkillRecord>; failed: string[] }> {
    const ingested: Array<CapabilityManifest | SkillRecord> = [];
    const failed: string[] = [];
    const now = new Date().toISOString();

    for (const item of items) {
      try {
        await this.store.ingest(item, {
          source: this.source,
          version: '1.0.0',
          ingestionDate: now,
          trustTier: this._determineTrustTier(item),
        });
        ingested.push(item);
      } catch (error) {
        const itemId = 'id' in item ? item.id : 'unknown';
        failed.push(`${itemId}: ${String(error)}`);
      }
    }

    return { ingested, failed };
  }

  /**
   * Stage 4: VERIFY — validate translated artifacts against schema registry
   */
  private async _verify(items: Array<CapabilityManifest | SkillRecord>): Promise<VerifyResult> {
    return this.verifyStage.verify(items, this.schemaRegistry);
  }

  /**
   * Assemble IngestionManifest from all stage results.
   */
  private _assembleManifest(
    discovered: RawArtifact[],
    translated: Array<CapabilityManifest | SkillRecord>,
    ingested: Array<CapabilityManifest | SkillRecord>,
    failedTranslate: string[],
    failedIngest: string[],
    verifyResult: VerifyResult
  ): IngestionManifest {
    const now = new Date().toISOString();
    const allFailed = [...failedTranslate, ...failedIngest];

    const capabilities = ingested.filter((item) => 'skills' in item) as CapabilityManifest[];
    const skills = ingested.filter((item) => 'source' in item && !('skills' in item)) as SkillRecord[];

    return {
      source: this.source,
      version: '1.0.0',
      ingestionDate: now,
      expected: {
        capabilities: discovered.filter((a) => a.id.includes('capability')).length,
        skills: discovered.filter((a) => a.id.includes('skill')).length,
        tools: 0,
        memoryRecords: 0,
      },
      actual: {
        capabilities: capabilities.length,
        skills: skills.length,
        tools: 0,
        memoryRecords: 0,
      },
      passed: verifyResult.passed,
      failed: allFailed.map((error) => {
        const [itemId, msg] = error.split(': ');
        return { item: itemId || 'unknown', error: msg || error };
      }),
      untested: verifyResult.untested,
      rollbackPlan: verifyResult.rollbackPlan,
    };
  }

  /**
   * Determine trust tier for an artifact (stub; extended by Phase 6).
   */
  private _determineTrustTier(item: CapabilityManifest | SkillRecord): number {
    if ('skills' in item) return 2; // Suggest for capabilities
    return 1; // Suggest for skills (default)
  }

  /**
   * Create default SchemaRegistry (loads from schemas/ dir).
   */
  private _createDefaultSchemaRegistry(): ISchemaRegistry {
    // Stub implementation for Phase 5 — will integrate with @shay/core SchemaRegistry
    return {
      validate: () => {
        // Phase 5: implement schema validation
      },
      has: () => true,
    };
  }

  /**
   * Create default IngestedCapabilityStore (stub; extended by Phase 5).
   */
  private _createDefaultStore(): IngestedCapabilityStore {
    return {
      ingest: async () => {
        // Stub: Phase 5 implements persistent storage
      },
      list: async () => [],
    };
  }

  /**
   * Create default HermesSource.
   */
  private _createDefaultHermesSource(): HermesSource {
    return new HermesSourceImpl(this.skillsDir);
  }

  /**
   * Create default AdapterRegistry with four built-in adapters.
   */
  private _createDefaultAdapterRegistry(): AdapterRegistry {
    const registry = new DefaultAdapterRegistry();
    // Register default adapters (stubs for Phase 4)
    registry.register('json', new JsonAdapter());
    registry.register('yaml', new YamlAdapter());
    registry.register('markdown', new MarkdownAdapter());
    registry.register('text', new TextAdapter());
    return registry;
  }
}

/**
 * DefaultAdapterRegistry — maps artifact format to Adapter instance.
 */
class DefaultAdapterRegistry implements AdapterRegistry {
  private adapters: Map<string, Adapter> = new Map();

  register(format: string, adapter: Adapter): void {
    this.adapters.set(format, adapter);
  }

  resolve(artifact: RawArtifact): Adapter {
    const adapter = this.adapters.get(artifact.format);
    if (!adapter) {
      throw new Error(`No adapter registered for format: ${artifact.format}`);
    }
    return adapter;
  }
}

/**
 * Built-in Adapters — stubs for Phase 4 implementation.
 */
class JsonAdapter implements Adapter {
  async translate(artifact: RawArtifact): Promise<CapabilityManifest | SkillRecord> {
    throw new Error('JsonAdapter.translate() not yet implemented');
  }
}

class YamlAdapter implements Adapter {
  async translate(artifact: RawArtifact): Promise<CapabilityManifest | SkillRecord> {
    throw new Error('YamlAdapter.translate() not yet implemented');
  }
}

class MarkdownAdapter implements Adapter {
  async translate(artifact: RawArtifact): Promise<CapabilityManifest | SkillRecord> {
    throw new Error('MarkdownAdapter.translate() not yet implemented');
  }
}

class TextAdapter implements Adapter {
  async translate(artifact: RawArtifact): Promise<CapabilityManifest | SkillRecord> {
    throw new Error('TextAdapter.translate() not yet implemented');
  }
}

export type { AdapterRegistry as IAdapterRegistry };
