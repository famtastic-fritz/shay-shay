/**
 * @shay/bridge — OASF (Open Agentic Schema Framework) support
 *
 * Bidirectional translation between minimal OASF descriptors and
 * CapabilityManifests. The translation is round-trippable for the
 * fields defined in the `shay:oasf-descriptor` schema.
 */

import type { CapabilityManifest } from '@shay/capabilities';

/**
 * Minimal OASF descriptor.
 * Mirrors the `shay:oasf-descriptor` JSON schema.
 */
export interface OasfDescriptor {
  /** Unique identifier for this capability. */
  id: string;
  /** Semantic version string. */
  version: string;
  /** Human-readable name. */
  name: string;
  /** Detailed description of what the capability provides. */
  description: string;
  /** Optional required permissions. */
  permissions?: string[];
  /** Optional capability IDs this depends on. */
  dependencies?: string[];
  /** Optional path to the main export file. */
  entrypoint?: string;
}

/**
 * Convert an OASF descriptor to a CapabilityManifest.
 *
 * The mapping is 1:1 — all fields are structurally identical between
 * the two types for the MVP schema set.
 */
export function oasfToManifest(descriptor: OasfDescriptor): CapabilityManifest {
  return {
    id: descriptor.id,
    version: descriptor.version,
    name: descriptor.name,
    description: descriptor.description,
    ...(descriptor.permissions !== undefined && { permissions: descriptor.permissions }),
    ...(descriptor.dependencies !== undefined && { dependencies: descriptor.dependencies }),
    ...(descriptor.entrypoint !== undefined && { entrypoint: descriptor.entrypoint }),
  };
}

/**
 * Convert a CapabilityManifest to an OASF descriptor.
 *
 * The mapping is 1:1. Fields that are absent on the manifest are omitted
 * from the descriptor so the round-trip is lossless.
 */
export function manifestToOasf(manifest: CapabilityManifest): OasfDescriptor {
  return {
    id: manifest.id,
    version: manifest.version,
    name: manifest.name,
    description: manifest.description,
    ...(manifest.permissions !== undefined && { permissions: manifest.permissions }),
    ...(manifest.dependencies !== undefined && { dependencies: manifest.dependencies }),
    ...(manifest.entrypoint !== undefined && { entrypoint: manifest.entrypoint }),
  };
}
