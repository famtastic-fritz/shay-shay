/**
 * HermesSource
 *
 * Discovers and reads skill manifests from a filesystem source (e.g., ~/.shay/skills).
 * Strict read-only: no writes to external directories.
 *
 * Discovers files named SKILL.md (format 'hermes-skill') and CLAUDE.md/AGENTS.md
 * (format 'claude-skill'). Returns empty array if no files found. Throws descriptive
 * error if skillsDir is not readable.
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { RawArtifact } from '../types.js';

export class HermesSource {
  private skillsDir: string;

  constructor(skillsDir?: string) {
    this.skillsDir = skillsDir || path.join(os.homedir(), '.shay', 'skills');
  }

  async discover(): Promise<RawArtifact[]> {
    const artifacts: RawArtifact[] = [];

    // Verify directory is readable
    try {
      fs.accessSync(this.skillsDir, fs.constants.R_OK);
    } catch {
      throw new Error(
        `Skills directory is not readable: ${this.skillsDir}. ` +
          'Verify the path exists and has read permissions.'
      );
    }

    // Walk the skills directory
    try {
      const entries = fs.readdirSync(this.skillsDir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(this.skillsDir, entry.name);

        if (entry.isDirectory()) {
          // Look for SKILL.md in subdirectories
          const skillPath = path.join(fullPath, 'SKILL.md');
          if (fs.existsSync(skillPath)) {
            try {
              const rawContent = fs.readFileSync(skillPath, 'utf-8');
              artifacts.push({
                id: entry.name,
                path: skillPath,
                format: 'hermes-skill',
                rawContent,
              });
            } catch (err) {
              // Skip files that can't be read
              continue;
            }
          }
        } else if (entry.isFile()) {
          // Check for SKILL.md, CLAUDE.md, AGENTS.md at root level
          if (entry.name === 'SKILL.md') {
            try {
              const rawContent = fs.readFileSync(fullPath, 'utf-8');
              artifacts.push({
                id: path.basename(this.skillsDir),
                path: fullPath,
                format: 'hermes-skill',
                rawContent,
              });
            } catch (err) {
              // Skip files that can't be read
              continue;
            }
          } else if (entry.name === 'CLAUDE.md' || entry.name === 'AGENTS.md') {
            try {
              const rawContent = fs.readFileSync(fullPath, 'utf-8');
              artifacts.push({
                id: entry.name.replace('.md', '').toLowerCase(),
                path: fullPath,
                format: 'claude-skill',
                rawContent,
              });
            } catch (err) {
              // Skip files that can't be read
              continue;
            }
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.message.includes('not readable')) {
        throw err;
      }
      // Directory doesn't exist or can't be read — return empty array
      return artifacts;
    }

    return artifacts;
  }

  getSkillsDir(): string {
    return this.skillsDir;
  }
}
