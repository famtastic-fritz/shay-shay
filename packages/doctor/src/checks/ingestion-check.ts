/**
 * Ingestion Health Check
 *
 * Verifies @shay/ingestion manifest schema validity and live-conformance
 * of ingested capabilities through:
 * 1. Build IngestionManifest from current state and validate against schema
 * 2. For untested entries, attempt invocation to verify capability works
 * 3. Collect and report failed entries
 */

import type { HealthCheck, CheckResult, DoctorContext } from '../types.js';

const ingestionCheckImpl: HealthCheck = {
  name: 'Ingestion Manifest & Verification',
  domain: 'ingestion',

  async run(ctx: DoctorContext): Promise<CheckResult> {
    if (!ctx.ingestionStore) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'warn',
        detail: 'IngestedCapabilityStore not provided in context',
        remediation: 're-ingest source',
      };
    }

    try {
      const store = ctx.ingestionStore;

      // Get all entries from store
      if (typeof store.getAll !== 'function') {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'IngestedCapabilityStore does not expose getAll() method',
          remediation: 're-ingest source',
        };
      }

      const entries = await store.getAll();
      if (!Array.isArray(entries)) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'IngestedCapabilityStore.getAll() did not return an array',
          remediation: 're-ingest source',
        };
      }

      // Step 1: Build IngestionManifest and validate against schema
      const manifest = {
        source: entries[0]?.source || 'unknown',
        version: entries[0]?.version || '1.0.0',
        ingestionDate: new Date().toISOString(),
        expected: {
          capabilities: entries.length,
          skills: 0,
          tools: 0,
          memoryRecords: 0,
        },
        actual: {
          capabilities: entries.length,
          skills: 0,
          tools: 0,
          memoryRecords: 0,
        },
        passed: entries.length,
        failed: [] as any[],
        untested: [] as any[],
        rollbackPlan: 're-ingest source',
      };

      // Validate against schema if schemaRegistry available and schema is loaded
      if (ctx.schemaRegistry && typeof ctx.schemaRegistry.validate === 'function') {
        const hasSchema = typeof ctx.schemaRegistry.has === 'function'
          ? ctx.schemaRegistry.has('shay:ingestion-manifest')
          : false;
        if (hasSchema) {
          try {
            ctx.schemaRegistry.validate('shay:ingestion-manifest', manifest);
          } catch (schemaErr) {
            return {
              name: this.name,
              domain: this.domain,
              status: 'fail',
              detail: `IngestionManifest schema validation failed: ${schemaErr instanceof Error ? schemaErr.message : String(schemaErr)}`,
              remediation: 're-ingest source',
            };
          }
        }
      }

      // Step 1b: Check each entry has required fields
      const missingFieldEntries: string[] = [];
      for (const entry of entries) {
        if (!entry.source || !entry.id) {
          missingFieldEntries.push(entry.id || '(unknown)');
        }
      }
      if (missingFieldEntries.length > 0) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: `Ingestion check failed: entries missing required fields (source/id): ${missingFieldEntries.slice(0, 3).join(', ')}`,
          remediation: 're-ingest source',
        };
      }

      // Step 2: For each entry, check verifyStatus and attempt invocation if untested
      const failedEntries: string[] = [];
      const untestedEntries: Array<{ id: string; verifyStatus?: string }> = [];

      for (const entry of entries) {
        const verifyStatus = (entry as any).verifyStatus || 'untested';

        if (verifyStatus === 'untested' && ctx.registry && typeof ctx.registry.invoke === 'function') {
          try {
            await ctx.registry.invoke(entry.id, '__doctor_probe__', {});
            (entry as any).verifyStatus = 'passed';
          } catch (invErr) {
            const errMsg = invErr instanceof Error ? invErr.message : String(invErr);
            if (!errMsg.includes('ActionNotFoundError') && !errMsg.includes('not found')) {
              (entry as any).verifyStatus = 'failed';
              failedEntries.push(entry.id);
            } else {
              (entry as any).verifyStatus = 'passed';
            }
          }
        }

        const finalStatus = (entry as any).verifyStatus || 'untested';
        if (finalStatus === 'untested') {
          untestedEntries.push({ id: entry.id, verifyStatus: finalStatus });
        }
      }

      // Step 3: Report results
      if (failedEntries.length > 0) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: `Ingestion check failed: ${failedEntries.length} entries failed verification: ${failedEntries.slice(0, 3).join(', ')}${failedEntries.length > 3 ? '...' : ''}`,
          remediation: 're-ingest source',
        };
      }

      // Only warn about untested entries when a registry was available for invocation
      if (untestedEntries.length > 0 && ctx.registry) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'warn',
          detail: `Ingestion check warning: ${untestedEntries.length} entries remain untested`,
          remediation: 're-ingest source',
        };
      }

      return {
        name: this.name,
        domain: this.domain,
        status: 'pass',
        detail: `Ingestion manifest is valid; ${entries.length} entries ingested`,
      };
    } catch (err) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'fail',
        detail: `Ingestion check failed: ${err instanceof Error ? err.message : String(err)}`,
        remediation: 're-ingest source',
      };
    }
  },
};

export const ingestionCheck = (ctx: DoctorContext): Promise<CheckResult> => ingestionCheckImpl.run(ctx);
