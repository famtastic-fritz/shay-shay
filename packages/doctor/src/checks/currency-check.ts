/**
 * Currency (Release) Health Check
 *
 * Verifies release currency via @shay/senses ReleaseMonitor or ReleaseAlerts:
 * 1. Retrieve alerts via ctx.senses.getAlerts() or similar accessor
 * 2. For each alert affecting ingested sources:
 *    - breaking class → 'fail' with 're-ingest' remediation
 *    - feature/deprecation class → 'warn'
 * 3. Aggregate to overall status
 */

import type { HealthCheck, CheckResult, DoctorContext } from '../types.js';

const currencyCheckImpl: HealthCheck = {
  name: 'Release Currency & Alerts',
  domain: 'currency',

  async run(ctx: DoctorContext): Promise<CheckResult> {
    if (!ctx.senses) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'warn',
        detail: 'ReleaseMonitor (senses) not provided in context',
        remediation: 're-ingest',
      };
    }

    try {
      const senses = ctx.senses;

      // Try multiple possible accessor methods
      let alerts: any[] = [];
      if (typeof (senses as any).getAlerts === 'function') {
        alerts = await (senses as any).getAlerts();
      } else if (typeof (senses as any).digest === 'function') {
        alerts = await (senses as any).digest();
      } else if (typeof (senses as any).alerts === 'function') {
        alerts = await (senses as any).alerts();
      } else if ((senses as any).alerts && Array.isArray((senses as any).alerts)) {
        alerts = (senses as any).alerts;
      }

      if (!Array.isArray(alerts)) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'warn',
          detail: 'ReleaseMonitor does not expose getAlerts() or equivalent accessor',
          remediation: 're-ingest',
        };
      }

      // Filter alerts that affect ingested sources
      const affectingIngested = alerts.filter((alert) => alert.affectsIngested === true);

      if (affectingIngested.length === 0) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'pass',
          detail: 'No release alerts affecting ingested sources',
        };
      }

      // Aggregate by severity
      let hasBreaking = false;
      let hasFeatureOrDeprecation = false;
      const affectedSources: string[] = [];

      for (const alert of affectingIngested) {
        const releaseClass = alert.releaseClass;
        const source = alert.ingestedSource || alert.event?.source || 'unknown';

        if (!affectedSources.includes(source)) {
          affectedSources.push(source);
        }

        if (releaseClass === 'breaking') {
          hasBreaking = true;
        } else if (releaseClass === 'feature' || releaseClass === 'deprecation') {
          hasFeatureOrDeprecation = true;
        }
      }

      // Determine status
      if (hasBreaking) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: `Critical release: breaking changes affecting ${affectedSources.join(', ')}`,
          remediation: 're-ingest',
        };
      }

      if (hasFeatureOrDeprecation) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'warn',
          detail: `Release updates available: ${affectedSources.join(', ')} (feature/deprecation)`,
          remediation: 're-ingest',
        };
      }

      return {
        name: this.name,
        domain: this.domain,
        status: 'pass',
        detail: `All ${affectingIngested.length} alerts reviewed; no actionable breaks`,
      };
    } catch (err) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'fail',
        detail: `Currency check failed: ${err instanceof Error ? err.message : String(err)}`,
        remediation: 're-ingest',
      };
    }
  },
};

export const currencyCheck = (ctx: DoctorContext): Promise<CheckResult> => currencyCheckImpl.run(ctx);
