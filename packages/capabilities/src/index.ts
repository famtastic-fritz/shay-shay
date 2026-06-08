/**
 * @shay/capabilities
 *
 * Internal Capability Registry — register, validate, invoke, and introspect
 * capabilities. Bridges ingested external capabilities via importIngested.
 */

export type { Capability, CapabilityHandler, CapabilityRecord, CapabilityManifest } from './types.js';
export { CapabilityRegistry, CapabilityNotFoundError, ActionNotFoundError } from './registry.js';
export { importIngested } from './from-ingestion.js';
