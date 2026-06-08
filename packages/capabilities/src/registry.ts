/**
 * @shay/capabilities — CapabilityRegistry
 *
 * Central registry for all Shay capabilities. Validates manifests against the
 * 'shay:capability-manifest' JSON schema before registration. Supports
 * registration, lookup, listing, invocation, and removal of capabilities.
 */

import { SchemaRegistry, TrustTier } from '@shay/core';
import type { CapabilityManifest } from '@shay/ingestion';
import type { CapabilityHandler, CapabilityRecord } from './types.js';
import fs from 'node:fs';
import path from 'node:path';

/**
 * Thrown when a capability ID is not found in the registry.
 */
export class CapabilityNotFoundError extends Error {
  constructor(id: string) {
    super(`Capability '${id}' not found`);
    this.name = 'CapabilityNotFoundError';
  }
}

/**
 * Thrown when an action is not declared on the capability's manifest
 * (or when the capability has no declared actions list and the action
 * is otherwise unresolvable — in that case invocation proceeds and
 * the handler is expected to validate).
 */
export class ActionNotFoundError extends Error {
  constructor(id: string, action: string) {
    super(`Action '${action}' not found on capability '${id}'`);
    this.name = 'ActionNotFoundError';
  }
}

/** Lazily loaded schema registry pre-loaded with the capability-manifest schema. */
function buildSchemaRegistry(): SchemaRegistry {
  const sr = new SchemaRegistry();
  const schemaPath = path.resolve(
    new URL('../../../schemas/capability-manifest.schema.json', import.meta.url).pathname
  );
  const raw = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));
  sr.register('shay:capability-manifest', raw);
  return sr;
}

/**
 * CapabilityRegistry manages internal and external capability registrations.
 *
 * - Internal capabilities default to TrustTier.Confirm (3).
 * - External capabilities default to TrustTier.Suggest (1).
 */
export class CapabilityRegistry {
  private records: Map<string, CapabilityRecord> = new Map();
  private schemaRegistry: SchemaRegistry;

  constructor(schemaRegistry?: SchemaRegistry) {
    this.schemaRegistry = schemaRegistry ?? buildSchemaRegistry();
  }

  /**
   * Register a capability with its handler.
   *
   * @param manifest - Must be valid against 'shay:capability-manifest' schema.
   * @param handler - Async function handling (action, input) invocations.
   * @param options - Optional source and trustTier overrides.
   * @throws ValidationError if the manifest fails schema validation.
   */
  register(
    manifest: CapabilityManifest,
    handler: CapabilityHandler,
    options?: { source?: 'internal' | 'external'; trustTier?: TrustTier }
  ): void {
    this.schemaRegistry.validate('shay:capability-manifest', manifest);
    const source = options?.source ?? 'internal';
    const trustTier = options?.trustTier ?? (source === 'external' ? TrustTier.Suggest : TrustTier.Confirm);
    this.records.set(manifest.id, { manifest, handler, source, trustTier });
  }

  /**
   * Retrieve a capability record by ID.
   *
   * @throws CapabilityNotFoundError if not registered.
   */
  get(id: string): CapabilityRecord {
    const record = this.records.get(id);
    if (!record) throw new CapabilityNotFoundError(id);
    return record;
  }

  /**
   * List all registered capability records.
   */
  list(): CapabilityRecord[] {
    return Array.from(this.records.values());
  }

  /**
   * Check whether a capability ID is registered.
   */
  has(id: string): boolean {
    return this.records.has(id);
  }

  /**
   * Invoke a capability action with the given input.
   *
   * @throws CapabilityNotFoundError if the capability is not registered.
   * @throws ActionNotFoundError if the manifest declares explicit actions and the requested action is absent.
   */
  async invoke(id: string, action: string, input: unknown): Promise<unknown> {
    const record = this.get(id);
    // If the manifest has an explicit actions list, validate the action name.
    const actions = (record.manifest as any).actions as string[] | undefined;
    if (Array.isArray(actions) && !actions.includes(action)) {
      throw new ActionNotFoundError(id, action);
    }
    return record.handler(action, input);
  }

  /**
   * Remove a capability from the registry.
   *
   * @throws CapabilityNotFoundError if not registered.
   */
  unregister(id: string): void {
    if (!this.records.has(id)) throw new CapabilityNotFoundError(id);
    this.records.delete(id);
  }
}
