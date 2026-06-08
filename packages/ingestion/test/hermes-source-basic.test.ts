import { describe, it, expect } from 'vitest';
import { HermesSource } from '../src/sources/hermes-source.js';

describe('HermesSource basic import', () => {
  it('should instantiate with default directory', () => {
    const source = new HermesSource();
    const dir = source.getSkillsDir();
    expect(dir).toBeTruthy();
    expect(dir).toContain('.shay');
  });

  it('should instantiate with custom directory', () => {
    const customDir = '/tmp/test';
    const source = new HermesSource(customDir);
    expect(source.getSkillsDir()).toBe(customDir);
  });
});
