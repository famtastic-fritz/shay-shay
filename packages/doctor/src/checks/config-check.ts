/**
 * Config Health Check
 *
 * Verifies configuration object consistency through:
 * 1. Validate config against 'shay:config' JSON schema
 * 2. Check for model-id style mismatches (no internal aliases)
 */

import type { HealthCheck, CheckResult, DoctorContext } from '../types.js';

const configCheckImpl: HealthCheck = {
  name: 'Configuration Consistency',
  domain: 'config',

  async run(ctx: DoctorContext): Promise<CheckResult> {
    if (!ctx.config) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'warn',
        detail: 'Configuration object not provided in context',
        remediation: 'correct config before starting Shay',
      };
    }

    try {
      const config = ctx.config;

      // Sub-check 1: Schema validation
      if (!ctx.schemaRegistry) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'warn',
          detail: 'SchemaRegistry not provided in context; cannot validate config schema',
          remediation: 'correct config before starting Shay',
        };
      }

      if (typeof ctx.schemaRegistry.validate === 'function') {
        try {
          ctx.schemaRegistry.validate('shay:config', config);
        } catch (schemaErr) {
          return {
            name: this.name,
            domain: this.domain,
            status: 'fail',
            detail: `Config schema validation failed: ${schemaErr instanceof Error ? schemaErr.message : String(schemaErr)}`,
            remediation: 'correct config before starting Shay',
          };
        }
      }

      // Sub-check 2: Provider/model-id style check
      const internalModelAliases = [
        'model-small',
        'model-medium',
        'model-large',
        'vendor-a-model',
        'vendor-b-model',
      ];

      const styleIssues: string[] = [];

      if (config.model && typeof config.model === 'string') {
        for (const alias of internalModelAliases) {
          if (config.model.includes(alias) && !config.model.includes('-')) {
            // Alias found without version; flag as style mismatch
            styleIssues.push(`model "${config.model}" uses internal alias without version specificity`);
            break;
          }
        }
      }

      if (styleIssues.length > 0) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'warn',
          detail: styleIssues.join('; '),
          remediation: 'correct config before starting Shay',
        };
      }

      return {
        name: this.name,
        domain: this.domain,
        status: 'pass',
        detail: 'Configuration object is valid and consistent',
      };
    } catch (err) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'fail',
        detail: `Config check failed: ${err instanceof Error ? err.message : String(err)}`,
        remediation: 'correct config before starting Shay',
      };
    }
  },
};

export const configCheck = (ctx: DoctorContext): Promise<CheckResult> => configCheckImpl.run(ctx);
