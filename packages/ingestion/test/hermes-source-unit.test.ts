import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { HermesSource } from '../src/sources/hermes-source.js';

describe('HermesSource', () => {
  let testDir: string;

  beforeEach(() => {
    testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-'));
  });

  afterEach(() => {
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true });
    }
  });

  it('should instantiate with custom directory', () => {
    const source = new HermesSource(testDir);
    expect(source.getSkillsDir()).toBe(testDir);
  });

  it('should instantiate with default directory', () => {
    const source = new HermesSource();
    const dir = source.getSkillsDir();
    expect(dir).toContain('.shay');
    expect(dir).toContain('skills');
  });

  it('should discover SKILL.md in root directory', async () => {
    const content = '---\nid: test\n---\n# Content';
    fs.writeFileSync(path.join(testDir, 'SKILL.md'), content);

    const source = new HermesSource(testDir);
    const artifacts = await source.discover();

    expect(artifacts.length).toBe(1);
    expect(artifacts[0].id).toBeTruthy();
    expect(artifacts[0].path).toContain('SKILL.md');
    expect(artifacts[0].format).toBe('hermes-skill');
    expect(artifacts[0].rawContent).toBe(content);
  });

  it('should discover SKILL.md in subdirectories', async () => {
    const subdir = path.join(testDir, 'my-skill');
    fs.mkdirSync(subdir);
    const content = '---\nid: sub\n---\n# Sub';
    fs.writeFileSync(path.join(subdir, 'SKILL.md'), content);

    const source = new HermesSource(testDir);
    const artifacts = await source.discover();

    expect(artifacts.length).toBe(1);
    expect(artifacts[0].id).toBe('my-skill');
    expect(artifacts[0].format).toBe('hermes-skill');
  });

  it('should discover CLAUDE.md as claude-skill', async () => {
    const content = '# Claude skills';
    fs.writeFileSync(path.join(testDir, 'CLAUDE.md'), content);

    const source = new HermesSource(testDir);
    const artifacts = await source.discover();

    expect(artifacts.length).toBe(1);
    expect(artifacts[0].id).toBe('claude');
    expect(artifacts[0].format).toBe('claude-skill');
    expect(artifacts[0].rawContent).toBe(content);
  });

  it('should discover AGENTS.md as claude-skill', async () => {
    const content = '# Agent skills';
    fs.writeFileSync(path.join(testDir, 'AGENTS.md'), content);

    const source = new HermesSource(testDir);
    const artifacts = await source.discover();

    expect(artifacts.length).toBe(1);
    expect(artifacts[0].id).toBe('agents');
    expect(artifacts[0].format).toBe('claude-skill');
  });

  it('should discover mixed file types', async () => {
    fs.writeFileSync(path.join(testDir, 'SKILL.md'), '# Skill');
    fs.writeFileSync(path.join(testDir, 'CLAUDE.md'), '# Claude');
    fs.writeFileSync(path.join(testDir, 'AGENTS.md'), '# Agents');

    const source = new HermesSource(testDir);
    const artifacts = await source.discover();

    expect(artifacts.length).toBe(3);
    const formats = artifacts.map((a) => a.format);
    expect(formats).toContain('hermes-skill');
    expect(formats).toContain('claude-skill');
  });

  it('should return empty array for empty directory', async () => {
    const source = new HermesSource(testDir);
    const artifacts = await source.discover();
    expect(artifacts).toEqual([]);
  });

  it('should throw error if directory not readable', async () => {
    const unreadable = fs.mkdtempSync(path.join(os.tmpdir(), 'unreadable-'));
    try {
      fs.chmodSync(unreadable, 0o000);
      const source = new HermesSource(unreadable);
      await expect(source.discover()).rejects.toThrow('not readable');
    } finally {
      fs.chmodSync(unreadable, 0o755);
      fs.rmSync(unreadable, { recursive: true });
    }
  });

  it('should skip unreadable files gracefully', async () => {
    const skillPath = path.join(testDir, 'SKILL.md');
    fs.writeFileSync(skillPath, '# Content');
    fs.chmodSync(skillPath, 0o000);

    const source = new HermesSource(testDir);
    const artifacts = await source.discover();

    expect(artifacts.length).toBe(0);

    // Restore permissions for cleanup
    fs.chmodSync(skillPath, 0o644);
  });

  it('should ignore files that do not match discovery patterns', async () => {
    fs.writeFileSync(path.join(testDir, 'README.md'), '# Readme');
    fs.writeFileSync(path.join(testDir, 'skill.md'), '# Lowercase');
    fs.writeFileSync(path.join(testDir, 'SKILL.JSON'), '{}');

    const source = new HermesSource(testDir);
    const artifacts = await source.discover();

    expect(artifacts.length).toBe(0);
  });
});
