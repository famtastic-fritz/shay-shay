/**
 * Authority Health Check
 *
 * Verifies @shay/core AuthorityRegistry tier policy enforcement through:
 * 1. Check ingested entries don't have trustTier > Suggest (1)
 * 2. Check external capabilities don't exceed Suggest without manual grant
 */

import type { HealthCheck, CheckResult, DoctorContext } from '../types.js';

const authorityCheckImpl: HealthCheck = {
  name: 'Authority Tier Policy Enforcement',
  domain: 'authority',

  async run(ctx: DoctorContext): Promise<CheckResult> {
    if (!ctx.authority) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'warn',
        detail: 'AuthorityRegistry not provided in context',
        remediation: 'revoke elevated tier or add manual grant via authority.setTier({manual:true})',
      };
    }

    try {
      const authority = ctx.authority;
      const violations: string[] = [];

      // Invariant 1: Check ingested entries don't exceed Suggest tier
      if (ctx.ingestionStore && typeof ctx.ingestionStore.getAll === 'function') {
        const entries = await ctx.ingestionStore.getAll();
        for (const entry of entries) {
          const trustTier = entry.trustTier ?? 1;
          if (trustTier > 1) {
            // Suggest = 1, so > 1 is a violation
            violations.push(`Ingested entry ${entry.id} has trustTier ${trustTier} (exceeds Suggest)`);
          }
        }
      }

      // Invariant 2: Check external capabilities don't exceed Suggest without manual grant
      if (ctx.registry && typeof ctx.registry.list === 'function') {
        const capabilities = await ctx.registry.list();
        for (const capRecord of capabilities) {
          const source = capRecord.source || 'unknown';
          if (source === 'external') {
            const trustTier = capRecord.trustTier ?? 1;
            if (trustTier > 1) {
              // Check if there's a manual grant on record
              const capId = capRecord.manifest?.id || (capRecord as any).id;
              const manualGrantKey = `${capId}:manual`;

              let hasManualGrant = false;
              try {
                // Attempt to retrieve the tier for the manual grant key
                const grantTier = typeof authority.getTier === 'function' ? authority.getTier(manualGrantKey) : undefined;
                hasManualGrant = grantTier !== undefined && grantTier > 0;
              } catch {
                // getTier might not exist or might throw; assume no grant
              }

              if (!hasManualGrant) {
                violations.push(`External capability ${capId} has trustTier ${trustTier} without manual grant`);
              }
            }
          }
        }
      }

      if (violations.length > 0) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: violations.slice(0, 3).join('; ') + (violations.length > 3 ? `... (${violations.length - 3} more)` : ''),
          remediation: 'revoke elevated tier or add manual grant via authority.setTier({manual:true})',
        };
      }

      return {
        name: this.name,
        domain: this.domain,
        status: 'pass',
        detail: 'Authority registry enforces correct tier policies',
      };
    } catch (err) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'fail',
        detail: `Authority check failed: ${err instanceof Error ? err.message : String(err)}`,
        remediation: 'revoke elevated tier or add manual grant via authority.setTier({manual:true})',
      };
    }
  },
};

export const authorityCheck = (ctx: DoctorContext): Promise<CheckResult> => authorityCheckImpl.run(ctx);
