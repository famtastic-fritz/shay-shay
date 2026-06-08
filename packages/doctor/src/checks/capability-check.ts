/**
 * Capability Registry Health Check
 *
 * Verifies @shay/capabilities CapabilityRegistry manifest completeness
 * and invocability through:
 * 1. Assert each registered capability has id, name, version, description
 * 2. Invoke with probe action ('__doctor_probe__') to verify dispatch
 * 3. ActionNotFoundError is acceptable (probe confirmed dispatch)
 */

import type { HealthCheck, CheckResult, DoctorContext } from '../types.js';

const capabilityCheckImpl: HealthCheck = {
  name: 'Capability Registry Manifests',
  domain: 'capabilities',

  async run(ctx: DoctorContext): Promise<CheckResult> {
    if (!ctx.registry) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'warn',
        detail: 'CapabilityRegistry not provided in context',
        remediation: 're-register capability with a complete manifest',
      };
    }

    try {
      const registry = ctx.registry;

      // Get list of registered capabilities
      if (typeof registry.list !== 'function') {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'CapabilityRegistry does not expose list() method',
          remediation: 're-register capability with a complete manifest',
        };
      }

      const capabilities = await registry.list();
      if (!Array.isArray(capabilities)) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'CapabilityRegistry.list() did not return an array',
          remediation: 're-register capability with a complete manifest',
        };
      }

      const failingCapabilities: string[] = [];
      const incompleteManifests: string[] = [];

      // Check each capability
      for (const capRecord of capabilities) {
        const manifest = capRecord.manifest || capRecord;
        const capId = manifest.id || (capRecord as any).id;

        // Sub-check 1: Verify manifest has required fields
        const hasId = !!manifest.id;
        const hasName = !!manifest.name;
        const hasVersion = !!manifest.version;
        const hasDescription = !!manifest.description;

        if (!hasId || !hasName || !hasVersion || !hasDescription) {
          const missing = [
            !hasId ? 'id' : '',
            !hasName ? 'name' : '',
            !hasVersion ? 'version' : '',
            !hasDescription ? 'description' : '',
          ]
            .filter(Boolean)
            .join(', ');
          incompleteManifests.push(`${capId} (missing: ${missing})`);
        }

        // Sub-check 2: Try to invoke with probe action
        if (typeof registry.invoke !== 'function') {
          return {
            name: this.name,
            domain: this.domain,
            status: 'fail',
            detail: 'CapabilityRegistry does not expose invoke() method',
            remediation: 're-register capability with a complete manifest',
          };
        }

        try {
          await registry.invoke(capId, '__doctor_probe__', {});
        } catch (invocationErr) {
          const errMsg = invocationErr instanceof Error ? invocationErr.message : String(invocationErr);
          // ActionNotFoundError is acceptable (means dispatch worked but action missing)
          // Other errors are failures
          if (!errMsg.includes('ActionNotFoundError') && !errMsg.includes('not found')) {
            failingCapabilities.push(`${capId} (${errMsg})`);
          }
        }
      }

      // Aggregate results
      if (failingCapabilities.length > 0 || incompleteManifests.length > 0) {
        const issues: string[] = [];
        if (failingCapabilities.length > 0) {
          issues.push(`${failingCapabilities.length} capability(ies) failed invocation: ${failingCapabilities.slice(0, 3).join('; ')}${failingCapabilities.length > 3 ? '...' : ''}`);
        }
        if (incompleteManifests.length > 0) {
          issues.push(`${incompleteManifests.length} manifest(s) incomplete: ${incompleteManifests.slice(0, 3).join('; ')}${incompleteManifests.length > 3 ? '...' : ''}`);
        }

        const severity = failingCapabilities.length > 0 ? 'fail' : 'warn';
        return {
          name: this.name,
          domain: this.domain,
          status: severity as any,
          detail: issues.join('; '),
          remediation: 're-register capability with a complete manifest',
        };
      }

      return {
        name: this.name,
        domain: this.domain,
        status: 'pass',
        detail: `All ${capabilities.length} capabilities have complete manifests and are invocable`,
      };
    } catch (err) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'fail',
        detail: `Capability check failed: ${err instanceof Error ? err.message : String(err)}`,
        remediation: 're-register capability with a complete manifest',
      };
    }
  },
};

export const capabilityCheck = (ctx: DoctorContext): Promise<CheckResult> => capabilityCheckImpl.run(ctx);
