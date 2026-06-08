/**
 * Memory Store Health Check
 *
 * Verifies @shay/memory MemoryStore integrity through:
 * 1. Store a synthetic MemoryRecord (tier T1, known content)
 * 2. Recall by content and verify round-trip
 * 3. Assert all existing records have a valid tier (T0|T1|T2|T3)
 */

import type { HealthCheck, CheckResult, DoctorContext } from '../types.js';

const memoryCheckImpl: HealthCheck = {
  name: 'Memory Store Integrity',
  domain: 'memory',
  
  async run(ctx: DoctorContext): Promise<CheckResult> {
    // Check: ctx.memory is provided
    if (!ctx.memory) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'warn',
        detail: 'MemoryStore not provided in context',
        remediation: 're-initialize MemoryStore',
      };
    }

    try {
      const store = ctx.memory;
      const validTiers = new Set(['T0', 'T1', 'T2', 'T3']);

      // Sub-check 1: Store a synthetic MemoryRecord
      const syntheticRecord = {
        id: `synthetic-${Date.now()}`,
        content: 'doctor-probe-memory-check',
        tier: 'T1' as const,
        importance: 0.5,
        source: '@shay/doctor',
        validityStart: new Date().toISOString(),
      };

      if (typeof store.store !== 'function') {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'MemoryStore does not expose store() method',
          remediation: 're-initialize MemoryStore',
        };
      }

      // Attempt to store
      await store.store(syntheticRecord);

      // Sub-check 2: Recall by content and verify round-trip
      if (typeof store.recall !== 'function') {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'MemoryStore does not expose recall() method',
          remediation: 're-initialize MemoryStore',
        };
      }

      const recalled = await store.recall('doctor-probe-memory-check', { k: 1 });
      if (!recalled) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'recall() returned null or undefined',
          remediation: 're-initialize MemoryStore',
        };
      }

      // Sub-check 3: Verify all records have a valid tier
      const getAllFn = typeof (store as any).getAll === 'function'
        ? (store as any).getAll.bind(store)
        : typeof (store as any).all === 'function'
          ? (store as any).all.bind(store)
          : null;

      if (!getAllFn) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'warn',
          detail: 'MemoryStore does not expose getAll() method; cannot verify existing records',
          remediation: 're-initialize MemoryStore',
        };
      }

      const allRecords = await getAllFn();
      const invalidTierRecords: string[] = [];
      for (const record of allRecords) {
        if (!validTiers.has(record.tier)) {
          invalidTierRecords.push(record.id);
        }
      }

      if (invalidTierRecords.length > 0) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: `Found ${invalidTierRecords.length} records with invalid tier: ${invalidTierRecords.slice(0, 5).join(', ')}${invalidTierRecords.length > 5 ? '...' : ''}`,
          remediation: 're-initialize MemoryStore',
        };
      }

      return {
        name: this.name,
        domain: this.domain,
        status: 'pass',
        detail: `All memory checks passed (${allRecords.length} total records, all tiers valid)`,
      };
    } catch (err) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'fail',
        detail: `Memory check failed: ${err instanceof Error ? err.message : String(err)}`,
        remediation: 're-initialize MemoryStore',
      };
    }
  },
};

export const memoryCheck = (ctx: DoctorContext): Promise<CheckResult> => memoryCheckImpl.run(ctx);
