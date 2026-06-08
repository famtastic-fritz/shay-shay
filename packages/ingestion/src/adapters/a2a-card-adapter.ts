import { RawArtifact, CapabilityManifest, SkillRecord } from '../types.js';
import { SkillAdapter } from './adapter.js';

interface A2aAgentCard {
  name: string;
  description?: string;
  version?: string;
  capabilities?: unknown[];
}

function slugify(str: string): string {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export class A2aCardAdapter implements SkillAdapter {
  canHandle(artifact: RawArtifact): boolean {
    return artifact.format === 'a2a-card' || (artifact as any).metadata?.type === 'a2a-card';
  }

  translate(artifact: RawArtifact): CapabilityManifest | SkillRecord {
    let agentCard: A2aAgentCard;
    try {
      agentCard = JSON.parse(artifact.rawContent) as A2aAgentCard;
    } catch {
      throw new Error(`Failed to parse A2A Agent Card JSON from ${artifact.path}`);
    }

    const name = agentCard.name || 'A2A Agent';
    const id = slugify(name);
    const description = agentCard.description || '';
    const version = agentCard.version || '0.1.0';

    return {
      id,
      name,
      version,
      description,
      source: artifact.path,
      trustTier: 1,
      ingestionDate: new Date().toISOString(),
      dependencies: [],
    };
  }
}
