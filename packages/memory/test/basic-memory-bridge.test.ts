import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { BasicMemoryBridge } from '../src/basic-memory-bridge.js';

describe('BasicMemoryBridge', () => {
  let testDir: string;

  beforeEach(() => {
    testDir = fs.mkdtempSync(path.join(process.cwd(), 'shay-test-'));
  });

  afterEach(() => {
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });

  it('read() returns [] when basePath does not exist', async () => {
    const nonExistentPath = path.join(testDir, 'nonexistent');
    const bridge = new BasicMemoryBridge({ basePath: nonExistentPath });

    const results = await bridge.read();

    expect(results).toEqual([]);
  });

  it('read() parses a .md file with valid YAML frontmatter and returns a MemoryRecord with correct fields', async () => {
    const mdContent = `---
tier: T0
importance: 0.9
---
# My Note
This is the body content.`;

    fs.writeFileSync(path.join(testDir, 'test.md'), mdContent);

    const bridge = new BasicMemoryBridge({ basePath: testDir });
    const results = await bridge.read();

    expect(results).toHaveLength(1);
    expect(results[0].content).toContain('# My Note');
    expect(results[0].content).toContain('This is the body content');
    expect(results[0].tier).toBe('T0');
    expect(results[0].importance).toBe(0.9);
  });

  it('read() falls back to defaults (tier="T2", importance=0.5) when frontmatter is absent or incomplete', async () => {
    const mdContent = `# No frontmatter
Just some content without YAML.`;

    fs.writeFileSync(path.join(testDir, 'no-fm.md'), mdContent);

    const bridge = new BasicMemoryBridge({ basePath: testDir });
    const results = await bridge.read();

    expect(results).toHaveLength(1);
    expect(results[0].tier).toBe('T2');
    expect(results[0].importance).toBe(0.5);
  });

  it('read() NEVER calls any write/append/unlink — verify by checking that the temp dir contains only the files placed there before the call', async () => {
    fs.writeFileSync(path.join(testDir, 'file1.md'), '# File 1\nContent 1');
    fs.writeFileSync(path.join(testDir, 'file2.md'), '# File 2\nContent 2');

    const filesBeforeRead = fs.readdirSync(testDir).sort();
    expect(filesBeforeRead).toEqual(['file1.md', 'file2.md']);

    const bridge = new BasicMemoryBridge({ basePath: testDir });
    await bridge.read();

    const filesAfterRead = fs.readdirSync(testDir).sort();
    expect(filesAfterRead).toEqual(['file1.md', 'file2.md']);
  });

  it('read() handles multiple .md files returning one record per file', async () => {
    fs.writeFileSync(path.join(testDir, 'note1.md'), '---\ntier: T1\n---\nNote 1 content');
    fs.writeFileSync(path.join(testDir, 'note2.md'), '---\ntier: T2\n---\nNote 2 content');
    fs.writeFileSync(path.join(testDir, 'note3.md'), 'Note 3 content');

    const bridge = new BasicMemoryBridge({ basePath: testDir });
    const results = await bridge.read();

    expect(results).toHaveLength(3);

    const contents = results.map((r) => r.content);
    expect(contents.some((c) => c.includes('Note 1 content'))).toBe(true);
    expect(contents.some((c) => c.includes('Note 2 content'))).toBe(true);
    expect(contents.some((c) => c.includes('Note 3 content'))).toBe(true);
  });

  it('read() ignores non-.md files', async () => {
    fs.writeFileSync(path.join(testDir, 'valid.md'), 'Valid markdown');
    fs.writeFileSync(path.join(testDir, 'ignored.txt'), 'This should be ignored');
    fs.writeFileSync(path.join(testDir, 'ignored.json'), '{"key": "value"}');

    const bridge = new BasicMemoryBridge({ basePath: testDir });
    const results = await bridge.read();

    expect(results).toHaveLength(1);
    expect(results[0].content).toContain('Valid markdown');
  });

  it('read() handles incomplete frontmatter gracefully', async () => {
    const mdContent = `---
tier: T1
---
Content with partial frontmatter`;

    fs.writeFileSync(path.join(testDir, 'partial.md'), mdContent);

    const bridge = new BasicMemoryBridge({ basePath: testDir });
    const results = await bridge.read();

    expect(results).toHaveLength(1);
    expect(results[0].tier).toBe('T1');
    expect(results[0].importance).toBe(0.5);
  });

  it('read() handles malformed YAML gracefully', async () => {
    const mdContent = `---
this: is: bad: yaml
---
Content after bad YAML`;

    fs.writeFileSync(path.join(testDir, 'badyaml.md'), mdContent);

    const bridge = new BasicMemoryBridge({ basePath: testDir });
    const results = await bridge.read();

    expect(results).toHaveLength(1);
    expect(results[0].tier).toBe('T2');
    expect(results[0].importance).toBe(0.5);
  });
});
