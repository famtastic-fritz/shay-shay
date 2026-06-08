import type { DoctorReport, CheckResult } from './types.js';
export type { DoctorContext } from './types.js';

/**
 * CheckFn is a plain async function that takes a DoctorContext and returns a CheckResult.
 * This is the callable form used by Doctor.register() and individual check exports.
 */
export type CheckFn = (ctx: import('./types.js').DoctorContext) => Promise<CheckResult>;

/**
 * Doctor is the continuous immune system for the Shay ecosystem.
 *
 * It maintains an ordered list of registered CheckFns and provides
 * methods to run them all, run specific domains, or configure continuous
 * health monitoring via an injected scheduler.
 *
 * All operations are fully async. No global singletons, no real timers.
 * Tests inject mock contexts and schedulers directly.
 */
export class Doctor {
  private checks: Array<{ name: string; fn: CheckFn }> = [];

  /**
   * register adds a named CheckFn to the Doctor's registry.
   * Checks are stored in registration order.
   *
   * @param name - Identifier for this check
   * @param fn - Async check function returning a CheckResult
   */
  public register(name: string, fn: CheckFn): void {
    this.checks.push({ name, fn });
  }

  /**
   * runAll runs all registered checks and returns a DoctorReport.
   *
   * healthy = true only if no check has status 'fail'.
   * Emits 'doctor:report' event on ctx.eventBus if provided.
   */
  public async runAll(ctx: import('./types.js').DoctorContext): Promise<DoctorReport> {
    const timestamp = new Date().toISOString();
    const results: CheckResult[] = [];

    for (const { fn } of this.checks) {
      const result = await fn(ctx);
      results.push(result);
    }

    const healthy = !results.some((r) => r.status === 'fail');

    const report: DoctorReport = {
      timestamp,
      healthy,
      checks: results,
    };

    if (ctx.eventBus) {
      ctx.eventBus.emit({
        id: crypto.randomUUID(),
        type: 'doctor:report',
        source: 'doctor',
        timestamp,
        payload: report,
      });
    }

    return report;
  }

  /**
   * runContinuous registers a recurring job with the injected scheduler
   * that calls runAll(ctx) on each tick.
   *
   * Tests invoke the scheduled function directly — no real timers.
   */
  public runContinuous(
    ctx: import('./types.js').DoctorContext,
    scheduler: { schedule(fn: () => void | Promise<void>, intervalMs: number): void }
  ): void {
    const job = async () => {
      await this.runAll(ctx);
    };

    scheduler.schedule(job, 60000); // Default: 60 second interval
  }
}
