/**
 * @shay/capabilities — importIngested
 *
 * Bridges the @shay/ingestion IngestedCapabilityStore into the CapabilityRegistry.
 * Each entry is imported as source:'external' with TrustTier.Suggest (1).
 */

import { TrustTier } from '@shay/core';
import type { IngestedCapabilityStore } from '@shay/ingestion';
import type { CapabilityRegistry } from './registry.js';

/**
 * Pull all entries from an IngestedCapabilityStore into the provided
 * CapabilityRegistry. Each entry is tagged:
 *   - source: 'external'
 *   - trustTier: TrustTier.Suggest (1)
 *
 * Entries whose IDs are already registered are silently skipped to allow
 * idempotent imports.
 *
 * The handler for imported capabilities is a no-op stub that throws
 * an informative error — external capabilities are typically invoked
 * via @shay/bridge, not directly through the registry handler.
 */
export function importIngested(
  store: IngestedCapabilityStore,
  registry: CapabilityRegistry
): void {
  const entries = store.getAll();
  for (const entry of entries) {
    if (registry.has(entry.id)) continue;

    const { id, version, name, description, permissions, dependencies, entrypoint } = entry;
    const manifest = { id, version, name, description, permissions, dependencies, entrypoint };

    registry.register(
      manifest,
      async (_action: string, _input: unknown) => {
        throw new Error(
          `Capability '${id}' is an external ingested capability. ` +
          `Invoke it via @shay/bridge, not directly through the registry handler.`
        );
      },
      { source: 'external', trustTier: TrustTier.Suggest }
    );
  }
}
