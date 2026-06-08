/**
 * @shay/capabilities — Core types
 *
 * Defines the Capability, CapabilityHandler, and CapabilityRecord shapes
 * used throughout the capability registry.
 */

import type { CapabilityManifest } from '@shay/ingestion';
import { TrustTier } from '@shay/core';

export type { CapabilityManifest };

/**
 * A handler function that executes a named action for a capability.
 * Returns a Promise resolving to an arbitrary result.
 */
export type CapabilityHandler = (
  action: string,
  input: unknown
) => Promise<unknown>;

/**
 * A registered capability — manifest paired with its handler.
 */
export interface Capability {
  manifest: CapabilityManifest;
  handler: CapabilityHandler;
}

/**
 * A full registry record that adds provenance and trust metadata to a Capability.
 */
export interface CapabilityRecord extends Capability {
  source: 'internal' | 'external';
  trustTier: TrustTier;
}
