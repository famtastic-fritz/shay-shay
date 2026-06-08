import { RawArtifact, CapabilityManifest, SkillRecord } from '../types.js';
import { SkillAdapter } from './adapter.js';

interface HermesSkillFrontmatter {
  id?: string;
  name?: string;
  version?: string;
  description?: string;
  permissions?: string[];
  tags?: string[];
  entrypoint?: string;
}

function slugify(str: string): string {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function parseHermesFrontmatter(content: string): HermesSkillFrontmatter {
  const lines = content.split('\n');
  const frontmatter: HermesSkillFrontmatter = {};

  if (lines[0].trim() === '---') {
    let idx = 1;
    let currentArrayKey: string | null = null;
    let currentArray: string[] = [];

    while (idx < lines.length && lines[idx].trim() !== '---') {
      const line = lines[idx];
      const trimmed = line.trim();

      // Check if this is an array item (starts with -)
      if (currentArrayKey && trimmed.startsWith('- ')) {
        const item = trimmed.substring(2).trim();
        currentArray.push(item);
      } else if (trimmed.includes(':')) {
        // Save previous array if any
        if (currentArrayKey && currentArray.length > 0) {
          (frontmatter as Record<string, unknown>)[currentArrayKey] = currentArray;
          currentArray = [];
        }
        currentArrayKey = null;

        const colonIdx = trimmed.indexOf(':');
        const key = trimmed.substring(0, colonIdx).trim();
        const value = trimmed.substring(colonIdx + 1).trim();

        if ((key === 'permissions' || key === 'tags') && !value) {
          // Array is on next lines
          currentArrayKey = key;
          currentArray = [];
        } else if (key === 'permissions' || key === 'tags') {
          // Inline array format [a, b, c]
          if (value.startsWith('[') && value.endsWith(']')) {
            const arrayStr = value.slice(1, -1);
            frontmatter[key] = arrayStr
              .split(',')
              .map((item) => item.trim())
              .filter((item) => item.length > 0);
          }
        } else {
          (frontmatter as Record<string, unknown>)[key] = value;
        }
      }
      idx++;
    }

    // Save last array if any
    if (currentArrayKey && currentArray.length > 0) {
      (frontmatter as Record<string, unknown>)[currentArrayKey] = currentArray;
    }
  }

  return frontmatter;
}

export class HermesSkillAdapter implements SkillAdapter {
  canHandle(artifact: RawArtifact): boolean {
    return artifact.format === 'hermes-skill';
  }

  translate(artifact: RawArtifact): CapabilityManifest | SkillRecord {
    const content = artifact.rawContent || (artifact as any).content || '';
    const frontmatter = parseHermesFrontmatter(content);

    let id = frontmatter.id;
    if (!id) {
      const filename = (artifact as any).path ? (artifact as any).path.split('/').pop() : 'skill';
      id = slugify((filename || 'skill').replace(/\.(yml|yaml|txt)$/, ''));
    }

    return {
      id,
      name: frontmatter.name || id,
      version: frontmatter.version || '0.1.0',
      description: frontmatter.description || '',
      source: (artifact as any).path || 'unknown',
      trustTier: 1 as const,
      ingestionDate: new Date().toISOString(),
      permissions: frontmatter.permissions || [],
      dependencies: [],
      tags: frontmatter.tags || [],
      entrypoint: frontmatter.entrypoint,
    } as SkillRecord;
  }
}
