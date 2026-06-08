import { RawArtifact, CapabilityManifest, SkillRecord } from '../types.js';
import { SkillAdapter } from './adapter.js';

interface ClaudeSkillFrontmatter {
  name?: string;
  description?: string;
  version?: string;
}

function slugify(str: string): string {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function parseClaudeFrontmatter(content: string): ClaudeSkillFrontmatter {
  const lines = content.split('\n');
  const frontmatter: ClaudeSkillFrontmatter = {};

  if (lines[0].trim() === '---') {
    let idx = 1;
    while (idx < lines.length && lines[idx].trim() !== '---') {
      const line = lines[idx];
      if (line.includes(':')) {
        const colonIdx = line.indexOf(':');
        const key = line.substring(0, colonIdx).trim();
        const value = line.substring(colonIdx + 1).trim();
        (frontmatter as Record<string, unknown>)[key] = value;
      }
      idx++;
    }
  }

  return frontmatter;
}

function extractH1AndFirstParagraph(
  content: string
): { heading?: string; paragraph?: string } {
  const lines = content.split('\n');
  let heading: string | undefined;
  let paragraph: string | undefined;
  let inContent = false;

  if (lines[0].trim() === '---') {
    let idx = 1;
    while (idx < lines.length && lines[idx].trim() !== '---') {
      idx++;
    }
    inContent = true;
    idx++;

    for (; idx < lines.length; idx++) {
      const line = lines[idx].trim();
      if (line.startsWith('# ') && !heading) {
        heading = line.substring(2).trim();
      } else if (line && line !== '' && !line.startsWith('#') && !paragraph) {
        paragraph = line;
        break;
      }
    }
  } else {
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('# ') && !heading) {
        heading = trimmed.substring(2).trim();
      } else if (trimmed && trimmed !== '' && !trimmed.startsWith('#') && !paragraph) {
        paragraph = trimmed;
        break;
      }
    }
  }

  return { heading, paragraph };
}

export class ClaudeSkillAdapter implements SkillAdapter {
  canHandle(artifact: RawArtifact): boolean {
    return artifact.format === 'claude-skill' || (artifact as any).metadata?.type === 'claude-skill';
  }

  translate(artifact: RawArtifact): CapabilityManifest | SkillRecord {
    const content = artifact.rawContent || (artifact as any).content || '';
    const frontmatter = parseClaudeFrontmatter(content);
    const { heading, paragraph } = extractH1AndFirstParagraph(content);

    const name = frontmatter.name || heading || 'Claude Skill';
    const id = slugify(name);
    const description = frontmatter.description || paragraph || '';

    return {
      id,
      name,
      version: frontmatter.version || '0.1.0',
      description,
      source: artifact.path,
      trustTier: 1,
      ingestionDate: new Date().toISOString(),
      dependencies: [],
    };
  }
}
