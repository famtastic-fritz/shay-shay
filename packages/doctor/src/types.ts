/**
 * @shay/doctor — Core types
 *
 * Defines the HealthCheck, CheckResult, DoctorReport, and DoctorContext
 * interfaces used throughout the Doctor subsystem for system health
 * verification and diagnostics.
 */

import type { MemoryStore, EmbeddingProvider } from '@shay/memory';
import type { CapabilityRegistry } from '@shay/capabilities';
import type { IngestedCapabilityStore } from '@shay/ingestion';
import type { ReleaseMonitor } from '@shay/senses';
import type { EventBus, SchemaRegistry } from '@shay/core';

/**
 * CheckStatus represents the outcome of a single health check.
 *
 * - 'pass': The check completed successfully and conditions are met
 * - 'warn': The check completed but flagged a non-critical issue
 * - 'fail': The check detected a critical failure or missing requirement
 */
export type CheckStatus = 'pass' | 'warn' | 'fail';

/**
 * HealthCheck defines a single diagnostic probe into system state.
 *
 * A check is a pure function that examines one aspect of the system
 * (e.g., memory store connectivity, schema registry validity, event bus state)
 * and reports its findings back to the Doctor.
 *
 * Properties:
 *   name - Short, human-readable name of the check (e.g., "Memory Store Connected")
 *   domain - Domain this check belongs to (e.g., "memory", "schema", "events")
 *   run - Async function that performs the check and returns a CheckResult
 */
export interface HealthCheck {
  name: string;
  domain: string;
  run(ctx: DoctorContext): Promise<CheckResult>;
}

/**
 * CheckResult represents the output of a single health check.
 *
 * Properties:
 *   name - Name of the check that produced this result
 *   domain - Domain the check belongs to
 *   status - Outcome: 'pass', 'warn', or 'fail'
 *   detail - Detailed message explaining the check result
 *   remediation - Optional guidance on how to fix a 'warn' or 'fail' result
 */
export interface CheckResult {
  name: string;
  domain: string;
  status: CheckStatus;
  detail: string;
  remediation?: string;
}

/**
 * DoctorReport is the final health report from a Doctor run.
 *
 * Properties:
 *   timestamp - ISO 8601 timestamp when the report was generated
 *   healthy - Boolean: true if all checks passed, false if any failed
 *   checks - Array of CheckResult objects from all health checks
 */
export interface DoctorReport {
  timestamp: string;
  healthy: boolean;
  checks: CheckResult[];
}

/**
 * DoctorContext provides injected subsystem instances to health checks.
 *
 * Checks receive a DoctorContext and call out to whatever subsystems
 * they need to probe. All fields are optional to allow a-la-carte
 * dependency injection based on what checks are registered.
 *
 * Properties:
 *   memory - Optional MemoryStore instance for verifying memory layer health
 *   embeddingProvider - Optional EmbeddingProvider for semantic search layer
 *   registry - Optional CapabilityRegistry for capability layer health
 *   ingestionStore - Optional IngestedCapabilityStore for ingestion state
 *   senses - Optional ReleaseMonitor for release tracking and version checks
 *   eventBus - Optional EventBus for event infrastructure validation
 *   schemaRegistry - Optional SchemaRegistry for schema validation
 *   authority - Optional AuthorityRegistry for tier policy enforcement
 *   mcp - Optional McpClient for transport validation
 *   config - Optional ShayConfig for configuration validation
 */
export interface DoctorContext {
  memory?: MemoryStore;
  embeddingProvider?: EmbeddingProvider;
  registry?: CapabilityRegistry;
  ingestionStore?: IngestedCapabilityStore;
  senses?: ReleaseMonitor;
  eventBus?: EventBus;
  schemaRegistry?: SchemaRegistry;
  authority?: any;
  mcp?: any;
  config?: any;
}
