import { RawArtifact, CapabilityManifest, SkillRecord } from '../types.js';
import { SkillAdapter } from './adapter.js';

interface McpToolSchema {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

function slugify(str: string): string {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export class McpToolAdapter implements SkillAdapter {
  canHandle(artifact: RawArtifact): boolean {
    return artifact.format === 'mcp-tool' || (artifact as any).metadata?.type === 'mcp-tool';
  }

  translate(artifact: RawArtifact): CapabilityManifest | SkillRecord {
    let toolSchema: McpToolSchema;
    try {
      toolSchema = JSON.parse(artifact.rawContent) as McpToolSchema;
    } catch {
      throw new Error(`Failed to parse MCP tool JSON from ${artifact.path}`);
    }

    const name = toolSchema.name || 'MCP Tool';
    const id = slugify(name);
    const description = toolSchema.description || '';

    return {
      id,
      name,
      version: '0.1.0',
      description,
      source: artifact.path,
      trustTier: 1,
      ingestionDate: new Date().toISOString(),
      dependencies: [],
    };
  }
}
