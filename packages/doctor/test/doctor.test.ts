/**
 * Hermetic tests for the Doctor class.
 *
 * Tests verify:
 * - AGGREGATE test: all six checks registered, all passing, healthy === true, checks.length === 6
 * - FAIL-AGGREGATE test: one check returns 'fail', healthy === false
 * - EVENT-BUS test: report emitted via EventBus with correct payload
 * - CONTINUOUS test: runContinuous with spy scheduler, function invoked deterministically
 * - Strictly disjoint test groups
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { Doctor } from '../src/doctor.js';
import { EventBus, SchemaRegistry } from '@shay/core';
import type { DoctorContext, CheckFn, DoctorReport } from '../src/doctor.js';
import type { ShayConfig } from '@shay/core';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

describe('doctor', () => {
  let schemaRegistry: SchemaRegistry;
  let tmpdir: string;

  beforeEach(() => {
    schemaRegistry = new SchemaRegistry();

    // Load schemas
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const schemasDir = path.resolve(__dirname, '../../../schemas');

    schemaRegistry.loadFromDir(schemasDir);

    tmpdir = fs.mkdtempSync(path.join(os.tmpdir(), 'shay-doctor-test-'));
  });

  describe('aggregate', () => {
    it('should run all registered checks and produce a healthy report', async () => {
      const doctor = new Doctor();

      // Register six passing checks
      const checks: CheckFn[] = [
        async () => ({
          name: 'check-1',
          domain: 'memory',
          status: 'pass',
          detail: 'passed',
        }),
        async () => ({
          name: 'check-2',
          domain: 'capability',
          status: 'pass',
          detail: 'passed',
        }),
        async () => ({
          name: 'check-3',
          domain: 'ingestion',
          status: 'pass',
          detail: 'passed',
        }),
        async () => ({
          name: 'check-4',
          domain: 'connector',
          status: 'pass',
          detail: 'passed',
        }),
        async () => ({
          name: 'check-5',
          domain: 'authority',
          status: 'pass',
          detail: 'passed',
        }),
        async () => ({
          name: 'check-6',
          domain: 'config',
          status: 'pass',
          detail: 'passed',
        }),
      ];

      checks.forEach((checkFn, idx) => {
        doctor.register(`check-${idx + 1}`, checkFn);
      });

      const eventLog = path.join(tmpdir, 'events.jsonl');
      const eventBus = new EventBus(schemaRegistry, eventLog);

      const config: ShayConfig = {
        version: '1.0.0',
        name: 'shay',
      };

      const ctx: DoctorContext = {
        config,
        schemaRegistry,
        eventBus,
      };

      const report = await doctor.runAll(ctx);

      expect(report.healthy).toBe(true);
      expect(report.checks).toHaveLength(6);
      expect(report.timestamp).toBeDefined();
    });
  });

  describe('fail-aggregate', () => {
    it('should mark report as unhealthy if one check fails', async () => {
      const doctor = new Doctor();

      // Register one passing and one failing check
      const passingCheck: CheckFn = async () => ({
        name: 'passing',
        domain: 'memory',
        status: 'pass',
        detail: 'passed',
      });

      const failingCheck: CheckFn = async () => ({
        name: 'failing',
        domain: 'capability',
        status: 'fail',
        detail: 'failed',
        remediation: 'fix it',
      });

      doctor.register('passing-check', passingCheck);
      doctor.register('failing-check', failingCheck);

      const eventLog = path.join(tmpdir, 'events2.jsonl');
      const eventBus = new EventBus(schemaRegistry, eventLog);

      const config: ShayConfig = {
        version: '1.0.0',
        name: 'shay',
      };

      const ctx: DoctorContext = {
        config,
        schemaRegistry,
        eventBus,
      };

      const report = await doctor.runAll(ctx);

      expect(report.healthy).toBe(false);
      expect(report.checks).toHaveLength(2);
      expect(report.checks.some((c) => c.status === 'fail')).toBe(true);
    });
  });

  describe('event-bus', () => {
    it('should emit doctor:report event on EventBus', async () => {
      const doctor = new Doctor();

      const checkFn: CheckFn = async () => ({
        name: 'test-check',
        domain: 'test',
        status: 'pass',
        detail: 'passed',
      });

      doctor.register('test-check', checkFn);

      const eventLog = path.join(tmpdir, 'events3.jsonl');
      const eventBus = new EventBus(schemaRegistry, eventLog);

      const config: ShayConfig = {
        version: '1.0.0',
        name: 'shay',
      };

      const ctx: DoctorContext = {
        config,
        schemaRegistry,
        eventBus,
      };

      let emittedEvent: any = null;
      eventBus.subscribe('doctor:report', (event) => {
        emittedEvent = event;
      });

      const report = await doctor.runAll(ctx);

      // Verify event was emitted
      expect(emittedEvent).toBeDefined();
      expect(emittedEvent.type).toBe('doctor:report');
      expect(emittedEvent.payload).toEqual(report);
    });
  });

  describe('continuous', () => {
    it('should schedule recurring health checks with injected scheduler', async () => {
      const doctor = new Doctor();

      const checkFn: CheckFn = async () => ({
        name: 'continuous-check',
        domain: 'test',
        status: 'pass',
        detail: 'passed',
      });

      doctor.register('continuous-check', checkFn);

      const eventLog = path.join(tmpdir, 'events4.jsonl');
      const eventBus = new EventBus(schemaRegistry, eventLog);

      const config: ShayConfig = {
        version: '1.0.0',
        name: 'shay',
      };

      const ctx: DoctorContext = {
        config,
        schemaRegistry,
        eventBus,
      };

      // Create a spy scheduler
      let scheduledFn: (() => void | Promise<void>) | null = null;
      let scheduledIntervalMs: number | null = null;

      const spyScheduler = {
        schedule: (fn: () => void | Promise<void>, intervalMs: number) => {
          scheduledFn = fn;
          scheduledIntervalMs = intervalMs;
        },
      };

      doctor.runContinuous(ctx, spyScheduler);

      // Verify that schedule was called
      expect(scheduledFn).toBeDefined();
      expect(scheduledIntervalMs).toBe(60000);

      // Call the scheduled function directly (no real timer)
      if (scheduledFn) {
        await scheduledFn();
      }

      // Verify that at least one health check was executed by reading the event log
      const eventLogContent = fs.readFileSync(eventLog, 'utf-8');
      expect(eventLogContent).toContain('doctor:report');
    });
  });
});
