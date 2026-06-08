/**
 * IngestedCapabilityStore — Registry for the INGEST stage
 *
 * Stores and retrieves ingested capability entries. Minimal internal store
 * holding an in-memory Map<string, IngestedEntry> keyed by capability id.
 * Supports persistence of IngestionManifest to disk.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import type { CapabilityManifest, IngestionManifest, TrustTier } from './types.js';

/**
 * IngestedEntry combines a CapabilityManifest with provenance metadata
 * added by the INGEST stage. Requires source, trustTier, and ingestionDate.
 */
export interface IngestedEntry extends CapabilityManifest {
  source: string;
  trustTier: TrustTier;
  ingestionDate: string;
}

/**
 * IngestedCapabilityStore manages the INGEST stage's internal registry
 * of ingested capabilities. It holds items in memory and can persist
 * an IngestionManifest to disk.
 */
export class IngestedCapabilityStore {
  private store: Map<string, IngestedEntry> = new Map();

  /**
   * Ingest a list of capability items or a single item, tagging each with provenance metadata.
   * Items without an existing trustTier default to 1 (Suggest).
   *
   * @param items - Single item or array of items to ingest
   * @param provenance - Provenance data (source, version, date)
   */
  async ingest(
    items: (CapabilityManifest & { trustTier?: TrustTier }) | Array<CapabilityManifest & { trustTier?: TrustTier }>,
    provenance: { source: string; version: string; ingestionDate: string }
  ): Promise<void> {
    const itemsArray = Array.isArray(items) ? items : [items];
    for (const item of itemsArray) {
      const entry: IngestedEntry = {
        ...item,
        source: provenance.source,
        trustTier: item.trustTier ?? (1 as TrustTier),
        ingestionDate: provenance.ingestionDate,
      };
      this.store.set(entry.id, entry);
    }
  }

  /**
   * Persist the IngestionManifest to disk.
   * Writes to the provided path (creating parent directories as needed).
   *
   * @param pathOrManifest - File path for output
   */
  async persistManifest(pathOrManifest: string): Promise<void> {
    const items = Array.from(this.store.values());

    // Create parent directory if needed
    const dir = path.dirname(pathOrManifest);
    if (dir && dir !== '.') {
      fs.mkdirSync(dir, { recursive: true });
    }

    // Build the manifest from stored entries
    const manifest = {
      source: items[0]?.source || 'unknown',
      version: '1.0.0',
      ingestionDate: new Date().toISOString(),
      expected: {
        capabilities: 0,
        skills: items.length,
        tools: 0,
        memoryRecords: 0,
      },
      actual: {
        capabilities: 0,
        skills: items.length,
        tools: 0,
        memoryRecords: 0,
      },
      passed: items.length,
      failed: [],
      untested: [],
      rollbackPlan: 'Remove ingested entries from IngestedCapabilityStore for source; re-run DISCOVER to restore previous state.',
    };

    fs.writeFileSync(pathOrManifest, JSON.stringify(manifest, null, 2), 'utf-8');
  }

  /**
   * Get all ingested entries as an array.
   */
  getAll(): IngestedEntry[] {
    return Array.from(this.store.values());
  }

  /**
   * Clear the store. If source is provided, only remove entries from that source.
   *
   * @param source - Optional source to filter by
   */
  clear(source?: string): void {
    if (!source) {
      this.store.clear();
    } else {
      const idsToDelete = Array.from(this.store.entries())
        .filter(([, entry]) => entry.source === source)
        .map(([id]) => id);
      for (const id of idsToDelete) {
        this.store.delete(id);
      }
    }
  }
}
