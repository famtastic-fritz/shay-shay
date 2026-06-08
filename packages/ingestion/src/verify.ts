/**
 * VERIFY Stage — Schema Validation
 *
 * Validates translated artifacts (CapabilityManifest and SkillRecord) against
 * registered JSON schemas. Produces a VerifyResult with pass/fail/untested counts
 * and a rollback plan for failed items.
 *
 * Validation rules:
 * - CapabilityManifest: validated against 'shay:capability-manifest' schema
 * - SkillRecord: validated against 'shay:skill-record' schema
 * - Live execution validation deferred to Phase 7 Doctor
 */

import type { CapabilityManifest, SkillRecord } from './types.js';

/**
 * SchemaRegistry interface for validation
 */
export interface ISchemaRegistry {
  validate(name: string, payload: unknown): void;
  has(name: string): boolean;
}

/**
 * FailedItem — artifact that failed schema validation
 */
export interface FailedItem {
  item: string;
  error: string;
}

/**
 * UntestedItem — artifact that passed structural validation but awaits live execution testing
 */
export interface UntestedItem {
  item: string;
  reason: string;
}

/**
 * VerifyResult — outcome of verification stage
 */
export interface VerifyResult {
  passed: number;
  failed: FailedItem[];
  untested: UntestedItem[];
  rollbackPlan: string;
}

/**
 * VerifyStage — validates translated artifacts against schema registry
 */
export class VerifyStage {
  /**
   * Verify a batch of translated artifacts against the schema registry.
   * Returns counts and details of passed/failed/untested items.
   * Rollback plan is static and applies to the entire ingestion source.
   */
  verify(items: Array<CapabilityManifest | SkillRecord>, registry: ISchemaRegistry): VerifyResult {
    let passedCount = 0;
    const failed: FailedItem[] = [];
    const untested: UntestedItem[] = [];

    for (const item of items) {
      const itemId = this._getItemId(item);
      const schemaName = this._getSchemaName(item);

      try {
        // Validate against schema
        if (registry.has(schemaName)) {
          registry.validate(schemaName, item);
          passedCount++;

          // Live execution testing deferred to Phase 7 Doctor
          if (this._shouldDeferExecution(item)) {
            untested.push({
              item: itemId,
              reason: 'Live execution validation deferred to Phase 7 Doctor',
            });
          }
        } else {
          failed.push({
            item: itemId,
            error: `Schema '${schemaName}' not found in registry`,
          });
        }
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        failed.push({
          item: itemId,
          error: errorMsg,
        });
      }
    }

    return {
      passed: passedCount,
      failed,
      untested,
      rollbackPlan: this._generateRollbackPlan(),
    };
  }

  /**
   * Extract item ID for error reporting
   */
  private _getItemId(item: CapabilityManifest | SkillRecord): string {
    return item.id || 'unknown';
  }

  /**
   * Determine schema name based on item type
   */
  private _getSchemaName(item: CapabilityManifest | SkillRecord): string {
    if (this._isCapabilityManifest(item)) {
      return 'shay:capability-manifest';
    }
    return 'shay:skill-record';
  }

  /**
   * Type guard: is this a CapabilityManifest?
   */
  private _isCapabilityManifest(item: CapabilityManifest | SkillRecord): boolean {
    return 'skills' in item;
  }

  /**
   * Determine if live execution testing should be deferred for this item.
   * Phase 7 Doctor will handle runtime validation.
   */
  private _shouldDeferExecution(item: CapabilityManifest | SkillRecord): boolean {
    // Stub: Phase 7 will define deferred execution criteria
    // For now, all items pass structural validation; execution is deferred
    return true;
  }

  /**
   * Generate a static rollback plan for the entire ingestion source.
   * Provides clear recovery instructions if issues are discovered post-ingestion.
   */
  private _generateRollbackPlan(): string {
    return 'Remove ingested entries from IngestedCapabilityStore for source <source>; re-run DISCOVER to restore previous state.';
  }
}
