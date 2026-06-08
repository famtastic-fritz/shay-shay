import { RawArtifact, CapabilityManifest, SkillRecord } from '../types.js';

export interface SkillAdapter {
  canHandle(artifact: RawArtifact): boolean;
  translate(artifact: RawArtifact): CapabilityManifest | SkillRecord;
}

export class AdapterRegistry {
  private adapters: SkillAdapter[] = [];

  register(adapter: SkillAdapter): void {
    this.adapters.push(adapter);
  }

  resolve(artifact: RawArtifact): SkillAdapter {
    for (const adapter of this.adapters) {
      if (adapter.canHandle(artifact)) {
        return adapter;
      }
    }
    throw new Error(`No adapter found for artifact format: ${artifact.format}`);
  }
}
