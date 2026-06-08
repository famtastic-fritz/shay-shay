import fs from 'fs';
import path from 'path';

export interface ShayConfig {
  version: string;
  name: string;
  description?: string;
  paths?: {
    workspace?: string;
    config?: string;
    schemas?: string;
  };
  defaults?: {
    model?: string;
    timeout?: number;
  };
}

export class ShayConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ShayConfigError';
  }
}

function parseYamlLike(content: string): Record<string, any> {
  const lines = content.split('\n');
  const result: Record<string, any> = {};
  let currentKey: string | null = null;
  let currentValue: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    if (line.match(/^[a-zA-Z0-9_]+:/)) {
      if (currentKey && currentValue.length > 0) {
        result[currentKey] = currentValue.join('\n').trim();
      }
      const [key, ...valueParts] = trimmed.split(':');
      currentKey = key.trim();
      const value = valueParts.join(':').trim();
      currentValue = value ? [value] : [];
    } else if (currentKey && line.match(/^\s+/)) {
      currentValue.push(trimmed);
    }
  }

  if (currentKey && currentValue.length > 0) {
    result[currentKey] = currentValue.join('\n').trim();
  }

  return result;
}

export function loadConfig(configPath?: string): ShayConfig {
  const resolvedPath =
    configPath || path.join(process.cwd(), 'shay.config.yaml');

  if (!fs.existsSync(resolvedPath)) {
    throw new ShayConfigError(
      `Config file not found at ${resolvedPath}. ` +
        'Create shay.config.yaml with required keys: version, name.'
    );
  }

  const content = fs.readFileSync(resolvedPath, 'utf-8');
  const parsed = parseYamlLike(content);

  if (!parsed.version || !parsed.name) {
    throw new ShayConfigError(
      'Config must contain required keys: version, name'
    );
  }

  const config: ShayConfig = {
    version: parsed.version || '0.1.0',
    name: parsed.name,
    description: parsed.description,
    paths: parsed.paths ? parseYamlLike(parsed.paths) : undefined,
    defaults: parsed.defaults ? parseYamlLike(parsed.defaults) : undefined,
  };

  return config;
}
