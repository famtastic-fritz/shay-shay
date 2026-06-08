import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  loadConfig,
  getActiveContext,
  ShayConfigError,
} from '../src/config.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '../../../..');
const realConfigPath = path.join(repoRoot, 'shay.config.yaml');

describe('config', () => {
  let tempConfigPath: string;

  beforeEach(() => {
    tempConfigPath = path.join(os.tmpdir(), `shay-config-${Date.now()}.yaml`);
  });

  afterEach(() => {
    if (fs.existsSync(tempConfigPath)) {
      fs.unlinkSync(tempConfigPath);
    }
  });

  it('loadConfig loads and validates valid shay.config.yaml from repo root', () => {
    if (fs.existsSync(realConfigPath)) {
      const config = loadConfig(realConfigPath);

      expect(config).toBeDefined();
      expect(typeof config.version).toBe('string');
      expect(typeof config.name).toBe('string');
    }
  });

  it('loadConfig throws ShayConfigError for missing required fields', () => {
    const yamlContent = `
description: Test config without name
version: 0.1.0
`;
    fs.writeFileSync(tempConfigPath, yamlContent);

    expect(() => {
      loadConfig(tempConfigPath);
    }).toThrow(ShayConfigError);
  });

  it('getActiveContext returns the last loaded config', () => {
    if (fs.existsSync(realConfigPath)) {
      const config1 = loadConfig(realConfigPath);
      const config2 = getActiveContext();

      expect(config2.version).toBe(config1.version);
      expect(config2.name).toBe(config1.name);
    }
  });

  it('getActiveContext throws before any config is loaded', () => {
    if (fs.existsSync(realConfigPath)) {
      const config1 = loadConfig(realConfigPath);
      const context = getActiveContext();
      expect(context).toBeDefined();
      expect(context.name).toBe(config1.name);
    }
  });

  it('loadConfig throws ShayConfigError when config fails JSON schema validation', () => {
    const yamlContent = `version: 123
name: TestApp
`;
    fs.writeFileSync(tempConfigPath, yamlContent);

    expect(() => {
      loadConfig(tempConfigPath);
    }).toThrow(ShayConfigError);
  });
});
