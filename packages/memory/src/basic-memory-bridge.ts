import { promises as fs } from 'node:fs';
import { createHash } from 'node:crypto';
import { homedir } from 'node:os';
import { join } from 'node:path';
import type { MemoryRecord, MemoryTier } from './types.js';

/**
 * BasicMemoryBridge — read-only adapter for basic-memory markdown files.
 *
 * Recursively scans a directory for .md files, parses YAML frontmatter,
 * and constructs MemoryRecord objects.
 */
export class BasicMemoryBridge {
  private basePath: string;

  constructor(options?: { basePath?: string }) {
    this.basePath = options?.basePath ?? join(homedir(), 'basic-memory');
  }

  /**
   * Read all .md files from basePath and convert to MemoryRecord array.
   *
   * Returns [] if basePath does not exist.
   */
  async read(): Promise<MemoryRecord[]> {
    try {
      await fs.access(this.basePath);
    } catch {
      // Directory doesn't exist
      return [];
    }

    const records: MemoryRecord[] = [];
    await this.walkDirectory(this.basePath, records);
    return records;
  }

  /**
   * Recursively walk directory and collect .md files.
   */
  private async walkDirectory(
    dirPath: string,
    records: MemoryRecord[]
  ): Promise<void> {
    const entries = await fs.readdir(dirPath, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = join(dirPath, entry.name);

      if (entry.isDirectory()) {
        await this.walkDirectory(fullPath, records);
      } else if (entry.isFile() && entry.name.endsWith('.md')) {
        try {
          const record = await this.parseMarkdownFile(fullPath);
          if (record) {
            records.push(record);
          }
        } catch {
          // Skip files that fail to parse
        }
      }
    }
  }

  /**
   * Parse a single .md file into a MemoryRecord.
   *
   * Extracts YAML frontmatter (between leading --- and second ---).
   * Remaining text is the content body.
   */
  private async parseMarkdownFile(
    filePath: string
  ): Promise<MemoryRecord | null> {
    const content = await fs.readFile(filePath, 'utf-8');

    // Extract frontmatter
    const fm = this.parseYamlFrontmatter(content);
    const body = fm.body;
    const frontmatter = fm.frontmatter;

    if (!body.trim()) {
      return null; // Skip empty files
    }

    // Generate ID from file path if not provided
    const id =
      (typeof frontmatter.id === 'string' ? frontmatter.id : null) ??
      createHash('sha1').update(filePath).digest('hex').slice(0, 12);

    // Get file stats for mtime
    const stats = await fs.stat(filePath);

    // Extract and validate tier
    let tier: MemoryTier = 'T2';
    const tierStr = frontmatter.tier;
    if (typeof tierStr === 'string' && ['T0', 'T1', 'T2', 'T3'].includes(tierStr)) {
      tier = tierStr as MemoryTier;
    }

    return {
      id,
      content: body.trim(),
      tier,
      importance: Number(frontmatter.importance ?? 0.5),
      source: (typeof frontmatter.source === 'string' ? frontmatter.source : null) ?? filePath,
      validityStart:
        (typeof frontmatter.validityStart === 'string' ? frontmatter.validityStart : null) ?? stats.mtime.toISOString(),
      validityEnd: typeof frontmatter.validityEnd === 'string' ? frontmatter.validityEnd : undefined,
      entities: Array.isArray(frontmatter.entities) ? (frontmatter.entities as string[]) : undefined,
    };
  }

  /**
   * Hand-rolled YAML frontmatter parser.
   *
   * Looks for leading --- and second --- delimiters.
   * Returns { frontmatter: { [key: string]: any }, body: string }
   */
  private parseYamlFrontmatter(
    content: string
  ): {
    frontmatter: Record<string, unknown>;
    body: string;
  } {
    const lines = content.split('\n');
    const frontmatter: Record<string, unknown> = {};

    if (lines[0] !== '---') {
      return { frontmatter, body: content };
    }

    let endIndex = -1;
    for (let i = 1; i < lines.length; i++) {
      if (lines[i] === '---') {
        endIndex = i;
        break;
      }
    }

    if (endIndex === -1) {
      return { frontmatter, body: content };
    }

    // Parse YAML key-value pairs
    for (let i = 1; i < endIndex; i++) {
      const line = lines[i];
      const match = line.match(/^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)/);
      if (match) {
        const key = match[1];
        const value = match[2].trim();

        // Simple type conversion
        if (value === 'true') {
          frontmatter[key] = true;
        } else if (value === 'false') {
          frontmatter[key] = false;
        } else if (value.startsWith('[') && value.endsWith(']')) {
          // Parse YAML array (simple case)
          try {
            const arrayStr = value.slice(1, -1);
            frontmatter[key] = arrayStr
              .split(',')
              .map((v) => v.trim().replace(/^["']|["']$/g, ''));
          } catch {
            frontmatter[key] = value;
          }
        } else if (!isNaN(Number(value))) {
          frontmatter[key] = Number(value);
        } else {
          frontmatter[key] = value.replace(/^["']|["']$/g, '');
        }
      }
    }

    const body = lines.slice(endIndex + 1).join('\n');
    return { frontmatter, body };
  }
}
