/**
 * @shay/bridge — A2A (Agent-to-Agent) protocol support
 *
 * Parses and produces A2A Agent Cards. Maps Agent Cards to CapabilityManifests
 * so that remote agents are addressable through the local CapabilityRegistry.
 */

import type { CapabilityManifest } from '@shay/capabilities';

/**
 * A2A Agent Card — the public identity descriptor for an agent.
 * Mirrors the `shay:agent-card` JSON schema.
 */
export interface AgentCard {
  /** Human-readable agent name. */
  name: string;
  /** Optional description of what the agent does. */
  description?: string;
  /** Semantic version string for this card. */
  version: string;
  /** Capability IDs advertised by this agent. */
  capabilities: string[];
}

/**
 * Parse an Agent Card from a raw JSON value.
 *
 * @throws TypeError if required fields (name, version, capabilities) are missing
 *   or if capabilities is not an array.
 */
export function parseAgentCard(json: unknown): AgentCard {
  if (typeof json !== 'object' || json === null) {
    throw new TypeError('Agent card must be a non-null object');
  }
  const obj = json as Record<string, unknown>;
  if (typeof obj.name !== 'string') throw new TypeError('Agent card missing required string field: name');
  if (typeof obj.version !== 'string') throw new TypeError('Agent card missing required string field: version');
  if (!Array.isArray(obj.capabilities)) throw new TypeError('Agent card missing required array field: capabilities');

  return {
    name: obj.name,
    version: obj.version,
    description: typeof obj.description === 'string' ? obj.description : undefined,
    capabilities: obj.capabilities as string[],
  };
}

/**
 * Convert an Agent Card into a list of CapabilityManifests.
 *
 * Each capability ID on the card becomes a minimal manifest. Callers should
 * register the resulting manifests with source:'external', TrustTier.Suggest.
 */
export function toCapabilityManifests(card: AgentCard): CapabilityManifest[] {
  return card.capabilities.map((capId) => ({
    id: `${card.name}::${capId}`,
    version: card.version,
    name: capId,
    description: `Capability '${capId}' provided by agent '${card.name}'`,
  }));
}

/**
 * Produce an Agent Card from a list of CapabilityManifests.
 *
 * Lets Shay publish her own card so external agents can discover her
 * available capabilities.
 *
 * @param manifests - The list of manifests to advertise.
 * @param agentName - The name to give the produced card.
 * @param agentVersion - The version string for the card.
 */
export function produceAgentCard(
  manifests: CapabilityManifest[],
  agentName: string = 'shay',
  agentVersion: string = '0.1.0'
): AgentCard {
  return {
    name: agentName,
    version: agentVersion,
    description: `Agent card for ${agentName}`,
    capabilities: manifests.map((m) => m.id),
  };
}
